import sys
import shutil
import sqlite3
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

# Point at your src/ directory
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from api.main import app  # now resolves correctly

client = TestClient(app)

def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status":"ok"}

def test_get_valid_stat():
    res = client.get("/stats/FirePen")
    assert res.status_code == 200
    body = res.json()
    assert body["stat_key"] == "FirePen"
    assert "unit" in body and "description" in body

def test_get_invalid_stat():
    res = client.get("/stats/DoesNotExist")
    assert res.status_code == 404
