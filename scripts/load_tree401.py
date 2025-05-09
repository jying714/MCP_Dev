#!/usr/bin/env python3
import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime

# === Ensure db directory exists immediately ===
PROJECT_ROOT = Path(__file__).parent.parent
DB_DIR = PROJECT_ROOT / "db"
DB_DIR.mkdir(parents=True, exist_ok=True)

# === Paths ===
HERE = Path(__file__).parent
ROOT = HERE.parent
DB_PATH = ROOT / "db" / "passive_tree.db"
DATA_FILE = ROOT / "data" / "tree401.json"
LOG_DIR = ROOT / "logs" / "load_tree401"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# === Logging ===
LOG_FILE = LOG_DIR / "load_tree401.log"
logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# === SQL TEMPLATES ===
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
VALUES (?, ?, ?);
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

SOURCE_URL = "https://assets-ng.maxroll.gg/poe2planner/game/tree401.json"

# === Helpers ===
def upsert_version(conn):
    tag = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    cur = conn.execute(
        "INSERT INTO tree_versions(version_tag, fetched_at, source_url) VALUES (?,?,?)",
        (tag, datetime.utcnow(), SOURCE_URL)
    )
    vid = cur.lastrowid
    logger.info(f"Created version {vid} ({tag})")
    return vid


def load_raw(conn, vid, raw):
    conn.execute(
        "INSERT INTO raw_trees(version_id, raw_json) VALUES (?,?)",
        (vid, json.dumps(raw))
    )
    logger.debug("Stored raw JSON")


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
        logger.error(f"Node {nid}: no valid position (pos={pos!r}, x={n.get('x')!r}, y={n.get('y')!r})")
        raise ValueError(f"Node {nid} has no valid position")

    try:
        return int(rx), int(ry)
    except Exception:
        logger.error(f"Node {nid}: non-integer position (x={rx!r}, y={ry!r})")
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

# === Loaders ===
def load_nodes(conn, vid, nodes, groups, skills):
    for nid_str, n in nodes.items():
        nid = int(nid_str)
        sid = n.get("skill_id", "")
        det = skills.get(sid)
        if det is None:
            conn.execute(NODE_ERROR_SQL, (vid, nid, "missing_skill", sid))
            det = {}
        try:
            x, y = extract_position(n, nid, groups)
        except Exception:
            conn.execute(NODE_ERROR_SQL, (vid, nid, "missing_position", repr(n.get("position"))))
            raise

        ntype = compute_node_type(sid, det)
        name = det.get("name") or ""
        is_playable = int(bool(name.strip()) and not name.startswith("[DNT-UNUSED]"))

        conn.execute(
            NODE_INSERT_SQL,
            (
                nid, vid,
                x, y,
                ntype,
                det.get("name"),
                det.get("description"),
                n.get("orbitIndex"),
                n.get("parent"),
                is_playable,
            )
        )
    logger.info(f"Upserted {len(nodes)} nodes")


def load_edges(conn, vid, nodes):
    for nid_str, n in nodes.items():
        nid = int(nid_str)
        for c in n.get("connections", []):
            cid = int(c.get("id") if isinstance(c, dict) else c)
            radius = c.get("radius") if isinstance(c, dict) else None

            if nid == cid:
                conn.execute(EDGE_ERROR_SQL, (vid, nid, cid, "self_loop", radius))
                conn.execute(EDGE_INSERT_SQL, (nid, cid, vid))
                continue

            if isinstance(radius, int) and radius >= 1_000_000_000:
                conn.execute(EDGE_ERROR_SQL, (vid, nid, cid, "outlier_radius", radius))
                conn.execute(EDGE_INSERT_SQL, (nid, cid, vid))
                continue

            conn.execute(EDGE_INSERT_SQL, (nid, cid, vid))
    logger.info("Loaded raw edges (directional)")


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
    logger.info("Mirrored missing reverse edges")


def load_effects(conn, vid, nodes, skills):
    for nid_str, n in nodes.items():
        nid = int(nid_str)
        sid = n.get("skill_id", "")
        for stat in skills.get(sid, {}).get("stats", []):
            if isinstance(stat, dict):
                key = stat.get("statKey") or stat.get("key")
                val = stat.get("value") or stat.get("values")
                if isinstance(val, list) and val:
                    val = val[0]
                try:
                    val = float(val)
                except:
                    val = 0.0
            elif isinstance(stat, str):
                key = stat
                val = 0.0
            else:
                continue
            conn.execute(EFFECT_INSERT_SQL, (nid, key, val, vid))
    logger.info("Loaded stat effects")


def load_starting_nodes(conn, vid, raw, groups, skills):
    roots = raw.get("passive_tree", {}).get("root_passives", [])
    for nid in roots:
        n = raw["passive_tree"]["nodes"].get(str(nid), {})
        try:
            x, y = extract_position(n, nid, groups)
        except:
            logger.warning(f"Skipping starting node {nid}: cannot extract position")
            continue
        sid = n.get("skill_id", "")
        cls = skills.get(sid, {}).get("ascendancy") or "Passive"
        conn.execute(STARTING_NODE_SQL, (vid, nid, cls, x, y))
    logger.info(f"Loaded {len(roots)} starting_nodes")

# === Main ===

def main():
    if not DATA_FILE.exists():
        logger.error("Missing tree401.json — run fetch script first")
        print("❌ data/tree401.json is missing—run fetch script first")
        return

    raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    pt = raw.get("passive_tree", {})
    nodes = pt.get("nodes", {})
    groups = pt.get("groups", {})
    skills = raw.get("passive_skills", {})

    conn = sqlite3.connect(DB_PATH)
    try:
        vid = upsert_version(conn)
        load_raw(conn, vid, raw)
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

if __name__ == '__main__':
    main()
