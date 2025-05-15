# src/api/stats.py
from fastapi import APIRouter, HTTPException, Query
import sqlite3, json
from pathlib import Path

router = APIRouter()
DB_PATH = Path(__file__).parent.parent / 'db' / 'passive_tree.db'

def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

@router.get('/stats/', summary="List all stat keys")
def list_stats(limit: int = Query(100, ge=1, le=1000), offset: int = 0):
    conn = get_db()
    rows = conn.execute(
        "SELECT stat_key, version_id FROM stat_definitions ORDER BY stat_key LIMIT ? OFFSET ?",
        (limit, offset)
    ).fetchall()
    conn.close()
    return [{"stat_key": r["stat_key"], "version_id": r["version_id"]} for r in rows]

@router.get('/stats/{stat_key}', summary="Get a stat definition or override")
def get_stat(stat_key: str, skill_key: str = Query(None)):
    conn = get_db()

    # Try override first
    if skill_key:
        row = conn.execute(
            "SELECT override_desc, override_params, version_id "
            "FROM stat_overrides WHERE stat_key=? AND skill_key=?",
            (stat_key, skill_key)
        ).fetchone()
        if row:
            conn.close()
            return {
                "stat_key": stat_key,
                "description": row["override_desc"],
                "parameters": json.loads(row["override_params"]),
                "override": True,
                "version_id": row["version_id"]
            }

    # Fallback to generic
    row = conn.execute(
        "SELECT unit, description, param_keys, version_id "
        "FROM stat_definitions WHERE stat_key=?",
        (stat_key,)
    ).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Stat not found")

    return {
        "stat_key": stat_key,
        "unit": row["unit"],
        "description": row["description"],
        "parameters": json.loads(row["param_keys"]),
        "override": False,
        "version_id": row["version_id"]
    }
