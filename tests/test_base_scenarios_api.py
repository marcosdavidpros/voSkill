from conftest import _request

from voskill.api.dependencies import get_actor_id, get_base_scenario_repository
from voskill.main import app


class MemoryBaseScenarioRepository:
    def __init__(self) -> None:
        self.created: list[dict[str, object]] = []
        self.snapshot = {
            "snapshot_id": "SNP-001",
            "profiles": [
                {"person_id": "P-001", "competencies": {"SKILL-1": 4}, "availability": {"2026-01": 40}}
            ],
            "demands": [
                {"demand_id": "D-001", "skill_id": "SKILL-1", "proficiency_level": 3, "period": "2026-01", "load_amount": 10}
            ],
        }

    def create_base_scenario(self, **values: object) -> dict[str, object]:
        self.created.append(values)
        return {
            "scenario_id": "SCN-001",
            "snapshot_id": "SNP-001",
            "project_id": values["project_id"],
            "scenario_name": values["scenario_name"],
            "scenario_type": "BASE",
        }

    def get_optimization_snapshot(self, scenario_id: str) -> dict[str, object]:
        assert scenario_id == "SCN-001"
        return self.snapshot

    def update_base_scenario(self, scenario_id: str, **values: object) -> dict[str, object]:
        self.updated = {"scenario_id": scenario_id, **values}
        return {
            "scenario_id": scenario_id,
            "snapshot_id": "SNP-002",
            "project_id": "PRJ-001",
            "scenario_name": values["scenario_name"],
            "scenario_type": "BASE",
        }

    def list_scenarios(self) -> list[dict[str, object]]:
        return [{
            "scenario_id": "SCN-001",
            "scenario_name": "Baseline",
            "scenario_type": "BASE",
            "project_id": "PRJ-001",
            "project_name": "Atlas",
        }]


def test_update_base_scenario_replaces_name_and_availability() -> None:
    repository = MemoryBaseScenarioRepository()
    app.dependency_overrides[get_actor_id] = lambda: "A0091250"
    app.dependency_overrides[get_base_scenario_repository] = lambda: repository
    try:
        response = _request(
            "PUT",
            "/scenarios/SCN-001",
            {
                "scenario_name": "Renamed",
                "participants": [{"person_id": "P-001", "availability": {"2026-01": 80}}],
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["scenario_name"] == "Renamed"
    assert response.json()["snapshot_id"] == "SNP-002"
    assert repository.updated["scenario_id"] == "SCN-001"
    assert repository.updated["actor_id"] == "A0091250"
    assert repository.updated["participants"] == [
        {"person_id": "P-001", "availability": {"2026-01": 80}}
    ]


def test_update_base_scenario_requires_authentication() -> None:
    response = _request(
        "PUT",
        "/scenarios/SCN-001",
        {"scenario_name": "Renamed", "participants": []},
    )

    assert response.status_code == 401


def test_list_scenarios_returns_selectable_names() -> None:
    app.dependency_overrides[get_actor_id] = lambda: "A0091250"
    app.dependency_overrides[get_base_scenario_repository] = lambda: MemoryBaseScenarioRepository()
    try:
        response = _request("GET", "/scenarios")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == [{
        "scenario_id": "SCN-001",
        "scenario_name": "Baseline",
        "scenario_type": "BASE",
        "project_id": "PRJ-001",
        "project_name": "Atlas",
    }]


def test_list_scenarios_requires_authentication() -> None:
    response = _request("GET", "/scenarios")

    assert response.status_code == 401


def test_create_base_scenario_persists_participant_availability() -> None:
    repository = MemoryBaseScenarioRepository()
    app.dependency_overrides[get_actor_id] = lambda: "A0091250"
    app.dependency_overrides[get_base_scenario_repository] = lambda: repository
    try:
        response = _request(
            "POST",
            "/projects/PRJ-001/scenarios",
            {
                "scenario_name": "Baseline January",
                "participants": [
                    {"person_id": "P-001", "availability": {"2026-01": 40}}
                ],
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json() == {
        "scenario_id": "SCN-001",
        "snapshot_id": "SNP-001",
        "project_id": "PRJ-001",
        "scenario_name": "Baseline January",
        "scenario_type": "BASE",
    }
    assert repository.created[0]["actor_id"] == "A0091250"
    assert repository.created[0]["participants"] == [
        {"person_id": "P-001", "availability": {"2026-01": 40}}
    ]


def test_optimizer_snapshot_contains_profiles_competencies_availability_and_demands() -> None:
    repository = MemoryBaseScenarioRepository()
    app.dependency_overrides[get_actor_id] = lambda: "A0091250"
    app.dependency_overrides[get_base_scenario_repository] = lambda: repository
    try:
        response = _request("GET", "/scenarios/SCN-001/optimization-snapshot")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["snapshot_id"] == "SNP-001"
    assert response.json()["profiles"][0]["competencies"] == {"SKILL-1": 4}
    assert response.json()["profiles"][0]["availability"] == {"2026-01": 40}
    assert response.json()["demands"][0]["demand_id"] == "D-001"


def test_base_scenario_routes_require_authentication() -> None:
    response = _request(
        "POST",
        "/projects/PRJ-001/scenarios",
        {"scenario_name": "Baseline", "participants": []},
    )

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTHENTICATION_REQUIRED"
