import hashlib
import json
from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest

from voskill.base_scenarios import BaseScenarioRepository
from voskill.scenario_comparison import ScenarioError


class FakeCursor:
    def __init__(
        self,
        *,
        person_exists: bool = True,
        scenario_row: tuple[object, ...] | None = ("PRJ-001", "BASE"),
        alternatives: int = 0,
        name_taken: bool = False,
    ) -> None:
        self.person_exists = person_exists
        self.scenario_row = scenario_row
        self.alternatives = alternatives
        self.name_taken = name_taken
        self.update_params: dict[str, object] | None = None
        self.one = None
        self.rows = []
        self.statements: list[tuple[str, dict[str, object]]] = []
        self.snapshot_params: dict[str, object] | None = None
        self.scenario_params: dict[str, object] | None = None

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def execute(self, statement: str, **binds: object) -> None:
        self.statements.append((statement, binds))
        if "SELECT PROJECT_ID, SCENARIO_TYPE" in statement:
            self.one = self.scenario_row
        elif "SELECT COUNT(*)" in statement and "BASE_SCENARIO_ID" in statement:
            self.one = (self.alternatives,)
        elif "UPDATE VSK_SCENARIOS" in statement:
            self.update_params = binds
        elif "FROM VSK_PROJECTS" in statement:
            self.one = (date(2026, 1, 1), date(2026, 12, 1), "hours")
        elif "SELECT SCENARIO_ID" in statement and "FROM VSK_SCENARIOS" in statement:
            self.one = ("OTHER",) if self.name_taken else None
        elif "FROM VSK_PROJECT_DEMANDS" in statement:
            self.rows = [("D-001", "SKILL-1", 3, date(2026, 1, 1), Decimal(10), "hours")]
        elif "FROM VSK_PERSONS" in statement:
            self.one = ("P-001",) if self.person_exists else None
        elif "FROM VSK_PERSON_COMPETENCIES" in statement:
            self.rows = [("SKILL-1", 4)]
        elif "INSERT INTO VSK_SCENARIO_SNAPSHOTS" in statement:
            self.snapshot_params = binds
        elif "INSERT INTO VSK_SCENARIOS" in statement:
            self.scenario_params = binds
        elif "SELECT S.SCENARIO_ID, S.SCENARIO_NAME" in statement:
            self.rows = [("SCN-001", "Baseline", "BASE", "PRJ-001", "Atlas")]
        elif "SELECT S.SCENARIO_TYPE, P.SNAPSHOT_JSON" in statement:
            self.one = ("BASE", json.dumps({
                "snapshot_id": "SNP-001",
                "profiles": [{"person_id": "P-001", "competencies": {"SKILL-1": 4}, "availability": {"2026-01": 40.0}}],
                "demands": [{"demand_id": "D-001", "skill_id": "SKILL-1", "proficiency_level": 3, "period": "2026-01", "load_amount": 10.0}],
                "periods": {"2026-01": {"demand": {"SKILL-1": {"level": 3, "loadAmount": 10.0}}, "availability": {"P-001": {"hours": 40.0}}}},
            }))

    def fetchone(self):
        return self.one

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, cursor: FakeCursor) -> None:
        self.cursor_value = cursor
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def cursor(self):
        return self.cursor_value

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


def _participants() -> list[dict[str, object]]:
    return [{"person_id": "P-001", "availability": {"2026-01": Decimal(40)}}]


def test_create_base_scenario_persists_optimizer_and_comparison_snapshot_atomically() -> None:
    cursor = FakeCursor()
    connection = FakeConnection(cursor)
    repository = BaseScenarioRepository(lambda: connection)

    result = repository.create_base_scenario("PRJ-001", "January baseline", _participants(), "A0091250")

    UUID(result["scenario_id"])
    UUID(result["snapshot_id"])
    assert result["scenario_type"] == "BASE"
    snapshot_params = cursor.snapshot_params
    assert snapshot_params is not None
    assert len(snapshot_params["snapshot_sha256"]) == 64
    assert hashlib.sha256(str(snapshot_params["snapshot_json"]).encode()).hexdigest() == snapshot_params["snapshot_sha256"]
    stored = json.loads(str(snapshot_params["snapshot_json"]))
    assert stored["profiles"][0]["competencies"] == {"SKILL-1": 4}
    assert stored["profiles"][0]["availability"] == {"2026-01": 40.0}
    assert stored["demands"][0]["demand_id"] == "D-001"
    assert stored["periods"]["2026-01"]["demand"]["SKILL-1"]["loadAmount"] == 10.0
    assert cursor.scenario_params["scenario_id"] == result["scenario_id"]
    assert cursor.scenario_params["snapshot_id"] == result["snapshot_id"]
    assert connection.commits == 1
    assert connection.rollbacks == 0
    assert connection.closed is True


def test_unknown_participant_rolls_back_without_persisting_snapshot() -> None:
    cursor = FakeCursor(person_exists=False)
    connection = FakeConnection(cursor)
    repository = BaseScenarioRepository(lambda: connection)

    with pytest.raises(ScenarioError) as error:
        repository.create_base_scenario("PRJ-001", "January baseline", _participants(), "A0091250")

    assert error.value.code == "PERSON_NOT_FOUND"
    assert cursor.snapshot_params is None
    assert cursor.scenario_params is None
    assert connection.commits == 0
    assert connection.rollbacks == 1
    assert connection.closed is True


def test_availability_period_outside_horizon_is_rejected_without_persistence() -> None:
    cursor = FakeCursor()
    connection = FakeConnection(cursor)
    repository = BaseScenarioRepository(lambda: connection)
    participants = [{"person_id": "P-001", "availability": {"2027-01": Decimal(40)}}]

    with pytest.raises(ScenarioError) as error:
        repository.create_base_scenario("PRJ-001", "January baseline", participants, "A0091250")

    assert error.value.code == "PERIOD_OUTSIDE_HORIZON"
    assert cursor.snapshot_params is None
    assert connection.commits == 0
    assert connection.rollbacks == 1


def test_update_base_scenario_creates_new_snapshot_and_repoints_scenario() -> None:
    cursor = FakeCursor()
    connection = FakeConnection(cursor)
    repository = BaseScenarioRepository(lambda: connection)

    result = repository.update_base_scenario("SCN-001", "Renamed", _participants(), "A0091250")

    assert result["scenario_id"] == "SCN-001"
    assert result["scenario_name"] == "Renamed"
    assert result["project_id"] == "PRJ-001"
    UUID(result["snapshot_id"])
    assert cursor.snapshot_params is not None
    assert cursor.snapshot_params["snapshot_id"] == result["snapshot_id"]
    assert cursor.update_params == {
        "scenario_id": "SCN-001",
        "snapshot_id": result["snapshot_id"],
        "scenario_name": "Renamed",
    }
    assert cursor.scenario_params is None
    assert connection.commits == 1
    assert connection.closed is True


@pytest.mark.parametrize(
    ("cursor_kwargs", "code", "status"),
    [
        ({"scenario_row": None}, "SCENARIO_NOT_FOUND", 404),
        ({"scenario_row": ("PRJ-001", "ALTERNATIVE")}, "SCENARIO_NOT_EDITABLE", 422),
        ({"alternatives": 2}, "SCENARIO_HAS_ALTERNATIVES", 409),
        ({"name_taken": True}, "SCENARIO_ALREADY_EXISTS", 409),
    ],
)
def test_update_base_scenario_rejects_without_persisting(
    cursor_kwargs: dict[str, object], code: str, status: int
) -> None:
    cursor = FakeCursor(**cursor_kwargs)
    connection = FakeConnection(cursor)
    repository = BaseScenarioRepository(lambda: connection)

    with pytest.raises(ScenarioError) as error:
        repository.update_base_scenario("SCN-001", "Renamed", _participants(), "A0091250")

    assert (error.value.code, error.value.status_code) == (code, status)
    assert cursor.snapshot_params is None
    assert cursor.update_params is None
    assert connection.commits == 0
    assert connection.rollbacks == 1


def test_list_scenarios_returns_names_with_project_names() -> None:
    cursor = FakeCursor()
    connection = FakeConnection(cursor)
    repository = BaseScenarioRepository(lambda: connection)

    scenarios = repository.list_scenarios()

    assert scenarios == [{
        "scenario_id": "SCN-001",
        "scenario_name": "Baseline",
        "scenario_type": "BASE",
        "project_id": "PRJ-001",
        "project_name": "Atlas",
    }]
    assert connection.closed is True


def test_get_optimizer_snapshot_returns_saved_profiles_and_demands() -> None:
    cursor = FakeCursor()
    connection = FakeConnection(cursor)
    repository = BaseScenarioRepository(lambda: connection)

    snapshot = repository.get_optimization_snapshot("SCN-001")

    assert snapshot["snapshot_id"] == "SNP-001"
    assert snapshot["profiles"][0]["person_id"] == "P-001"
    assert snapshot["demands"][0]["demand_id"] == "D-001"
    assert connection.closed is True
