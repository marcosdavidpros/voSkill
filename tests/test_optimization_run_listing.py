import json
from datetime import UTC, datetime

from conftest import _request

from voskill.api.dependencies import get_actor_id, get_optimization_run_repository
from voskill.main import app
from voskill.optimization_runs import OptimizationRunRepository

CREATED_AT = datetime(2026, 11, 9, 12, 0, tzinfo=UTC)
RESULT = {
    "feasible_alternatives": [{"alternative_id": "A-001"}, {"alternative_id": "A-002"}],
    "run_metadata": {"snapshot_id": "SNP-1"},
}


class FakeCursor:
    def __init__(self) -> None:
        self.statements: list[tuple[str, dict[str, object]]] = []
        self.rows: list[tuple[object, ...]] = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def execute(self, statement: str, **binds: object) -> None:
        self.statements.append((statement, binds))
        if "FROM VSK_OPTIMIZATION_RUNS" in statement:
            self.rows = [("RUN-1", json.dumps(RESULT), CREATED_AT), ("RUN-2", "{}", CREATED_AT)]
        elif "FROM VSK_SCENARIOS" in statement:
            self.rows = [("SNP-1", "Baseline", "Atlas")]

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self) -> None:
        self.cursor_value = FakeCursor()
        self.closed = False

    def cursor(self):
        return self.cursor_value

    def close(self):
        self.closed = True


def test_list_runs_returns_scenario_names_and_alternative_ids() -> None:
    connection = FakeConnection()
    repository = OptimizationRunRepository(lambda: connection)

    runs = repository.list_runs("U-001", can_audit=False)

    assert runs == [
        {
            "run_id": "RUN-1",
            "created_at": CREATED_AT,
            "scenario_name": "Baseline",
            "project_name": "Atlas",
            "alternative_ids": ["A-001", "A-002"],
        },
        {
            "run_id": "RUN-2",
            "created_at": CREATED_AT,
            "scenario_name": None,
            "project_name": None,
            "alternative_ids": [],
        },
    ]
    runs_statement, binds = connection.cursor_value.statements[0]
    assert "ACTOR_ID = :actor_id" in runs_statement
    assert binds == {"actor_id": "U-001"}
    assert connection.closed is True


def test_auditor_lists_runs_from_every_actor() -> None:
    connection = FakeConnection()
    repository = OptimizationRunRepository(lambda: connection)

    repository.list_runs("U-001", can_audit=True)

    runs_statement, binds = connection.cursor_value.statements[0]
    assert "ACTOR_ID" not in runs_statement.split("ORDER BY")[0].split("FROM")[1]
    assert binds == {}


class MemoryRepository:
    def __init__(self) -> None:
        self.calls: list[tuple[str, bool]] = []

    def list_runs(self, actor_id: str, can_audit: bool) -> list[dict[str, object]]:
        self.calls.append((actor_id, can_audit))
        return [{
            "run_id": "RUN-1",
            "created_at": CREATED_AT,
            "scenario_name": "Baseline",
            "project_name": "Atlas",
            "alternative_ids": ["A-001"],
        }]


def test_runs_endpoint_lists_runs_for_the_authenticated_actor() -> None:
    repository = MemoryRepository()
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_optimization_run_repository] = lambda: repository
    try:
        response = _request("GET", "/optimization-runs")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()[0]["run_id"] == "RUN-1"
    assert response.json()[0]["scenario_name"] == "Baseline"
    assert response.json()[0]["alternative_ids"] == ["A-001"]
    assert repository.calls == [("U-001", False)]


def test_runs_endpoint_requires_authentication() -> None:
    assert _request("GET", "/optimization-runs").status_code == 401
