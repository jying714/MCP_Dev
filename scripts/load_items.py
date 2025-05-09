#!/usr/bin/env python3
import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime

# === Ensure db directory exists immediately ===
PROJECT_ROOT = Path(__file__).parent.parent
DB_DIR       = PROJECT_ROOT / "db"
DB_DIR.mkdir(parents=True, exist_ok=True)

# === Paths ===
HERE     = Path(__file__).parent
ROOT     = HERE.parent
DB_PATH  = ROOT / "db" / "passive_tree.db"

# Location of your PoB JSON snapshots
DATA_DIR = ROOT / "data" / "pob"

# Ensure ETL log directory exists
LOG_DIR  = ROOT / "logs" / "load_items"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# === Logging ===
LOG_FILE = LOG_DIR / "load_items.log"
logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# === SQL TEMPLATES ===
INSERT_VERSION_SQL = """
INSERT INTO item_versions(version_tag, fetched_at, source)
VALUES (?, ?, ?);
"""

# Upsert instead of plain INSERT to avoid UNIQUE violations
INSERT_RAW_SQL = """
INSERT OR REPLACE INTO raw_item_snapshots(version_id, category, raw_json)
VALUES (?, ?, ?);
"""

INSERT_BASE_SQL = """
INSERT OR REPLACE INTO base_items(base_name, version_id, metadata)
VALUES (?, ?, ?);
"""

INSERT_UNIQUE_SQL = """
INSERT OR REPLACE INTO unique_items(item_name, base_name, version_id, metadata)
VALUES (?, ?, ?, ?);
"""

INSERT_UNIQUE_MOD_SQL = """
INSERT OR REPLACE INTO unique_mods(item_name, version_id, modifier)
VALUES (?, ?, ?);
"""

INSERT_GEM_SQL = """
INSERT OR REPLACE INTO gems(gem_name, version_id, metadata)
VALUES (?, ?, ?);
"""

INSERT_SKILL_SQL = """
INSERT OR REPLACE INTO monster_skills(skill_name, version_id, metadata)
VALUES (?, ?, ?);
"""

# Mark the source of PoB data
SOURCE = "PoB-PoE2/src/Data@dev"

def upsert_item_version(conn):
    tag = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    cur = conn.execute(
        INSERT_VERSION_SQL,
        (tag, datetime.utcnow(), SOURCE)
    )
    vid = cur.lastrowid
    logger.info(f"⮕ Created item_version {vid} ({tag})")
    return vid

def load_raw(conn, vid, category, path: Path):
    """
    Upsert the raw JSON snapshot for the given category.
    """
    raw = path.read_text(encoding="utf-8")
    conn.execute(
        INSERT_RAW_SQL,
        (vid, category, raw)
    )
    logger.debug(f"⮕ Upserted raw JSON for '{category}'")

def load_bases(conn, vid, items):
    for itm in items:
        conn.execute(
            INSERT_BASE_SQL,
            (
                itm["baseType"],
                vid,
                json.dumps(itm.get("metadata", {})),
            )
        )
    logger.info(f"⮕ Upserted {len(items)} base_items")

def load_uniques(conn, vid, items):
    for itm in items:
        name = itm["name"]
        base = itm.get("baseType", "")
        meta = itm.get("metadata", {})
        conn.execute(
            INSERT_UNIQUE_SQL,
            (
                name,
                base,
                vid,
                json.dumps(meta),
            )
        )
        for mod in itm.get("modifiers", []):
            conn.execute(
                INSERT_UNIQUE_MOD_SQL,
                (name, vid, mod)
            )
    logger.info(f"⮕ Upserted {len(items)} unique_items + modifiers")

def load_gems(conn, vid, items):
    for itm in items:
        conn.execute(
            INSERT_GEM_SQL,
            (
                itm["baseType"],
                vid,
                json.dumps(itm.get("metadata", {})),
            )
        )
    logger.info(f"⮕ Upserted {len(items)} gems")

def load_skills(conn, vid, items):
    for itm in items:
        conn.execute(
            INSERT_SKILL_SQL,
            (
                itm["name"],
                vid,
                json.dumps(itm.get("metadata", {})),
            )
        )
    logger.info(f"⮕ Upserted {len(items)} monster_skills")

def main():
    # Paths to the four PoB JSON snapshots
    files = {
        "bases":   DATA_DIR / "bases.json",
        "uniques": DATA_DIR / "uniques.json",
        "gems":    DATA_DIR / "gems.json",
        "skills":  DATA_DIR / "skills.json",
    }
    missing = [c for c, p in files.items() if not p.exists()]
    if missing:
        print(f"❌ Missing JSON for: {', '.join(missing)} in {DATA_DIR}")
        return

    conn = sqlite3.connect(DB_PATH)
    try:
        vid = upsert_item_version(conn)

        # Load raw snapshots (upsert)
        for cat, path in files.items():
            load_raw(conn, vid, cat, path)

        # Load structured data
        data = {cat: json.loads(path.read_text(encoding="utf-8"))
                for cat, path in files.items()}

        load_bases(conn,   vid, data["bases"])
        load_uniques(conn, vid, data["uniques"])
        load_gems(conn,    vid, data["gems"])
        load_skills(conn,  vid, data["skills"])

        conn.commit()
        logger.info(f"✅ Loaded items version {vid}")
        print(f"✅ Loaded items version {vid}")
    except Exception:
        conn.rollback()
        logger.exception("❌ Failed loading items")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    main()
