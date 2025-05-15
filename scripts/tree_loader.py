# scripts/tree_loader.py
#!/usr/bin/env python3
"""
Loader functions for PoB JSON tree into MCP SQLite, updated to use 'classesStart'.
"""
import sqlite3
import logging

# ── SQL TEMPLATES ─────────────────────────────────────────────────────────────
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
ASC_INSERT_SQL = """
INSERT OR REPLACE INTO ascendancy_nodes
  (ascendancy, node_id, version_id, x, y, node_type, name, description)
VALUES (?, ?, ?, ?, ?, ?, ?, ?);
"""

logger = logging.getLogger(__name__)

# ── POSITION & TYPE EXTRACTORS ─────────────────────────────────────────────────
def extract_position(n: dict, nid: int, groups) -> tuple[int, int]:
    """
    1) Use nested 'position'. 2) Use n['x'],n['y']. 3) Use group's 'id' lookup. 4) Default to (0,0).
    """
    # nested
    pos = n.get("position")
    if isinstance(pos, dict) and "x" in pos and "y" in pos:
        return int(pos["x"]), int(pos["y"])
    # explicit
    rx, ry = n.get("x"), n.get("y")
    if rx is not None and ry is not None:
        return int(rx), int(ry)
    # group lookup
    grp_id = n.get("group")
    grp = {}
    if isinstance(groups, list):
        for g in groups:
            if not isinstance(g, dict):
                continue
            if g.get("id") == grp_id:
                grp = g
                break
    elif isinstance(groups, dict):
        grp = groups.get(grp_id) or groups.get(str(grp_id), {})
    rx, ry = grp.get("x"), grp.get("y")
    if rx is not None and ry is not None:
        return int(rx), int(ry)
    # fallback
    logger.warning(f"Node {nid}: missing coords; defaulting to (0,0)")
    return 0, 0


def compute_node_type(n: dict) -> str:
    if n.get("ascendancyName"): return "Ascendancy"
    if n.get("isKeystone"):     return "Keystone"
    if n.get("isNotable"):      return "Notable"
    if n.get("options"):        return "Choice"
    if n.get("isAscendancyStart"): return "Start"
    return "Regular"

# ── LOADERS ────────────────────────────────────────────────────────────────────
def load_nodes(conn: sqlite3.Connection, vid: int, nodes: dict, groups):
    count = 0
    for nid_str, n in nodes.items():
        try:
            nid = int(nid_str)
        except ValueError:
            continue
        x, y = extract_position(n, nid, groups)
        ntype = compute_node_type(n)
        name = n.get("name") or ""
        desc = n.get("description") or ""
        orbit_idx = n.get("orbitIndex")
        grp_id = n.get("group")
        playable = int(bool(name))
        conn.execute(NODE_INSERT_SQL, (nid, vid, x, y, ntype, name, desc, orbit_idx, grp_id, playable))
        count += 1
    logger.info(f"Upserted {count} passive_nodes")


def load_edges(conn: sqlite3.Connection, vid: int, nodes: dict):
    for nid_str, n in nodes.items():
        nid = int(nid_str)
        for c in n.get("connections", []):
            cid = int(c.get("id") if isinstance(c, dict) else c)
            conn.execute(EDGE_INSERT_SQL, (nid, cid, vid))
            conn.execute(EDGE_INSERT_SQL, (cid, nid, vid))
    logger.info("Loaded node_edges")


def mirror_edges(conn: sqlite3.Connection, vid: int):
    conn.execute("""
      INSERT OR IGNORE INTO node_edges(from_node_id,to_node_id,version_id)
      SELECT to_node_id,from_node_id,version_id
        FROM node_edges
       WHERE version_id=?
         AND (to_node_id,from_node_id,version_id)
             NOT IN (SELECT from_node_id,to_node_id,version_id FROM node_edges WHERE version_id=?)
    """, (vid, vid))
    logger.info("Mirrored reverse edges")


def load_effects(conn: sqlite3.Connection, vid: int, nodes: dict):
    count = 0
    for nid_str, n in nodes.items():
        nid = int(nid_str)
        for stat in n.get("stats", []):
            conn.execute(EFFECT_INSERT_SQL, (nid, stat, 0.0, vid))
            count += 1
    logger.info(f"Loaded {count} node_effects")


def load_starting_nodes(conn: sqlite3.Connection, vid: int, nodes: dict, groups):
    """
    Inserts starting nodes by using each node's 'classesStart' list.
    """
    count = 0
    for nid_str, n in nodes.items():
        classes = n.get("classesStart") or []
        if not isinstance(classes, list):
            continue
        try:
            nid = int(nid_str)
        except ValueError:
            continue
        x, y = extract_position(n, nid, groups)
        for cls in classes:
            conn.execute(STARTING_NODE_SQL, (vid, nid, cls, x, y))
            count += 1
    logger.info(f"Loaded {count} starting_nodes")


def load_ascendancy_nodes(conn: sqlite3.Connection, asc_vid: int, nodes: dict, groups):
    count = 0
    for nid_str, n in nodes.items():
        asc = n.get("ascendancyName")
        if not asc:
            continue
        try:
            nid = int(nid_str)
        except ValueError:
            continue
        x, y = extract_position(n, nid, groups)
        name = n.get("name") or ""
        desc = n.get("description") or ""
        conn.execute(ASC_INSERT_SQL, (asc, nid, asc_vid, x, y, "Ascendancy", name, desc))
        count += 1
    logger.info(f"Loaded {count} ascendancy_nodes")