import pytest
from oracle_fakes import FakeConnection, FakeCursor

from voskill.skill_relations import RelationError, SkillRelationRepository


def test_create_skill_relation_persists_confidence_and_actor() -> None:
    cursor = FakeCursor()
    cursor.skill_ids = {"SKILL-1", "SKILL-2"}
    connection = FakeConnection(cursor)
    repository = SkillRelationRepository(connection_factory=lambda: connection)

    relation = repository.create(
        source_skill_id="SKILL-1",
        target_skill_id="SKILL-2",
        confidence=0.65,
        actor_id="U-001",
    )

    assert relation["source_skill_id"] == "SKILL-1"
    assert relation["target_skill_id"] == "SKILL-2"
    assert relation["confidence"] == 0.65
    assert relation["actor_id"] == "U-001"
    assert cursor.relation_insert_params is not None
    assert cursor.relation_insert_params["confidence"] == 0.65
    assert connection.commit_count == 1

def test_unknown_source_skill_is_rejected_without_storing_relation() -> None:
    cursor = FakeCursor()
    connection = FakeConnection(cursor)
    repository = SkillRelationRepository(connection_factory=lambda: connection)

    with pytest.raises(RelationError) as raised:
        repository.create(
            source_skill_id="SKILL-404",
            target_skill_id="SKILL-1",
            confidence=0.65,
            actor_id="U-001",
        )

    assert raised.value.code == "UNKNOWN_SKILL"
    assert cursor.relation_insert_params is None
    assert connection.commit_count == 0

def test_confidence_above_one_is_rejected_without_storing_relation() -> None:
    cursor = FakeCursor()
    connection = FakeConnection(cursor)
    repository = SkillRelationRepository(connection_factory=lambda: connection)

    with pytest.raises(RelationError) as raised:
        repository.create(
            source_skill_id="SKILL-1",
            target_skill_id="SKILL-2",
            confidence=1.2,
            actor_id="U-001",
        )

    assert raised.value.code == "INVALID_CONFIDENCE"
    assert cursor.relation_insert_params is None
    assert connection.commit_count == 0

def test_infer_for_person_returns_source_level_and_relation_provenance() -> None:
    cursor = FakeCursor()
    cursor.inference_record = ("REL-001", "SKILL-1", "SKILL-2", 0.65, 4)
    connection = FakeConnection(cursor)
    repository = SkillRelationRepository(connection_factory=lambda: connection)

    inference = repository.infer_for_person("P-001", "SKILL-2")

    assert inference == {
        "status": "inferred",
        "person_id": "P-001",
        "target_skill_id": "SKILL-2",
        "inferred_level": 4,
        "source_skill_id": "SKILL-1",
        "relation_id": "REL-001",
        "confidence": 0.65,
        "reason": None,
    }
    query = next(
        statement
        for statement, _ in cursor.statements
        if "FROM VSK_SKILL_RELATIONS" in statement
    )
    assert "ACTIVE_FLAG = 'Y'" in query
    assert "VSK_PERSON_COMPETENCIES" in query
    assert connection.commit_count == 0
    assert connection.rollback_count == 0
    assert cursor.competency_insert_params is None

def test_infer_for_person_without_relation_or_confirmed_source_is_insufficient() -> None:
    cursor = FakeCursor()
    connection = FakeConnection(cursor)
    repository = SkillRelationRepository(connection_factory=lambda: connection)

    inference = repository.infer_for_person("P-001", "SKILL-2")

    assert inference == {
        "status": "insufficient_evidence",
        "person_id": "P-001",
        "target_skill_id": "SKILL-2",
        "inferred_level": None,
        "source_skill_id": None,
        "relation_id": None,
        "confidence": None,
        "reason": "insufficient_evidence",
    }
    assert connection.commit_count == 0
    assert cursor.competency_insert_params is None