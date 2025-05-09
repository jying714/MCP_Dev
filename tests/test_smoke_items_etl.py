import sqlite3
import json
import pytest
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "db" / "passive_tree.db"

@pytest.fixture(scope="module")
def conn():
    conn = sqlite3.connect(DB_PATH)
    yield conn
    conn.close()

def test_raw_snapshots_count(conn):
    cur = conn.execute("SELECT COUNT(*) FROM raw_item_snapshots;")
    count, = cur.fetchone()
    assert count >= 4, f"Expected at least 4 raw snapshots, got {count}"

def test_bases_count(conn):
    cur = conn.execute("SELECT COUNT(*) FROM base_items;")
    count, = cur.fetchone()
    assert count > 0, f"Expected >0 base_items, got {count}"

def test_uniques_count(conn):
    cur = conn.execute("SELECT COUNT(*) FROM unique_items;")
    count, = cur.fetchone()
    assert count > 0, f"Expected >0 unique_items, got {count}"

def test_unique_mods_count(conn):
    cur = conn.execute("SELECT COUNT(*) FROM unique_mods;")
    count, = cur.fetchone()
    assert count > 0, f"Expected >0 unique_mods, got {count}"

def test_gems_count(conn):
    cur = conn.execute("SELECT COUNT(*) FROM gems;")
    count, = cur.fetchone()
    assert count > 0, f"Expected >0 gems, got {count}"

def test_skills_count(conn):
    cur = conn.execute("SELECT COUNT(*) FROM monster_skills;")
    count, = cur.fetchone()
    assert count > 0, f"Expected >0 monster_skills, got {count}"

# New tests for normalized gem schema

def test_gems_core_present(conn):
    # There should be as many rows in gems_core as in gems for latest version
    ver = conn.execute("SELECT MAX(version_id) FROM item_versions;").fetchone()[0]
    legacy = conn.execute("SELECT COUNT(*) FROM gems WHERE version_id = ?", (ver,)).fetchone()[0]
    core   = conn.execute("SELECT COUNT(*) FROM gems_core WHERE version_id = ?", (ver,)).fetchone()[0]
    assert core == legacy, f"Expected gems_core count {legacy}, got {core}"

def test_gem_tags_populated(conn):
    # At least one tag row exists
    cur = conn.execute("SELECT COUNT(*) FROM gem_tags;")
    count, = cur.fetchone()
    assert count > 0, f"Expected >0 gem_tags, got {count}"

def test_gem_attributes_populated(conn):
    cur = conn.execute("SELECT COUNT(*) FROM gem_attributes;")
    count, = cur.fetchone()
    assert count > 0, f"Expected >0 gem_attributes, got {count}"

def test_gem_additional_stats_populated(conn):
    cur = conn.execute("SELECT COUNT(*) FROM gem_additional_stats;")
    count, = cur.fetchone()
    assert count > 0, f"Expected >0 gem_additional_stats, got {count}"

def test_sample_gem_core_fields(conn):
    # Verify Ice Nova core fields
    ver = conn.execute("SELECT MAX(version_id) FROM item_versions;").fetchone()[0]
    row = conn.execute("""
        SELECT name, base_type_name, granted_effect_id, variant_id, support_flag
          FROM gems_core
         WHERE version_id = ? AND gem_name = ?
    """, (ver, "Metadata/Items/Gems/SkillGemIceNova")).fetchone()
    assert row is not None, "Ice Nova not found in gems_core"
    name, base_type, geid, vid, sup = row
    assert name is not None and base_type is not None, "Core fields missing"
