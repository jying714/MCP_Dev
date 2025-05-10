# tests/test_smoke_mod_parsed.py

import sqlite3
from pathlib import Path
import pytest

DB_PATH = Path(__file__).parent.parent / "db" / "passive_tree.db"

@pytest.fixture(scope="module")
def conn():
    """Connect once per module to the passive_tree.db."""
    connection = sqlite3.connect(str(DB_PATH))
    connection.row_factory = sqlite3.Row
    yield connection
    connection.close()


def test_mod_parsed_table_exists(conn):
    """Ensure the mod_parsed table was created."""
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='mod_parsed';"
    )
    assert cur.fetchone() is not None, "mod_parsed table does not exist"


def test_mod_parsed_has_rows(conn):
    """Ensure that mod_parsed has at least one row."""
    cur = conn.execute("SELECT COUNT(*) AS cnt FROM mod_parsed;")
    assert cur.fetchone()[0] > 0, "mod_parsed table is empty"


def test_key_columns_not_null(conn):
    """item_name, version_id, and stat_key should never be NULL."""
    cur = conn.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM mod_parsed
        WHERE item_name IS NULL
           OR version_id IS NULL
           OR stat_key IS NULL;
        """
    )
    assert cur.fetchone()[0] == 0, "Null found in key columns of mod_parsed"


def test_min_value_le_max_value(conn):
    """For rows with both min_value and max_value, ensure min_value ≤ max_value."""
    cur = conn.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM mod_parsed
        WHERE min_value IS NOT NULL
          AND max_value IS NOT NULL
          AND min_value > max_value;
        """
    )
    assert cur.fetchone()[0] == 0, "Found rows where min_value > max_value"


def test_unique_mods_parsed(conn):
    """
    Every distinct (item_name, version_id) in unique_mods
    should appear at least once in mod_parsed.
    """
    total = conn.execute(
        "SELECT COUNT(DISTINCT item_name || '::' || version_id) AS total FROM unique_mods;"
    ).fetchone()[0]

    if total == 0:
        pytest.skip("No unique_mods loaded; skipping this check")

    parsed = conn.execute(
        """
        SELECT COUNT(DISTINCT u.item_name || '::' || u.version_id) AS parsed
        FROM unique_mods u
        JOIN mod_parsed m
          ON m.item_name = u.item_name
         AND m.version_id = u.version_id;
        """
    ).fetchone()[0]

    assert parsed >= total, f"Parsed {parsed}/{total} unique_mods entries"
