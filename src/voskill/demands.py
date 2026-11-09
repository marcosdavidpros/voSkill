from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

import oracledb

from .connection import open_oracle_connection


class DemandError(ValueError):
    def __init__(self, code: str, status_code: int, field: str | None = None) -> None:
        self.code = code
        self.status_code = status_code
        self.field = field
        super().__init__(code)


class DemandRepository:
    def __init__(
        self,
        connection_factory: Callable[[], oracledb.Connection] = open_oracle_connection,
    ) -> None:
        self._connection_factory = connection_factory

    def create(
        self,
        project_id: str,
        skill_id: str,
        proficiency_level: int,
        period_start: date,
        load_amount: Decimal,
        load_unit: str,
        actor_id: str,
    ) -> dict[str, object]:
        connection = self._connection_factory()
        try:
            with connection.cursor() as cursor:
                self._validate(
                    cursor,
                    project_id,
                    skill_id,
                    proficiency_level,
                    period_start,
                    load_amount,
                    load_unit,
                )
                demand_id = str(uuid4())
                cursor.execute(
                    """
                    INSERT INTO VSK_PROJECT_DEMANDS (
                        DEMAND_ID, PROJECT_ID, SKILL_ID, PROFICIENCY_LEVEL,
                        PERIOD_START, LOAD_AMOUNT, LOAD_UNIT, ACTOR_ID
                    ) VALUES (
                        :demand_id, :project_id, :skill_id, :proficiency_level,
                        :period_start, :load_amount, :load_unit, :actor_id
                    )
                    """,
                    demand_id=demand_id,
                    project_id=project_id,
                    skill_id=skill_id,
                    proficiency_level=proficiency_level,
                    period_start=period_start,
                    load_amount=load_amount,
                    load_unit=load_unit,
                    actor_id=actor_id,
                )
                connection.commit()
                return self._record(
                    (
                        demand_id,
                        project_id,
                        skill_id,
                        proficiency_level,
                        period_start,
                        load_amount,
                        load_unit,
                        actor_id,
                    )
                )
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def list_for_project(self, project_id: str) -> list[dict[str, object]]:
        connection = self._connection_factory()
        try:
            with connection.cursor() as cursor:
                self._get_project(cursor, project_id)
                cursor.execute(
                    """
                    SELECT DEMAND_ID, PROJECT_ID, SKILL_ID, PROFICIENCY_LEVEL,
                           PERIOD_START, LOAD_AMOUNT, LOAD_UNIT, ACTOR_ID
                      FROM VSK_PROJECT_DEMANDS
                     WHERE PROJECT_ID = :project_id
                     ORDER BY PERIOD_START, DEMAND_ID
                    """,
                    project_id=project_id,
                )
                return [self._record(row) for row in cursor.fetchall()]
        finally:
            connection.close()

    def update(
        self,
        demand_id: str,
        project_id: str,
        skill_id: str,
        proficiency_level: int,
        period_start: date,
        load_amount: Decimal,
        load_unit: str,
        actor_id: str,
    ) -> dict[str, object]:
        connection = self._connection_factory()
        try:
            with connection.cursor() as cursor:
                self._validate(
                    cursor,
                    project_id,
                    skill_id,
                    proficiency_level,
                    period_start,
                    load_amount,
                    load_unit,
                )
                cursor.execute(
                    """
                    UPDATE VSK_PROJECT_DEMANDS
                       SET SKILL_ID = :skill_id,
                           PROFICIENCY_LEVEL = :proficiency_level,
                           PERIOD_START = :period_start,
                           LOAD_AMOUNT = :load_amount,
                           LOAD_UNIT = :load_unit,
                           ACTOR_ID = :actor_id,
                           UPDATED_AT = SYSTIMESTAMP
                     WHERE DEMAND_ID = :demand_id
                       AND PROJECT_ID = :project_id
                    """,
                    demand_id=demand_id,
                    project_id=project_id,
                    skill_id=skill_id,
                    proficiency_level=proficiency_level,
                    period_start=period_start,
                    load_amount=load_amount,
                    load_unit=load_unit,
                    actor_id=actor_id,
                )
                if cursor.rowcount == 0:
                    raise DemandError("DEMAND_NOT_FOUND", 404)
                connection.commit()
                return self._record(
                    (
                        demand_id,
                        project_id,
                        skill_id,
                        proficiency_level,
                        period_start,
                        load_amount,
                        load_unit,
                        actor_id,
                    )
                )
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _validate(
        self,
        cursor: oracledb.Cursor,
        project_id: str,
        skill_id: str,
        proficiency_level: int,
        period_start: date,
        load_amount: Decimal,
        load_unit: str,
    ) -> None:
        if not 1 <= proficiency_level <= 5:
            raise DemandError("INVALID_LEVEL", 422, "proficiency_level")
        if load_amount < 0:
            raise DemandError("INVALID_LOAD", 422, "load_amount")

        horizon_start, horizon_end, project_load_unit = self._get_project(cursor, project_id)
        if load_unit != project_load_unit:
            raise DemandError("INVALID_LOAD_UNIT", 422, "load_unit")
        if period_start.day != 1:
            raise DemandError("INVALID_PERIOD", 422, "period")
        if not self._as_date(horizon_start) <= period_start <= self._as_date(horizon_end):
            raise DemandError("PERIOD_OUTSIDE_HORIZON", 422, "period")

        cursor.execute(
            "SELECT SKILL_ID FROM VSK_SKILLS WHERE SKILL_ID = :skill_id",
            skill_id=skill_id,
        )
        if cursor.fetchone() is None:
            raise DemandError("UNKNOWN_SKILL", 422, "skill_id")

    @staticmethod
    def _get_project(cursor: oracledb.Cursor, project_id: str) -> tuple[object, object, str]:
        cursor.execute(
            """
            SELECT HORIZON_START, HORIZON_END, LOAD_UNIT
              FROM VSK_PROJECTS
             WHERE PROJECT_ID = :project_id
            """,
            project_id=project_id,
        )
        project = cursor.fetchone()
        if project is None:
            raise DemandError("PROJECT_NOT_FOUND", 404, "project_id")
        return project[0], project[1], project[2]

    @classmethod
    def _record(cls, row: tuple[object, ...]) -> dict[str, object]:
        period_start = cls._as_date(row[4])
        return {
            "demand_id": row[0],
            "project_id": row[1],
            "skill_id": row[2],
            "proficiency_level": row[3],
            "period": period_start.strftime("%Y-%m"),
            "load_amount": row[5],
            "load_unit": row[6],
            "actor_id": row[7],
        }

    @staticmethod
    def _as_date(value: date | datetime) -> date:
        return value.date() if isinstance(value, datetime) else value