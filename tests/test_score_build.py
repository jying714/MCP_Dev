import sys
import os
import pytest

# Ensure the 'src' directory is on sys.path to import our API modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from api.main import score_build
from api.schemas import BuildMetrics


def test_score_build_tanky():
    # Only 'tanky' goal should use life, armor, and eshield weights
    metrics = BuildMetrics(
        life=100.0,
        armor=50.0,
        eshield=25.0,
        damage_inc={
            "Fire Damage": 0.0,
            "Cold Damage": 0.0,
            "Lightning Damage": 0.0,
            "Physical Damage": 0.0,
            "Projectile Damage": 0.0,
        },
        crit_chance=0.0,
        total_points=10
    )
    score = score_build(metrics, ['tanky'])
    expected = 100.0 * 0.6 + 50.0 * 0.3 + 25.0 * 0.1
    assert score == pytest.approx(expected)


def test_score_build_bossing():
    # Only 'bossing' goal should use damage and crit weights
    metrics = BuildMetrics(
        life=0.0,
        armor=0.0,
        eshield=0.0,
        damage_inc={
            "Fire Damage": 0.0,
            "Cold Damage": 0.0,
            "Lightning Damage": 40.0,
            "Physical Damage": 0.0,
            "Projectile Damage": 60.0,
        },
        crit_chance=10.0,
        total_points=10
    )
    score = score_build(metrics, ['bossing'])
    expected = 40.0 * 0.4 + 60.0 * 0.3 + 10.0 * 0.3
    assert score == pytest.approx(expected)


def test_score_build_multiple_goals():
    # Combined goals should sum their respective weighted contributions
    metrics = BuildMetrics(
        life=100.0,
        armor=50.0,
        eshield=25.0,
        damage_inc={
            "Fire Damage": 0.0,
            "Cold Damage": 0.0,
            "Lightning Damage": 40.0,
            "Physical Damage": 0.0,
            "Projectile Damage": 60.0,
        },
        crit_chance=10.0,
        total_points=10
    )
    score = score_build(metrics, ['tanky', 'bossing'])
    expected_tanky = 100.0 * 0.6 + 50.0 * 0.3 + 25.0 * 0.1
    expected_bossing = 40.0 * 0.4 + 60.0 * 0.3 + 10.0 * 0.3
    assert score == pytest.approx(expected_tanky + expected_bossing)


def test_score_build_unknown_goal():
    # Unknown goals should contribute zero to the total score
    metrics = BuildMetrics(
        life=100.0,
        armor=50.0,
        eshield=25.0,
        damage_inc={
            "Fire Damage": 0.0,
            "Cold Damage": 0.0,
            "Lightning Damage": 40.0,
            "Physical Damage": 0.0,
            "Projectile Damage": 60.0,
        },
        crit_chance=10.0,
        total_points=10
    )
    score = score_build(metrics, ['unknown'])
    assert score == pytest.approx(0.0)
