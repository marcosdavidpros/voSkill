from collections.abc import Callable
from datetime import UTC, date, datetime, time
from uuid import uuid4

import oracledb

from .connection import open_oracle_connection


class CompetencyError(ValueError):
    def __init__(self, code: str, status_code: int, field: str | None = None) -> None:
        self.code = code
        self.status_code = status_code
        self.field = field
        super().__init__(code)


class CompetencyRepository:
    def __init__(
        self,
        connection_factory: Callable[[], oracledb.Connection] = open_oracle_connection,
    ) -> None:
        self._connection_factory = connection_factory

    def create(
        self,
        person_id: str,
        skill_id: str,
        proficiency_level: int,
        evidence: str,
        review_date: date,
        actor_id: str,
    ) -> dict[str, object]:
        connection = self._connection_factory()
        try:
            with connection.cursor() as cursor:
                if not 1 <= proficiency_level <= 5:
                    raise CompetencyError("INVALID_LEVEL", 422, "proficiency_level")
                if not evidence.strip():
                    raise CompetencyError("REQUIRED_EVIDENCE", 422, "evidence")

                cursor.execute(
                    "SELECT PERSON_ID FROM VSK_PERSONS WHERE PERSON_ID = :person_id",
                    person_id=person_id,
                )
                if cursor.fetchone() is None:
                    raise CompetencyError("PERSON_NOT_FOUND", 404, "person_id")

                cursor.execute(
                    "SELECT SKILL_ID, SKILL_NAME FROM VSK_SKILLS WHERE SKILL_ID = :skill_id",
                    skill_id=skill_id,
                )
                skill = cursor.fetchone()
                if skill is None:
                    raise CompetencyError("UNKNOWN_SKILL", 422, "skill_id")

                cursor.execute(
                    """
                    SELECT COMPETENCY_ID
                      FROM VSK_PERSON_COMPETENCIES
                     WHERE PERSON_ID = :person_id AND SKILL_ID = :skill_id
                    """,
                    person_id=person_id,
                    skill_id=skill_id,
                )
                if cursor.fetchone() is not None:
                    raise CompetencyError("COMPETENCY_ALREADY_EXISTS", 409)

                competency_id = str(uuid4())
                reviewed_at = datetime.combine(review_date, time.min, tzinfo=UTC)
                cursor.execute(
                    """
                    INSERT INTO VSK_PERSON_COMPETENCIES (
                        COMPETENCY_ID, PERSON_ID, SKILL_ID, PROFICIENCY_LEVEL,
                        EVIDENCE, ORIGIN_TYPE, ACTOR_ID, REVIEWED_AT
                    ) VALUES (
                        :competency_id, :person_id, :skill_id, :proficiency_level,
                        :evidence, :origin_type, :actor_id, :reviewed_at
                    )
                    """,
                    competency_id=competency_id,
                    person_id=person_id,
                    skill_id=skill_id,
                    proficiency_level=proficiency_level,
                    evidence=evidence.strip(),
                    origin_type="MANUAL",
                    actor_id=actor_id,
                    reviewed_at=reviewed_at,
                )
                connection.commit()
                return {
                    "competency_id": competency_id,
                    "person_id": person_id,
                    "skill_id": skill[0],
                    "skill_name": skill[1],
                    "proficiency_level": proficiency_level,
                    "evidence": evidence.strip(),
                    "origin_type": "MANUAL",
                    "actor_id": actor_id,
                    "review_date": review_date.isoformat(),
                }
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def list_for_person(self, person_id: str) -> list[dict[str, object]]:
        connection = self._connection_factory()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT PERSON_ID FROM VSK_PERSONS WHERE PERSON_ID = :person_id",
                    person_id=person_id,
                )
                if cursor.fetchone() is None:
                    raise CompetencyError("PERSON_NOT_FOUND", 404, "person_id")

                cursor.execute(
                    """
                    SELECT C.COMPETENCY_ID, C.PERSON_ID, C.SKILL_ID, S.SKILL_NAME,
                           C.PROFICIENCY_LEVEL, C.EVIDENCE, C.ORIGIN_TYPE,
                           C.ACTOR_ID, C.REVIEWED_AT
                      FROM VSK_PERSON_COMPETENCIES C
                      JOIN VSK_SKILLS S ON S.SKILL_ID = C.SKILL_ID
                     WHERE C.PERSON_ID = :person_id
                     ORDER BY S.SKILL_NAME
                    """,
                    person_id=person_id,
                )
                return [self._record(row) for row in cursor.fetchall()]
        finally:
            connection.close()

    def correct(
        self,
        person_id: str,
        competency_id: str,
        proficiency_level: int,
        evidence: str,
        review_date: date,
        actor_id: str,
    ) -> dict[str, object]:
        if not 1 <= proficiency_level <= 5:
            raise CompetencyError("INVALID_LEVEL", 422, "proficiency_level")
        if not evidence.strip():
            raise CompetencyError("REQUIRED_EVIDENCE", 422, "evidence")

        connection = self._connection_factory()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT COMPETENCY_ID, SKILL_ID, PROFICIENCY_LEVEL, EVIDENCE, ORIGIN_TYPE
                      FROM VSK_PERSON_COMPETENCIES
                     WHERE COMPETENCY_ID = :competency_id AND PERSON_ID = :person_id
                     FOR UPDATE
                    """,
                    competency_id=competency_id,
                    person_id=person_id,
                )
                current = cursor.fetchone()
                if current is None:
                    raise CompetencyError("COMPETENCY_NOT_FOUND", 404)

                cursor.execute(
                    "SELECT SKILL_NAME FROM VSK_SKILLS WHERE SKILL_ID = :skill_id",
                    skill_id=current[1],
                )
                skill = cursor.fetchone()
                if skill is None:
                    raise CompetencyError("UNKNOWN_SKILL", 422, "skill_id")

                changed_at = datetime.now(UTC)
                cursor.execute(
                    """
                    INSERT INTO VSK_PERSON_COMPETENCY_HISTORY (
                        HISTORY_ID, COMPETENCY_ID, PREVIOUS_LEVEL, NEW_LEVEL,
                        PREVIOUS_EVIDENCE, NEW_EVIDENCE, ACTOR_ID, CHANGED_AT
                    ) VALUES (
                        :history_id, :competency_id, :previous_level, :new_level,
                        :previous_evidence, :new_evidence, :actor_id, :changed_at
                    )
                    """,
                    history_id=str(uuid4()),
                    competency_id=competency_id,
                    previous_level=current[2],
                    new_level=proficiency_level,
                    previous_evidence=current[3],
                    new_evidence=evidence.strip(),
                    actor_id=actor_id,
                    changed_at=changed_at,
                )
                reviewed_at = datetime.combine(review_date, time.min, tzinfo=UTC)
                cursor.execute(
                    """
                    UPDATE VSK_PERSON_COMPETENCIES
                       SET PROFICIENCY_LEVEL = :proficiency_level,
                           EVIDENCE = :evidence,
                           ACTOR_ID = :actor_id,
                           REVIEWED_AT = :reviewed_at
                     WHERE COMPETENCY_ID = :competency_id AND PERSON_ID = :person_id
                    """,
                    proficiency_level=proficiency_level,
                    evidence=evidence.strip(),
                    actor_id=actor_id,
                    reviewed_at=reviewed_at,
                    competency_id=competency_id,
                    person_id=person_id,
                )
                connection.commit()
                return {
                    "competency_id": competency_id,
                    "person_id": person_id,
                    "skill_id": current[1],
                    "skill_name": skill[0],
                    "proficiency_level": proficiency_level,
                    "evidence": evidence.strip(),
                    "origin_type": current[4],
                    "actor_id": actor_id,
                    "review_date": review_date.isoformat(),
                }
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _record(row: tuple[object, ...]) -> dict[str, object]:
        reviewed_at = row[8]
        review_date = reviewed_at.date() if isinstance(reviewed_at, datetime) else reviewed_at
        return {
            "competency_id": row[0],
            "person_id": row[1],
            "skill_id": row[2],
            "skill_name": row[3],
            "proficiency_level": row[4],
            "evidence": row[5],
            "origin_type": row[6],
            "actor_id": row[7],
            "review_date": review_date.isoformat(),
        }