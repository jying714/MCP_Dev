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

def test_stat_definitions_not_empty(conn):
    cur = conn.execute("SELECT COUNT(*) FROM stat_definitions;")
    count, = cur.fetchone()
    assert count > 0, f"Expected >0 stat_definitions, got {count}"

def test_stat_definitions_complete(conn):
    cur = conn.execute(
        "SELECT COUNT(*) FROM stat_definitions WHERE unit IS NULL OR description IS NULL;"
    )
    missing, = cur.fetchone()
    assert missing == 0, f"{missing} stat_definitions rows are missing metadata"
