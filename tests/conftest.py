# tests/conftest.py
import os
import subprocess
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH      = PROJECT_ROOT / "db" / "passive_tree.db"

@pytest.fixture(scope="session", autouse=True)
def rebuild_db_and_run_etl():
    # 1) Remove old database
    if DB_PATH.exists():
        DB_PATH.unlink()

    # 2) Recreate schema and apply migrations
    subprocess.run(
        ["python", "scripts/setup_db.py"],
        cwd=str(PROJECT_ROOT),
        check=True
    )

    # 3) Load passive tree + ascendancy
    subprocess.run(
        ["python", "scripts/tree_etl.py", "run", "--poe-version", "401"],
        cwd=str(PROJECT_ROOT),
        check=True
    )

    # 4) Fetch and parse stat definitions
    subprocess.run(
        ["python", "scripts/fetch_stats.py"],
        cwd=str(PROJECT_ROOT),
        check=True
    )
    subprocess.run(
        ["python", "scripts/parse_stats.py"],
        cwd=str(PROJECT_ROOT),
        check=True
    )

    # yield to allow the rest of tests to run against this fresh DB
    yield
