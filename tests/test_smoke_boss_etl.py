import sqlite3
import json
from pathlib import Path
import pytest

class TestSmokeBossETL:
    @classmethod
    def setup_class(cls):
        # Set up paths and load raw JSON fixtures
        project_root = Path(__file__).parent.parent
        cls.db_path = project_root / "db" / "passive_tree.db"
        cls.bosses_json_path = project_root / "data" / "bosses.json"
        cls.boss_skills_json_path = project_root / "data" / "boss_skills.json"

        # Load JSON data
        with open(cls.bosses_json_path, 'r', encoding='utf-8') as f:
            cls.bosses_raw = json.load(f)
        with open(cls.boss_skills_json_path, 'r', encoding='utf-8') as f:
            cls.boss_skills_raw = json.load(f)

        # Open DB connection and determine latest version
        cls.conn = sqlite3.connect(str(cls.db_path))
        cur = cls.conn.execute("SELECT MAX(version_id) FROM boss_versions")
        result = cur.fetchone()
        assert result and result[0] is not None, "boss_versions table is empty"
        cls.version_id = result[0]

    @classmethod
    def teardown_class(cls):
        cls.conn.close()

    def test_raw_snapshots_count(self):
        # Expect two raw snapshots: bosses and boss_skills
        cur = self.conn.execute(
            "SELECT COUNT(*) FROM raw_boss_snapshots WHERE version_id = ?",
            (self.version_id,)
        )
        count = cur.fetchone()[0]
        assert count == 2, f"Expected 2 raw snapshots, got {count}"

    def test_bosses_count(self):
        # Number of bosses loaded should match JSON
        expected = len(self.bosses_raw)
        cur = self.conn.execute(
            "SELECT COUNT(*) FROM bosses WHERE version_id = ?",
            (self.version_id,)
        )
        count = cur.fetchone()[0]
        assert count == expected, f"Expected {expected} bosses, got {count}"

    def test_boss_skills_loaded(self):
        # There should be at least one boss skill loaded
        cur = self.conn.execute(
            "SELECT COUNT(*) FROM boss_skills WHERE boss_id IN (SELECT id FROM bosses WHERE version_id = ?)",
            (self.version_id,)
        )
        count = cur.fetchone()[0]
        assert count > 0, "Expected at least one boss skill to be loaded"

    def test_unmatched_skills_recorded(self):
        # Cortex Ground Degen should be recorded as unmatched
        cur = self.conn.execute(
            "SELECT skill_key FROM unmatched_skills WHERE version_id = ?",
            (self.version_id,)
        )
        unmatched = {row[0] for row in cur.fetchall()}
        assert "Cortex Ground Degen" in unmatched, f"Expected 'Cortex Ground Degen' in unmatched_skills, got {unmatched}"

    def test_override_skills_mapped(self):
        # Ensure override skills are not in unmatched and are present in boss_skills
        for skill in ["Eater Beam", "Exarch Ball"]:
            cur_unmatched = self.conn.execute(
                "SELECT 1 FROM unmatched_skills WHERE version_id = ? AND skill_key = ?",
                (self.version_id, skill)
            )
            assert cur_unmatched.fetchone() is None, f"Override skill '{skill}' should not be in unmatched_skills"

            cur_skill = self.conn.execute(
                "SELECT 1 FROM boss_skills WHERE skill_key = ? AND boss_id IN (SELECT id FROM bosses WHERE version_id = ?)",
                (skill, self.version_id)
            )
            assert cur_skill.fetchone() is not None, f"Override skill '{skill}' should be loaded into boss_skills"

    # New tests for normalized schema
    def test_core_table_count(self):
        # Core table should match legacy count
        legacy = self.conn.execute(
            "SELECT COUNT(*) FROM boss_skills WHERE boss_id IN (SELECT id FROM bosses WHERE version_id = ?)",
            (self.version_id,)
        ).fetchone()[0]
        core = self.conn.execute(
            "SELECT COUNT(*) FROM boss_skills_core WHERE boss_id IN (SELECT id FROM bosses WHERE version_id = ?)",
            (self.version_id,)
        ).fetchone()[0]
        assert core == legacy, f"Expected boss_skills_core count {legacy}, got {core}"

    def test_sample_multiplier_entry(self):
        # For Atziri Flameblast, multiplier table has correct Fire entry
        # Find skill_id
        skill_id = self.conn.execute("""
            SELECT c.id
              FROM boss_skills_core c
              JOIN bosses b ON c.boss_id = b.id
             WHERE b.version_id = ? AND c.skill_key = ?
        """, (self.version_id, "Atziri Flameblast")).fetchone()[0]
        # JSON value
        expected_base, expected_ratio = self.boss_skills_raw["Atziri Flameblast"]["DamageMultipliers"]["Fire"]
        row = self.conn.execute("""
            SELECT base_value, ratio_value
              FROM boss_skill_multipliers
             WHERE skill_id = ? AND damage_type = 'Fire'
        """, (skill_id,)).fetchone()
        assert row is not None, "Multiplier row for Fire missing"
        base, ratio = row
        assert abs(base - expected_base) < 1e-6 and abs(ratio - expected_ratio) < 1e-6, \
            f"Expected Fire multiplier ({expected_base}, {expected_ratio}), got ({base}, {ratio})"

    def test_penetration_values(self):
        # For Atziri Flameblast, base_pen=8 and uber_pen=10
        skill_id = self.conn.execute("""
            SELECT id FROM boss_skills_core
             WHERE boss_id IN (SELECT id FROM bosses WHERE version_id = ?)
               AND skill_key = ?
        """, (self.version_id, "Atziri Flameblast")).fetchone()[0]
        row = self.conn.execute("""
            SELECT base_pen, uber_pen
              FROM boss_skill_penetrations
             WHERE skill_id = ? AND pen_type = 'FirePen'
        """, (skill_id,)).fetchone()
        assert row == (8, 10), f"Expected FirePen (8,10), got {row}"

    def test_additional_stats_flag(self):
        # For Shaper Slam in uber phase, CannotBeBlocked should be a flag
        skill_id = self.conn.execute("""
            SELECT id FROM boss_skills_core
             WHERE skill_key = ? AND boss_id IN (SELECT id FROM bosses WHERE version_id = ?)
        """, ("Shaper Slam", self.version_id)).fetchone()[0]
        row = self.conn.execute("""
            SELECT stat_value, is_flag
              FROM boss_skill_additional_stats
             WHERE skill_id = ? AND phase = 'uber' AND stat_key = 'CannotBeBlocked'
        """, (skill_id,)).fetchone()
        assert row == (None, 1), f"Expected unable-to-block flag (None,1), got {row}"
