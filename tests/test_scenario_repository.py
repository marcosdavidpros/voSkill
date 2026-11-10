import json
from datetime import datetime

import pytest
from oracle_fakes import FakeConnection, FakeCursor

from voskill.database import ScenarioError, ScenarioRepository


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


def test_get_competency_snapshot_returns_scenario_data_with_deltas_applied() -> None:
    snapshot = {
        "periods": {
            "2026-01": {
                "demand": {"CLOUD": {"level": 2, "loadAmount": 10}},
                "availability": {"P-001": {"hours": 40}},
            }
        }
    }
    deltas = {"periods": {"2026-01": {"availability": {"P-001": {"hours": 32}}}}}

    class SnapshotCursor:
        def __enter__(self):
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def execute(self, statement: str, **parameters: object) -> None:
            assert parameters == {"scenario_id": "S-001"}
            self.row = ("P-001", "SNAP-001", json.dumps(deltas), json.dumps(snapshot))

        def fetchone(self) -> tuple:
            return self.row

    class SnapshotConnection:
        def __init__(self) -> None:
            self.closed = False

        def cursor(self) -> SnapshotCursor:
            return SnapshotCursor()

        def close(self) -> None:
            self.closed = True

    connection = SnapshotConnection()
    repository = ScenarioRepository(connection_factory=lambda: connection)

    scenario = repository.get_competency_snapshot("S-001")

    assert scenario["scenario_id"] == "S-001"
    assert scenario["project_id"] == "P-001"
    assert scenario["snapshot_id"] == "SNAP-001"
    assert scenario["snapshot"]["periods"]["2026-01"]["availability"] == {
        "P-001": {"hours": 32}
    }
    assert connection.closed