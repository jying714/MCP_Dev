import pytest
import sqlite3
from pathlib import Path
import shutil
import os

@pytest.fixture
def conn(tmp_path):
    # Copy the existing work DB into a temp path for isolated testing
    src = os.environ.get("TEST_DB_PATH", "db/passive_tree.db")
    dst = tmp_path / "passive_tree.db"
    shutil.copy(src, dst)
    return sqlite3.connect(dst)

def test_ascendancy_tables_exist(conn):
    tables = [
        "ascendancy_versions",
        "raw_ascendancy_snapshots",
        "ascendancy_nodes",
    ]
    for tbl in tables:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (tbl,)
        )
        assert cur.fetchone(), f"Table `{tbl}` is missing from your schema"

def test_ascendancy_version_created(conn):
    # There should be at least one version row
    cur = conn.execute("SELECT COUNT(*) FROM ascendancy_versions;")
    count, = cur.fetchone()
    assert count >= 1, f"Expected >=1 ascendancy_versions, got {count}"

def test_raw_ascendancy_snapshot(conn):
    # raw_ascendancy_snapshots should reference the latest version
    cur = conn.execute("SELECT MAX(version_id) FROM ascendancy_versions;")
    version_id, = cur.fetchone()
    assert version_id is not None, "No version_id in ascendancy_versions"

    cur = conn.execute(
        "SELECT COUNT(*) FROM raw_ascendancy_snapshots WHERE version_id = ?;",
        (version_id,)
    )
    count, = cur.fetchone()
    assert count == 1, f"Expected 1 raw_ascendancy_snapshots for version {version_id}, got {count}"

def test_ascendancy_nodes_loaded(conn):
    # There should be at least one ascendancy node for the latest version
    cur = conn.execute("SELECT MAX(version_id) FROM ascendancy_versions;")
    version_id, = cur.fetchone()
    cur = conn.execute(
        "SELECT COUNT(*) FROM ascendancy_nodes WHERE version_id = ?;",
        (version_id,)
    )
    count, = cur.fetchone()
    assert count > 0, f"Expected >0 ascendancy_nodes for version {version_id}, got {count}"
