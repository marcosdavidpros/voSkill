from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

import oracledb

from .database import open_oracle_connection


class SuggestionError(ValueError):
    def __init__(self, code: str, status_code: int, field: str | None = None) -> None:
        self.code = code
        self.status_code = status_code
        self.field = field
        super().__init__(code)


class SuggestionRepository:
    def __init__(
        self,
        connection_factory: Callable[[], oracledb.Connection] = open_oracle_connection,
    ) -> None:
        self._connection_factory = connection_factory

    def create_suggestion(
        self,
        person_id: str,
        skill_name: str,
        proficiency_level: int,
        confidence: float,
        evidence_span: str,
        source_sha256: str,
        actor_id: str,
    ) -> dict[str, object]:
        if not skill_name.strip():
            raise SuggestionError("INVALID_SKILL", 422, "skill_name")
        if not 1 <= proficiency_level <= 5:
            raise SuggestionError("INVALID_LEVEL", 422, "proficiency_level")
        if not 0 <= confidence <= 1:
            raise SuggestionError("INVALID_CONFIDENCE", 422, "confidence")
        if not evidence_span.strip():
            raise SuggestionError("MISSING_EVIDENCE", 422, "evidence_span")
        if len(source_sha256) != 64:
            raise SuggestionError("INVALID_SOURCE_HASH", 422, "source_sha256")

        connection = self._connection_factory()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT PERSON_ID FROM VSK_PERSONS WHERE PERSON_ID = :person_id",
                    person_id=person_id,
                )
                if cursor.fetchone() is None:
                    raise SuggestionError("PERSON_NOT_FOUND", 404, "person_id")

                suggestion_id = str(uuid4())
                created_at = datetime.now(UTC)
                cursor.execute(
                    """
                    INSERT INTO VSK_SKILL_SUGGESTIONS (
                        SUGGESTION_ID, PERSON_ID, SUGGESTED_SKILL_NAME, SUGGESTED_LEVEL,
                        CONFIDENCE, EVIDENCE_SPAN, SOURCE_SHA256, STATUS, CREATED_BY, CREATED_AT
                    ) VALUES (
                        :suggestion_id, :person_id, :skill_name, :proficiency_level,
                        :confidence, :evidence_span, :source_sha256, :status,
                        :actor_id, :created_at
                    )
                    """,
                    suggestion_id=suggestion_id,
                    person_id=person_id,
                    skill_name=skill_name.strip(),
                    proficiency_level=proficiency_level,
                    confidence=confidence,
                    evidence_span=evidence_span.strip(),
                    source_sha256=source_sha256,
                    status="PENDING_REVIEW",
                    actor_id=actor_id,
                    created_at=created_at,
                )
                connection.commit()
                return {
                    "suggestion_id": suggestion_id,
                    "person_id": person_id,
                    "skill_name": skill_name.strip(),
                    "proficiency_level": proficiency_level,
                    "confidence": confidence,
                    "evidence_span": evidence_span.strip(),
                    "source_sha256": source_sha256,
                    "status": "PENDING_REVIEW",
                    "actor_id": actor_id,
                    "created_at": created_at,
                }
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def lock_pending_suggestion(
        cursor: oracledb.Cursor,
        person_id: str,
        suggestion_id: str,
    ) -> tuple[object, ...]:
        cursor.execute(
            """
            SELECT SUGGESTION_ID, PERSON_ID, SUGGESTED_SKILL_NAME,
                   SUGGESTED_LEVEL, CONFIDENCE, EVIDENCE_SPAN, SOURCE_SHA256,
                   STATUS, CREATED_BY, CREATED_AT
              FROM VSK_SKILL_SUGGESTIONS
             WHERE SUGGESTION_ID = :suggestion_id AND PERSON_ID = :person_id
             FOR UPDATE
            """,
            suggestion_id=suggestion_id,
            person_id=person_id,
        )
        suggestion = cursor.fetchone()
        if suggestion is None:
            raise SuggestionError("SUGGESTION_NOT_FOUND", 404)
        if suggestion[7] != "PENDING_REVIEW":
            raise SuggestionError("SUGGESTION_ALREADY_REVIEWED", 409)
        return suggestion

    @staticmethod
    def update_review_state(
        cursor: oracledb.Cursor,
        person_id: str,
        suggestion_id: str,
        status: str,
        reviewer_id: str,
        reviewed_at: datetime,
        reviewed_level: int | None = None,
        reviewed_evidence: str | None = None,
        competency_id: str | None = None,
    ) -> None:
        cursor.execute(
            """
            UPDATE VSK_SKILL_SUGGESTIONS
               SET STATUS = :status, REVIEWED_BY = :reviewer_id,
                   REVIEWED_AT = :reviewed_at, REVIEWED_LEVEL = :reviewed_level,
                   REVIEWED_EVIDENCE = :reviewed_evidence,
                   COMPETENCY_ID = :competency_id
             WHERE SUGGESTION_ID = :suggestion_id
               AND PERSON_ID = :person_id
               AND STATUS = 'PENDING_REVIEW'
            """,
            status=status,
            reviewer_id=reviewer_id,
            reviewed_at=reviewed_at,
            reviewed_level=reviewed_level,
            reviewed_evidence=reviewed_evidence,
            competency_id=competency_id,
            suggestion_id=suggestion_id,
            person_id=person_id,
        )