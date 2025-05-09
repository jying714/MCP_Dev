#!/usr/bin/env python3
import argparse
import sqlite3
import json
import logging
import sys
from pathlib import Path
from datetime import datetime

# === Path setup ===
HERE         = Path(__file__).parent
PROJECT_ROOT = HERE.parent
DB_DIR       = PROJECT_ROOT / "db"
DB_DIR.mkdir(parents=True, exist_ok=True)

# === SQL Schema paths & defaults ===
DB_PATH = DB_DIR / "passive_tree.db"

# === Logging Setup ===
LOG_DIR = PROJECT_ROOT / "logs" / "load_tree401"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "load_tree401.log"
logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# === SQL Templates ===
NODE_INSERT_SQL = """
INSERT OR REPLACE INTO passive_nodes
  (node_id, version_id, x, y, node_type, name, description, orbit, group_id, is_playable)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
"""
NODE_ERROR_SQL = """
INSERT OR IGNORE INTO node_errors
  (version_id, node_id, error_type, raw_value)
VALUES (?, ?, ?, ?);
"""
EDGE_INSERT_SQL = """
INSERT OR REPLACE INTO node_edges
  (from_node_id, to_node_id, version_id)
VALUES (?, ?, ?, ?);
"""
EDGE_ERROR_SQL = """
INSERT OR IGNORE INTO edge_errors
  (version_id, from_node_id, to_node_id, error_type, raw_radius)
VALUES (?, ?, ?, ?, ?);
"""
EFFECT_INSERT_SQL = """
INSERT OR REPLACE INTO node_effects
  (node_id, stat_key, value, version_id)
VALUES (?, ?, ?, ?);
"""
STARTING_NODE_SQL = """
INSERT OR REPLACE INTO starting_nodes
  (version_id, node_id, class, x, y)
VALUES (?, ?, ?, ?, ?);
"""

# === Helper Functions ===

def parse_args():
    p = argparse.ArgumentParser(description="Load a versioned tree JSON into SQLite")
    p.add_argument("--json-file", required=True,
                   help="Path to the raw tree JSON snapshot")
    p.add_argument("--version-id", required=True, type=int,
                   help="The version_id already created in tree_versions")
    return p.parse_args()

def extract_position(n, nid, groups):
    pos = n.get("position")
    if isinstance(pos, dict):
        rx, ry = pos.get("x"), pos.get("y")
    elif isinstance(pos, (list, tuple)) and len(pos) >= 2:
        rx, ry = pos[0], pos[1]
    elif isinstance(pos, int):
        parent = n.get("parent")
        grp = groups.get(str(parent), {})
        rx, ry = grp.get("x"), grp.get("y")
        logger.debug(f"Node {nid}: numeric position → group {parent} center ({rx},{ry})")
    else:
        rx, ry = n.get("x"), n.get("y")

    if rx is None or ry is None:
        logger.error(f"Node {nid}: no valid position")
        raise ValueError(f"Node {nid} has no valid position")

    try:
        return int(rx), int(ry)
    except:
        logger.error(f"Node {nid}: non-integer position")
        raise

def compute_node_type(skill_id, details):
    if skill_id.startswith("Ascendancy"):
        return "Ascendancy"
    if details.get("is_keystone"):
        return "Keystone"
    if details.get("is_notable"):
        return "Notable"
    if details.get("is_just_icon"):
        return "Mastery"
    if details.get("is_multiple_choice"):
        return "Choice"
    if "socket" in skill_id.lower():
        return "Jewel Socket"
    if "Start" in skill_id:
        return "Start"
    if "Small" in skill_id:
        return "Small"
    return "Regular"

def load_nodes(conn, vid, nodes, groups, skills):
    for nid_str, n in nodes.items():
        nid = int(nid_str)
        sid = n.get("skill_id", "")
        det = skills.get(sid) or {}
        if not det:
            conn.execute(NODE_ERROR_SQL, (vid, nid, "missing_skill", sid))
        try:
            x, y = extract_position(n, nid, groups)
        except Exception:
            conn.execute(NODE_ERROR_SQL, (vid, nid, "missing_position", repr(n.get("position"))))
            continue

        ntype = compute_node_type(sid, det)
        name = det.get("name") or ""
        is_playable = int(bool(name.strip()) and not name.startswith("[DNT-UNUSED]"))

        conn.execute(
            NODE_INSERT_SQL,
            (nid, vid, x, y, ntype, det.get("name"), det.get("description"),
             n.get("orbitIndex"), n.get("parent"), is_playable)
        )
    logger.info(f"Upserted {len(nodes)} nodes")

def load_edges(conn, vid, nodes):
    for nid_str, n in nodes.items():
        nid = int(nid_str)
        for c in n.get("connections", []):
            # figure out child ID; radius is ignored for insertion
            if isinstance(c, dict):
                cid = int(c.get("id", 0))
            else:
                cid = int(c)

            # We expect exactly three columns: from_node_id, to_node_id, version_id
            sql = EDGE_INSERT_SQL.strip()
            params = (nid, cid, vid)

            # === DEBUG OUTPUT ===
            print(f"[DEBUG] SQL    = {sql!r}")
            print(f"[DEBUG] params = {params!r} (len={len(params)})")
            # ====================

            try:
                conn.execute(EDGE_INSERT_SQL, params)
            except Exception as e:
                print(f"[ERROR] insert failed: params={params!r} → {e}")
                raise


def mirror_edges(conn, vid):
    conn.execute("""
      INSERT OR IGNORE INTO node_edges(from_node_id, to_node_id, version_id)
        SELECT to_node_id, from_node_id, version_id
          FROM node_edges
         WHERE version_id = ?
           AND (to_node_id, from_node_id, version_id)
               NOT IN (
                 SELECT from_node_id, to_node_id, version_id
                   FROM node_edges
                  WHERE version_id = ?
               );
    """, (vid, vid))
    logger.info("Mirrored reverse edges")

def load_effects(conn, vid, nodes, skills):
    for nid_str, n in nodes.items():
        nid = int(nid_str)
        sid = n.get("skill_id", "")
        for stat in skills.get(sid, {}).get("stats", []):
            if isinstance(stat, dict):
                key = stat.get("statKey") or stat.get("key")
                val = stat.get("value") or stat.get("values") or 0
            else:
                key, val = stat, 0
            try:
                val = float(val) if not isinstance(val, list) else float(val[0])
            except:
                val = 0.0
            conn.execute(EFFECT_INSERT_SQL, (nid, key, val, vid))
    logger.info("Loaded stat effects")

def load_starting_nodes(conn, vid, raw, groups, skills):
    roots = raw.get("passive_tree", {}).get("root_passives", [])
    for nid in roots:
        node = raw["passive_tree"]["nodes"].get(str(nid), {})
        try:
            x, y = extract_position(node, nid, groups)
        except:
            logger.warning(f"Skipping starting node {nid}: bad position")
            continue
        sid = node.get("skill_id", "")
        cls = skills.get(sid, {}).get("ascendancy") or "Passive"
        conn.execute(STARTING_NODE_SQL, (vid, nid, cls, x, y))
    logger.info(f"Loaded {len(roots)} starting nodes")

def main():
    args = parse_args()
    json_path = Path(args.json_file)
    vid = args.version_id

    if not json_path.exists():
        logger.error(f"Missing JSON at {json_path}")
        print(f"❌ Missing JSON at {json_path}")
        sys.exit(1)

    raw = json.loads(json_path.read_text(encoding="utf-8"))
    pt = raw.get("passive_tree", {})
    nodes = pt.get("nodes", {})
    groups = pt.get("groups", {})
    skills = raw.get("passive_skills", {})

    conn = sqlite3.connect(DB_PATH)
    try:
        # Store raw JSON for completeness (errors if already loaded)
        conn.execute(
            "INSERT OR REPLACE INTO raw_trees(version_id, raw_json) VALUES (?, ?)",
            (vid, json.dumps(raw))
        )
        load_nodes(conn, vid, nodes, groups, skills)
        load_edges(conn, vid, nodes)
        mirror_edges(conn, vid)
        load_effects(conn, vid, nodes, skills)
        load_starting_nodes(conn, vid, raw, groups, skills)
        conn.commit()
        logger.info(f"✅ Fully loaded version {vid}")
        print(f"✅ Loaded version {vid}")
    except Exception:
        conn.rollback()
        logger.exception("Load failed")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    main()
