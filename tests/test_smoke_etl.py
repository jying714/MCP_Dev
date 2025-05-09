import unittest
import sqlite3
import json
from pathlib import Path

class SmokeETLTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Locate project root and set paths
        project_root = Path(__file__).parent.parent
        cls.db_path = project_root / "db" / "passive_tree.db"
        cls.data_path = project_root / "data" / "tree401.json"

        # Load raw JSON
        with open(cls.data_path, 'r', encoding='utf-8') as f:
            cls.raw = json.load(f)

        # Open DB connection
        cls.conn = sqlite3.connect(cls.db_path)

        # Retrieve the latest version_id
        cur = cls.conn.execute("SELECT MAX(version_id) FROM tree_versions")
        cls.version_id = cur.fetchone()[0]

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    def test_node_count(self):
        # Number of nodes should match JSON
        json_count = len(self.raw["passive_tree"]["nodes"])
        cur = self.conn.execute(
            "SELECT COUNT(*) FROM passive_nodes WHERE version_id = ?", (self.version_id,)
        )
        db_count = cur.fetchone()[0]
        self.assertEqual(
            db_count, json_count,
            f"Expected {json_count} nodes, got {db_count}"
        )

    def test_node_types(self):
        # All nodes should have a non-null node_type
        cur = self.conn.execute(
            "SELECT COUNT(*) FROM passive_nodes WHERE version_id = ? AND node_type IS NOT NULL",
            (self.version_id,)
        )
        count_with_type = cur.fetchone()[0]
        total = len(self.raw["passive_tree"]["nodes"])
        missing = total - count_with_type
        self.assertEqual(
            missing, 0,
            f"{missing} nodes missing node_type"
        )

    def test_edge_count(self):
        # Raw directed edges in JSON
        raw = sum(
            len(n.get("connections", []))
            for n in self.raw["passive_tree"]["nodes"].values()
        )
        # Count self-loop connections in raw JSON
        self_loops = sum(
            1 for nid_str, n in self.raw["passive_tree"]["nodes"].items()
            for c in n.get("connections", [])
            if int(c.get("id") if isinstance(c, dict) else c) == int(nid_str)
        )
        # Expected edges = raw edges + mirrored edges, except self-loops not mirrored
        expected = raw * 2 - self_loops
        cur = self.conn.execute(
            "SELECT COUNT(*) FROM node_edges WHERE version_id = ?", (self.version_id,)
        )
        db_edges = cur.fetchone()[0]
        self.assertEqual(
            db_edges, expected,
            f"Expected {expected} edges (raw+mirrored-self_loops), got {db_edges}"
        )

    def test_effect_count(self):
        # Sum of all stat entries for each node's skill in the tree
        json_effects = sum(
            len(self.raw["passive_skills"].get(n.get("skill_id"), {}).get("stats", []))
            for n in self.raw["passive_tree"]["nodes"].values()
        )
        cur = self.conn.execute(
            "SELECT COUNT(*) FROM node_effects WHERE version_id = ?", (self.version_id,)
        )
        db_effects = cur.fetchone()[0]
        self.assertEqual(
            db_effects, json_effects,
            f"Expected {json_effects} effects loaded, got {db_effects}"
        )

    def test_sample_node_effects(self):
        # Choose a sample node from passive_tree and its skill
        sample_nid_str = next(iter(self.raw["passive_tree"]["nodes"]))
        sample_node = self.raw["passive_tree"]["nodes"][sample_nid_str]
        sample_skill_id = sample_node.get("skill_id")
        sample_skill = self.raw["passive_skills"].get(sample_skill_id, {})
        skill_idx = int(sample_nid_str)
        json_stats = sample_skill.get("stats", [])
        stat_keys = []
        for stat in json_stats:
            if isinstance(stat, dict):
                stat_keys.append(stat.get("statKey") or stat.get("key"))
            else:
                stat_keys.append(stat)
        json_keys = sorted(stat_keys)

        cur = self.conn.execute(
            """
            SELECT stat_key FROM node_effects
             WHERE version_id = ? AND node_id = ?
             ORDER BY stat_key
            """,
            (self.version_id, skill_idx)
        )
        db_keys = sorted(row[0] for row in cur.fetchall())
        self.assertListEqual(
            db_keys, json_keys,
            f"Effects for node {sample_nid_str} ({sample_skill_id}) do not match JSON"
        )

    def test_playable_flag(self):
        # Ensure every node is either playable (1) or placeholder (0)
        cur = self.conn.execute(
            "SELECT COUNT(*) FROM passive_nodes WHERE version_id = ? AND is_playable IN (0,1)",
            (self.version_id,)
        )
        valid = cur.fetchone()[0]

        cur = self.conn.execute(
            "SELECT COUNT(*) FROM passive_nodes WHERE version_id = ?",
            (self.version_id,)
        )
        total = cur.fetchone()[0]

        self.assertEqual(valid, total, "Every node must have is_playable = 0 or 1")


if __name__ == '__main__':
    unittest.main()
