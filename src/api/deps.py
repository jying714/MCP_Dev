# src/api/deps.py
import sqlite3
from pathlib import Path
from fastapi import Depends

DB_PATH = Path(__file__).parent.parent.parent / "db" / "passive_tree.db"

def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    try:
        yield conn
    finally:
        conn.close()
