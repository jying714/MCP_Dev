import sys
import shutil
import sqlite3
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from api.main import app

client = TestClient(app)

def test_list_fire_penetration():
    res = client.get("/boss/penetration/fire")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) > 0
    first = data[0]
    assert "skill_id" in first and "base_penetration" in first
