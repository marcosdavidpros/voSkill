from datetime import UTC, datetime
from json import loads

import pytest

from voskill.optimization_runs import (
    OptimizationRunError,
    OptimizationRunRepository,
    run_optimization,
)


def _snapshot() -> dict:
    return {
        "snapshot_id": "S-001",
        "profiles": [
            {
                "person_id": "P-001",
                "competencies": {"SKILL-1": 4},
                "availability": {"2026-01": 40},
            },
            {
                "person_id": "P-002",
                "competencies": {"SKILL-1": 2},
                "availability": {"2026-01": 50},
            },
        ],
        "demands": [
            {
                "demand_id": "D-001",
                "skill_id": "SKILL-1",
                "proficiency_level": 3,
                "period": "2026-01",
                "load_amount": 40,
            }
        ],
    }


class MemoryOptimizationRunRepository:
    def __init__(self) -> None:
        self.records: dict[str, dict] = {}

    def create_run(self, **values: object) -> dict:
        record = {
            **values,
            "created_at": datetime(2026, 11, 9, tzinfo=UTC),
        }
        self.records[record["run_id"]] = record
        return record

    def get_run(self, run_id: str) -> dict:
        if run_id not in self.records:
            raise OptimizationRunError("RUN_NOT_FOUND", 404)
        return self.records[run_id]


class FakeCursor:
    def __init__(self) -> None:
        self.params: dict | None = None
        self.insert_params: dict | None = None
        self.row: tuple | None = None
        self.current: tuple | None = None

    def __enter__(self):
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, statement: str, **parameters: object) -> None:
        normalized = " ".join(statement.upper().split())
        self.params = dict(parameters)
        if normalized.startswith("INSERT INTO VSK_OPTIMIZATION_RUNS"):
            self.insert_params = dict(parameters)
            self.row = (
                parameters["run_id"],
                parameters["snapshot_hash"],
                parameters["algorithm_version"],
                parameters["configuration_json"],
                parameters["seed"],
                parameters["alternatives_hash"],
                parameters["result_json"],
                parameters["actor_id"],
                parameters["created_at"],
            )
        elif normalized.startswith("SELECT RUN_ID"):
            self.current = self.row

    def fetchone(self) -> tuple | None:
        return self.current


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


def test_same_snapshot_and_seed_produce_identical_run_metadata_and_hashes() -> None:
    repository = MemoryOptimizationRunRepository()

    first = run_optimization(
        _snapshot(),
        seed=42,
        actor_id="U-001",
        repository=repository,
        population_size=20,
        generations=12,
    )
    second = run_optimization(
        _snapshot(),
        seed=42,
        actor_id="U-001",
        repository=repository,
        population_size=20,
        generations=12,
    )

    metadata_fields = (
        "snapshot_hash",
        "algorithm_version",
        "configuration",
        "seed",
        "alternatives_hash",
    )
    assert {field: first[field] for field in metadata_fields} == {
        field: second[field] for field in metadata_fields
    }
    assert first["created_at"] == datetime(2026, 11, 9, tzinfo=UTC)
    assert first["run_id"] != second["run_id"]


def test_negative_seed_is_rejected_without_creating_a_run_record() -> None:
    repository = MemoryOptimizationRunRepository()

    with pytest.raises(OptimizationRunError) as raised:
        run_optimization(
            _snapshot(),
            seed=-1,
            actor_id="U-001",
            repository=repository,
        )

    assert raised.value.code == "INVALID_SEED"
    assert raised.value.status_code == 422
    assert repository.records == {}


def test_optimization_run_repository_persists_and_reads_run_metadata() -> None:
    cursor = FakeCursor()
    connection = FakeConnection(cursor)
    repository = OptimizationRunRepository(connection_factory=lambda: connection)
    values = {
        "run_id": "RUN-001",
        "snapshot_hash": "a" * 64,
        "algorithm_version": "pymoo-0.6.2",
        "configuration": {"population_size": 20, "generations": 12},
        "seed": 42,
        "alternatives_hash": "b" * 64,
        "result": {"status": "feasible", "feasible_alternatives": []},
        "actor_id": "U-001",
        "created_at": datetime(2026, 11, 9, tzinfo=UTC),
    }

    created = repository.create_run(**values)
    retrieved = repository.get_run("RUN-001")

    assert created["snapshot_hash"] == "a" * 64
    assert created["algorithm_version"] == "pymoo-0.6.2"
    assert created["configuration"] == values["configuration"]
    assert created["seed"] == 42
    assert created["created_at"] == values["created_at"]
    assert retrieved["result"] == values["result"]
    assert loads(cursor.insert_params["configuration_json"]) == values["configuration"]
    assert connection.commit_count == 1
    assert connection.closed