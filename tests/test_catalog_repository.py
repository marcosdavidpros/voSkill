from uuid import UUID

import pytest

from voskill.catalog import CatalogError, CatalogRepository


class CatalogCursor:
    def __init__(self, *, existing_skill: bool = False, fail_on_insert: bool = False) -> None:
        self.existing_skill = existing_skill
        self.fail_on_insert = fail_on_insert
        self.statement = ""
        self.binds: dict[str, object] = {}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def execute(self, statement: str, **binds: object) -> None:
        self.statement = statement
        self.binds = binds
        if self.fail_on_insert and statement.lstrip().startswith("INSERT"):
            raise RuntimeError("database write failed")

    def fetchall(self):
        if "VSK_PERSONS" in self.statement:
            return [("P-001", "Alex")]
        return [("SKILL-1", "Python", "Scripting")]

    def fetchone(self):
        if self.existing_skill and "SELECT SKILL_ID" in self.statement:
            return ("SKILL-1",)
        return None


class CatalogConnection:
    def __init__(self, *, existing_skill: bool = False, fail_on_insert: bool = False) -> None:
        self.cursor_value = CatalogCursor(existing_skill=existing_skill, fail_on_insert=fail_on_insert)
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def cursor(self):
        return self.cursor_value

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


def test_catalog_repository_filters_inactive_people_and_lists_skill_fields() -> None:
    connection = CatalogConnection()
    repository = CatalogRepository(lambda: connection)

    people = repository.list_people()
    assert people == [{"person_id": "P-001", "display_name": "Alex"}]
    assert "ACTIVE_FLAG = 'Y'" in connection.cursor_value.statement
    assert "ORDER BY DISPLAY_NAME, PERSON_ID" in connection.cursor_value.statement
    skills = repository.list_skills()
    assert skills == [{"skill_id": "SKILL-1", "skill_name": "Python", "description": "Scripting"}]
    assert "ORDER BY SKILL_NAME" in connection.cursor_value.statement
    assert connection.cursor_value.binds == {}
    assert connection.closed is True


def test_create_person_trims_name_uses_generated_uuid_and_commits() -> None:
    connection = CatalogConnection()
    repository = CatalogRepository(lambda: connection)

    person = repository.create_person("  Sam  ")

    assert person["display_name"] == "Sam"
    assert UUID(str(person["person_id"]))
    assert connection.cursor_value.binds["display_name"] == "Sam"
    assert connection.cursor_value.binds["person_id"] == person["person_id"]
    assert "INSERT INTO VSK_PERSONS" in connection.cursor_value.statement
    assert "'Y'" in connection.cursor_value.statement
    assert connection.committed is True
    assert connection.rolled_back is False
    assert connection.closed is True


def test_create_skill_trims_fields_uses_generated_uuid_and_commits() -> None:
    connection = CatalogConnection()
    repository = CatalogRepository(lambda: connection)

    skill = repository.create_skill("  Kubernetes  ", "  Container orchestration  ")

    assert skill["skill_name"] == "Kubernetes"
    assert skill["description"] == "Container orchestration"
    assert UUID(str(skill["skill_id"]))
    assert connection.cursor_value.binds == {
        "skill_id": skill["skill_id"],
        "skill_name": "Kubernetes",
        "description": "Container orchestration",
    }
    assert "INSERT INTO VSK_SKILLS" in connection.cursor_value.statement
    assert connection.committed is True
    assert connection.rolled_back is False
    assert connection.closed is True


def test_create_skill_normalizes_blank_description_to_null() -> None:
    connection = CatalogConnection()
    repository = CatalogRepository(lambda: connection)

    skill = repository.create_skill("Go", "   ")

    assert skill["description"] is None
    assert connection.cursor_value.binds["description"] is None
    assert connection.committed is True


def test_catalog_insert_failure_rolls_back_and_closes_connection() -> None:
    connection = CatalogConnection(fail_on_insert=True)
    repository = CatalogRepository(lambda: connection)

    with pytest.raises(RuntimeError, match="database write failed"):
        repository.create_person("Sam")

    assert connection.committed is False
    assert connection.rolled_back is True
    assert connection.closed is True


def test_skill_insert_failure_rolls_back_without_committing() -> None:
    connection = CatalogConnection(fail_on_insert=True)
    repository = CatalogRepository(lambda: connection)

    with pytest.raises(RuntimeError, match="database write failed"):
        repository.create_skill("Rust", "Systems language")

    assert connection.cursor_value.binds["skill_name"] == "Rust"
    assert connection.cursor_value.binds["description"] == "Systems language"
    assert connection.committed is False
    assert connection.rolled_back is True
    assert connection.closed is True


def test_duplicate_skill_is_case_insensitive_and_rolls_back() -> None:
    connection = CatalogConnection(existing_skill=True)
    repository = CatalogRepository(lambda: connection)

    with pytest.raises(CatalogError) as error:
        repository.create_skill("python")

    assert error.value.code == "SKILL_ALREADY_EXISTS"
    assert error.value.status_code == 409
    assert connection.cursor_value.binds == {"skill_name": "python"}
    assert "UPPER(TRIM(SKILL_NAME))" in connection.cursor_value.statement
    assert "INSERT INTO VSK_SKILLS" not in connection.cursor_value.statement
    assert connection.committed is False
    assert connection.rolled_back is True
    assert connection.closed is True


def test_blank_catalog_names_are_rejected_before_connection_opens() -> None:
    def connection_must_not_open():
        raise AssertionError("invalid input must be rejected before connecting to Oracle")

    repository = CatalogRepository(connection_must_not_open)

    with pytest.raises(CatalogError, match="REQUIRED_DISPLAY_NAME"):
        repository.create_person("   ")
    with pytest.raises(CatalogError, match="REQUIRED_SKILL_NAME"):
        repository.create_skill(" \t ")
