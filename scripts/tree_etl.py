#!/usr/bin/env python3
"""
Unified ETL for PathOfBuilding-PoE2 tree.lua (fetch + load) for MCP

Usage:
  python tree_etl.py run --poe-version 401
  python tree_etl.py fetch --poe-version 401
  python tree_etl.py load --lua-file data/raw_trees/401_0_2_<timestamp>.lua
"""
import argparse
import requests
import logging
import sqlite3
import json
import os
from pathlib import Path
from datetime import datetime
from slpp import slpp  # pip install slpp

# === Paths & Constants ===
HERE = Path(__file__).parent
PROJECT_ROOT = HERE.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw_trees"
LOG_DIR = PROJECT_ROOT / "logs" / "tree_etl"
DB_DIR = PROJECT_ROOT / "db"
DB_PATH = DB_DIR / "passive_tree.db"

for d in (DATA_DIR, RAW_DIR, LOG_DIR, DB_DIR):
    d.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "tree_etl.log"
logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Raw content base: using 'dev' branch for PoE2 updates
POB_RAW_BASE = (
    "https://raw.githubusercontent.com/PathOfBuildingCommunity/"
    "PathOfBuilding-PoE2/dev"
)

# Hybrid mapping: PoE patch -> PoB subfolder under src/TreeData
TAG_MAP = {
    "401": "0_2",
    # future PoE patch versions -> PoB folder mappings
}

# === Helper Functions ===
def get_pob_folder(poe_version: str) -> str:
    folder = TAG_MAP.get(poe_version)
    if not folder:
        logger.error(f"No PoB folder mapping for PoE version {poe_version}")
        raise ValueError(f"Missing PoB folder for PoE version {poe_version}")
    return folder


def fetch_tree(poe_version: str) -> Path:
    """Fetch the PoB tree.lua for the given PoE version and save snapshots."""
    folder = get_pob_folder(poe_version)
    url = f"{POB_RAW_BASE}/src/TreeData/{folder}/tree.lua"
    logger.info(f"Fetching PoB tree.lua from {url}")
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    content = resp.text

    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    raw_file = RAW_DIR / f"{poe_version}_{folder}_{timestamp}.lua"
    raw_file.write_text(content, encoding="utf-8")

    latest = DATA_DIR / f"tree{poe_version}.lua"
    latest.write_text(content, encoding="utf-8")

    logger.info(f"Saved raw PoB tree to {raw_file}")
    print(raw_file)
    return raw_file


def parse_lua(lua_path: Path) -> dict:
    """Strip leading 'return' and trailing semicolon, then decode Lua table to Python dict."""
    text = lua_path.read_text(encoding="utf-8")
    if text.startswith("return "):
        text = text[len("return "):]
    text = text.rstrip().rstrip(";")
    return slpp.decode(text)


def upsert_version(conn: sqlite3.Connection, source: str) -> int:
    cur = conn.execute(
        "INSERT INTO tree_versions(version_tag, fetched_at, source_url) VALUES (?, ?, ?)",
        (datetime.utcnow().isoformat(), datetime.utcnow(), source)
    )
    vid = cur.lastrowid
    logger.info(f"Created tree version {vid}")
    return vid


def load_pipeline(conn: sqlite3.Connection, vid: int, data: dict):
    # Raw snapshot
    conn.execute(
        "INSERT OR REPLACE INTO raw_trees(version_id, raw_json) VALUES (?, ?)",
        (vid, json.dumps(data))
    )

    # Existing loader functions must be imported or defined above
    load_nodes(conn, vid, data.get("nodes", {}), data.get("groups", {}), data.get("passive_skills", {}))
    load_edges(conn, vid, data.get("nodes", {}))
    mirror_edges(conn, vid)
    load_effects(conn, vid, data.get("nodes", {}), data.get("passive_skills", {}))
    load_starting_nodes(conn, vid, {"passive_tree": data}, data.get("groups", {}), data.get("passive_skills", {}))

    asc_vid = conn.execute("INSERT INTO ascendancy_versions DEFAULT VALUES;").lastrowid
    conn.execute(
        "INSERT INTO raw_ascendancy_snapshots(version_id, raw_json) VALUES (?,?)",
        (asc_vid, json.dumps(data))
    )
    load_ascendancy_nodes(conn, asc_vid, data.get("nodes", {}), data.get("groups", {}), data.get("passive_skills", {}))

    logger.info(f"Loaded data for tree version {vid} and ascendancy version {asc_vid}")


def load_tree(lua_path: Path):
    conn = sqlite3.connect(str(DB_PATH))
    try:
        vid = upsert_version(conn, lua_path.as_uri())
        data = parse_lua(lua_path)
        load_pipeline(conn, vid, data)
        conn.commit()
        print(f"✅ Loaded tree version {vid}")
    except Exception:
        conn.rollback()
        logger.exception("Load pipeline failed")
        raise
    finally:
        conn.close()

# === CLI Entrypoint ===
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="PoB tree ETL for MCP")
    sub = parser.add_subparsers(dest="cmd", required=True)

    pf = sub.add_parser("fetch", help="Fetch tree.lua from PoB")
    pf.add_argument("--poe-version", default="401", help="PoE patch version (e.g. 401)")

    pl = sub.add_parser("load", help="Load a local tree.lua into DB")
    pl.add_argument("--lua-file", type=Path, required=True, help="Path to tree.lua file")

    pr = sub.add_parser("run", help="Fetch then load end-to-end")
    pr.add_argument("--poe-version", default="401", help="PoE patch version (e.g. 401)")

    args = parser.parse_args()
    if args.cmd == "fetch":
        fetch_tree(args.poe_version)
    elif args.cmd == "load":
        load_tree(args.lua_file)
    elif args.cmd == "run":
        lua = fetch_tree(args.poe_version)
        load_tree(lua)
