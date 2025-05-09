import json
import sqlite3
import pytest
from pathlib import Path

class SmokeItemsETLTest:
    @classmethod
    def setup_class(cls):
        root = Path(__file__).parent.parent
        cls.db_path   = root / "db"   / "passive_tree.db"
        cls.data_dir  = root / "data" / "pob"

        # load JSON snapshots
        cls.bases   = json.loads((cls.data_dir / "bases.json").read_text(encoding="utf-8"))
        cls.uniques = json.loads((cls.data_dir / "uniques.json").read_text(encoding="utf-8"))
        cls.gems    = json.loads((cls.data_dir / "gems.json").read_text(encoding="utf-8"))
        cls.skills  = json.loads((cls.data_dir / "skills.json").read_text(encoding="utf-8"))

        cls.conn = sqlite3.connect(cls.db_path)
        # grab latest item_version
        cur = cls.conn.execute("SELECT MAX(id) FROM item_versions")
        cls.version_id = cur.fetchone()[0]

    @classmethod
    def teardown_class(cls):
        cls.conn.close()

    def assertCount(self, table, expected):
        cur = self.conn.execute(f"SELECT COUNT(*) FROM {table} WHERE version_id = ?", (self.version_id,))
        actual = cur.fetchone()[0]
        assert actual == expected, f"{table}: expected {expected} rows for version {self.version_id}, got {actual}"

    def test_base_items_count(self):
        self.assertCount("base_items", len(self.bases))

    def test_unique_items_count(self):
        self.assertCount("unique_items", len(self.uniques))

    def test_gems_count(self):
        self.assertCount("gems", len(self.gems))

    def test_monster_skills_count(self):
        self.assertCount("monster_skills", len(self.skills))

    def test_raw_snapshot_count(self):
        # we should have exactly four raw snapshots loaded
        cur = self.conn.execute(
            "SELECT COUNT(*) FROM raw_item_snapshots WHERE version_id = ?",
            (self.version_id,)
        )
        count = cur.fetchone()[0]
        assert count == 4, f"raw_item_snapshots: expected 4 categories, got {count}"

    def test_unique_modifiers_count(self):
        # total distinct modifiers across all JSON uniques
        distinct_mods = {m for u in self.uniques for m in u.get("modifiers", [])}
        cur = self.conn.execute(
            "SELECT COUNT(DISTINCT modifier) FROM unique_mods WHERE version_id = ?",
            (self.version_id,)
        )
        db_mods = cur.fetchone()[0]
        assert db_mods == len(distinct_mods), f"unique_mods: expected {len(distinct_mods)}, got {db_mods}"
