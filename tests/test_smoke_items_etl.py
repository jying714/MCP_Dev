import sqlite3
import json
import pytest
from pathlib import Path

# Adjust path if your DB is elsewhere
DB_PATH = Path(__file__).parent.parent / "db" / "passive_tree.db"

@pytest.fixture(scope="module")
def conn():
    """Connect once per module and tear down."""
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
