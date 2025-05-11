# src/api/optimizer.py
import re
from typing import Dict, List, Tuple, Any

# Define how high-level goals map to stat_key patterns and scoring weights
GOAL_CRITERIA: Dict[str, Dict[str, Any]] = {
    "tanky": {
        "patterns": [r"Life", r"Armour", r"Energy Shield", r"Resistance"],
        "weights": {
            "life": 0.6,
            "armor": 0.3,
            "eshield": 0.1
        }
    },
    "bossing": {
        "patterns": [r"Damage", r"Crit"],
        "weights": {
            # Metric keys correspond to BuildMetrics fields or DAMAGE_TYPES keys
            "Lightning Damage": 0.4,
            "Projectile Damage": 0.3,
            "crit_chance": 0.3
        }
    },
    "speed": {
        "patterns": [r"Movement Speed", r"Attack Speed"],
        "weights": {
            "speed": 0.7,
            "attack_speed": 0.3
        }
    }
}

# List of damage types for metrics
DAMAGE_TYPES = [
    "Fire Damage",
    "Cold Damage",
    "Lightning Damage",
    "Physical Damage",
    "Projectile Damage"
]

# Pattern for critical strike chance
CRIT_PATTERN = re.compile(r"Critical Strike Chance", re.IGNORECASE)


def build_stat_weights(goals: List[str]) -> Dict[str, float]:
    """
    Build a flat mapping of stat_key pattern to weight, given list of goals.
    This influences node scoring during path optimization.
    """
    weights: Dict[str, float] = {}
    for goal in goals:
        criteria = GOAL_CRITERIA.get(goal.lower())
        if not criteria:
            continue
        for pat in criteria["patterns"]:
            # For node scoring, use equal weight among patterns
            weights[pat] = 1.0
    return weights


def node_score(
    node_id: Any,
    node_effects: Dict[Any, List[Tuple[str, float]]],
    parsed_mods: Dict[Any, List[Tuple[str, float, float, bool]]],
    stat_weights: Dict[str, float]
) -> float:
    """
    Compute a heuristic score for a single node based on its effects and goal patterns.
    """
    score = 0.0
    effects = node_effects.get(node_id, [])
    mods = parsed_mods.get(node_id, [])

    # Score static node effects
    for stat_key, value in effects:
        for pat, w in stat_weights.items():
            if re.search(pat, stat_key, re.IGNORECASE):
                score += value * w
    # Score parsed mods by average
    for stat_key, mn, mx, is_range in mods:
        avg = ((mn + mx) / 2) if (mn is not None and mx is not None) else (mn or 0)
        for pat, w in stat_weights.items():
            if re.search(pat, stat_key, re.IGNORECASE):
                score += avg * w
    return score


def optimize_path(
    nodes: Dict[int, Dict[str, Any]],
    edges: Dict[int, List[int]],
    node_effects: Dict[int, List[Tuple[str, float]]],
    parsed_mods: Dict[int, List[Tuple[str, float, float, bool]]],
    start_node: int,
    ascendancy_nodes: List[int],
    goals: List[str],
    max_points: int
) -> List[int]:
    """
    Greedy graph expansion: pick highest-scoring neighbor nodes until max_points reached.
    """
    # Build scoring weights from high-level goals
    stat_weights = build_stat_weights(goals)
    selected = {start_node}
    path = [start_node]
    frontier = set(edges.get(start_node, [])) - selected

    while len(path) < max_points and frontier:
        best_node = None
        best_score = 0.0
        for node in list(frontier):
            score = node_score(node, node_effects, parsed_mods, stat_weights)
            if score > best_score:
                best_score = score
                best_node = node
        # If no node yields positive score, stop
        if best_node is None or best_score <= 0:
            break
        selected.add(best_node)
        path.append(best_node)
        frontier.remove(best_node)
        for nbr in edges.get(best_node, []):
            if nbr not in selected:
                frontier.add(nbr)

    # Append ascendancy if enabled
    if ascendancy_nodes and len(path) < max_points:
        for nd in ascendancy_nodes:
            if len(path) < max_points:
                path.append(nd)
            else:
                break

    return path
