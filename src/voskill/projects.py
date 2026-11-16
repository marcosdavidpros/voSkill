from collections.abc import Callable
from datetime import date, datetime
from uuid import uuid4

import oracledb

from .connection import open_oracle_connection


class ProjectError(ValueError):
    def __init__(self, code: str, status_code: int, field: str | None = None) -> None:
        self.code = code
        self.status_code = status_code
        self.field = field
        super().__init__(code)


class ProjectRepository:
    def __init__(
        self,
        connection_factory: Callable[[], oracledb.Connection] = open_oracle_connection,
    ) -> None:
        self._connection_factory = connection_factory

    def list_projects(self) -> list[dict[str, object]]:
        connection = self._connection_factory()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT PROJECT_ID, PROJECT_NAME, HORIZON_START, HORIZON_END, LOAD_UNIT
                      FROM VSK_PROJECTS
                     ORDER BY PROJECT_NAME, PROJECT_ID
                    """
                )
                return [self._record(row) for row in cursor.fetchall()]
        finally:
            connection.close()

    def create_project(
        self,
        project_name: str,
        horizon_start: date,
        horizon_end: date,
        load_unit: str,
    ) -> dict[str, object]:
        normalized_name = project_name.strip()
        if not normalized_name:
            raise ProjectError("REQUIRED_PROJECT_NAME", 422, "project_name")
        if horizon_start.day != 1 or horizon_end.day != 1 or horizon_start > horizon_end:
            raise ProjectError("INVALID_HORIZON", 422, "horizon_start")
        if load_unit != "hours":
            raise ProjectError("INVALID_LOAD_UNIT", 422, "load_unit")

        connection = self._connection_factory()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT PROJECT_ID FROM VSK_PROJECTS WHERE PROJECT_NAME = :project_name",
                    project_name=normalized_name,
                )
                if cursor.fetchone() is not None:
                    raise ProjectError("PROJECT_ALREADY_EXISTS", 409, "project_name")

                project_id = str(uuid4())
                cursor.execute(
                    """
                    INSERT INTO VSK_PROJECTS (
                        PROJECT_ID, PROJECT_NAME, HORIZON_START, HORIZON_END, LOAD_UNIT
                    ) VALUES (
                        :project_id, :project_name, :horizon_start, :horizon_end, :load_unit
                    )
                    """,
                    project_id=project_id,
                    project_name=normalized_name,
                    horizon_start=horizon_start,
                    horizon_end=horizon_end,
                    load_unit=load_unit,
                )
                connection.commit()
                return {
                    "project_id": project_id,
                    "project_name": normalized_name,
                    "horizon_start": horizon_start,
                    "horizon_end": horizon_end,
                    "load_unit": load_unit,
                }
        except ProjectError:
            connection.rollback()
            raise
        except oracledb.IntegrityError as error:
            connection.rollback()
            raise ProjectError("PROJECT_ALREADY_EXISTS", 409, "project_name") from error
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def update_project(
        self,
        project_id: str,
        project_name: str,
        horizon_start: date,
        horizon_end: date,
        load_unit: str,
    ) -> dict[str, object]:
        normalized_name = project_name.strip()
        if not normalized_name:
            raise ProjectError("REQUIRED_PROJECT_NAME", 422, "project_name")
        if horizon_start.day != 1 or horizon_end.day != 1 or horizon_start > horizon_end:
            raise ProjectError("INVALID_HORIZON", 422, "horizon_start")
        if load_unit != "hours":
            raise ProjectError("INVALID_LOAD_UNIT", 422, "load_unit")

        connection = self._connection_factory()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT PROJECT_ID
                      FROM VSK_PROJECTS
                     WHERE PROJECT_NAME = :project_name
                       AND PROJECT_ID <> :project_id
                    """,
                    project_name=normalized_name,
                    project_id=project_id,
                )
                if cursor.fetchone() is not None:
                    raise ProjectError("PROJECT_ALREADY_EXISTS", 409, "project_name")
                cursor.execute(
                    """
                    SELECT COUNT(*)
                      FROM VSK_PROJECT_DEMANDS
                     WHERE PROJECT_ID = :project_id
                       AND (PERIOD_START < :horizon_start OR PERIOD_START > :horizon_end)
                    """,
                    project_id=project_id,
                    horizon_start=horizon_start,
                    horizon_end=horizon_end,
                )
                outside = cursor.fetchone()
                if outside is not None and int(outside[0]) > 0:
                    raise ProjectError("HORIZON_EXCLUDES_DEMANDS", 409, "horizon_start")
                cursor.execute(
                    """
                    UPDATE VSK_PROJECTS
                       SET PROJECT_NAME = :project_name,
                           HORIZON_START = :horizon_start,
                           HORIZON_END = :horizon_end
                     WHERE PROJECT_ID = :project_id
                    """,
                    project_id=project_id,
                    project_name=normalized_name,
                    horizon_start=horizon_start,
                    horizon_end=horizon_end,
                )
                if cursor.rowcount == 0:
                    raise ProjectError("PROJECT_NOT_FOUND", 404)
                connection.commit()
                return {
                    "project_id": project_id,
                    "project_name": normalized_name,
                    "horizon_start": horizon_start,
                    "horizon_end": horizon_end,
                    "load_unit": load_unit,
                }
        except ProjectError:
            connection.rollback()
            raise
        except oracledb.IntegrityError as error:
            connection.rollback()
            raise ProjectError("PROJECT_ALREADY_EXISTS", 409, "project_name") from error
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @classmethod
    def _record(cls, row: tuple[object, ...]) -> dict[str, object]:
        return {
            "project_id": row[0],
            "project_name": row[1],
            "horizon_start": cls._as_date(row[2]),
            "horizon_end": cls._as_date(row[3]),
            "load_unit": row[4],
        }

    @staticmethod
    def _as_date(value: date | datetime) -> date:
        return value.date() if isinstance(value, datetime) else value