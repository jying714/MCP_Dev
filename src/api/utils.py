import sqlite3
from typing import Dict, List, Tuple, Any


def load_passive_graph(
    db: sqlite3.Connection, version_id: int
) -> Tuple[Dict[int, Dict[str, Any]], Dict[int, List[int]]]:
    """
    Load passive skill tree nodes and edges for a given version.

    Returns:
      - nodes: mapping node_id -> { 'x': int, 'y': int, 'node_type': str, 'name': str }
      - edges: adjacency list mapping node_id -> list of neighbor node_ids
    """
    cur = db.cursor()
    # Load nodes
    cur.execute(
        """
        SELECT node_id, x, y, node_type, name
        FROM passive_nodes
        WHERE version_id = ?
        """,
        (version_id,)
    )
    node_rows = cur.fetchall()
    nodes = {
        row[0]: { 'x': row[1], 'y': row[2], 'node_type': row[3], 'name': row[4] }
        for row in node_rows
    }

    # Load edges
    cur.execute(
        """
        SELECT from_node_id, to_node_id
        FROM node_edges
        WHERE version_id = ?
        """,
        (version_id,)
    )
    edge_rows = cur.fetchall()
    edges: Dict[int, List[int]] = { node_id: [] for node_id in nodes }
    for from_id, to_id in edge_rows:
        edges.setdefault(from_id, []).append(to_id)
        edges.setdefault(to_id, []).append(from_id)

    return nodes, edges


def load_node_effects(
    db: sqlite3.Connection, version_id: int
) -> Dict[int, List[Tuple[str, float]]]:
    """
    Load static node effects (stat_key, value) for each passive node.

    Returns mapping node_id -> list of (stat_key, value).
    """
    cur = db.cursor()
    cur.execute(
        """
        SELECT node_id, stat_key, value
        FROM node_effects
        WHERE version_id = ?
        """,
        (version_id,)
    )
    rows = cur.fetchall()
    effects: Dict[int, List[Tuple[str, float]]] = {}
    for node_id, stat_key, value in rows:
        effects.setdefault(node_id, []).append((stat_key, value))
    return effects


def load_parsed_mods(
    db: sqlite3.Connection, version_id: int
) -> Dict[int, List[Tuple[str, float, float, bool]]]:
    """
    Load parsed modifiers for nodes and items for a given version.

    Returns mapping item_name_or_node_id -> list of (stat_key, min_value, max_value, is_range).
    """
    cur = db.cursor()
    cur.execute(
        """
        SELECT item_name, stat_key, min_value, max_value, is_range
        FROM mod_parsed
        WHERE version_id = ?
        """,
        (version_id,)
    )
    rows = cur.fetchall()
    mods: Dict[int, List[Tuple[str, float, float, bool]]] = {}
    for key, stat_key, mn, mx, is_range in rows:
        # item_name may be int-like for node_id or str for items
        identifier = key
        mods.setdefault(identifier, []).append((stat_key, mn, mx, bool(is_range)))
    return mods


def load_starting_node(
    db: sqlite3.Connection, class_name: str, version_id: int
) -> int:
    """
    Fetch the starting passive node ID for a given character class and version.
    """
    cur = db.cursor()
    cur.execute(
        """
        SELECT node_id
        FROM starting_nodes
        WHERE class = ? AND version_id = ?
        LIMIT 1
        """,
        (class_name, version_id)
    )
    row = cur.fetchone()
    if not row:
        raise ValueError(f"Starting node not found for class {class_name}")
    return row[0]


def load_ascendancy_nodes(
    db: sqlite3.Connection, class_name: str, version_id: int
) -> List[int]:
    """
    Return the list of ascendancy keystone node IDs for a given class and tree version.
    """
    cur = db.cursor()
    cur.execute(
        """
        SELECT node_id
        FROM ascendancy_nodes
        WHERE ascendancy = ? AND version_id = ?
        """,
        (class_name, version_id)
    )
    return [row[0] for row in cur.fetchall()]
