from voskill.suggestions import SuggestionError


class MemorySuggestionRepository:
    def __init__(self) -> None:
        self.suggestions: list[dict] = []
        self.confirmed_competencies: list[dict] = []

    def create_suggestion(self, **values: object) -> dict:
        suggestion = {
            "suggestion_id": "SG-001",
            "status": "PENDING_REVIEW",
            "created_at": "2026-11-08T12:00:00+00:00",
            **values,
        }
        self.suggestions.append(suggestion)
        return suggestion

    def review_suggestion(
        self,
        person_id: str,
        suggestion_id: str,
        decision: str,
        reviewer_id: str,
        reviewed_level: int | None = None,
        reviewed_evidence: str | None = None,
    ) -> dict:
        suggestion = next(
            row
            for row in self.suggestions
            if row["suggestion_id"] == suggestion_id and row["person_id"] == person_id
        )
        if suggestion["status"] != "PENDING_REVIEW":
            raise SuggestionError("SUGGESTION_ALREADY_REVIEWED", 409)
        suggestion.update(
            status={"accept": "ACCEPTED", "edit": "EDITED", "reject": "REJECTED"}[decision],
            reviewed_by=reviewer_id,
            reviewed_at="2026-11-08T12:30:00+00:00",
            reviewed_level=(
                reviewed_level
                if decision == "edit"
                else suggestion["proficiency_level"] if decision == "accept" else None
            ),
            reviewed_evidence=(
                reviewed_evidence
                if decision == "edit"
                else suggestion["evidence_span"] if decision == "accept" else None
            ),
        )
        if decision in {"accept", "edit"}:
            self.confirmed_competencies.append(
                {
                    "person_id": person_id,
                    "skill_name": suggestion["skill_name"],
                    "proficiency_level": suggestion["reviewed_level"],
                    "evidence": suggestion["reviewed_evidence"],
                    "actor_id": reviewer_id,
                }
            )
        return suggestion


def _pending_suggestion(repository: MemorySuggestionRepository) -> dict:
    return repository.create_suggestion(
        person_id="P-001",
        skill_name="Kubernetes",
        proficiency_level=4,
        confidence=0.92,
        evidence_span="Migração do cluster Kubernetes",
        source_sha256="a" * 64,
        actor_id="U-001",
    )


class FixedCompetencyExtractor:
    def extract(self, source_text: str) -> dict:
        return {
            "skill_name": "Kubernetes",
            "proficiency_level": 4,
            "confidence": 0.92,
            "evidence_span": "Migração do cluster Kubernetes",
        }


class FailedCompetencyExtractor:
    def extract(self, source_text: str) -> dict:
        raise SuggestionError("PROVIDER_UNAVAILABLE", 503)


class UnsupportedEvidenceExtractor:
    def extract(self, source_text: str) -> dict:
        return {
            "skill_name": "Kubernetes",
            "proficiency_level": 4,
            "confidence": 0.92,
            "evidence_span": "Texto que não existe na fonte",
        }