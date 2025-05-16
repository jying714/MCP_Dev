import os
import sqlite3
import json
import subprocess
import pytest
from pathlib import Path

@pytest.fixture(scope="session", autouse=True)
def rebuild_etl(tmp_path_factory):
    project_root = Path(__file__).parent.parent
    db_path = project_root / "db" / "passive_tree.db"

    # 1) Delete any old database
    if db_path.exists():
        db_path.unlink()

    # 2) Rebuild schema
    subprocess.run(
        ["python", "scripts/setup_db.py"],
        cwd=str(project_root),
        check=True
    )

    # 3) Run the tree ETL
    subprocess.run(
        ["python", "scripts/tree_etl.py", "run", "--poe-version", "401"],
        cwd=str(project_root),
        check=True
    )

    # 4) Fetch & parse stats
    subprocess.run(
        ["python", "scripts/fetch_stats.py"],
        cwd=str(project_root),
        check=True
    )
    subprocess.run(
        ["python", "scripts/parse_stats.py"],
        cwd=str(project_root),
        check=True
    )

    yield

class TestSmokeETL:
    @pytest.fixture(autouse=True)
    def _connect(self):
        project_root = Path(__file__).parent.parent
        self.db_path = project_root / "db" / "passive_tree.db"
        self.data_path = project_root / "data" / "tree401.json"
        with open(self.data_path, 'r', encoding='utf-8') as f:
            self.raw = json.load(f)
        self.conn = sqlite3.connect(self.db_path)
        cur = self.conn.execute("SELECT MAX(version_id) FROM tree_versions")
        self.version_id = cur.fetchone()[0]
        yield
        self.conn.close()

    def test_node_count(self):
        expected = len(self.raw["passive_tree"]["nodes"])
        cur = self.conn.execute(
            "SELECT COUNT(*) FROM passive_nodes WHERE version_id = ?", (self.version_id,)
        )
        assert cur.fetchone()[0] == expected

    def test_node_types(self):
        cur = self.conn.execute(
            "SELECT COUNT(*) FROM passive_nodes WHERE version_id = ? AND node_type IS NOT NULL",
            (self.version_id,)
        )
        count_with_type = cur.fetchone()[0]
        total = len(self.raw["passive_tree"]["nodes"])
        assert count_with_type == total

    def test_edge_count(self):
        raw = sum(len(n.get("connections", []))
                  for n in self.raw["passive_tree"]["nodes"].values())
        self_loops = sum(
            1
            for nid_str, n in self.raw["passive_tree"]["nodes"].items()
            for c in n.get("connections", [])
            if int(c.get("id") if isinstance(c, dict) else c) == int(nid_str)
        )
        expected = raw * 2 - self_loops
        cur = self.conn.execute(
            "SELECT COUNT(*) FROM node_edges WHERE version_id = ?", (self.version_id,)
        )
        assert cur.fetchone()[0] == expected

    def test_effect_count(self):
        json_effects = sum(
            len(self.raw["passive_skills"].get(n.get("skill_id"), {}).get("stats", []))
            for n in self.raw["passive_tree"]["nodes"].values()
        )
        cur = self.conn.execute(
            "SELECT COUNT(*) FROM node_effects WHERE version_id = ?", (self.version_id,)
        )
        assert cur.fetchone()[0] == json_effects

    def test_sample_node_effects(self):
        sample = next(iter(self.raw["passive_tree"]["nodes"]))
        node = self.raw["passive_tree"]["nodes"][sample]
        stats = self.raw["passive_skills"].get(node["skill_id"], {}).get("stats", [])
        expected_keys = sorted(
            s.get("statKey", s.get("key")) if isinstance(s, dict) else s
            for s in stats
        )
        cur = self.conn.execute(
            "SELECT stat_key FROM node_effects WHERE version_id = ? AND node_id = ? ORDER BY stat_key",
            (self.version_id, int(sample))
        )
        assert [r[0] for r in cur.fetchall()] == expected_keys

    def test_playable_flag(self):
        cur = self.conn.execute(
            "SELECT COUNT(*) FROM passive_nodes WHERE version_id = ? AND is_playable IN (0,1)",
            (self.version_id,)
        )
        valid = cur.fetchone()[0]
        cur = self.conn.execute(
            "SELECT COUNT(*) FROM passive_nodes WHERE version_id = ?", (self.version_id,)
        )
        total = cur.fetchone()[0]
        assert valid == total
