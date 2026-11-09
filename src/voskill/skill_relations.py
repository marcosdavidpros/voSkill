from collections.abc import Callable
from uuid import uuid4

import oracledb

from .database import open_oracle_connection


class RelationError(ValueError):
    def __init__(self, code: str, status_code: int, field: str | None = None) -> None:
        self.code = code
        self.status_code = status_code
        self.field = field
        super().__init__(code)


class SkillRelationRepository:
    def __init__(
        self,
        connection_factory: Callable[[], oracledb.Connection] = open_oracle_connection,
    ) -> None:
        self._connection_factory = connection_factory

    def create(
        self,
        source_skill_id: str,
        target_skill_id: str,
        confidence: float,
        actor_id: str,
    ) -> dict[str, object]:
        if not 0 <= confidence <= 1:
            raise RelationError("INVALID_CONFIDENCE", 422, "confidence")
        if source_skill_id == target_skill_id:
            raise RelationError("INVALID_RELATION", 422, "target_skill_id")

        connection = self._connection_factory()
        try:
            with connection.cursor() as cursor:
                for field, skill_id in (
                    ("source_skill_id", source_skill_id),
                    ("target_skill_id", target_skill_id),
                ):
                    cursor.execute(
                        "SELECT SKILL_ID FROM VSK_SKILLS WHERE SKILL_ID = :skill_id",
                        skill_id=skill_id,
                    )
                    if cursor.fetchone() is None:
                        raise RelationError("UNKNOWN_SKILL", 422, field)

                cursor.execute(
                    """
                    SELECT RELATION_ID
                      FROM VSK_SKILL_RELATIONS
                     WHERE SOURCE_SKILL_ID = :source_skill_id
                       AND TARGET_SKILL_ID = :target_skill_id
                    """,
                    source_skill_id=source_skill_id,
                    target_skill_id=target_skill_id,
                )
                if cursor.fetchone() is not None:
                    raise RelationError("RELATION_ALREADY_EXISTS", 409)

                relation_id = str(uuid4())
                cursor.execute(
                    """
                    INSERT INTO VSK_SKILL_RELATIONS (
                        RELATION_ID, SOURCE_SKILL_ID, TARGET_SKILL_ID,
                        CONFIDENCE, ACTOR_ID
                    ) VALUES (
                        :relation_id, :source_skill_id, :target_skill_id,
                        :confidence, :actor_id
                    )
                    """,
                    relation_id=relation_id,
                    source_skill_id=source_skill_id,
                    target_skill_id=target_skill_id,
                    confidence=confidence,
                    actor_id=actor_id,
                )
                connection.commit()
                return {
                    "relation_id": relation_id,
                    "source_skill_id": source_skill_id,
                    "target_skill_id": target_skill_id,
                    "confidence": confidence,
                    "active": True,
                    "actor_id": actor_id,
                }
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def infer_for_person(self, person_id: str, target_skill_id: str) -> dict[str, object]:
        connection = self._connection_factory()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT R.RELATION_ID, R.SOURCE_SKILL_ID, R.TARGET_SKILL_ID,
                           R.CONFIDENCE, C.PROFICIENCY_LEVEL
                      FROM VSK_SKILL_RELATIONS R
                      JOIN VSK_PERSON_COMPETENCIES C
                        ON C.SKILL_ID = R.SOURCE_SKILL_ID
                       AND C.PERSON_ID = :person_id
                     WHERE R.TARGET_SKILL_ID = :target_skill_id
                       AND R.ACTIVE_FLAG = 'Y'
                     ORDER BY R.CONFIDENCE DESC, R.RELATION_ID
                     FETCH FIRST 1 ROWS ONLY
                    """,
                    person_id=person_id,
                    target_skill_id=target_skill_id,
                )
                row = cursor.fetchone()
        finally:
            connection.close()

        if row is None:
            return {
                "status": "insufficient_evidence",
                "person_id": person_id,
                "target_skill_id": target_skill_id,
                "inferred_level": None,
                "source_skill_id": None,
                "relation_id": None,
                "confidence": None,
                "reason": "insufficient_evidence",
            }

        relation_id, source_skill_id, _, confidence, source_level = row
        return {
            "status": "inferred",
            "person_id": person_id,
            "target_skill_id": target_skill_id,
            "inferred_level": source_level,
            "source_skill_id": source_skill_id,
            "relation_id": relation_id,
            "confidence": float(confidence),
            "reason": None,
        }