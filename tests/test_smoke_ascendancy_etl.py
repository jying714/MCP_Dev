import pytest
import sqlite3

@pytest.fixture
def conn(tmp_path):
    # point at the same DB your smoke tests use
    db = tmp_path / "passive_tree.db"
    # assume setup_db.py has been run in CI before tests
    # copy the work DB schema into tmp_path/passive_tree.db
    import shutil, os
    src = os.environ.get("TEST_DB_PATH", "db/passive_tree.db")
    shutil.copy(src, db)
    return sqlite3.connect(db)

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
