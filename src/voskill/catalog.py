from collections.abc import Callable
from uuid import uuid4

import oracledb

from .connection import open_oracle_connection


class CatalogError(ValueError):
    def __init__(self, code: str, status_code: int) -> None:
        self.code = code
        self.status_code = status_code
        super().__init__(code)


class CatalogRepository:
    def __init__(
        self,
        connection_factory: Callable[[], oracledb.Connection] = open_oracle_connection,
    ) -> None:
        self._connection_factory = connection_factory

    def list_people(self) -> list[dict[str, object]]:
        connection = self._connection_factory()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT PERSON_ID, DISPLAY_NAME
                      FROM VSK_PERSONS
                     WHERE ACTIVE_FLAG = 'Y'
                     ORDER BY DISPLAY_NAME, PERSON_ID
                    """
                )
                return [
                    {"person_id": row[0], "display_name": row[1]}
                    for row in cursor.fetchall()
                ]
        finally:
            connection.close()

    def create_person(self, display_name: str) -> dict[str, object]:
        normalized_name = display_name.strip()
        if not normalized_name:
            raise CatalogError("REQUIRED_DISPLAY_NAME", 422)
        person_id = str(uuid4())
        connection = self._connection_factory()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO VSK_PERSONS (PERSON_ID, DISPLAY_NAME, ACTIVE_FLAG)
                    VALUES (:person_id, :display_name, 'Y')
                    """,
                    person_id=person_id,
                    display_name=normalized_name,
                )
                connection.commit()
            return {"person_id": person_id, "display_name": normalized_name}
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def list_skills(self) -> list[dict[str, object]]:
        connection = self._connection_factory()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT SKILL_ID, SKILL_NAME, DESCRIPTION
                      FROM VSK_SKILLS
                     ORDER BY SKILL_NAME, SKILL_ID
                    """
                )
                return [
                    {"skill_id": row[0], "skill_name": row[1], "description": row[2]}
                    for row in cursor.fetchall()
                ]
        finally:
            connection.close()

    def create_skill(self, skill_name: str, description: str | None = None) -> dict[str, object]:
        normalized_name = skill_name.strip()
        if not normalized_name:
            raise CatalogError("REQUIRED_SKILL_NAME", 422)
        normalized_description = description.strip() if description and description.strip() else None
        connection = self._connection_factory()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT SKILL_ID
                      FROM VSK_SKILLS
                     WHERE UPPER(TRIM(SKILL_NAME)) = UPPER(:skill_name)
                    """,
                    skill_name=normalized_name,
                )
                if cursor.fetchone() is not None:
                    raise CatalogError("SKILL_ALREADY_EXISTS", 409)
                skill_id = str(uuid4())
                cursor.execute(
                    """
                    INSERT INTO VSK_SKILLS (SKILL_ID, SKILL_NAME, DESCRIPTION)
                    VALUES (:skill_id, :skill_name, :description)
                    """,
                    skill_id=skill_id,
                    skill_name=normalized_name,
                    description=normalized_description,
                )
                connection.commit()
                return {
                    "skill_id": skill_id,
                    "skill_name": normalized_name,
                    "description": normalized_description,
                }
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
