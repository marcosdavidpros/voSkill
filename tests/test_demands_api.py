from api_helpers import MemoryDemandRepository
from conftest import _request

from voskill.database import DemandError
from voskill.main import app, get_actor_id, get_demand_repository


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

def test_demand_routes_carry_title_and_epic_and_delete_rows() -> None:
    repository = MemoryDemandRepository()
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_demand_repository] = lambda: repository
    payload = {
        "skill_id": "SKILL-1",
        "proficiency_level": 3,
        "period": "2026-01",
        "load_amount": 40,
        "load_unit": "hours",
        "title": "Integra\u00e7\u00e3o com fila",
        "epic": "Pagamentos",
    }

    try:
        created = _request("POST", "/projects/P-001/demands", payload)
        listed = _request("GET", "/projects/P-001/demands")
        deleted = _request("DELETE", "/projects/P-001/demands/D-001")
        missing = _request("DELETE", "/projects/P-001/demands/D-001")
        after = _request("GET", "/projects/P-001/demands")
    finally:
        app.dependency_overrides.clear()

    assert created.status_code == 201
    assert created.json()["title"] == "Integra\u00e7\u00e3o com fila"
    assert created.json()["epic"] == "Pagamentos"
    assert listed.json()[0]["epic"] == "Pagamentos"
    assert deleted.status_code == 204
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "DEMAND_NOT_FOUND"
    assert after.json() == []


def test_demand_title_and_epic_are_optional_and_length_limited() -> None:
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
        without_labels = _request("POST", "/projects/P-001/demands", payload)
        too_long = _request("POST", "/projects/P-001/demands", {**payload, "title": "x" * 201})
    finally:
        app.dependency_overrides.clear()

    assert without_labels.status_code == 201
    assert without_labels.json()["title"] is None
    assert without_labels.json()["epic"] is None
    assert too_long.status_code == 422


def test_demand_delete_requires_authenticated_actor() -> None:
    response = _request("DELETE", "/projects/P-001/demands/D-001")

    assert response.status_code == 401


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