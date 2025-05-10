import sqlite3
import shutil
import os
from pathlib import Path
import pytest

@pytest.fixture(scope="function")
def conn(tmp_path):
    # Copy the real DB into a temp file for isolated testing
    src = os.environ.get("TEST_DB_PATH", "db/passive_tree.db")
    dst = tmp_path / "passive_tree.db"
    shutil.copy(src, dst)
    conn = sqlite3.connect(dst)
    yield conn
    conn.close()

def test_vw_boss_fire_penetration(conn):
    cur = conn.execute("SELECT COUNT(*) FROM vw_boss_fire_penetration;")
    count, = cur.fetchone()
    assert count > 0, "Expected >0 rows in vw_boss_fire_penetration"

    cur = conn.execute("PRAGMA table_info('vw_boss_fire_penetration');")
    cols = [row[1] for row in cur.fetchall()]
    expected = {'skill_id','skill_name','base_penetration','uber_penetration','unit','description'}
    assert set(cols) >= expected, f"vw_boss_fire_penetration missing columns: {expected - set(cols)}"

def test_vw_gems_projectile(conn):
    cur = conn.execute("SELECT COUNT(*) FROM vw_gems_projectile;")
    count, = cur.fetchone()
    assert count > 0, "Expected >0 rows in vw_gems_projectile"

    cur = conn.execute("SELECT gem_name FROM vw_gems_projectile LIMIT 5;")
    names = [row[0] for row in cur.fetchall()]
    assert names, "vw_gems_projectile returned no gem names"
