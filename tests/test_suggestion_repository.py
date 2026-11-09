from datetime import UTC, datetime

import pytest
from oracle_fakes import FakeConnection, FakeCursor

from voskill.suggestion_review import SuggestionReviewRepository as SuggestionRepository
from voskill.suggestions import SuggestionError


def test_create_suggestion_persists_pending_review_without_confirming_competency() -> None:
    cursor = FakeCursor()
    connection = FakeConnection(cursor)
    repository = SuggestionRepository(connection_factory=lambda: connection)

    suggestion = repository.create_suggestion(
        person_id="P-001",
        skill_name="Kubernetes",
        proficiency_level=4,
        confidence=0.92,
        evidence_span="Migração do cluster Kubernetes",
        source_sha256="a" * 64,
        actor_id="U-001",
    )

    assert suggestion["person_id"] == "P-001"
    assert suggestion["skill_name"] == "Kubernetes"
    assert suggestion["proficiency_level"] == 4
    assert suggestion["confidence"] == 0.92
    assert suggestion["evidence_span"] == "Migração do cluster Kubernetes"
    assert suggestion["status"] == "PENDING_REVIEW"
    assert suggestion["actor_id"] == "U-001"
    assert cursor.suggestion_insert_params is not None
    assert cursor.suggestion_insert_params["status"] == "PENDING_REVIEW"
    assert cursor.competency_insert_params is None
    assert connection.commit_count == 1

def test_suggestion_for_unknown_person_is_rejected_without_insert() -> None:
    cursor = FakeCursor()
    cursor.person_exists = False
    connection = FakeConnection(cursor)
    repository = SuggestionRepository(connection_factory=lambda: connection)

    with pytest.raises(SuggestionError) as raised:
        repository.create_suggestion(
            person_id="P-404",
            skill_name="Kubernetes",
            proficiency_level=4,
            confidence=0.92,
            evidence_span="Kubernetes",
            source_sha256="a" * 64,
            actor_id="U-001",
        )

    assert raised.value.code == "PERSON_NOT_FOUND"
    assert cursor.suggestion_insert_params is None
    assert cursor.competency_insert_params is None
    assert connection.commit_count == 0

def test_accept_suggestion_adds_reviewed_competency_and_updates_status() -> None:
    cursor = FakeCursor()
    cursor.current_competency = None
    cursor.skill_exists = False
    connection = FakeConnection(cursor)
    repository = SuggestionRepository(connection_factory=lambda: connection)

    reviewed = repository.review_suggestion(
        person_id="P-001",
        suggestion_id="SG-001",
        decision="accept",
        reviewer_id="U-001",
    )

    assert reviewed["status"] == "ACCEPTED"
    assert reviewed["reviewed_by"] == "U-001"
    assert reviewed["reviewed_level"] == 4
    assert reviewed["reviewed_evidence"] == "Migração do cluster Kubernetes"
    assert cursor.skill_insert_params["skill_name"] == "Kubernetes"
    assert cursor.competency_insert_params["origin_type"] == "REVIEWED_SUGGESTION"
    assert cursor.competency_insert_params["proficiency_level"] == 4
    assert cursor.suggestion_update_params["status"] == "ACCEPTED"
    assert cursor.suggestion_update_params["reviewer_id"] == "U-001"
    assert connection.commit_count == 1

def test_edit_suggestion_updates_competency_and_retains_original_in_history() -> None:
    cursor = FakeCursor()
    connection = FakeConnection(cursor)
    repository = SuggestionRepository(connection_factory=lambda: connection)

    reviewed = repository.review_suggestion(
        person_id="P-001",
        suggestion_id="SG-001",
        decision="edit",
        reviewer_id="U-001",
        reviewed_level=3,
        reviewed_evidence="Operação de cluster Kubernetes",
    )

    assert reviewed["status"] == "EDITED"
    assert reviewed["reviewed_level"] == 3
    assert reviewed["reviewed_evidence"] == "Operação de cluster Kubernetes"
    assert cursor.history_insert_params["previous_level"] == 4
    assert cursor.history_insert_params["new_level"] == 3
    assert cursor.history_insert_params["actor_id"] == "U-001"
    assert cursor.competency_update_params["proficiency_level"] == 3
    assert cursor.competency_update_params["evidence"] == "Operação de cluster Kubernetes"
    assert cursor.suggestion_update_params["status"] == "EDITED"
    assert connection.commit_count == 1

def test_reject_suggestion_changes_only_review_state() -> None:
    cursor = FakeCursor()
    connection = FakeConnection(cursor)
    repository = SuggestionRepository(connection_factory=lambda: connection)

    reviewed = repository.review_suggestion(
        person_id="P-001",
        suggestion_id="SG-001",
        decision="reject",
        reviewer_id="U-001",
    )

    assert reviewed["status"] == "REJECTED"
    assert reviewed["reviewed_by"] == "U-001"
    assert cursor.suggestion_update_params["status"] == "REJECTED"
    assert cursor.competency_insert_params is None
    assert cursor.competency_update_params is None
    assert cursor.history_insert_params is None
    assert connection.commit_count == 1

def test_already_reviewed_suggestion_cannot_be_applied_twice() -> None:
    cursor = FakeCursor()
    cursor.suggestion_record = (
        "SG-001",
        "P-001",
        "Kubernetes",
        4,
        0.92,
        "Migração do cluster Kubernetes",
        "a" * 64,
        "REJECTED",
        "U-001",
        datetime(2026, 11, 8, tzinfo=UTC),
    )
    connection = FakeConnection(cursor)
    repository = SuggestionRepository(connection_factory=lambda: connection)

    with pytest.raises(SuggestionError) as raised:
        repository.review_suggestion(
            person_id="P-001",
            suggestion_id="SG-001",
            decision="accept",
            reviewer_id="U-001",
        )

    assert raised.value.code == "SUGGESTION_ALREADY_REVIEWED"
    assert cursor.suggestion_update_params is None
    assert cursor.competency_insert_params is None
    assert connection.commit_count == 0