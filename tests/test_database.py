import json
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Self
from unittest.mock import patch

import pytest

from voskill.config import OracleCredentials
from voskill.database import (
    CompetencyError,
    CompetencyRepository,
    DemandError,
    DemandRepository,
    ScenarioError,
    ScenarioRepository,
    open_oracle_connection,
)


class FakeCursor:
    def __init__(self, demand_rows: list[tuple] | None = None) -> None:
        self.project = (date(2026, 1, 1), date(2026, 6, 1), "hours")
        self.person_exists = True
        self.base_scenario = ("B-001", "P-001", "S-001")
        self.skill_exists = True
        self.demand_rows = demand_rows or []
        self.statements: list[tuple[str, dict]] = []
        self.current_one = None
        self.current_rows: list[tuple] = []
        self.insert_params: dict | None = None
        self.update_params: dict | None = None
        self.scenario_insert_params: dict | None = None
        self.scenario_records: list[tuple] = []
        self.competency_rows: list[tuple] = []
        self.competency_insert_params: dict | None = None
        self.rowcount = 1

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, statement: str, parameters: dict | None = None, **kwargs: object) -> None:
        bound = dict(parameters or {})
        bound.update(kwargs)
        normalized = " ".join(statement.upper().split())
        self.statements.append((normalized, bound))

        if "FROM VSK_PROJECTS" in normalized:
            self.current_one = self.project
        elif "JOIN VSK_SKILLS" in normalized and "VSK_PERSON_COMPETENCIES" in normalized:
            self.current_rows = self.competency_rows
        elif "FROM VSK_PERSONS" in normalized:
            self.current_one = (bound.get("person_id"),) if self.person_exists else None
        elif "FROM VSK_PERSON_COMPETENCIES" in normalized:
            self.current_one = None
        elif "FROM VSK_SKILLS" in normalized:
            self.current_one = ("SKILL-1", "Kubernetes") if self.skill_exists else None
        elif normalized.startswith("SELECT DEMAND_ID"):
            self.current_rows = self.demand_rows
        elif normalized.startswith("INSERT INTO VSK_PROJECT_DEMANDS"):
            self.insert_params = bound
        elif normalized.startswith("UPDATE VSK_PROJECT_DEMANDS"):
            self.update_params = bound
        elif normalized.startswith("INSERT INTO VSK_PERSON_COMPETENCIES"):
            self.competency_insert_params = bound
        elif "JOIN VSK_SCENARIO_SNAPSHOTS" in normalized:
            self.current_rows = self.scenario_records
        elif "FROM VSK_SCENARIOS" in normalized:
            self.current_one = (
                self.base_scenario
                if self.base_scenario is not None
                and bound.get("base_scenario_id") == self.base_scenario[0]
                else None
            )
        elif normalized.startswith("INSERT INTO VSK_SCENARIOS"):
            self.scenario_insert_params = bound

    def fetchone(self) -> tuple | None:
        return self.current_one

    def fetchall(self) -> list[tuple]:
        return self.current_rows


class FakeConnection:
    def __init__(self, cursor: FakeCursor) -> None:
        self.fake_cursor = cursor
        self.commit_count = 0
        self.rollback_count = 0
        self.closed = False

    def cursor(self) -> FakeCursor:
        return self.fake_cursor

    def commit(self) -> None:
        self.commit_count += 1

    def rollback(self) -> None:
        self.rollback_count += 1

    def close(self) -> None:
        self.closed = True


def test_open_oracle_connection_uses_explicit_credentials() -> None:
    credentials = OracleCredentials(
        user="app_user",
        password="secret",
        dsn="//db.example:1521/service",
    )
    connection = object()

    with patch("voskill.database.oracledb.connect", return_value=connection) as connect:
        result = open_oracle_connection(credentials)

    assert result is connection
    connect.assert_called_once_with(
        user="app_user",
        password="secret",
        dsn="//db.example:1521/service",
    )


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


def test_create_alternative_reuses_immutable_snapshot_and_records_deltas() -> None:
    cursor = FakeCursor()
    connection = FakeConnection(cursor)
    repository = ScenarioRepository(connection_factory=lambda: connection)
    deltas = {"demandOverrides": [{"period": "2026-01", "loadAmount": 48}]}

    alternative = repository.create_alternative(
        base_scenario_id="B-001",
        name="Alternative A",
        deltas=deltas,
        actor_id="U-001",
    )

    assert alternative["base_scenario_id"] == "B-001"
    assert alternative["project_id"] == "P-001"
    assert alternative["snapshot_id"] == "S-001"
    assert alternative["actor_id"] == "U-001"
    assert isinstance(alternative["created_at"], datetime)
    assert alternative["deltas"] == deltas
    assert cursor.scenario_insert_params is not None
    assert cursor.scenario_insert_params["snapshot_id"] == "S-001"
    assert json.loads(cursor.scenario_insert_params["deltas_json"]) == deltas
    assert not any(
        statement.startswith(("UPDATE VSK_SCENARIO_SNAPSHOTS", "DELETE FROM VSK_SCENARIO_SNAPSHOTS"))
        for statement, _ in cursor.statements
    )
    assert connection.commit_count == 1
    assert connection.rollback_count == 0
    assert connection.closed


def test_create_alternative_for_missing_base_does_not_insert() -> None:
    cursor = FakeCursor()
    cursor.base_scenario = None
    connection = FakeConnection(cursor)
    repository = ScenarioRepository(connection_factory=lambda: connection)

    with pytest.raises(ScenarioError) as raised:
        repository.create_alternative(
            base_scenario_id="B-404",
            name="Alternative A",
            deltas={"demandOverrides": []},
            actor_id="U-001",
        )

    assert raised.value.code == "BASE_SCENARIO_NOT_FOUND"
    assert cursor.scenario_insert_params is None
    assert connection.commit_count == 0
    assert connection.rollback_count == 1


def test_compare_merges_scenario_deltas_and_marks_missing_availability() -> None:
    snapshot = {
        "periods": {
            "2026-01": {
                "demand": {"SKILL-1": {"level": 3, "loadAmount": 40}},
                "availability": {"PERSON-1": {"hours": 40}},
            },
            "2026-02": {
                "demand": {"SKILL-1": {"level": 3, "loadAmount": 32}},
                "availability": {"PERSON-1": {"hours": 32}},
            },
        }
    }
    deltas = {
        "periods": {
            "2026-01": {"demand": {"SKILL-1": {"loadAmount": 48}}},
            "2026-02": {"availability": None},
        }
    }
    cursor = FakeCursor()
    cursor.scenario_records = [
        ("S-001", "P-001", "SNAP-1", "BASE", "{}", json.dumps(snapshot)),
        (
            "S-002",
            "P-001",
            "SNAP-1",
            "ALTERNATIVE",
            json.dumps(deltas),
            json.dumps(snapshot),
        ),
    ]
    connection = FakeConnection(cursor)
    repository = ScenarioRepository(connection_factory=lambda: connection)

    comparison = repository.compare("S-001", "S-002")

    assert comparison["scenario_ids"] == ["S-001", "S-002"]
    scenarios = {scenario["scenario_id"]: scenario for scenario in comparison["scenarios"]}
    assert scenarios["S-001"]["status"] == "complete"
    assert scenarios["S-002"]["status"] == "incomplete"
    assert scenarios["S-002"]["missing"] == [{"period": "2026-02", "field": "availability"}]
    january = next(row for row in comparison["periods"] if row["period"] == "2026-01")
    assert january["assumptions"]["S-001"]["demand"]["SKILL-1"]["loadAmount"] == 40
    assert january["assumptions"]["S-002"]["demand"]["SKILL-1"]["loadAmount"] == 48
    assert "demand" in january["changed_values"]
    assert "metrics" not in comparison
    assert not any(
        statement.startswith(("INSERT", "UPDATE", "DELETE"))
        for statement, _ in cursor.statements
    )
    assert connection.commit_count == 0


def test_compare_returns_error_for_unknown_scenario() -> None:
    cursor = FakeCursor()
    connection = FakeConnection(cursor)
    repository = ScenarioRepository(connection_factory=lambda: connection)

    with pytest.raises(ScenarioError) as raised:
        repository.compare("S-404", "S-405")

    assert raised.value.code == "UNKNOWN_SCENARIO"
    assert raised.value.status_code == 404
    assert connection.commit_count == 0