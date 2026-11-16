import pytest
from conftest import _request

from voskill.api.dependencies import get_actor_id, get_catalog_repository
from voskill.catalog import CatalogError, CatalogRepository
from voskill.main import app


class Cursor:
    def __init__(self, *, duplicate: bool = False, rowcount: int = 1) -> None:
        self.duplicate = duplicate
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
        return ("OTHER",) if self.duplicate and last.startswith("SELECT SKILL_ID") else None


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


def test_update_skill_trims_fields_checks_duplicates_excluding_itself_and_commits() -> None:
    cursor = Cursor()
    connection = Connection(cursor)
    repository = CatalogRepository(lambda: connection)

    skill = repository.update_skill("SK-1", "  Java 21  ", "  Linguagem  ")

    assert skill == {"skill_id": "SK-1", "skill_name": "Java 21", "description": "Linguagem"}
    duplicate_check, duplicate_binds = cursor.statements[0]
    assert "SKILL_ID <> :skill_id" in duplicate_check
    assert duplicate_binds == {"skill_name": "Java 21", "skill_id": "SK-1"}
    update, update_binds = cursor.statements[1]
    assert update.startswith("UPDATE VSK_SKILLS SET SKILL_NAME = :skill_name, DESCRIPTION = :description")
    assert update_binds == {"skill_id": "SK-1", "skill_name": "Java 21", "description": "Linguagem"}
    assert (connection.commits, connection.rollbacks, connection.closed) == (1, 0, True)


def test_update_skill_turns_blank_description_into_null() -> None:
    cursor = Cursor()
    repository = CatalogRepository(lambda: Connection(cursor))

    skill = repository.update_skill("SK-1", "Java", "   ")

    assert skill["description"] is None
    assert cursor.statements[1][1]["description"] is None


@pytest.mark.parametrize(
    ("cursor", "name", "code", "status"),
    [
        (Cursor(), "   ", "REQUIRED_SKILL_NAME", 422),
        (Cursor(duplicate=True), "Python", "SKILL_ALREADY_EXISTS", 409),
        (Cursor(rowcount=0), "Java", "SKILL_NOT_FOUND", 404),
    ],
)
def test_update_skill_rejects_invalid_requests_without_commit(
    cursor: Cursor, name: str, code: str, status: int
) -> None:
    connection = Connection(cursor)
    repository = CatalogRepository(lambda: connection)

    with pytest.raises(CatalogError) as error:
        repository.update_skill("SK-1", name, None)

    assert (error.value.code, error.value.status_code) == (code, status)
    assert connection.commits == 0
    assert connection.closed is (code != "REQUIRED_SKILL_NAME")


class MemoryCatalog:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str | None]] = []

    def update_skill(self, skill_id: str, skill_name: str, description: str | None) -> dict[str, object]:
        if skill_id == "SK-404":
            raise CatalogError("SKILL_NOT_FOUND", 404)
        self.calls.append((skill_id, skill_name, description))
        return {"skill_id": skill_id, "skill_name": skill_name, "description": description}


def _patch(repository: MemoryCatalog, skill_id: str, payload: dict):
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_catalog_repository] = lambda: repository
    try:
        return _request("PATCH", f"/skills/{skill_id}", payload)
    finally:
        app.dependency_overrides.clear()


def test_patch_skill_updates_name_and_description() -> None:
    repository = MemoryCatalog()

    response = _patch(repository, "SK-1", {"skill_name": "Java 21", "description": "Linguagem"})

    assert response.status_code == 200
    assert response.json() == {"skill_id": "SK-1", "skill_name": "Java 21", "description": "Linguagem"}
    assert repository.calls == [("SK-1", "Java 21", "Linguagem")]


def test_patch_skill_reports_unknown_skill_and_rejects_empty_name() -> None:
    repository = MemoryCatalog()

    missing = _patch(repository, "SK-404", {"skill_name": "Java"})
    empty = _patch(repository, "SK-1", {"skill_name": ""})

    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "SKILL_NOT_FOUND"
    assert empty.status_code == 422


def test_patch_skill_requires_authentication() -> None:
    assert _request("PATCH", "/skills/SK-1", {"skill_name": "Java"}).status_code == 401
