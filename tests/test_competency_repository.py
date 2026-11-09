from datetime import UTC, date, datetime

import pytest
from oracle_fakes import FakeConnection, FakeCursor

from voskill.database import (
    CompetencyError,
    CompetencyRepository,
    DemandRepository,
    ScenarioRepository,
    open_oracle_connection,
)


def test_create_manual_competency_persists_values_origin_and_actor() -> None:
    cursor = FakeCursor()
    connection = FakeConnection(cursor)
    repository = CompetencyRepository(connection_factory=lambda: connection)

    competency = repository.create(
        person_id="P-001",
        skill_id="SKILL-1",
        proficiency_level=4,
        evidence="Migração do cluster",
        review_date=date(2026, 11, 8),
        actor_id="U-001",
    )

    assert competency["person_id"] == "P-001"
    assert competency["skill_id"] == "SKILL-1"
    assert competency["skill_name"] == "Kubernetes"
    assert competency["proficiency_level"] == 4
    assert competency["evidence"] == "Migração do cluster"
    assert competency["origin_type"] == "MANUAL"
    assert competency["actor_id"] == "U-001"
    assert competency["review_date"] == "2026-11-08"
    assert cursor.competency_insert_params is not None
    assert cursor.competency_insert_params["actor_id"] == "U-001"
    assert cursor.competency_insert_params["origin_type"] == "MANUAL"
    assert connection.commit_count == 1
    assert connection.rollback_count == 0

def test_list_person_competencies_returns_persisted_values() -> None:
    cursor = FakeCursor()
    cursor.competency_rows = [
        (
            "C-001",
            "P-001",
            "SKILL-1",
            "Kubernetes",
            4,
            "Migração do cluster",
            "MANUAL",
            "U-001",
            datetime(2026, 11, 8, tzinfo=UTC),
        )
    ]
    connection = FakeConnection(cursor)
    repository = CompetencyRepository(connection_factory=lambda: connection)

    competencies = repository.list_for_person("P-001")

    assert len(competencies) == 1
    assert competencies[0]["proficiency_level"] == 4
    assert competencies[0]["evidence"] == "Migração do cluster"
    assert competencies[0]["origin_type"] == "MANUAL"
    assert competencies[0]["actor_id"] == "U-001"
    assert competencies[0]["review_date"] == "2026-11-08"

@pytest.mark.parametrize(
    ("proficiency_level", "evidence", "field", "code"),
    [
        (6, "evidence", "proficiency_level", "INVALID_LEVEL"),
        (4, "   ", "evidence", "REQUIRED_EVIDENCE"),
    ],
)
def test_invalid_competency_is_rejected_before_insert(
    proficiency_level: int,
    evidence: str,
    field: str,
    code: str,
) -> None:
    cursor = FakeCursor()
    connection = FakeConnection(cursor)
    repository = CompetencyRepository(connection_factory=lambda: connection)

    with pytest.raises(CompetencyError) as raised:
        repository.create(
            person_id="P-001",
            skill_id="SKILL-1",
            proficiency_level=proficiency_level,
            evidence=evidence,
            review_date=date(2026, 11, 8),
            actor_id="U-001",
        )

    assert raised.value.code == code
    assert raised.value.field == field
    assert cursor.competency_insert_params is None
    assert connection.commit_count == 0
    assert connection.rollback_count == 1

def test_competency_for_unknown_person_is_rejected_before_insert() -> None:
    cursor = FakeCursor()
    cursor.person_exists = False
    connection = FakeConnection(cursor)
    repository = CompetencyRepository(connection_factory=lambda: connection)

    with pytest.raises(CompetencyError) as raised:
        repository.create(
            person_id="P-404",
            skill_id="SKILL-1",
            proficiency_level=4,
            evidence="Evidence",
            review_date=date(2026, 11, 8),
            actor_id="U-001",
        )

    assert raised.value.code == "PERSON_NOT_FOUND"
    assert cursor.competency_insert_params is None

def test_correct_competency_updates_current_and_records_history_atomically() -> None:
    cursor = FakeCursor()
    connection = FakeConnection(cursor)
    repository = CompetencyRepository(connection_factory=lambda: connection)

    corrected = repository.correct(
        person_id="P-001",
        competency_id="C-001",
        proficiency_level=3,
        evidence="Operação do cluster",
        review_date=date(2026, 11, 8),
        actor_id="U-001",
    )

    assert corrected["proficiency_level"] == 3
    assert corrected["evidence"] == "Operação do cluster"
    assert corrected["actor_id"] == "U-001"
    assert cursor.history_insert_params is not None
    assert cursor.history_insert_params["previous_level"] == 4
    assert cursor.history_insert_params["new_level"] == 3
    assert cursor.history_insert_params["previous_evidence"] == "Old evidence"
    assert cursor.history_insert_params["actor_id"] == "U-001"
    assert isinstance(cursor.history_insert_params["changed_at"], datetime)
    assert cursor.competency_update_params is not None
    assert cursor.competency_update_params["proficiency_level"] == 3
    assert connection.commit_count == 1
    assert connection.rollback_count == 0

def test_correction_for_missing_competency_creates_no_history() -> None:
    cursor = FakeCursor()
    cursor.current_competency = None
    connection = FakeConnection(cursor)
    repository = CompetencyRepository(connection_factory=lambda: connection)

    with pytest.raises(CompetencyError) as raised:
        repository.correct(
            person_id="P-001",
            competency_id="C-404",
            proficiency_level=3,
            evidence="New evidence",
            review_date=date(2026, 11, 8),
            actor_id="U-001",
        )

    assert raised.value.code == "COMPETENCY_NOT_FOUND"
    assert cursor.history_insert_params is None
    assert cursor.competency_update_params is None
    assert connection.commit_count == 0
    assert connection.rollback_count == 1

def test_database_facade_reexports_domain_repositories() -> None:
    assert CompetencyRepository.__module__ == "voskill.competencies"
    assert DemandRepository.__module__ == "voskill.demands"
    assert ScenarioRepository.__module__ == "voskill.scenarios"
    assert open_oracle_connection.__module__ == "voskill.connection"