from api_helpers import MemorySkillInferenceRepository, MemorySkillRelationRepository
from conftest import _request

from voskill.main import app, get_actor_id, get_skill_relation_repository
from voskill.skill_relations import RelationError


def test_skill_relation_create_requires_explicit_management_authorization() -> None:
    repository = MemorySkillRelationRepository()
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_skill_relation_repository] = lambda: repository

    try:
        response = _request(
            "POST",
            "/skill-relations",
            {
                "source_skill_id": "SKILL-1",
                "target_skill_id": "SKILL-2",
                "confidence": 0.65,
            },
            state={"can_manage_skill_relations": False},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "FORBIDDEN"
    assert repository.rows == []

def test_authorized_user_can_create_skill_relation() -> None:
    repository = MemorySkillRelationRepository()
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_skill_relation_repository] = lambda: repository

    try:
        response = _request(
            "POST",
            "/skill-relations",
            {
                "source_skill_id": "SKILL-1",
                "target_skill_id": "SKILL-2",
                "confidence": 0.65,
            },
            state={"can_manage_skill_relations": True},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["source_skill_id"] == "SKILL-1"
    assert response.json()["target_skill_id"] == "SKILL-2"
    assert response.json()["confidence"] == 0.65
    assert response.json()["actor_id"] == "U-001"
    assert repository.rows[0]["actor_id"] == "U-001"

def test_skill_relation_api_rejects_invalid_confidence() -> None:
    repository = MemorySkillRelationRepository()
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_skill_relation_repository] = lambda: repository

    try:
        response = _request(
            "POST",
            "/skill-relations",
            {
                "source_skill_id": "SKILL-1",
                "target_skill_id": "SKILL-2",
                "confidence": 1.2,
            },
            state={"can_manage_skill_relations": True},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json()["detail"]["fieldErrors"] == {
        "confidence": "INVALID_CONFIDENCE"
    }
    assert repository.rows == []

def test_skill_relation_api_maps_unknown_skill_error() -> None:
    class UnknownSkillRepository:
        def create(self, **values: object) -> dict:
            raise RelationError("UNKNOWN_SKILL", 422, "target_skill_id")

    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_skill_relation_repository] = lambda: UnknownSkillRepository()

    try:
        response = _request(
            "POST",
            "/skill-relations",
            {
                "source_skill_id": "SKILL-1",
                "target_skill_id": "SKILL-404",
                "confidence": 0.65,
            },
            state={"can_manage_skill_relations": True},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "UNKNOWN_SKILL"
    assert response.json()["detail"]["fieldErrors"] == {
        "target_skill_id": "UNKNOWN_SKILL"
    }

def test_skill_inference_returns_traceable_result_without_changing_profile() -> None:
    repository = MemorySkillInferenceRepository(
        {
            "status": "inferred",
            "inferred_level": 4,
            "source_skill_id": "SKILL-1",
            "relation_id": "REL-001",
            "confidence": 0.65,
            "reason": None,
        }
    )
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_skill_relation_repository] = lambda: repository

    try:
        response = _request(
            "GET",
            "/people/P-001/skill-inference/SKILL-2",
            state={"authorized_person_ids": ["P-001"]},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "inferred"
    assert response.json()["inferred_level"] == 4
    assert response.json()["relationId"] == "REL-001"
    assert response.json()["confidence"] == 0.65
    assert repository.calls == [("P-001", "SKILL-2")]
    assert repository.confirmed_competencies == {"SKILL-1": 4}

def test_skill_inference_without_evidence_returns_no_level() -> None:
    repository = MemorySkillInferenceRepository(
        {
            "status": "insufficient_evidence",
            "inferred_level": None,
            "source_skill_id": None,
            "relation_id": None,
            "confidence": None,
            "reason": "insufficient_evidence",
        }
    )
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_skill_relation_repository] = lambda: repository

    try:
        response = _request(
            "GET",
            "/people/P-001/skill-inference/SKILL-2",
            state={"authorized_person_ids": ["P-001"]},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["inferred_level"] is None
    assert response.json()["reason"] == "insufficient_evidence"

def test_skill_inference_requires_person_authorization() -> None:
    repository = MemorySkillInferenceRepository({"status": "inferred"})
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_skill_relation_repository] = lambda: repository

    try:
        response = _request(
            "GET",
            "/people/P-001/skill-inference/SKILL-2",
            state={"authorized_person_ids": []},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert repository.calls == []