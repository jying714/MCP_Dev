#!/usr/bin/env python3
import sqlite3
from pathlib import Path

# 1. Locate (or create) the database file under db/
DB_PATH = Path(__file__).parent.parent / "db" / "passive_tree.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# 2. DDL statements – now with is_playable on passive_nodes
DDL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS tree_versions (
  version_id   INTEGER PRIMARY KEY AUTOINCREMENT,
  version_tag  TEXT      UNIQUE,
  fetched_at   DATETIME  NOT NULL,
  source_url   TEXT
);

CREATE TABLE IF NOT EXISTS raw_trees (
  version_id INTEGER PRIMARY KEY
    REFERENCES tree_versions(version_id)
    ON DELETE CASCADE,
  raw_json   TEXT      NOT NULL
);

CREATE TABLE IF NOT EXISTS passive_nodes (
  node_id     INTEGER  NOT NULL,
  version_id  INTEGER  NOT NULL
    REFERENCES tree_versions(version_id)
    ON DELETE CASCADE,
  x           INTEGER  NOT NULL,
  y           INTEGER  NOT NULL,
  node_type   TEXT     NOT NULL,
  name        TEXT,
  description TEXT,
  orbit       INTEGER,
  group_id    INTEGER,
  is_playable INTEGER  NOT NULL DEFAULT 1,
  PRIMARY KEY (node_id, version_id)
);

CREATE TABLE IF NOT EXISTS node_edges (
  from_node_id INTEGER NOT NULL,
  to_node_id   INTEGER NOT NULL,
  version_id   INTEGER NOT NULL
    REFERENCES tree_versions(version_id)
    ON DELETE CASCADE,
  PRIMARY KEY (from_node_id, to_node_id, version_id)
);

CREATE TABLE IF NOT EXISTS node_effects (
  node_id     INTEGER NOT NULL,
  stat_key    TEXT    NOT NULL,
  value       NUMERIC NOT NULL,
  version_id  INTEGER NOT NULL
    REFERENCES tree_versions(version_id)
    ON DELETE CASCADE,
  PRIMARY KEY (node_id, stat_key, version_id)
);

CREATE TABLE IF NOT EXISTS node_errors (
  version_id   INTEGER NOT NULL
    REFERENCES tree_versions(version_id)
    ON DELETE CASCADE,
  node_id      INTEGER NOT NULL,
  error_type   TEXT    NOT NULL,
  raw_value    TEXT,
  PRIMARY KEY (version_id, node_id, error_type)
);

CREATE TABLE IF NOT EXISTS edge_errors (
  version_id   INTEGER NOT NULL
    REFERENCES tree_versions(version_id)
    ON DELETE CASCADE,
  from_node_id INTEGER NOT NULL,
  to_node_id   INTEGER NOT NULL,
  error_type   TEXT    NOT NULL,
  raw_radius   NUMERIC,
  PRIMARY KEY (version_id, from_node_id, to_node_id, error_type)
);

CREATE TABLE IF NOT EXISTS starting_nodes (
  version_id INTEGER NOT NULL
    REFERENCES tree_versions(version_id)
    ON DELETE CASCADE,
  node_id    INTEGER NOT NULL,
  class      TEXT    NOT NULL,
  x          INTEGER NOT NULL,
  y          INTEGER NOT NULL,
  PRIMARY KEY (version_id, node_id)
);
"""

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.executescript(DDL)
    conn.commit()
    conn.close()
    print(f"✅ Schema (with is_playable) created/updated at {DB_PATH}")

if __name__ == "__main__":
    main()
