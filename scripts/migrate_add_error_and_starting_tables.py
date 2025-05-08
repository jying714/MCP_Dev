#!/usr/bin/env python3
import sqlite3
from pathlib import Path

# Path to your SQLite database
DB_PATH = Path(__file__).parent.parent / "db" / "passive_tree.db"

# DDL for the new tables
MIGRATION_DDL = """
PRAGMA foreign_keys = ON;

-- edge anomaly logging
CREATE TABLE IF NOT EXISTS edge_errors (
  version_id    INTEGER NOT NULL
    REFERENCES tree_versions(version_id) ON DELETE CASCADE,
  from_node_id  INTEGER NOT NULL,
  to_node_id    INTEGER NOT NULL,
  error_type    TEXT      NOT NULL,  -- 'self_loop' | 'outlier_radius'
  raw_radius    INTEGER,
  PRIMARY KEY (version_id, from_node_id, to_node_id, error_type)
);

-- node lookup misses
CREATE TABLE IF NOT EXISTS node_errors (
  version_id   INTEGER NOT NULL
    REFERENCES tree_versions(version_id) ON DELETE CASCADE,
  node_id      INTEGER NOT NULL,
  error_type   TEXT      NOT NULL,  -- 'missing_skill' | 'missing_group'
  raw_value    TEXT,
  PRIMARY KEY (version_id, node_id, error_type)
);

-- AI-friendly starting node lookup
CREATE TABLE IF NOT EXISTS starting_nodes (
  version_id   INTEGER NOT NULL
    REFERENCES tree_versions(version_id) ON DELETE CASCADE,
  node_id      INTEGER NOT NULL,
  class        TEXT      NOT NULL,  -- e.g. 'Warrior','Witch', etc.
  x            INTEGER   NOT NULL,
  y            INTEGER   NOT NULL,
  PRIMARY KEY (version_id, node_id)
);
"""

def main():
    if not DB_PATH.exists():
        print(f"❌ Database not found at {DB_PATH}. Run setup_db.py first.")
        return

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(MIGRATION_DDL)
        conn.commit()
        print("✅ Migration applied: edge_errors, node_errors, and starting_nodes tables created.")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
