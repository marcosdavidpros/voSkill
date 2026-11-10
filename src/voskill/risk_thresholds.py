from collections.abc import Callable
from datetime import UTC, datetime

import oracledb

from .connection import open_oracle_connection


class RiskThresholdError(ValueError):
    def __init__(self, code: str, status_code: int) -> None:
        self.code = code
        self.status_code = status_code
        super().__init__(code)


class RiskThresholdRepository:
    def __init__(
        self,
        connection_factory: Callable[[], oracledb.Connection] = open_oracle_connection,
    ) -> None:
        self._connection_factory = connection_factory

    def list_for_project(self, project_id: str) -> dict[str, int]:
        connection = self._connection_factory()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT SKILL_ID, MIN_CONFIRMED_PEOPLE
                      FROM VSK_CRITICAL_SKILL_THRESHOLDS
                     WHERE PROJECT_ID = :project_id
                     ORDER BY SKILL_ID
                    """,
                    project_id=project_id,
                )
                return {str(row[0]): int(row[1]) for row in cursor.fetchall()}
        finally:
            connection.close()

    def save(
        self,
        project_id: str,
        skill_id: str,
        threshold: int,
        actor_id: str,
    ) -> dict[str, object]:
        if isinstance(threshold, bool) or not isinstance(threshold, int) or threshold < 1:
            raise RiskThresholdError("INVALID_RISK_THRESHOLD", 422)

        connection = self._connection_factory()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT PROJECT_ID FROM VSK_PROJECTS WHERE PROJECT_ID = :project_id",
                    project_id=project_id,
                )
                if cursor.fetchone() is None:
                    raise RiskThresholdError("PROJECT_NOT_FOUND", 404)

                cursor.execute(
                    "SELECT SKILL_ID FROM VSK_SKILLS WHERE SKILL_ID = :skill_id",
                    skill_id=skill_id,
                )
                if cursor.fetchone() is None:
                    raise RiskThresholdError("UNKNOWN_SKILL", 404)

                updated_at = datetime.now(UTC)
                cursor.execute(
                    """
                    MERGE INTO VSK_CRITICAL_SKILL_THRESHOLDS target
                    USING (
                        SELECT :project_id AS project_id, :skill_id AS skill_id FROM dual
                    ) source
                       ON (target.PROJECT_ID = source.project_id AND target.SKILL_ID = source.skill_id)
                    WHEN MATCHED THEN UPDATE SET
                        target.MIN_CONFIRMED_PEOPLE = :threshold,
                        target.ACTOR_ID = :actor_id,
                        target.UPDATED_AT = :updated_at
                    WHEN NOT MATCHED THEN INSERT (
                        PROJECT_ID, SKILL_ID, MIN_CONFIRMED_PEOPLE, ACTOR_ID, UPDATED_AT
                    ) VALUES (
                        :project_id, :skill_id, :threshold, :actor_id, :updated_at
                    )
                    """,
                    project_id=project_id,
                    skill_id=skill_id,
                    threshold=threshold,
                    actor_id=actor_id,
                    updated_at=updated_at,
                )
                connection.commit()
                return {
                    "project_id": project_id,
                    "skill_id": skill_id,
                    "threshold": threshold,
                    "actor_id": actor_id,
                    "updated_at": updated_at,
                }
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()