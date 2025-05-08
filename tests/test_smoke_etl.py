import unittest
import json
import sqlite3
from pathlib import Path

class SmokeETLTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Locate project files
        root = Path(__file__).parent.parent
        cls.data_file = root / "data" / "tree401.json"
        cls.db_file   = root / "db"   / "passive_tree.db"

        # Load JSON
        with cls.data_file.open("r", encoding="utf-8") as f:
            cls.raw = json.load(f)

        # Open DB connection
        cls.conn = sqlite3.connect(str(cls.db_file))
        cls.conn.row_factory = lambda cursor, row: row

        # Find the latest version_id
        cur = cls.conn.execute("SELECT MAX(version_id) FROM tree_versions")
        cls.version_id = cur.fetchone()[0]

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    def test_node_count(self):
        """Ensure we loaded exactly as many nodes as in the JSON."""
        json_count = len(self.raw["passive_tree"]["nodes"])
        cur = self.conn.execute(
            "SELECT COUNT(*) FROM passive_nodes WHERE version_id = ?",
            (self.version_id,)
        )
        db_count = cur.fetchone()[0]
        self.assertEqual(
            db_count,
            json_count,
            f"DB has {db_count} nodes, but JSON has {json_count}"
        )

    def test_sample_node_effects(self):
        """Pick one node from the JSON and verify its stat effects match."""
        # Select a sample node ID from the JSON
        sample_id = int(next(iter(self.raw["passive_tree"]["nodes"])))
        json_stats = self.raw["passive_tree"]["nodes"][str(sample_id)].get("stats", [])
        json_keys = sorted(stat.get("statKey") or stat.get("key") for stat in json_stats)

        cur = self.conn.execute(
            """
            SELECT stat_key
            FROM node_effects
            WHERE version_id = ?
              AND node_id = ?
            ORDER BY stat_key
            """,
            (self.version_id, sample_id)
        )
        db_keys = sorted(row[0] for row in cur.fetchall())

        self.assertListEqual(
            db_keys,
            json_keys,
            f"Effects for node {sample_id} do not match JSON"
        )

    def test_edge_count(self):
        json_edges = sum(len(n.get("connections", []))
                         for n in self.raw["passive_tree"]["nodes"].values())
        cur = self.conn.execute(
            "SELECT COUNT(*) FROM node_edges WHERE version_id = ?",
            (self.version_id,)
        )
        db_edges = cur.fetchone()[0]
        self.assertEqual(db_edges, json_edges)

    def test_effect_count(self):
        skills = self.raw["passive_skills"]
        json_eff = sum(len(skills.get(n.get("skill_id"), {}).get("stats", []))
                       for n in self.raw["passive_tree"]["nodes"].values())
        cur = self.conn.execute(
            "SELECT COUNT(*) FROM node_effects WHERE version_id = ?",
            (self.version_id,)
        )
        db_eff = cur.fetchone()[0]
        self.assertEqual(db_eff, json_eff)

    def test_node_types(self):
        cur = self.conn.execute(
            "SELECT COUNT(*) FROM passive_nodes WHERE version_id = ? AND (node_type IS NULL OR node_type = '')",
            (self.version_id,)
        )
        missing = cur.fetchone()[0]
        self.assertEqual(missing, 0, f"{missing} nodes missing node_type")


if __name__ == "__main__":
    unittest.main()
