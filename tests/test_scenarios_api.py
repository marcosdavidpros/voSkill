from api_helpers import MemoryScenarioRepository
from conftest import _request

from voskill.main import app, get_actor_id, get_scenario_repository


def test_create_alternative_reuses_base_snapshot_and_returns_deltas() -> None:
    repository = MemoryScenarioRepository()
    base_snapshot_before = repository.base_snapshot
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_scenario_repository] = lambda: repository

    try:
        response = _request(
            "POST",
            "/scenarios/B-001/alternatives",
            {
                "name": "Alternative A",
                "deltas": {"demandOverrides": [{"period": "2026-01", "loadAmount": 48}]},
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["base_scenario_id"] == "B-001"
    assert response.json()["snapshot_id"] == "S-001"
    assert response.json()["actor_id"] == "U-001"
    assert response.json()["deltas"]["demandOverrides"][0]["loadAmount"] == 48
    assert repository.base_snapshot == base_snapshot_before

def test_create_alternative_for_missing_base_returns_stable_error() -> None:
    repository = MemoryScenarioRepository()
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_scenario_repository] = lambda: repository

    try:
        response = _request(
            "POST",
            "/scenarios/B-404/alternatives",
            {"name": "Alternative A", "deltas": {"demandOverrides": []}},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "BASE_SCENARIO_NOT_FOUND"
    assert repository.created_alternatives == []

def test_compare_scenarios_returns_assumptions_and_missing_fields() -> None:
    repository = MemoryScenarioRepository()
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_scenario_repository] = lambda: repository

    try:
        response = _request(
            "GET",
            "/scenarios/S-001/compare/S-002",
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["scenario_ids"] == ["S-001", "S-002"]
    assert response.json()["scenarios"][1]["status"] == "incomplete"
    assert response.json()["scenarios"][1]["missing"] == [
        {"period": "2026-02", "field": "availability"}
    ]
    assert "metrics" not in response.json()