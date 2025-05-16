#!/usr/bin/env python3
import os
import sqlite3
import glob
import logging
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
DB_DIR     = SCRIPT_DIR.parent / "db"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH    = DB_DIR / "passive_tree.db"

# ── Logging Setup ────────────────────────────────────────────────────────────
LOG = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def run_setup(db_path: str = str(DB_PATH)):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # ── BASE SCHEMA CREATION ──────────────────────────────────────────────────

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
    cur.execute("""
    CREATE TABLE IF NOT EXISTS passive_nodes (
      node_id      INTEGER,
      version_id   INTEGER NOT NULL REFERENCES tree_versions(version_id),
      x            INTEGER,
      y            INTEGER,
      node_type    TEXT,
      name         TEXT,
      description  TEXT,
      orbit        INTEGER,
      group_id     INTEGER,
      is_playable  BOOLEAN,
      PRIMARY KEY(node_id, version_id)
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS node_edges (
      from_node_id INTEGER NOT NULL,
      to_node_id   INTEGER NOT NULL,
      version_id   INTEGER NOT NULL REFERENCES tree_versions(version_id),
      PRIMARY KEY (from_node_id, to_node_id, version_id)
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS node_errors (
      version_id  INTEGER NOT NULL REFERENCES tree_versions(version_id),
      node_id     INTEGER NOT NULL,
      error_type  TEXT    NOT NULL,
      raw_value   TEXT,
      PRIMARY KEY (version_id, node_id, error_type, raw_value)
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS edge_errors (
      version_id     INTEGER NOT NULL REFERENCES tree_versions(version_id),
      from_node_id   INTEGER NOT NULL,
      to_node_id     INTEGER NOT NULL,
      error_type     TEXT    NOT NULL,
      raw_radius     TEXT,
      PRIMARY KEY (version_id, from_node_id, to_node_id, error_type, raw_radius)
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS node_effects (
      node_id     INTEGER NOT NULL REFERENCES passive_nodes(node_id),
      stat_key    TEXT    NOT NULL,
      value       REAL,
      version_id  INTEGER NOT NULL REFERENCES tree_versions(version_id),
      PRIMARY KEY (node_id, stat_key, version_id)
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS starting_nodes (
      version_id  INTEGER NOT NULL REFERENCES tree_versions(version_id),
      node_id     INTEGER NOT NULL REFERENCES passive_nodes(node_id),
      class       TEXT,
      x           INTEGER,
      y           INTEGER,
      PRIMARY KEY (version_id, node_id, class)
    );
    """)
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
      PRIMARY KEY (ascendancy, node_id, version_id)
    );
    """)
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
    cur.execute("""
    CREATE TABLE IF NOT EXISTS base_items (
      base_name   TEXT NOT NULL,
      version_id  INTEGER NOT NULL REFERENCES item_versions(version_id),
      metadata    TEXT,
      PRIMARY KEY(base_name, version_id)
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS unique_items (
      item_name   TEXT NOT NULL,
      base_name   TEXT,
      version_id  INTEGER NOT NULL REFERENCES item_versions(version_id),
      metadata    TEXT,
      PRIMARY KEY(item_name, version_id)
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS unique_mods (
      item_name   TEXT    NOT NULL,
      version_id  INTEGER NOT NULL REFERENCES item_versions(version_id),
      modifier    TEXT,
      PRIMARY KEY(item_name, version_id, modifier)
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS gems (
      gem_name    TEXT NOT NULL,
      version_id  INTEGER NOT NULL REFERENCES item_versions(version_id),
      metadata    TEXT,
      PRIMARY KEY(gem_name, version_id)
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS monster_skills (
      skill_name  TEXT NOT NULL,
      version_id  INTEGER NOT NULL REFERENCES item_versions(version_id),
      metadata    TEXT,
      PRIMARY KEY(skill_name, version_id)
    );
    """)
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
    cur.execute("""
    CREATE TABLE IF NOT EXISTS unmatched_skills (
      version_id  INTEGER NOT NULL REFERENCES boss_versions(version_id),
      skill_key   TEXT    NOT NULL,
      PRIMARY KEY(version_id, skill_key)
    );
    """)
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
      UNIQUE(version_id, key)
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS boss_skills (
      id          INTEGER PRIMARY KEY AUTOINCREMENT,
      boss_id     INTEGER NOT NULL REFERENCES bosses(id),
      skill_key   TEXT    NOT NULL,
      name        TEXT,
      description TEXT,
      cooldown    REAL,
      tags        TEXT
    );
    """)

    conn.commit()

    # ── APPLY MIGRATIONS ────────────────────────────────────────────────────────

    migration_files = sorted(glob.glob(str(SCRIPT_DIR.parent / "migrations" / "*.sql")))
    for mfile in migration_files:
        LOG.info(f"Applying migration {Path(mfile).name}")
        sql = Path(mfile).read_text(encoding="utf-8")
        try:
            conn.executescript(sql)
        except sqlite3.OperationalError as e:
            LOG.warning(f"Skipping {Path(mfile).name}: {e}")
    conn.commit()
    conn.close()

    LOG.info(f"Database schema is up to date ({db_path})")


if __name__ == "__main__":
    run_setup()
