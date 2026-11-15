from datetime import date, datetime
from uuid import UUID

import pytest

from voskill.projects import ProjectError, ProjectRepository


class FakeCursor:
    def __init__(self, *, existing_project: bool = False) -> None:
        self.statements: list[tuple[str, dict[str, object]]] = []
        self.existing_project = existing_project
        self.one: tuple[object, ...] | None = None
        self.rows: list[tuple[object, ...]] = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def execute(self, statement: str, **binds: object) -> None:
        self.statements.append((statement, binds))
        if "SELECT PROJECT_ID FROM VSK_PROJECTS" in statement:
            self.one = ("existing-id",) if self.existing_project else None
        elif "SELECT PROJECT_ID, PROJECT_NAME" in statement:
            self.rows = [
                ("uuid-1", "Atlas", datetime(2026, 1, 1), date(2026, 12, 1), "hours")
            ]

    def fetchone(self):
        return self.one

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, *, existing_project: bool = False) -> None:
        self.cursor_value = FakeCursor(existing_project=existing_project)
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def cursor(self):
        return self.cursor_value

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def test_project_repository_inserts_parameterized_uuid_and_commits() -> None:
    connection = FakeConnection()
    repository = ProjectRepository(lambda: connection)

    project = repository.create_project(
        " Atlas ", date(2026, 1, 1), date(2026, 12, 1), "hours"
    )

    UUID(project["project_id"])
    assert project["project_name"] == "Atlas"
    assert project["horizon_start"] == date(2026, 1, 1)
    insert_sql, binds = connection.cursor_value.statements[-1]
    assert "INSERT INTO VSK_PROJECTS" in insert_sql
    assert binds["project_name"] == "Atlas"
    assert binds["load_unit"] == "hours"
    assert connection.committed is True
    assert connection.rolled_back is False
    assert connection.closed is True


def test_project_repository_lists_date_values_as_dates() -> None:
    connection = FakeConnection()
    repository = ProjectRepository(lambda: connection)

    projects = repository.list_projects()

    assert projects == [
        {
            "project_id": "uuid-1",
            "project_name": "Atlas",
            "horizon_start": date(2026, 1, 1),
            "horizon_end": date(2026, 12, 1),
            "load_unit": "hours",
        }
    ]
    assert "ORDER BY PROJECT_NAME" in connection.cursor_value.statements[0][0]
    assert connection.closed is True


def test_project_repository_rejects_duplicate_and_rolls_back() -> None:
    connection = FakeConnection(existing_project=True)
    repository = ProjectRepository(lambda: connection)

    with pytest.raises(ProjectError) as error:
        repository.create_project("Atlas", date(2026, 1, 1), date(2026, 12, 1), "hours")

    assert error.value.code == "PROJECT_ALREADY_EXISTS"
    assert connection.committed is False
    assert connection.rolled_back is True
    assert connection.closed is True