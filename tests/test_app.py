import asyncio

import httpx
from fastapi.exceptions import RequestValidationError
from starlette.requests import Request

from voskill.database import CompetencyError, DemandError, ScenarioError
from voskill.main import (
    app,
    get_actor_id,
    get_competency_repository,
    get_demand_repository,
    get_scenario_repository,
    handle_request_validation_error,
)


def test_health_endpoint_does_not_require_oracle() -> None:
    async def get_health() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/health")

    response = asyncio.run(get_health())

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def _request(method: str, path: str, payload: dict | None = None) -> httpx.Response:
    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, path, json=payload)

    return asyncio.run(send())


class MemoryDemandRepository:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def create(self, **values: object) -> dict:
        record = {
            "demand_id": "D-001",
            **values,
            "period": values["period_start"].strftime("%Y-%m"),
        }
        del record["period_start"]
        self.rows.append(record)
        return record

    def list_for_project(self, project_id: str) -> list[dict]:
        return [row for row in self.rows if row["project_id"] == project_id]

    def update(self, demand_id: str, project_id: str, **values: object) -> dict:
        for row in self.rows:
            if row["demand_id"] == demand_id and row["project_id"] == project_id:
                row.update(values)
                row["period"] = values["period_start"].strftime("%Y-%m")
                del row["period_start"]
                return row
        raise DemandError("DEMAND_NOT_FOUND", 404)


class MemoryCompetencyRepository:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def create(self, **values: object) -> dict:
        if not 1 <= values["proficiency_level"] <= 5:
            raise CompetencyError("INVALID_LEVEL", 422, "proficiency_level")
        if not values["evidence"].strip():
            raise CompetencyError("REQUIRED_EVIDENCE", 422, "evidence")
        record = {
            "competency_id": "C-001",
            "skill_name": "Kubernetes",
            "origin_type": "MANUAL",
            **values,
        }
        self.rows.append(record)
        return record

    def list_for_person(self, person_id: str) -> list[dict]:
        return [row for row in self.rows if row["person_id"] == person_id]


class MemoryScenarioRepository:
    def __init__(self) -> None:
        self.base_snapshot = b'{"demands":[]}'
        self.created_alternatives: list[dict] = []

    def create_alternative(
        self,
        base_scenario_id: str,
        name: str,
        deltas: dict,
        actor_id: str,
    ) -> dict:
        if base_scenario_id != "B-001":
            raise ScenarioError("BASE_SCENARIO_NOT_FOUND", 404)
        alternative = {
            "scenario_id": "A-001",
            "base_scenario_id": base_scenario_id,
            "project_id": "P-001",
            "snapshot_id": "S-001",
            "name": name,
            "actor_id": actor_id,
            "created_at": "2026-11-08T12:00:00+00:00",
            "deltas": deltas,
        }
        self.created_alternatives.append(alternative)
        return alternative

    def compare(self, first_scenario_id: str, second_scenario_id: str) -> dict:
        return {
            "scenario_ids": [first_scenario_id, second_scenario_id],
            "scenarios": [
                {"scenario_id": first_scenario_id, "status": "complete", "missing": []},
                {"scenario_id": second_scenario_id, "status": "incomplete", "missing": [
                    {"period": "2026-02", "field": "availability"}
                ]},
            ],
            "periods": [
                {
                    "period": "2026-01",
                    "assumptions": {first_scenario_id: {}, second_scenario_id: {}},
                    "changed_values": {},
                }
            ],
        }


def test_demand_write_requires_authenticated_actor_context() -> None:
    response = _request(
        "POST",
        "/projects/P-001/demands",
        {
            "skill_id": "SKILL-1",
            "proficiency_level": 3,
            "period": "2026-01",
            "load_amount": 40,
            "load_unit": "hours",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTHENTICATION_REQUIRED"


def test_manual_competency_create_and_read_returns_exact_values() -> None:
    repository = MemoryCompetencyRepository()
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_competency_repository] = lambda: repository

    try:
        created = _request(
            "POST",
            "/people/P-001/competencies",
            {
                "skill_id": "SKILL-1",
                "proficiency_level": 4,
                "evidence": "Migração do cluster",
                "review_date": "2026-11-08",
            },
        )
        read_back = _request("GET", "/people/P-001/competencies")
    finally:
        app.dependency_overrides.clear()

    assert created.status_code == 201
    assert created.json()["person_id"] == "P-001"
    assert created.json()["skill_name"] == "Kubernetes"
    assert created.json()["proficiency_level"] == 4
    assert created.json()["evidence"] == "Migração do cluster"
    assert created.json()["origin_type"] == "MANUAL"
    assert created.json()["actor_id"] == "U-001"
    assert created.json()["review_date"] == "2026-11-08"
    assert read_back.status_code == 200
    assert read_back.json()[0] == created.json()


def test_competency_write_requires_authenticated_actor() -> None:
    response = _request(
        "POST",
        "/people/P-001/competencies",
        {
            "skill_id": "SKILL-1",
            "proficiency_level": 4,
            "evidence": "Migração do cluster",
            "review_date": "2026-11-08",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTHENTICATION_REQUIRED"


def test_competency_repository_error_preserves_field_error() -> None:
    class RejectingCompetencyRepository:
        def create(self, **values: object) -> dict:
            raise CompetencyError("REQUIRED_EVIDENCE", 422, "evidence")

    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_competency_repository] = lambda: RejectingCompetencyRepository()

    try:
        response = _request(
            "POST",
            "/people/P-001/competencies",
            {
                "skill_id": "SKILL-1",
                "proficiency_level": 4,
                "evidence": "Evidence",
                "review_date": "2026-11-08",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "REQUIRED_EVIDENCE"
    assert response.json()["detail"]["fieldErrors"] == {"evidence": "REQUIRED_EVIDENCE"}


def test_competency_read_maps_unknown_person_to_404() -> None:
    class MissingPersonCompetencyRepository:
        def list_for_person(self, person_id: str) -> list[dict]:
            raise CompetencyError("PERSON_NOT_FOUND", 404, "person_id")

    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_competency_repository] = (
        lambda: MissingPersonCompetencyRepository()
    )

    try:
        response = _request("GET", "/people/P-404/competencies")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "PERSON_NOT_FOUND"
    assert response.json()["detail"]["fieldErrors"] == {"person_id": "PERSON_NOT_FOUND"}


def test_invalid_manual_competency_fields_are_rejected_without_partial_insert() -> None:
    repository = MemoryCompetencyRepository()
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_competency_repository] = lambda: repository

    try:
        invalid_level = _request(
            "POST",
            "/people/P-001/competencies",
            {
                "skill_id": "SKILL-1",
                "proficiency_level": 6,
                "evidence": "Evidence",
                "review_date": "2026-11-08",
            },
        )
        missing_evidence = _request(
            "POST",
            "/people/P-001/competencies",
            {
                "skill_id": "SKILL-1",
                "proficiency_level": 4,
                "evidence": "   ",
                "review_date": "2026-11-08",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert invalid_level.status_code == 422
    assert invalid_level.json()["detail"]["fieldErrors"] == {
        "proficiency_level": "INVALID_LEVEL"
    }
    assert missing_evidence.status_code == 422
    assert missing_evidence.json()["detail"]["fieldErrors"] == {
        "evidence": "REQUIRED_EVIDENCE"
    }
    assert repository.rows == []


def test_validation_handler_reports_leaf_field_for_nested_location() -> None:
    error = RequestValidationError(
        [
            {
                "loc": ("body", "competency", "evidence"),
                "msg": "Field required",
                "type": "missing",
            }
        ]
    )
    request = Request({"type": "http", "headers": []})

    response = asyncio.run(handle_request_validation_error(request, error))

    assert response.status_code == 422
    assert b'"evidence":"REQUIRED_EVIDENCE"' in response.body


def test_demand_routes_create_list_and_update_rows() -> None:
    repository = MemoryDemandRepository()
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_demand_repository] = lambda: repository
    payload = {
        "skill_id": "SKILL-1",
        "proficiency_level": 3,
        "period": "2026-01",
        "load_amount": 40,
        "load_unit": "hours",
    }

    try:
        created = _request("POST", "/projects/P-001/demands", payload)
        schedule = _request("GET", "/projects/P-001/demands")
        updated_payload = {**payload, "proficiency_level": 4, "load_amount": 32}
        updated = _request("PATCH", "/projects/P-001/demands/D-001", updated_payload)
    finally:
        app.dependency_overrides.clear()

    assert created.status_code == 201
    assert created.json()["project_id"] == "P-001"
    assert created.json()["actor_id"] == "U-001"
    assert schedule.status_code == 200
    assert schedule.json()[0]["period"] == "2026-01"
    assert updated.status_code == 200
    assert updated.json()["proficiency_level"] == 4
    assert updated.json()["load_amount"] == 32


def test_demand_api_preserves_repository_error_code() -> None:
    class RejectingRepository:
        def create(self, **values: object) -> dict:
            raise DemandError("INVALID_LOAD_UNIT", 422, "load_unit")

    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_demand_repository] = lambda: RejectingRepository()

    try:
        response = _request(
            "POST",
            "/projects/P-001/demands",
            {
                "skill_id": "SKILL-1",
                "proficiency_level": 3,
                "period": "2026-01",
                "load_amount": 40,
                "load_unit": "widgets",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INVALID_LOAD_UNIT"
    assert response.json()["detail"]["fieldErrors"] == {"load_unit": "INVALID_LOAD_UNIT"}


def test_invalid_payload_fields_are_reported_without_changing_schedule() -> None:
    repository = MemoryDemandRepository()
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_demand_repository] = lambda: repository
    valid_payload = {
        "skill_id": "SKILL-1",
        "proficiency_level": 3,
        "period": "2026-01",
        "load_amount": 40,
        "load_unit": "hours",
    }

    try:
        _request("POST", "/projects/P-001/demands", valid_payload)
        original_schedule = [row.copy() for row in repository.rows]
        invalid_level = _request(
            "POST",
            "/projects/P-001/demands",
            {**valid_payload, "proficiency_level": 6},
        )
        invalid_load = _request(
            "POST",
            "/projects/P-001/demands",
            {**valid_payload, "load_amount": -1},
        )
        current_schedule = _request("GET", "/projects/P-001/demands")
    finally:
        app.dependency_overrides.clear()

    assert invalid_level.status_code == 422
    assert invalid_level.json()["detail"]["fieldErrors"] == {
        "proficiency_level": "INVALID_LEVEL"
    }
    assert invalid_load.status_code == 422
    assert invalid_load.json()["detail"]["fieldErrors"] == {"load_amount": "INVALID_LOAD"}
    assert current_schedule.json() == original_schedule


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