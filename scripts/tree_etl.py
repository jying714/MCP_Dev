#!/usr/bin/env python3
import argparse
import requests
import re
import json
import logging
import sqlite3
import sys
from pathlib import Path
from datetime import datetime

# ── Ensure scripts/ is on import path ────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent.resolve()
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from tree_loader import (
    EFFECT_INSERT_SQL,
    load_nodes, load_edges, mirror_edges,
    load_starting_nodes, load_ascendancy_nodes
)

# ── Paths ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR     = PROJECT_ROOT / "data"
RAW_DIR      = DATA_DIR / "raw_trees"
LOG_DIR      = PROJECT_ROOT / "logs" / "tree_etl"
DB_DIR       = PROJECT_ROOT / "db"
DB_PATH      = DB_DIR / "passive_tree.db"
for d in (DATA_DIR, RAW_DIR, LOG_DIR, DB_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    filename=str(LOG_DIR / "tree_etl.log"),
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ── PoB Raw URL & Tag Map ─────────────────────────────────────────────────────
POB_RAW_BASE = (
    "https://raw.githubusercontent.com/PathOfBuildingCommunity/"
    "PathOfBuilding-PoE2/dev"
)
TAG_MAP = {"401": "0_2"}

def get_pob_folder(poe_version: str) -> str:
    folder = TAG_MAP.get(poe_version)
    if not folder:
        raise ValueError(f"No PoB folder mapping for PoE version {poe_version}")
    return folder

def fetch_tree(poe_version: str) -> Path:
    """
    1) Download the raw PoB tree.json
    2) Snapshot it to data/raw_trees
    3) Wrap into { passive_tree: {...}, passive_skills: {...} }
    4) Write wrapper to data/tree.json and data/tree{poe_version}.json
    """
    folder = get_pob_folder(poe_version)
    url = f"{POB_RAW_BASE}/src/TreeData/{folder}/tree.json"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()

    # 1) Save raw snapshot
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    raw_file = RAW_DIR / f"{poe_version}_{folder}_{ts}.json"
    raw_file.write_text(resp.text, encoding="utf-8")

    # 2) Decode JSON
    raw_data = resp.json()

    # 3) Build our wrapper
    wrapper = {
        "passive_tree": {
            "groups": raw_data.get("groups", {}),
            "nodes": raw_data.get("nodes", {}),
            "root_passives": raw_data.get("root_passives", []),
        },
        "passive_skills": raw_data.get("passive_skills", {})
    }

    # 4) Inject snake_case skill_id for every node (for tests & loader)
    for node in wrapper["passive_tree"]["nodes"].values():
        if "skillId" in node:
            node["skill_id"] = node["skillId"]

    # 5) Write wrapped JSON for ETL & tests
    (DATA_DIR / "tree.json").write_text(json.dumps(wrapper), encoding="utf-8")
    (DATA_DIR / f"tree{poe_version}.json").write_text(json.dumps(wrapper), encoding="utf-8")

    print(raw_file)
    return raw_file

def parse_json(json_path: Path) -> dict:
    return json.loads(json_path.read_text(encoding="utf-8"))

def upsert_version(conn: sqlite3.Connection, source: str) -> int:
    cur = conn.execute(
        "INSERT INTO tree_versions(version_tag,fetched_at,source_url) VALUES(?,?,?)",
        (datetime.utcnow().isoformat(), datetime.utcnow(), source)
    )
    return cur.lastrowid

def load_pipeline(conn: sqlite3.Connection, vid: int, data: dict):
    # 1) Store raw snapshot
    conn.execute(
        "INSERT OR REPLACE INTO raw_trees(version_id,raw_json) VALUES(?,?)",
        (vid, json.dumps(data))
    )

    # 2) Unwrap
    if "passive_tree" in data:
        tree_data = data["passive_tree"]
        skills_data = data.get("passive_skills", {})
    else:
        tree_data = data
        skills_data = data.get("passive_skills", {})

    nodes  = tree_data.get("nodes", {})
    groups = tree_data.get("groups", [])

    # 3) Load nodes & edges
    load_nodes(conn, vid, nodes, groups)
    load_edges(conn, vid, nodes)
    mirror_edges(conn, vid)

    # 4) Load node_effects, using either snake_case or camelCase
    count = 0
    for nid_str, node in nodes.items():
        try:
            nid = int(nid_str)
        except ValueError:
            continue

        # pick up either field
        skill_key = node.get("skill_id") or node.get("skillId")
        stats = skills_data.get(skill_key, {}).get("stats", [])
        for stat_key in stats:
            conn.execute(EFFECT_INSERT_SQL, (nid, stat_key, 0.0, vid))
            count += 1
    logger.info(f"Loaded {count} node_effects")

    # 5) Starting & Ascendancy
    load_starting_nodes(conn, vid, nodes, groups)
    asc_vid = conn.execute("INSERT INTO ascendancy_versions DEFAULT VALUES;").lastrowid
    conn.execute(
        "INSERT INTO raw_ascendancy_snapshots(version_id,raw_json) VALUES(?,?)",
        (asc_vid, json.dumps(data))
    )
    load_ascendancy_nodes(conn, asc_vid, nodes, groups)

def load_tree(json_path: Path):
    conn = sqlite3.connect(str(DB_PATH))
    try:
        vid  = upsert_version(conn, json_path.as_uri())
        data = parse_json(json_path)
        load_pipeline(conn, vid, data)
        conn.commit()
        print(f"Loaded tree version {vid}")
    except Exception:
        conn.rollback()
        logger.exception("Load failed")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="PoB JSON-only ETL for MCP")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fetch").add_argument("--poe-version", default="401")
    sub.add_parser("load").add_argument("--json-file", type=Path, required=True)
    sub.add_parser("run").add_argument("--poe-version", default="401")
    args = parser.parse_args()

    if args.cmd == "fetch":
        fetch_tree(args.poe_version)
    elif args.cmd == "load":
        load_tree(args.json_file)
    else:
        jf = fetch_tree(args.poe_version)
        load_tree(jf)
