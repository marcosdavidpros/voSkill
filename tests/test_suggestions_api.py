from hashlib import sha256

from conftest import _request
from suggestion_helpers import (
    FailedCompetencyExtractor,
    FixedCompetencyExtractor,
    MemorySuggestionRepository,
    UnsupportedEvidenceExtractor,
)

from voskill.main import app, get_actor_id, get_competency_extractor, get_suggestion_repository


def test_extraction_stores_pending_suggestion_without_changing_confirmed_profile() -> None:
    repository = MemorySuggestionRepository()
    confirmed_before = [row.copy() for row in repository.confirmed_competencies]
    source_text = "Experiência: Migração do cluster Kubernetes."
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_suggestion_repository] = lambda: repository
    app.dependency_overrides[get_competency_extractor] = lambda: FixedCompetencyExtractor()

    try:
        response = _request(
            "POST",
            "/people/P-001/competency-suggestions/extract",
            {"source_text": source_text},
            state={"authorized_person_ids": ["P-001"]},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["skill_name"] == "Kubernetes"
    assert response.json()["proficiency_level"] == 4
    assert response.json()["confidence"] == 0.92
    assert response.json()["evidence_span"] == "Migração do cluster Kubernetes"
    assert response.json()["status"] == "PENDING_REVIEW"
    assert response.json()["actor_id"] == "U-001"
    assert response.json()["source_sha256"] == sha256(source_text.encode("utf-8")).hexdigest()
    assert "source_text" not in repository.suggestions[0]
    assert len(repository.suggestions) == 1
    assert repository.confirmed_competencies == confirmed_before


def test_empty_source_returns_error_without_persisting_suggestion() -> None:
    repository = MemorySuggestionRepository()
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_suggestion_repository] = lambda: repository
    app.dependency_overrides[get_competency_extractor] = lambda: FixedCompetencyExtractor()

    try:
        response = _request(
            "POST",
            "/people/P-001/competency-suggestions/extract",
            {"source_text": "   "},
            state={"authorized_person_ids": ["P-001"]},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "EMPTY_SOURCE"
    assert repository.suggestions == []
    assert repository.confirmed_competencies == []


def test_extractor_failure_returns_provider_unavailable_without_persisting() -> None:
    repository = MemorySuggestionRepository()
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_suggestion_repository] = lambda: repository
    app.dependency_overrides[get_competency_extractor] = lambda: FailedCompetencyExtractor()

    try:
        response = _request(
            "POST",
            "/people/P-001/competency-suggestions/extract",
            {"source_text": "Migração do cluster Kubernetes"},
            state={"authorized_person_ids": ["P-001"]},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "PROVIDER_UNAVAILABLE"
    assert repository.suggestions == []
    assert repository.confirmed_competencies == []


def test_extractor_evidence_must_be_an_exact_source_span() -> None:
    repository = MemorySuggestionRepository()
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_suggestion_repository] = lambda: repository
    app.dependency_overrides[get_competency_extractor] = lambda: UnsupportedEvidenceExtractor()

    try:
        response = _request(
            "POST",
            "/people/P-001/competency-suggestions/extract",
            {"source_text": "Migração do cluster Kubernetes"},
            state={"authorized_person_ids": ["P-001"]},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "EVIDENCE_NOT_IN_SOURCE"
    assert repository.suggestions == []
    assert repository.confirmed_competencies == []
