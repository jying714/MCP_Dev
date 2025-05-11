import sys
import os
import pytest

# Ensure the 'src' directory is on sys.path to import our API modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from api.metrics import compute_metrics
from api.schemas import BuildMetrics


def test_compute_metrics_with_static_and_parsed():
    # Define a small set of nodes with static effects and parsed modifiers
    node_list = [1, 2, 3]

    # Static node_effects: node_id -> list of (stat_key, value)
    node_effects = {
        1: [("Life", 10.0), ("Armour", 5.0)],
        2: [("Energy Shield", 20.0)],
        3: [("Projectile Damage", 30.0)]
    }

    # Parsed modifiers: node_id -> list of (stat_key, min_value, max_value, is_range)
    parsed_mods = {
        1: [("Life", 5.0, 5.0, False)],                     # +5 life
        2: [("Lightning Damage", 5.0, 15.0, True)],         # +5–15% lightning (avg = 10)
        3: [("Critical Strike Chance", 2.0, 2.0, False)]    # +2% crit chance
    }

    # Compute metrics
    metrics = compute_metrics(node_list, node_effects, parsed_mods)
    assert isinstance(metrics, BuildMetrics)

    # Verify aggregated metrics
    assert metrics.life == pytest.approx(15.0)          # 10 + 5
    assert metrics.armor == pytest.approx(5.0)
    assert metrics.eshield == pytest.approx(20.0)
    # Damage increases
    expected_damage = {
        "Fire Damage": 0.0,
        "Cold Damage": 0.0,
        "Lightning Damage": pytest.approx(10.0),  # avg of 5 and 15
        "Physical Damage": 0.0,
        "Projectile Damage": pytest.approx(30.0)
    }
    assert metrics.damage_inc == expected_damage
    assert metrics.crit_chance == pytest.approx(2.0)
    assert metrics.total_points == len(node_list)


def test_compute_metrics_with_empty_nodes():
    # No nodes selected should yield zeroed metrics
    metrics = compute_metrics([], {}, {})
    assert metrics.life == 0.0
    assert metrics.armor == 0.0
    assert metrics.eshield == 0.0
    assert all(v == 0.0 for v in metrics.damage_inc.values())
    assert metrics.crit_chance == 0.0
    assert metrics.total_points == 0
