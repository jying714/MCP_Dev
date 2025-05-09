#!/usr/bin/env python3
import sqlite3
from pathlib import Path

# 1. Locate (or create) the database file under db/
DB_PATH = Path(__file__).parent.parent / "db" / "passive_tree.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# 2. DDL statements
DDL = """
PRAGMA foreign_keys = OFF;

-- Drop existing tables so schema upgrades take effect cleanly
DROP TABLE IF EXISTS ascendancy_nodes;
DROP TABLE IF EXISTS raw_ascendancy_snapshots;
DROP TABLE IF EXISTS ascendancy_versions;

DROP TABLE IF EXISTS monster_skills;
DROP TABLE IF EXISTS gems;
DROP TABLE IF EXISTS unique_mods;
DROP TABLE IF EXISTS unique_items;
DROP TABLE IF EXISTS base_items;
DROP TABLE IF EXISTS raw_item_snapshots;
DROP TABLE IF EXISTS item_versions;

DROP TABLE IF EXISTS starting_nodes;
DROP TABLE IF EXISTS edge_errors;
DROP TABLE IF EXISTS node_errors;
DROP TABLE IF EXISTS node_effects;
DROP TABLE IF EXISTS node_edges;
DROP TABLE IF EXISTS passive_nodes;
DROP TABLE IF EXISTS raw_trees;
DROP TABLE IF EXISTS tree_versions;

PRAGMA foreign_keys = ON;

-- Passive‑tree versioning
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

-- Item‑ETL versioning
CREATE TABLE IF NOT EXISTS item_versions (
  version_id   INTEGER PRIMARY KEY AUTOINCREMENT,
  version_tag  TEXT      UNIQUE,
  fetched_at   DATETIME  NOT NULL,
  source       TEXT
);

CREATE TABLE IF NOT EXISTS raw_item_snapshots (
  version_id INTEGER NOT NULL
    REFERENCES item_versions(version_id)
    ON DELETE CASCADE,
  category   TEXT      NOT NULL,
  raw_json   TEXT      NOT NULL,
  PRIMARY KEY (version_id, category)
);

CREATE TABLE IF NOT EXISTS base_items (
  base_name  TEXT    NOT NULL,
  version_id INTEGER NOT NULL
    REFERENCES item_versions(version_id)
    ON DELETE CASCADE,
  metadata   TEXT,
  PRIMARY KEY (base_name, version_id)
);

CREATE TABLE IF NOT EXISTS unique_items (
  item_name  TEXT    NOT NULL,
  base_name  TEXT,
  version_id INTEGER NOT NULL
    REFERENCES item_versions(version_id)
    ON DELETE CASCADE,
  metadata   TEXT,
  PRIMARY KEY (item_name, version_id)
);

CREATE TABLE IF NOT EXISTS unique_mods (
  item_name  TEXT    NOT NULL,
  version_id INTEGER NOT NULL
    REFERENCES item_versions(version_id)
    ON DELETE CASCADE,
  modifier   TEXT,
  PRIMARY KEY (item_name, modifier, version_id)
);

CREATE TABLE IF NOT EXISTS gems (
  gem_name   TEXT    NOT NULL,
  version_id INTEGER NOT NULL
    REFERENCES item_versions(version_id)
    ON DELETE CASCADE,
  metadata   TEXT,
  PRIMARY KEY (gem_name, version_id)
);

CREATE TABLE IF NOT EXISTS monster_skills (
  skill_name TEXT    NOT NULL,
  version_id INTEGER NOT NULL
    REFERENCES item_versions(version_id)
    ON DELETE CASCADE,
  metadata   TEXT,
  PRIMARY KEY (skill_name, version_id)
);

-- Ascendancy versioning & data
CREATE TABLE IF NOT EXISTS ascendancy_versions (
  version_id   INTEGER PRIMARY KEY AUTOINCREMENT,
  version_tag  TEXT      UNIQUE,
  fetched_at   DATETIME  NOT NULL,
  source       TEXT
);

CREATE TABLE IF NOT EXISTS raw_ascendancy_snapshots (
  version_id INTEGER PRIMARY KEY
    REFERENCES ascendancy_versions(version_id)
    ON DELETE CASCADE,
  raw_json   TEXT      NOT NULL
);

CREATE TABLE IF NOT EXISTS ascendancy_nodes (
  ascendancy TEXT    NOT NULL,
  node_id    INTEGER NOT NULL,
  version_id INTEGER NOT NULL
    REFERENCES ascendancy_versions(version_id)
    ON DELETE CASCADE,
  x          INTEGER,
  y          INTEGER,
  node_type  TEXT,
  name       TEXT,
  description TEXT,
  PRIMARY KEY (ascendancy, node_id, version_id)
);

PRAGMA foreign_keys = ON;
"""

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.executescript(DDL)
    conn.commit()
    conn.close()
    print(f"✅ Schema created (or updated) in {DB_PATH}")

if __name__ == "__main__":
    main()
