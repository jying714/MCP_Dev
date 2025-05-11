import sys
import os
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import HTTPStatusError

# Ensure src is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from api.main import router

# Create test app
test_app = FastAPI()
test_app.include_router(router)
client = TestClient(test_app)

@pytest.fixture(autouse=True)
def patch_dependencies(monkeypatch):
    # Default DB loader functions return minimal graph
    monkeypatch.setattr('api.main.load_passive_graph', lambda db, vid: ({1: {}}, {}))
    monkeypatch.setattr('api.main.load_node_effects', lambda db, vid: {1: []})
    monkeypatch.setattr('api.main.load_parsed_mods', lambda db, vid: {1: []})
    monkeypatch.setattr('api.main.load_starting_node', lambda db, cls, vid: 1)
    monkeypatch.setattr('api.main.load_ascendancy_nodes', lambda db, cls, vid: [])
    # Patch save_to_maxroll to return deterministic link
    monkeypatch.setattr('api.main.encode_maxroll_save', lambda node_list: "testid")


def test_build_endpoint_returns_expected_link():
    payload = {
        "character_class": "Ranger",
        "archetype": "Lightning",
        "include_ascendancy": False,
        "goals": [],
        "max_points": 1
    }
    response = client.post("/build", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["save"].endswith("testid")
    assert data["url"].endswith("testid")
    assert data["nodes"] == [1]
    assert data["metrics"]["life"] == 0.0
    assert data["score"] == 0.0


def test_build_endpoint_with_goals_and_skill_gems_and_defaults():
    # Omit optional max_points and include_ascendancy to use defaults
    payload = {
        "character_class": "Ranger",
        "archetype": "Physical",
        "goals": ["tanky"],
        "skill_gems": ["Lightning Bolt"]
    }
    response = client.post("/build", json=payload)
    assert response.status_code == 200
    data = response.json()
    # Defaults: max_points=122, include_ascendancy=False
    assert data["nodes"] == [1]
    assert data["url"].startswith("https://maxroll.gg/poe2/passive-tree/")


def test_build_endpoint_missing_required_fields():
    # Missing character_class and archetype and goals
    response = client.post("/build", json={})
    assert response.status_code == 422
    errors = response.json()["detail"]
    fields = {e['loc'][-1] for e in errors}
    assert "character_class" in fields
    assert "archetype" in fields
    assert "goals" in fields


def test_build_endpoint_invalid_character_class():
    payload = {
        "character_class": "InvalidClass",
        "archetype": "Lightning",
        "goals": []
    }
    response = client.post("/build", json=payload)
    assert response.status_code == 422
    assert any(err['loc'][-1] == 'character_class' for err in response.json()['detail'])


def test_build_endpoint_error_on_start_node(monkeypatch):
    # Simulate missing starting node
    def fail_start(db, cls, vid):
        raise ValueError("Starting node not found")
    monkeypatch.setattr('api.main.load_starting_node', fail_start)

    payload = {
        "character_class": "Ranger",
        "archetype": "Lightning",
        "goals": []
    }
    response = client.post("/build", json=payload)
    # Should propagate as 500 Internal Server Error
    assert response.status_code == 500
    assert response.json()['detail'] == "Starting node not found"
