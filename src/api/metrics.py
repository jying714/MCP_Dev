# src/api/metrics.py

import re
from typing import Dict, List, Tuple

from .schemas import BuildMetrics

# Damage types we track
DAMAGE_TYPES = [
    "Fire Damage",
    "Cold Damage",
    "Lightning Damage",
    "Physical Damage",
    "Projectile Damage",
]

# Pattern for critical strike chance
CRIT_PATTERN = re.compile(r"Critical Strike Chance", re.IGNORECASE)

def compute_metrics(
    node_list: List[int],
    node_effects: Dict[int, List[Tuple[str, float]]],
    parsed_mods: Dict[int, List[Tuple[str, float, float, bool]]]
) -> BuildMetrics:
    """
    Aggregate build statistics from selected nodes.

    - life: sum of all 'Life' bonuses
    - armor: sum of all 'Armour' bonuses
    - eshield: sum of all 'Energy Shield' bonuses
    - damage_inc: dict of DAMAGE_TYPES to total % increased
    - crit_chance: sum of all crit chance bonuses
    - total_points: number of nodes allocated
    """
    life = 0.0
    armor = 0.0
    eshield = 0.0
    crit_chance = 0.0
    damage_inc: Dict[str, float] = {dt: 0.0 for dt in DAMAGE_TYPES}

    def process_stat(stat_key: str, value: float):
        nonlocal life, armor, eshield, crit_chance
        if 'Life' in stat_key:
            life += value
        if 'Armour' in stat_key:
            armor += value
        if 'Energy Shield' in stat_key:
            eshield += value
        if CRIT_PATTERN.search(stat_key):
            crit_chance += value
        for dt in DAMAGE_TYPES:
            if dt in stat_key:
                damage_inc[dt] += value

    for node_id in node_list:
        # Static node effects
        for stat_key, val in node_effects.get(node_id, []):
            process_stat(stat_key, val)
        # Parsed modifiers (use average for ranges)
        for stat_key, mn, mx, is_range in parsed_mods.get(node_id, []):
            avg = ((mn + mx) / 2) if (mn is not None and mx is not None) else (mn or 0.0)
            process_stat(stat_key, avg)

    return BuildMetrics(
        life=life,
        armor=armor,
        eshield=eshield,
        damage_inc=damage_inc,
        crit_chance=crit_chance,
        total_points=len(node_list)
    )
