from datetime import date
from decimal import Decimal

import pytest
from oracle_fakes import FakeConnection, FakeCursor

from voskill.database import DemandError, DemandRepository


def test_create_demand_persists_values_and_commits() -> None:
    cursor = FakeCursor()
    connection = FakeConnection(cursor)
    repository = DemandRepository(connection_factory=lambda: connection)

    result = repository.create(
        project_id="P-001",
        skill_id="SKILL-1",
        proficiency_level=3,
        period_start=date(2026, 1, 1),
        load_amount=Decimal(40),
        load_unit="hours",
        actor_id="U-001",
    )

    assert result["project_id"] == "P-001"
    assert result["skill_id"] == "SKILL-1"
    assert result["proficiency_level"] == 3
    assert result["period"] == "2026-01"
    assert result["load_amount"] == Decimal(40)
    assert result["load_unit"] == "hours"
    assert cursor.insert_params is not None
    assert cursor.insert_params["actor_id"] == "U-001"
    assert connection.commit_count == 1
    assert connection.rollback_count == 0
    assert connection.closed

def test_list_demands_returns_each_period_without_collapsing_rows() -> None:
    cursor = FakeCursor(
        [
            ("D-1", "P-001", "SKILL-1", 3, date(2026, 1, 1), Decimal(40), "hours", "U-001"),
            ("D-2", "P-001", "SKILL-1", 4, date(2026, 2, 1), Decimal(32), "hours", "U-001"),
        ]
    )
    connection = FakeConnection(cursor)
    repository = DemandRepository(connection_factory=lambda: connection)

    result = repository.list_for_project("P-001")

    assert [row["period"] for row in result] == ["2026-01", "2026-02"]
    assert [row["load_amount"] for row in result] == [Decimal(40), Decimal(32)]
    assert [row["demand_id"] for row in result] == ["D-1", "D-2"]

def test_update_demand_keeps_row_editable() -> None:
    cursor = FakeCursor()
    connection = FakeConnection(cursor)
    repository = DemandRepository(connection_factory=lambda: connection)

    result = repository.update(
        demand_id="D-1",
        project_id="P-001",
        skill_id="SKILL-1",
        proficiency_level=4,
        period_start=date(2026, 2, 1),
        load_amount=Decimal(32),
        load_unit="hours",
        actor_id="U-002",
    )

    assert result["demand_id"] == "D-1"
    assert result["proficiency_level"] == 4
    assert result["period"] == "2026-02"
    assert result["load_amount"] == Decimal(32)
    assert cursor.update_params is not None
    assert cursor.update_params["actor_id"] == "U-002"
    assert connection.commit_count == 1

def test_unsupported_load_unit_is_rejected_without_insert() -> None:
    cursor = FakeCursor()
    connection = FakeConnection(cursor)
    repository = DemandRepository(connection_factory=lambda: connection)

    with pytest.raises(DemandError) as raised:
        repository.create(
            project_id="P-001",
            skill_id="SKILL-1",
            proficiency_level=3,
            period_start=date(2026, 1, 1),
            load_amount=Decimal(40),
            load_unit="widgets",
            actor_id="U-001",
        )

    assert raised.value.code == "INVALID_LOAD_UNIT"
    assert raised.value.field == "load_unit"
    assert cursor.insert_params is None
    assert connection.commit_count == 0
    assert connection.rollback_count == 1

def test_out_of_horizon_demand_is_rejected_without_insert() -> None:
    cursor = FakeCursor()
    connection = FakeConnection(cursor)
    repository = DemandRepository(connection_factory=lambda: connection)

    with pytest.raises(DemandError) as raised:
        repository.create(
            project_id="P-001",
            skill_id="SKILL-1",
            proficiency_level=3,
            period_start=date(2026, 7, 1),
            load_amount=Decimal(40),
            load_unit="hours",
            actor_id="U-001",
        )

    assert raised.value.code == "PERIOD_OUTSIDE_HORIZON"
    assert raised.value.field == "period"
    assert cursor.insert_params is None
    assert connection.commit_count == 0

@pytest.mark.parametrize(
    ("proficiency_level", "load_amount", "field", "code"),
    [
        (6, Decimal(40), "proficiency_level", "INVALID_LEVEL"),
        (3, Decimal(-1), "load_amount", "INVALID_LOAD"),
    ],
)
def test_invalid_level_or_load_is_rejected_before_insert(
    proficiency_level: int,
    load_amount: Decimal,
    field: str,
    code: str,
) -> None:
    cursor = FakeCursor()
    connection = FakeConnection(cursor)
    repository = DemandRepository(connection_factory=lambda: connection)

    with pytest.raises(DemandError) as raised:
        repository.create(
            project_id="P-001",
            skill_id="SKILL-1",
            proficiency_level=proficiency_level,
            period_start=date(2026, 1, 1),
            load_amount=load_amount,
            load_unit="hours",
            actor_id="U-001",
        )

    assert raised.value.code == code
    assert raised.value.field == field
    assert cursor.insert_params is None
    assert connection.commit_count == 0

def test_unknown_skill_is_rejected_before_insert() -> None:
    cursor = FakeCursor()
    cursor.skill_exists = False
    connection = FakeConnection(cursor)
    repository = DemandRepository(connection_factory=lambda: connection)

    with pytest.raises(DemandError) as raised:
        repository.create(
            project_id="P-001",
            skill_id="SKILL-404",
            proficiency_level=3,
            period_start=date(2026, 1, 1),
            load_amount=Decimal(40),
            load_unit="hours",
            actor_id="U-001",
        )

    assert raised.value.code == "UNKNOWN_SKILL"
    assert raised.value.field == "skill_id"
    assert cursor.insert_params is None
    assert connection.commit_count == 0