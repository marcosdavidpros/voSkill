from api_helpers import MemoryCompetencyRepository
from conftest import _request

from voskill.database import CompetencyError
from voskill.main import app, get_actor_id, get_competency_repository


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
            state={"authorized_person_ids": ["P-001"]},
        )
        read_back = _request(
            "GET",
            "/people/P-001/competencies",
            state={"authorized_person_ids": ["P-001"]},
        )
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
            state={"authorized_person_ids": ["P-001"]},
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
        response = _request(
            "GET",
            "/people/P-404/competencies",
            state={"authorized_person_ids": ["P-404"]},
        )
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
            state={"authorized_person_ids": ["P-001"]},
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
            state={"authorized_person_ids": ["P-001"]},
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