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

def test_stats_etl_and_api(client):
    # this assumes you have a TestClient fixture named client
    # 1) a known generic
    r1 = client.get("/api/stats/base_skill_effect_duration")
    assert r1.status_code == 200
    j1 = r1.json()
    assert j1["stat_key"] == "base_skill_effect_duration"
    assert "unit" in j1 and "description" in j1

    # 2) a known override
    r2 = client.get("/api/stats/active_skill_attack_damage_+%_final?skill_key=active")
    assert r2.status_code == 200
    j2 = r2.json()
    assert j2["override"] is True
