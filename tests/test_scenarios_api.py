import logging

from api_helpers import MemoryScenarioRepository
from conftest import _request

from voskill.main import app, get_actor_id, get_scenario_repository
from voskill.scenario_comparison import ScenarioError


class ScenarioComparisonAccessRepository(MemoryScenarioRepository):
    def __init__(self, *, include_people: bool = True) -> None:
        super().__init__()
        self.compare_calls = 0
        self.include_people = include_people

    def get_competency_snapshot(self, scenario_id: str) -> dict:
        if scenario_id not in {"S-001", "S-002"}:
            raise ScenarioError("SCENARIO_NOT_FOUND", 404)
        return {
            "project_id": "P-001",
            "snapshot": {
                "periods": {
                    "2026-02": {
                        "demand": {"SKILL-1": {"load_amount": 40}},
                        "availability": {"P-001": {"hours": 40}} if self.include_people else {},
                    }
                }
            },
        }

    def compare(self, first_scenario_id: str, second_scenario_id: str) -> dict:
        self.compare_calls += 1
        return {
            "scenario_ids": [first_scenario_id, second_scenario_id],
            "scenarios": [
                {"scenario_id": first_scenario_id, "status": "complete", "missing": []},
                {
                    "scenario_id": second_scenario_id,
                    "status": "incomplete",
                    "missing": [{"period": "2026-02", "field": "availability"}],
                },
            ],
            "periods": [
                {
                    "period": "2026-02",
                    "assumptions": {
                        first_scenario_id: {
                            "demand": {"SKILL-1": {"load_amount": 40}},
                            "availability": {"P-001": {"hours": 40}},
                        },
                        second_scenario_id: {
                            "demand": {"SKILL-1": {"load_amount": 48}},
                            "availability": {},
                        },
                    },
                    "changed_values": {"demand": {first_scenario_id: 40, second_scenario_id: 48}},
                }
            ],
        }


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
    repository = ScenarioComparisonAccessRepository()
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_scenario_repository] = lambda: repository

    try:
        response = _request(
            "GET",
            "/scenarios/S-001/compare/S-002",
            state={"actor_id": "U-001", "authorized_person_ids": ["P-001"]},
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


def test_unauthorized_scenario_comparison_is_forbidden_and_audited_without_values(caplog) -> None:
    repository = ScenarioComparisonAccessRepository()
    app.dependency_overrides[get_actor_id] = lambda: "U-999"
    app.dependency_overrides[get_scenario_repository] = lambda: repository

    try:
        with caplog.at_level(logging.WARNING, logger="voskill.audit"):
            response = _request(
                "GET",
                "/scenarios/S-001/compare/S-002",
                state={"actor_id": "U-999", "authorized_person_ids": []},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "FORBIDDEN"
    assert "load_amount" not in response.text
    assert repository.compare_calls == 0
    events = [record for record in caplog.records if record.name == "voskill.audit"]
    assert len(events) == 1
    assert events[0].actor_id == "U-999"
    assert events[0].resource_id == "S-001,S-002"
    assert events[0].action == "compare_scenarios"
    assert events[0].outcome == "denied"
    assert "load_amount" not in caplog.text


def test_scenario_comparison_with_no_participants_requires_project_access() -> None:
    repository = ScenarioComparisonAccessRepository(include_people=False)
    app.dependency_overrides[get_actor_id] = lambda: "U-999"
    app.dependency_overrides[get_scenario_repository] = lambda: repository

    try:
        response = _request(
            "GET",
            "/scenarios/S-001/compare/S-002",
            state={"actor_id": "U-999", "authorized_person_ids": []},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "FORBIDDEN"
    assert repository.compare_calls == 0


def test_authorized_project_manager_can_compare_scenarios() -> None:
    repository = ScenarioComparisonAccessRepository()
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_scenario_repository] = lambda: repository

    try:
        response = _request(
            "GET",
            "/scenarios/S-001/compare/S-002",
            state={"actor_id": "U-001", "authorized_project_ids": ["P-001"]},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert repository.compare_calls == 1