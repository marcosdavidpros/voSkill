from conftest import _request
from suggestion_helpers import MemorySuggestionRepository

from voskill.main import app, get_actor_id, get_suggestion_repository


def test_authorized_review_accepts_suggestion_into_confirmed_profile() -> None:
    repository = MemorySuggestionRepository()
    repository.create_suggestion(
        person_id="P-001",
        skill_name="Kubernetes",
        proficiency_level=4,
        confidence=0.92,
        evidence_span="Migração do cluster Kubernetes",
        source_sha256="a" * 64,
        actor_id="U-001",
    )
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_suggestion_repository] = lambda: repository

    try:
        response = _request(
            "POST",
            "/people/P-001/competency-suggestions/SG-001/review",
            {"decision": "accept"},
            state={"authorized_person_ids": ["P-001"]},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "ACCEPTED"
    assert response.json()["reviewed_by"] == "U-001"
    assert response.json()["reviewed_level"] == 4
    assert repository.confirmed_competencies == [
        {
            "person_id": "P-001",
            "skill_name": "Kubernetes",
            "proficiency_level": 4,
            "evidence": "Migração do cluster Kubernetes",
            "actor_id": "U-001",
        }
    ]


def test_authorized_review_can_edit_values_before_accepting() -> None:
    repository = MemorySuggestionRepository()
    repository.create_suggestion(
        person_id="P-001",
        skill_name="Kubernetes",
        proficiency_level=4,
        confidence=0.92,
        evidence_span="Migração do cluster Kubernetes",
        source_sha256="a" * 64,
        actor_id="U-001",
    )
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_suggestion_repository] = lambda: repository

    try:
        response = _request(
            "POST",
            "/people/P-001/competency-suggestions/SG-001/review",
            {
                "decision": "edit",
                "reviewed_level": 3,
                "reviewed_evidence": "Operação do cluster",
            },
            state={"authorized_person_ids": ["P-001"]},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "EDITED"
    assert response.json()["reviewed_level"] == 3
    assert response.json()["reviewed_evidence"] == "Operação do cluster"
    assert repository.confirmed_competencies[0]["proficiency_level"] == 3


def test_authorized_rejection_does_not_change_confirmed_profile() -> None:
    repository = MemorySuggestionRepository()
    repository.create_suggestion(
        person_id="P-001",
        skill_name="Kubernetes",
        proficiency_level=4,
        confidence=0.92,
        evidence_span="Migração do cluster Kubernetes",
        source_sha256="a" * 64,
        actor_id="U-001",
    )
    original_profile = [row.copy() for row in repository.confirmed_competencies]
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_suggestion_repository] = lambda: repository

    try:
        response = _request(
            "POST",
            "/people/P-001/competency-suggestions/SG-001/review",
            {"decision": "reject"},
            state={"authorized_person_ids": ["P-001"]},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "REJECTED"
    assert response.json()["reviewed_by"] == "U-001"
    assert repository.confirmed_competencies == original_profile


def test_unauthorized_review_returns_403_without_changing_suggestion_or_profile() -> None:
    repository = MemorySuggestionRepository()
    original_suggestion = repository.create_suggestion(
        person_id="P-001",
        skill_name="Kubernetes",
        proficiency_level=4,
        confidence=0.92,
        evidence_span="Migração do cluster Kubernetes",
        source_sha256="a" * 64,
        actor_id="U-001",
    ).copy()
    app.dependency_overrides[get_actor_id] = lambda: "U-999"
    app.dependency_overrides[get_suggestion_repository] = lambda: repository

    try:
        response = _request(
            "POST",
            "/people/P-001/competency-suggestions/SG-001/review",
            {"decision": "accept"},
            state={"authorized_person_ids": []},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert repository.suggestions[0] == original_suggestion
    assert repository.confirmed_competencies == []