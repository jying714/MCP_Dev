#!/usr/bin/env python3
import sqlite3

def run_setup(db_path: str = "passive_tree.db"):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    #
    # ─── PASSIVE & ASCENDANCY SCHEMA ───────────────────────────────────────────────
    #
    cur.execute("""
    CREATE TABLE IF NOT EXISTS tree_versions (
      id          INTEGER PRIMARY KEY AUTOINCREMENT,
      snapshot_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS raw_trees (
      id          INTEGER PRIMARY KEY AUTOINCREMENT,
      version_id  INTEGER NOT NULL REFERENCES tree_versions(id),
      raw_json    TEXT    NOT NULL,
      FOREIGN KEY(version_id) REFERENCES tree_versions(id)
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS passive_nodes (
      id          INTEGER PRIMARY KEY,
      version_id  INTEGER NOT NULL REFERENCES tree_versions(id),
      key         INTEGER NOT NULL,
      name        TEXT,
      type        TEXT,
      x           REAL,
      y           REAL,
      stats       TEXT,      -- JSON array
      is_keystone BOOLEAN,
      FOREIGN KEY(version_id) REFERENCES tree_versions(id)
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS node_edges (
      id          INTEGER PRIMARY KEY AUTOINCREMENT,
      version_id  INTEGER NOT NULL REFERENCES tree_versions(id),
      from_node   INTEGER NOT NULL REFERENCES passive_nodes(id),
      to_node     INTEGER NOT NULL REFERENCES passive_nodes(id),
      FOREIGN KEY(version_id) REFERENCES tree_versions(id)
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS node_effects (
      id          INTEGER PRIMARY KEY AUTOINCREMENT,
      version_id  INTEGER NOT NULL REFERENCES tree_versions(id),
      node_id     INTEGER NOT NULL REFERENCES passive_nodes(id),
      effect_key  TEXT    NOT NULL,
      params      TEXT,    -- JSON or CSV
      FOREIGN KEY(version_id) REFERENCES tree_versions(id)
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS starting_nodes (
      id          INTEGER PRIMARY KEY AUTOINCREMENT,
      version_id  INTEGER NOT NULL REFERENCES tree_versions(id),
      class_key   TEXT    NOT NULL,
      node_id     INTEGER NOT NULL REFERENCES passive_nodes(id),
      FOREIGN KEY(version_id) REFERENCES tree_versions(id)
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ascendancy_versions (
      id          INTEGER PRIMARY KEY AUTOINCREMENT,
      snapshot_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS raw_ascendancy_snapshots (
      id          INTEGER PRIMARY KEY AUTOINCREMENT,
      version_id  INTEGER NOT NULL REFERENCES ascendancy_versions(id),
      raw_json    TEXT    NOT NULL,
      FOREIGN KEY(version_id) REFERENCES ascendancy_versions(id)
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ascendancy_nodes (
      id            INTEGER PRIMARY KEY,
      version_id    INTEGER NOT NULL REFERENCES ascendancy_versions(id),
      ascendancy_key TEXT   NOT NULL,
      key            INTEGER NOT NULL,
      name           TEXT,
      x              REAL,
      y              REAL,
      stats          TEXT,     -- JSON array
      FOREIGN KEY(version_id) REFERENCES ascendancy_versions(id)
    );
    """)

    #
    # ─── ITEM SCHEMA ────────────────────────────────────────────────────────────────
    #
    cur.execute("""
    CREATE TABLE IF NOT EXISTS item_versions (
      id          INTEGER PRIMARY KEY AUTOINCREMENT,
      snapshot_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS raw_item_snapshots (
      id          INTEGER PRIMARY KEY AUTOINCREMENT,
      version_id  INTEGER NOT NULL REFERENCES item_versions(id),
      raw_json    TEXT    NOT NULL,
      FOREIGN KEY(version_id) REFERENCES item_versions(id)
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS base_items (
      id          INTEGER PRIMARY KEY,
      version_id  INTEGER NOT NULL REFERENCES item_versions(id),
      key         TEXT    NOT NULL,
      name        TEXT,
      item_class  TEXT,
      tags        TEXT,    -- JSON array
      FOREIGN KEY(version_id) REFERENCES item_versions(id)
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS unique_items (
      id          INTEGER PRIMARY KEY AUTOINCREMENT,
      version_id  INTEGER NOT NULL REFERENCES item_versions(id),
      key         TEXT    NOT NULL,
      name        TEXT,
      base_key    TEXT,
      tags        TEXT,    -- JSON array
      FOREIGN KEY(version_id) REFERENCES item_versions(id)
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS unique_mods (
      id          INTEGER PRIMARY KEY AUTOINCREMENT,
      unique_id   INTEGER NOT NULL REFERENCES unique_items(id),
      mod_text    TEXT,
      FOREIGN KEY(unique_id) REFERENCES unique_items(id)
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS gems (
      id          INTEGER PRIMARY KEY AUTOINCREMENT,
      version_id  INTEGER NOT NULL REFERENCES item_versions(id),
      key         TEXT    NOT NULL,
      name        TEXT,
      gem_type    TEXT,
      tags        TEXT,    -- JSON array
      FOREIGN KEY(version_id) REFERENCES item_versions(id)
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS monster_skills (
      id          INTEGER PRIMARY KEY AUTOINCREMENT,
      version_id  INTEGER NOT NULL REFERENCES item_versions(id),
      key         TEXT    NOT NULL,
      name        TEXT,
      tags        TEXT,    -- JSON array
      FOREIGN KEY(version_id) REFERENCES item_versions(id)
    );
    """)

    #
    # ─── BOSS SCHEMA ────────────────────────────────────────────────────────────────
    #
    cur.execute("""
    CREATE TABLE IF NOT EXISTS boss_versions (
      id          INTEGER PRIMARY KEY AUTOINCREMENT,
      snapshot_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS raw_boss_snapshots (
      id          INTEGER PRIMARY KEY AUTOINCREMENT,
      version_id  INTEGER NOT NULL REFERENCES boss_versions(id),
      raw_json    TEXT    NOT NULL,
      FOREIGN KEY(version_id) REFERENCES boss_versions(id)
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS bosses (
      id            INTEGER PRIMARY KEY AUTOINCREMENT,
      version_id    INTEGER NOT NULL REFERENCES boss_versions(id),
      key           TEXT    NOT NULL,
      name          TEXT    NOT NULL,
      tier          INTEGER,
      biome         TEXT,
      description   TEXT,
      armour_mult   INTEGER,
      evasion_mult  INTEGER,
      is_uber       BOOLEAN DEFAULT 0,
      UNIQUE(version_id, key),
      FOREIGN KEY(version_id) REFERENCES boss_versions(id)
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
      tags        TEXT,    -- JSON array
      FOREIGN KEY(boss_id) REFERENCES bosses(id)
    );
    """)

    conn.commit()
    conn.close()
    print("✅ Database schema is up to date.")

if __name__ == "__main__":
    run_setup()
