from datetime import UTC, datetime
from uuid import uuid4

from .suggestions import SuggestionError, SuggestionRepository


class SuggestionReviewRepository(SuggestionRepository):
    def review_suggestion(
        self,
        person_id: str,
        suggestion_id: str,
        decision: str,
        reviewer_id: str,
        reviewed_level: int | None = None,
        reviewed_evidence: str | None = None,
    ) -> dict[str, object]:
        if decision not in {"accept", "edit", "reject"}:
            raise SuggestionError("INVALID_REVIEW_DECISION", 422, "decision")
        if decision == "edit":
            if reviewed_level is None or not 1 <= reviewed_level <= 5:
                raise SuggestionError("INVALID_LEVEL", 422, "reviewed_level")
            if not reviewed_evidence or not reviewed_evidence.strip():
                raise SuggestionError("REQUIRED_EVIDENCE", 422, "reviewed_evidence")

        connection = self._connection_factory()
        try:
            with connection.cursor() as cursor:
                suggestion = self.lock_pending_suggestion(cursor, person_id, suggestion_id)
                reviewed_at = datetime.now(UTC)
                if decision == "reject":
                    self.update_review_state(
                        cursor, person_id, suggestion_id, "REJECTED", reviewer_id, reviewed_at
                    )
                    connection.commit()
                    return self._review_result(
                        suggestion, "REJECTED", reviewer_id, reviewed_at, None, None, None
                    )

                final_level = reviewed_level if decision == "edit" else suggestion[3]
                final_evidence = (
                    reviewed_evidence.strip() if decision == "edit" else suggestion[5]
                )
                cursor.execute(
                    "SELECT SKILL_ID, SKILL_NAME FROM VSK_SKILLS "
                    "WHERE UPPER(SKILL_NAME) = UPPER(:skill_name)",
                    skill_name=suggestion[2],
                )
                skill = cursor.fetchone()
                if skill is None:
                    skill_id = str(uuid4())
                    skill_name = suggestion[2]
                    cursor.execute(
                        "INSERT INTO VSK_SKILLS (SKILL_ID, SKILL_NAME) "
                        "VALUES (:skill_id, :skill_name)",
                        skill_id=skill_id,
                        skill_name=skill_name,
                    )
                else:
                    skill_id, skill_name = skill

                cursor.execute(
                    """
                    SELECT COMPETENCY_ID, PROFICIENCY_LEVEL, EVIDENCE
                      FROM VSK_PERSON_COMPETENCIES
                     WHERE PERSON_ID = :person_id AND SKILL_ID = :skill_id
                     FOR UPDATE
                    """,
                    person_id=person_id,
                    skill_id=skill_id,
                )
                current = cursor.fetchone()
                if current is None:
                    competency_id = str(uuid4())
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
                        proficiency_level=final_level,
                        evidence=final_evidence,
                        origin_type="REVIEWED_SUGGESTION",
                        actor_id=reviewer_id,
                        reviewed_at=reviewed_at,
                    )
                else:
                    competency_id = current[0]
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
                        previous_level=current[1],
                        new_level=final_level,
                        previous_evidence=current[2],
                        new_evidence=final_evidence,
                        actor_id=reviewer_id,
                        changed_at=reviewed_at,
                    )
                    cursor.execute(
                        """
                        UPDATE VSK_PERSON_COMPETENCIES
                           SET PROFICIENCY_LEVEL = :proficiency_level,
                               EVIDENCE = :evidence, ORIGIN_TYPE = 'REVIEWED_SUGGESTION',
                               ACTOR_ID = :actor_id, REVIEWED_AT = :reviewed_at
                         WHERE COMPETENCY_ID = :competency_id
                        """,
                        proficiency_level=final_level,
                        evidence=final_evidence,
                        actor_id=reviewer_id,
                        reviewed_at=reviewed_at,
                        competency_id=competency_id,
                    )

                status = "ACCEPTED" if decision == "accept" else "EDITED"
                self.update_review_state(
                    cursor,
                    person_id,
                    suggestion_id,
                    status,
                    reviewer_id,
                    reviewed_at,
                    final_level,
                    final_evidence,
                    competency_id,
                )
                connection.commit()
                return self._review_result(
                    suggestion, status, reviewer_id, reviewed_at,
                    final_level, final_evidence, competency_id,
                    skill_name=skill_name,
                )
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _review_result(
        suggestion: tuple[object, ...],
        status: str,
        reviewer_id: str,
        reviewed_at: datetime,
        reviewed_level: int | None,
        reviewed_evidence: str | None,
        competency_id: str | None,
        skill_name: str | None = None,
    ) -> dict[str, object]:
        return {
            "suggestion_id": suggestion[0],
            "person_id": suggestion[1],
            "skill_name": skill_name or suggestion[2],
            "proficiency_level": suggestion[3],
            "confidence": suggestion[4],
            "evidence_span": suggestion[5],
            "source_sha256": suggestion[6],
            "status": status,
            "actor_id": suggestion[8],
            "created_at": suggestion[9],
            "reviewed_by": reviewer_id,
            "reviewed_at": reviewed_at,
            "reviewed_level": reviewed_level,
            "reviewed_evidence": reviewed_evidence,
            "competency_id": competency_id,
        }