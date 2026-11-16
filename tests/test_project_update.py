from datetime import date

import pytest
from conftest import _request

from voskill.api.dependencies import get_project_repository
from voskill.main import app, get_actor_id
from voskill.projects import ProjectError, ProjectRepository


class Cursor:
    def __init__(self, *, duplicate: bool = False, demands_outside: int = 0, rowcount: int = 1) -> None:
        self.duplicate = duplicate
        self.demands_outside = demands_outside
        self.rowcount = rowcount
        self.statements: list[tuple[str, dict[str, object]]] = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def execute(self, statement: str, **binds: object) -> None:
        self.statements.append((" ".join(statement.split()), binds))

    def fetchone(self):
        last = self.statements[-1][0]
        if last.startswith("SELECT PROJECT_ID"):
            return ("OTHER",) if self.duplicate else None
        if last.startswith("SELECT COUNT(*)"):
            return (self.demands_outside,)
        return None


class Connection:
    def __init__(self, cursor: Cursor) -> None:
        self.cursor_value = cursor
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def cursor(self):
        return self.cursor_value

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.closed = True


def _update(cursor: Cursor, **overrides: object):
    connection = Connection(cursor)
    repository = ProjectRepository(lambda: connection)
    values = {
        "project_id": "PRJ-1",
        "project_name": "  Atlas 2  ",
        "horizon_start": date(2026, 2, 1),
        "horizon_end": date(2026, 11, 1),
        "load_unit": "hours",
        **overrides,
    }
    return connection, repository.update_project(**values)  # type: ignore[arg-type]


def test_update_project_renames_changes_horizon_and_commits() -> None:
    cursor = Cursor()

    connection, project = _update(cursor)

    assert project == {
        "project_id": "PRJ-1",
        "project_name": "Atlas 2",
        "horizon_start": date(2026, 2, 1),
        "horizon_end": date(2026, 11, 1),
        "load_unit": "hours",
    }
    duplicate_sql, duplicate_binds = cursor.statements[0]
    assert "PROJECT_ID <> :project_id" in duplicate_sql
    assert duplicate_binds == {"project_name": "Atlas 2", "project_id": "PRJ-1"}
    assert "FROM VSK_PROJECT_DEMANDS" in cursor.statements[1][0]
    update_sql, update_binds = cursor.statements[2]
    assert update_sql.startswith("UPDATE VSK_PROJECTS SET PROJECT_NAME = :project_name")
    assert update_binds["horizon_start"] == date(2026, 2, 1)
    assert (connection.commits, connection.rollbacks, connection.closed) == (1, 0, True)


@pytest.mark.parametrize(
    ("cursor", "overrides", "code", "status"),
    [
        (Cursor(duplicate=True), {}, "PROJECT_ALREADY_EXISTS", 409),
        (Cursor(demands_outside=2), {}, "HORIZON_EXCLUDES_DEMANDS", 409),
        (Cursor(rowcount=0), {}, "PROJECT_NOT_FOUND", 404),
        (Cursor(), {"project_name": "   "}, "REQUIRED_PROJECT_NAME", 422),
        (Cursor(), {"horizon_start": date(2026, 2, 15)}, "INVALID_HORIZON", 422),
        (Cursor(), {"horizon_start": date(2027, 1, 1)}, "INVALID_HORIZON", 422),
        (Cursor(), {"load_unit": "days"}, "INVALID_LOAD_UNIT", 422),
    ],
)
def test_update_project_rejects_invalid_requests_without_commit(
    cursor: Cursor, overrides: dict[str, object], code: str, status: int
) -> None:
    connection = Connection(cursor)
    repository = ProjectRepository(lambda: connection)
    values = {
        "project_id": "PRJ-1",
        "project_name": "Atlas",
        "horizon_start": date(2026, 2, 1),
        "horizon_end": date(2026, 11, 1),
        "load_unit": "hours",
        **overrides,
    }

    with pytest.raises(ProjectError) as error:
        repository.update_project(**values)  # type: ignore[arg-type]

    assert (error.value.code, error.value.status_code) == (code, status)
    assert connection.commits == 0


class MemoryProjects:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def update_project(self, **values: object) -> dict[str, object]:
        if values["project_id"] == "PRJ-404":
            raise ProjectError("PROJECT_NOT_FOUND", 404)
        self.calls.append(values)
        return {
            "project_id": values["project_id"],
            "project_name": values["project_name"],
            "horizon_start": values["horizon_start"],
            "horizon_end": values["horizon_end"],
            "load_unit": values["load_unit"],
        }


PAYLOAD = {
    "project_name": "Atlas 2",
    "horizon_start": "2026-02-01",
    "horizon_end": "2026-11-01",
    "load_unit": "hours",
}


def _patch(repository: MemoryProjects, project_id: str, payload: dict):
    app.dependency_overrides[get_actor_id] = lambda: "A0091250"
    app.dependency_overrides[get_project_repository] = lambda: repository
    try:
        return _request("PATCH", f"/projects/{project_id}", payload)
    finally:
        app.dependency_overrides.clear()


def test_patch_project_updates_name_and_horizon() -> None:
    repository = MemoryProjects()

    response = _patch(repository, "PRJ-1", PAYLOAD)

    assert response.status_code == 200
    assert response.json()["project_name"] == "Atlas 2"
    assert response.json()["horizon_end"] == "2026-11-01"
    assert repository.calls[0]["horizon_start"] == date(2026, 2, 1)


def test_patch_project_reports_unknown_project_with_stable_code() -> None:
    response = _patch(MemoryProjects(), "PRJ-404", PAYLOAD)

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "PROJECT_NOT_FOUND"


def test_patch_project_requires_authentication() -> None:
    assert _request("PATCH", "/projects/PRJ-1", PAYLOAD).status_code == 401
