# tests/test_build_api.py
import pytest
from fastapi.testclient import TestClient

from api.main import app

# Ensure the FastAPI app is available for testing
client = TestClient(app)

@ pytest.fixture(autouse=True)
def patch_dependencies(monkeypatch):
    # Mock DB loader dependencies to return minimal valid data
    monkeypatch.setattr('api.main.load_passive_graph', lambda db, vid: ({1: {}}, {}))
    monkeypatch.setattr('api.main.load_node_effects', lambda db, vid: {1: []})
    monkeypatch.setattr('api.main.load_parsed_mods', lambda db, vid: {1: []})
    monkeypatch.setattr('api.main.load_starting_node', lambda db, cls, vid: 1)
    monkeypatch.setattr('api.main.load_ascendancy_nodes', lambda db, cls, vid: [])
    # Patch encoding function to return deterministic test id
    monkeypatch.setattr('api.main.encode_maxroll_save', lambda node_list: "testid")


def test_build_endpoint_returns_expected_link():
    payload = {
        "character_class": "DexFour",
        "archetype": "",
        "include_ascendancy": False,
        "goals": [],
        "max_points": 1
    }
    response = client.post("/build", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["url"] == "https://maxroll.gg/poe2/passive-tree/?save=testid"
    assert data["save"] == "testid"


def test_build_endpoint_with_goals_and_skill_gems_and_defaults():
    payload = {
        "character_class": "DexFour",
        "archetype": "Lightning",
        "skill_gems": ["Lightning Bolt", "UnknownGem"],
        "include_ascendancy": True,
        "goals": ["tanky", "bossing"],
        "max_points": 5
    }
    response = client.post("/build", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["url"].endswith("?save=testid")
    # strategy should ignore invalid gem names without error
    assert isinstance(data["metrics"], dict)


def test_build_endpoint_missing_required_fields():
    # Omitting required fields yields 422
    response = client.post("/build", json={})
    assert response.status_code == 422


def test_build_endpoint_invalid_character_class():
    payload = {
        "character_class": "InvalidClass",
        "archetype": "",
        "include_ascendancy": False,
        "goals": [],
    }
    response = client.post("/build", json=payload)
    assert response.status_code == 422


def test_build_endpoint_error_on_start_node(monkeypatch):
    # Simulate loader throwing ValueError
    def fail_start(db, cls, vid):
        raise ValueError("Starting node not found")
    monkeypatch.setattr('api.main.load_starting_node', fail_start)

    payload = {
        "character_class": "Ranger",
        "archetype": "Lightning",
        "include_ascendancy": False,
        "goals": [],
    }
    response = client.post("/build", json=payload)
    assert response.status_code == 500
    assert response.json()["detail"] == "Starting node not found"
