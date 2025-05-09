#!/usr/bin/env python3
import os
import sqlite3
import glob
from pathlib import Path

# Compute paths
SCRIPT_DIR = Path(__file__).parent
DB_DIR     = SCRIPT_DIR.parent / "db"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH    = DB_DIR / "passive_tree.db"

def run_setup(db_path: str = str(DB_PATH)):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    #
    # ─── PASSIVE & ASCENDANCY SCHEMA ───────────────────────────────────────────────
    #

    # tree_versions & raw_trees
    cur.execute("""
    CREATE TABLE IF NOT EXISTS tree_versions (
      version_id   INTEGER PRIMARY KEY AUTOINCREMENT,
      version_tag  TEXT,
      fetched_at   DATETIME,
      source_url   TEXT
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS raw_trees (
      version_id  INTEGER NOT NULL REFERENCES tree_versions(version_id),
      raw_json    TEXT    NOT NULL,
      PRIMARY KEY(version_id)
    );
    """)

    # passive_nodes
    cur.execute("""
    CREATE TABLE IF NOT EXISTS passive_nodes (
      node_id      INTEGER PRIMARY KEY,
      version_id   INTEGER NOT NULL REFERENCES tree_versions(version_id),
      x            INTEGER,
      y            INTEGER,
      node_type    TEXT,
      name         TEXT,
      description  TEXT,
      orbit        INTEGER,
      group_id     INTEGER,
      is_playable  BOOLEAN,
      FOREIGN KEY(version_id) REFERENCES tree_versions(version_id)
    );
    """)

    # node_edges
    cur.execute("""
    CREATE TABLE IF NOT EXISTS node_edges (
      from_node_id INTEGER NOT NULL REFERENCES passive_nodes(node_id),
      to_node_id   INTEGER NOT NULL REFERENCES passive_nodes(node_id),
      version_id   INTEGER NOT NULL REFERENCES tree_versions(version_id),
      PRIMARY KEY (from_node_id, to_node_id, version_id)
    );
    """)

    # node_effects
    cur.execute("""
    CREATE TABLE IF NOT EXISTS node_effects (
      node_id     INTEGER NOT NULL REFERENCES passive_nodes(node_id),
      stat_key    TEXT    NOT NULL,
      value       REAL,
      version_id  INTEGER NOT NULL REFERENCES tree_versions(version_id),
      PRIMARY KEY (node_id, stat_key, version_id),
      FOREIGN KEY(node_id) REFERENCES passive_nodes(node_id),
      FOREIGN KEY(version_id) REFERENCES tree_versions(version_id)
    );
    """)

    # starting_nodes
    cur.execute("""
    CREATE TABLE IF NOT EXISTS starting_nodes (
      version_id  INTEGER NOT NULL REFERENCES tree_versions(version_id),
      node_id     INTEGER NOT NULL REFERENCES passive_nodes(node_id),
      class       TEXT,
      x           INTEGER,
      y           INTEGER,
      PRIMARY KEY (version_id, node_id, class),
      FOREIGN KEY(node_id) REFERENCES passive_nodes(node_id),
      FOREIGN KEY(version_id) REFERENCES tree_versions(version_id)
    );
    """)

    # ascendancy_versions & raw_ascendancy_snapshots
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ascendancy_versions (
      version_id   INTEGER PRIMARY KEY AUTOINCREMENT,
      snapshot_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS raw_ascendancy_snapshots (
      version_id  INTEGER NOT NULL REFERENCES ascendancy_versions(version_id),
      raw_json    TEXT    NOT NULL,
      PRIMARY KEY(version_id)
    );
    """)

    # ascendancy_nodes
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ascendancy_nodes (
      ascendancy  TEXT   NOT NULL,
      node_id     INTEGER NOT NULL,
      version_id  INTEGER NOT NULL REFERENCES ascendancy_versions(version_id),
      x           REAL,
      y           REAL,
      node_type   TEXT,
      name        TEXT,
      description TEXT,
      PRIMARY KEY (ascendancy, node_id, version_id),
      FOREIGN KEY(version_id) REFERENCES ascendancy_versions(version_id)
    );
    """)

    #
    # ─── ITEM SCHEMA ────────────────────────────────────────────────────────────────
    #

    # item_versions & raw_item_snapshots
    cur.execute("""
    CREATE TABLE IF NOT EXISTS item_versions (
      version_id   INTEGER PRIMARY KEY AUTOINCREMENT,
      version_tag  TEXT,
      fetched_at   DATETIME,
      source       TEXT
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS raw_item_snapshots (
      version_id  INTEGER NOT NULL REFERENCES item_versions(version_id),
      category    TEXT    NOT NULL,
      raw_json    TEXT    NOT NULL,
      PRIMARY KEY(version_id, category)
    );
    """)

    # base_items
    cur.execute("""
    CREATE TABLE IF NOT EXISTS base_items (
      base_name   TEXT NOT NULL,
      version_id  INTEGER NOT NULL REFERENCES item_versions(version_id),
      metadata    TEXT,
      PRIMARY KEY(base_name, version_id),
      FOREIGN KEY(version_id) REFERENCES item_versions(version_id)
    );
    """)

    # unique_items & unique_mods
    cur.execute("""
    CREATE TABLE IF NOT EXISTS unique_items (
      item_name   TEXT NOT NULL,
      base_name   TEXT,
      version_id  INTEGER NOT NULL REFERENCES item_versions(version_id),
      metadata    TEXT,
      PRIMARY KEY(item_name, version_id),
      FOREIGN KEY(version_id) REFERENCES item_versions(version_id)
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS unique_mods (
      item_name   TEXT    NOT NULL,
      version_id  INTEGER NOT NULL REFERENCES item_versions(version_id),
      modifier    TEXT,
      PRIMARY KEY(item_name, version_id, modifier),
      FOREIGN KEY(item_name, version_id) REFERENCES unique_items(item_name, version_id)
    );
    """)

    # gems
    cur.execute("""
    CREATE TABLE IF NOT EXISTS gems (
      gem_name    TEXT NOT NULL,
      version_id  INTEGER NOT NULL REFERENCES item_versions(version_id),
      metadata    TEXT,
      PRIMARY KEY(gem_name, version_id),
      FOREIGN KEY(version_id) REFERENCES item_versions(version_id)
    );
    """)

    # monster_skills
    cur.execute("""
    CREATE TABLE IF NOT EXISTS monster_skills (
      skill_name  TEXT NOT NULL,
      version_id  INTEGER NOT NULL REFERENCES item_versions(version_id),
      metadata    TEXT,
      PRIMARY KEY(skill_name, version_id),
      FOREIGN KEY(version_id) REFERENCES item_versions(version_id)
    );
    """)

    #
    # ─── BOSS SCHEMA ────────────────────────────────────────────────────────────────
    #

    # boss_versions & raw_boss_snapshots
    cur.execute("""
    CREATE TABLE IF NOT EXISTS boss_versions (
      version_id   INTEGER PRIMARY KEY AUTOINCREMENT,
      snapshot_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS raw_boss_snapshots (
      id           INTEGER PRIMARY KEY AUTOINCREMENT,
      version_id   INTEGER NOT NULL REFERENCES boss_versions(version_id),
      raw_json     TEXT    NOT NULL
    );
    """)

    # unmatched_skills
    cur.execute("""
    CREATE TABLE IF NOT EXISTS unmatched_skills (
      version_id  INTEGER NOT NULL REFERENCES boss_versions(version_id),
      skill_key   TEXT    NOT NULL,
      PRIMARY KEY(version_id, skill_key)
    );
    """)

    # bosses
    cur.execute("""
    CREATE TABLE IF NOT EXISTS bosses (
      id           INTEGER PRIMARY KEY AUTOINCREMENT,
      version_id   INTEGER NOT NULL REFERENCES boss_versions(version_id),
      key          TEXT    NOT NULL,
      name         TEXT    NOT NULL,
      tier         INTEGER,
      biome        TEXT,
      description  TEXT,
      armour_mult  INTEGER,
      evasion_mult INTEGER,
      is_uber      BOOLEAN DEFAULT 0,
      UNIQUE(version_id, key),
      FOREIGN KEY(version_id) REFERENCES boss_versions(version_id)
    );
    """)

    # boss_skills
    cur.execute("""
    CREATE TABLE IF NOT EXISTS boss_skills (
      id          INTEGER PRIMARY KEY AUTOINCREMENT,
      boss_id     INTEGER NOT NULL REFERENCES bosses(id),
      skill_key   TEXT    NOT NULL,
      name        TEXT,
      description TEXT,
      cooldown    REAL,
      tags        TEXT,
      FOREIGN KEY(boss_id) REFERENCES bosses(id)
    );
    """)

    # commit baseline schema
    conn.commit()

    #
    # ─── AUTOMATIC MIGRATIONS ─────────────────────────────────────────────────────
    #
    migration_files = sorted(glob.glob(str(SCRIPT_DIR.parent / "migrations" / "*.sql")))
    for mfile in migration_files:
        print(f"Applying migration {Path(mfile).name}…")
        with open(mfile, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
    conn.commit()

    conn.close()
    print(f"✅ Database schema is up to date ({db_path})")

if __name__ == "__main__":
    run_setup()
