import asyncio
from hashlib import sha256

import httpx
from fastapi.exceptions import RequestValidationError
from starlette.requests import Request

from voskill.database import CompetencyError, DemandError, ScenarioError
from voskill.main import (
    app,
    get_actor_id,
    get_competency_extractor,
    get_competency_repository,
    get_demand_repository,
    get_scenario_repository,
    get_skill_relation_repository,
    get_suggestion_repository,
    handle_request_validation_error,
)
from voskill.skill_relations import RelationError
from voskill.suggestions import SuggestionError


def test_health_endpoint_does_not_require_oracle() -> None:
    async def get_health() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/health")

    response = asyncio.run(get_health())

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


class StateInjector:
    def __init__(self, application, state: dict[str, object]) -> None:
        self.application = application
        self.state = state

    async def __call__(self, scope, receive, send) -> None:
        scope.setdefault("state", {}).update(self.state)
        await self.application(scope, receive, send)


def _request(
    method: str,
    path: str,
    payload: dict | None = None,
    state: dict[str, object] | None = None,
) -> httpx.Response:
    async def send() -> httpx.Response:
        application = StateInjector(app, state) if state is not None else app
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, path, json=payload)

    return asyncio.run(send())


class MemoryDemandRepository:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def create(self, **values: object) -> dict:
        record = {
            "demand_id": "D-001",
            **values,
            "period": values["period_start"].strftime("%Y-%m"),
        }
        del record["period_start"]
        self.rows.append(record)
        return record

    def list_for_project(self, project_id: str) -> list[dict]:
        return [row for row in self.rows if row["project_id"] == project_id]

    def update(self, demand_id: str, project_id: str, **values: object) -> dict:
        for row in self.rows:
            if row["demand_id"] == demand_id and row["project_id"] == project_id:
                row.update(values)
                row["period"] = values["period_start"].strftime("%Y-%m")
                del row["period_start"]
                return row
        raise DemandError("DEMAND_NOT_FOUND", 404)


class MemoryCompetencyRepository:
    def __init__(self) -> None:
        self.rows: list[dict] = []
        self.history: list[dict] = []

    def create(self, **values: object) -> dict:
        if not 1 <= values["proficiency_level"] <= 5:
            raise CompetencyError("INVALID_LEVEL", 422, "proficiency_level")
        if not values["evidence"].strip():
            raise CompetencyError("REQUIRED_EVIDENCE", 422, "evidence")
        record = {
            "competency_id": "C-001",
            "skill_name": "Kubernetes",
            "origin_type": "MANUAL",
            **values,
        }
        self.rows.append(record)
        return record

    def list_for_person(self, person_id: str) -> list[dict]:
        return [row for row in self.rows if row["person_id"] == person_id]

    def correct(self, **values: object) -> dict:
        row = next(
            row
            for row in self.rows
            if row["competency_id"] == values["competency_id"]
            and row["person_id"] == values["person_id"]
        )
        self.history.append(
            {
                "previous_level": row["proficiency_level"],
                "new_level": values["proficiency_level"],
                "actor_id": values["actor_id"],
                "changed_at": "2026-11-08T00:00:00+00:00",
            }
        )
        row.update(
            proficiency_level=values["proficiency_level"],
            evidence=values["evidence"],
            actor_id=values["actor_id"],
            review_date=values["review_date"].isoformat(),
        )
        return row


def _existing_competency() -> dict:
    return {
        "competency_id": "C-001",
        "person_id": "P-001",
        "skill_id": "SKILL-1",
        "skill_name": "Kubernetes",
        "proficiency_level": 4,
        "evidence": "Migração do cluster",
        "origin_type": "MANUAL",
        "actor_id": "U-001",
        "review_date": "2026-11-08",
    }


class MemoryScenarioRepository:
    def __init__(self) -> None:
        self.base_snapshot = b'{"demands":[]}'
        self.created_alternatives: list[dict] = []

    def create_alternative(
        self,
        base_scenario_id: str,
        name: str,
        deltas: dict,
        actor_id: str,
    ) -> dict:
        if base_scenario_id != "B-001":
            raise ScenarioError("BASE_SCENARIO_NOT_FOUND", 404)
        alternative = {
            "scenario_id": "A-001",
            "base_scenario_id": base_scenario_id,
            "project_id": "P-001",
            "snapshot_id": "S-001",
            "name": name,
            "actor_id": actor_id,
            "created_at": "2026-11-08T12:00:00+00:00",
            "deltas": deltas,
        }
        self.created_alternatives.append(alternative)
        return alternative

    def compare(self, first_scenario_id: str, second_scenario_id: str) -> dict:
        return {
            "scenario_ids": [first_scenario_id, second_scenario_id],
            "scenarios": [
                {"scenario_id": first_scenario_id, "status": "complete", "missing": []},
                {
                    "scenario_id": second_scenario_id,
                    "status": "incomplete",
                    "missing": [{"period": "2026-02", "field": "availability"}],
                },
            ],
            "periods": [
                {
                    "period": "2026-01",
                    "assumptions": {first_scenario_id: {}, second_scenario_id: {}},
                    "changed_values": {},
                }
            ],
        }


class MemorySkillRelationRepository:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def create(self, **values: object) -> dict:
        relation = {"relation_id": "R-001", "active": True, **values}
        self.rows.append(relation)
        return relation


class MemorySkillInferenceRepository:
    def __init__(self, result: dict) -> None:
        self.result = result
        self.confirmed_competencies = {"SKILL-1": 4}
        self.calls: list[tuple[str, str]] = []

    def infer_for_person(self, person_id: str, target_skill_id: str) -> dict:
        self.calls.append((person_id, target_skill_id))
        return {**self.result, "person_id": person_id, "target_skill_id": target_skill_id}


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
        reviewed_at = "2026-11-08T12:30:00+00:00"
        suggestion.update(
            status={"accept": "ACCEPTED", "edit": "EDITED", "reject": "REJECTED"}[decision],
            reviewed_by=reviewer_id,
            reviewed_at=reviewed_at,
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


def test_demand_write_requires_authenticated_actor_context() -> None:
    response = _request(
        "POST",
        "/projects/P-001/demands",
        {
            "skill_id": "SKILL-1",
            "proficiency_level": 3,
            "period": "2026-01",
            "load_amount": 40,
            "load_unit": "hours",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTHENTICATION_REQUIRED"


def test_skill_relation_create_requires_explicit_management_authorization() -> None:
    repository = MemorySkillRelationRepository()
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_skill_relation_repository] = lambda: repository

    try:
        response = _request(
            "POST",
            "/skill-relations",
            {
                "source_skill_id": "SKILL-1",
                "target_skill_id": "SKILL-2",
                "confidence": 0.65,
            },
            state={"can_manage_skill_relations": False},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "FORBIDDEN"
    assert repository.rows == []


def test_authorized_user_can_create_skill_relation() -> None:
    repository = MemorySkillRelationRepository()
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_skill_relation_repository] = lambda: repository

    try:
        response = _request(
            "POST",
            "/skill-relations",
            {
                "source_skill_id": "SKILL-1",
                "target_skill_id": "SKILL-2",
                "confidence": 0.65,
            },
            state={"can_manage_skill_relations": True},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["source_skill_id"] == "SKILL-1"
    assert response.json()["target_skill_id"] == "SKILL-2"
    assert response.json()["confidence"] == 0.65
    assert response.json()["actor_id"] == "U-001"
    assert repository.rows[0]["actor_id"] == "U-001"


def test_skill_relation_api_rejects_invalid_confidence() -> None:
    repository = MemorySkillRelationRepository()
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_skill_relation_repository] = lambda: repository

    try:
        response = _request(
            "POST",
            "/skill-relations",
            {
                "source_skill_id": "SKILL-1",
                "target_skill_id": "SKILL-2",
                "confidence": 1.2,
            },
            state={"can_manage_skill_relations": True},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json()["detail"]["fieldErrors"] == {
        "confidence": "INVALID_CONFIDENCE"
    }
    assert repository.rows == []


def test_skill_relation_api_maps_unknown_skill_error() -> None:
    class UnknownSkillRepository:
        def create(self, **values: object) -> dict:
            raise RelationError("UNKNOWN_SKILL", 422, "target_skill_id")

    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_skill_relation_repository] = lambda: UnknownSkillRepository()

    try:
        response = _request(
            "POST",
            "/skill-relations",
            {
                "source_skill_id": "SKILL-1",
                "target_skill_id": "SKILL-404",
                "confidence": 0.65,
            },
            state={"can_manage_skill_relations": True},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "UNKNOWN_SKILL"
    assert response.json()["detail"]["fieldErrors"] == {
        "target_skill_id": "UNKNOWN_SKILL"
    }


def test_skill_inference_returns_traceable_result_without_changing_profile() -> None:
    repository = MemorySkillInferenceRepository(
        {
            "status": "inferred",
            "inferred_level": 4,
            "source_skill_id": "SKILL-1",
            "relation_id": "REL-001",
            "confidence": 0.65,
            "reason": None,
        }
    )
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_skill_relation_repository] = lambda: repository

    try:
        response = _request(
            "GET",
            "/people/P-001/skill-inference/SKILL-2",
            state={"authorized_person_ids": ["P-001"]},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "inferred"
    assert response.json()["inferred_level"] == 4
    assert response.json()["relationId"] == "REL-001"
    assert response.json()["confidence"] == 0.65
    assert repository.calls == [("P-001", "SKILL-2")]
    assert repository.confirmed_competencies == {"SKILL-1": 4}


def test_skill_inference_without_evidence_returns_no_level() -> None:
    repository = MemorySkillInferenceRepository(
        {
            "status": "insufficient_evidence",
            "inferred_level": None,
            "source_skill_id": None,
            "relation_id": None,
            "confidence": None,
            "reason": "insufficient_evidence",
        }
    )
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_skill_relation_repository] = lambda: repository

    try:
        response = _request(
            "GET",
            "/people/P-001/skill-inference/SKILL-2",
            state={"authorized_person_ids": ["P-001"]},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["inferred_level"] is None
    assert response.json()["reason"] == "insufficient_evidence"


def test_skill_inference_requires_person_authorization() -> None:
    repository = MemorySkillInferenceRepository({"status": "inferred"})
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_skill_relation_repository] = lambda: repository

    try:
        response = _request(
            "GET",
            "/people/P-001/skill-inference/SKILL-2",
            state={"authorized_person_ids": []},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert repository.calls == []


def test_manual_competency_create_and_read_returns_exact_values() -> None:
    repository = MemoryCompetencyRepository()
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_competency_repository] = lambda: repository

    try:
        created = _request(
            "POST",
            "/people/P-001/competencies",
            {
                "skill_id": "SKILL-1",
                "proficiency_level": 4,
                "evidence": "Migração do cluster",
                "review_date": "2026-11-08",
            },
            state={"authorized_person_ids": ["P-001"]},
        )
        read_back = _request("GET", "/people/P-001/competencies")
    finally:
        app.dependency_overrides.clear()

    assert created.status_code == 201
    assert created.json()["person_id"] == "P-001"
    assert created.json()["skill_name"] == "Kubernetes"
    assert created.json()["proficiency_level"] == 4
    assert created.json()["evidence"] == "Migração do cluster"
    assert created.json()["origin_type"] == "MANUAL"
    assert created.json()["actor_id"] == "U-001"
    assert created.json()["review_date"] == "2026-11-08"
    assert read_back.status_code == 200
    assert read_back.json()[0] == created.json()


def test_competency_write_requires_authenticated_actor() -> None:
    response = _request(
        "POST",
        "/people/P-001/competencies",
        {
            "skill_id": "SKILL-1",
            "proficiency_level": 4,
            "evidence": "Migração do cluster",
            "review_date": "2026-11-08",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTHENTICATION_REQUIRED"


def test_competency_repository_error_preserves_field_error() -> None:
    class RejectingCompetencyRepository:
        def create(self, **values: object) -> dict:
            raise CompetencyError("REQUIRED_EVIDENCE", 422, "evidence")

    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_competency_repository] = lambda: RejectingCompetencyRepository()

    try:
        response = _request(
            "POST",
            "/people/P-001/competencies",
            {
                "skill_id": "SKILL-1",
                "proficiency_level": 4,
                "evidence": "Evidence",
                "review_date": "2026-11-08",
            },
            state={"authorized_person_ids": ["P-001"]},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "REQUIRED_EVIDENCE"
    assert response.json()["detail"]["fieldErrors"] == {"evidence": "REQUIRED_EVIDENCE"}


def test_competency_read_maps_unknown_person_to_404() -> None:
    class MissingPersonCompetencyRepository:
        def list_for_person(self, person_id: str) -> list[dict]:
            raise CompetencyError("PERSON_NOT_FOUND", 404, "person_id")

    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_competency_repository] = (
        lambda: MissingPersonCompetencyRepository()
    )

    try:
        response = _request("GET", "/people/P-404/competencies")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "PERSON_NOT_FOUND"
    assert response.json()["detail"]["fieldErrors"] == {"person_id": "PERSON_NOT_FOUND"}


def test_authorized_competency_correction_updates_value_and_history() -> None:
    repository = MemoryCompetencyRepository()
    repository.rows.append(_existing_competency())
    app.dependency_overrides[get_competency_repository] = lambda: repository

    response = _request(
        "PATCH",
        "/people/P-001/competencies/C-001",
        {
            "proficiency_level": 3,
            "evidence": "Operação do cluster",
            "review_date": "2026-11-08",
        },
        state={"actor_id": "U-001", "authorized_person_ids": ["P-001"]},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["proficiency_level"] == 3
    assert response.json()["actor_id"] == "U-001"
    assert repository.history == [
        {
            "previous_level": 4,
            "new_level": 3,
            "actor_id": "U-001",
            "changed_at": "2026-11-08T00:00:00+00:00",
        }
    ]


def test_person_can_correct_own_competency() -> None:
    repository = MemoryCompetencyRepository()
    repository.rows.append(_existing_competency())
    app.dependency_overrides[get_competency_repository] = lambda: repository

    response = _request(
        "PATCH",
        "/people/P-001/competencies/C-001",
        {
            "proficiency_level": 3,
            "evidence": "Atualização pela própria pessoa",
            "review_date": "2026-11-08",
        },
        state={"actor_id": "P-001"},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["actor_id"] == "P-001"
    assert response.json()["proficiency_level"] == 3
    assert repository.history[0]["actor_id"] == "P-001"


def test_extraction_stores_pending_suggestion_without_changing_confirmed_profile() -> None:
    repository = MemorySuggestionRepository()
    confirmed_before = [row.copy() for row in repository.confirmed_competencies]
    source_text = "Experiência: Migração do cluster Kubernetes."
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_suggestion_repository] = lambda: repository
    app.dependency_overrides[get_competency_extractor] = lambda: FixedCompetencyExtractor()

    try:
        response = _request(
            "POST",
            "/people/P-001/competency-suggestions/extract",
            {"source_text": source_text},
            state={"authorized_person_ids": ["P-001"]},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["skill_name"] == "Kubernetes"
    assert response.json()["proficiency_level"] == 4
    assert response.json()["confidence"] == 0.92
    assert response.json()["evidence_span"] == "Migração do cluster Kubernetes"
    assert response.json()["status"] == "PENDING_REVIEW"
    assert response.json()["actor_id"] == "U-001"
    assert response.json()["source_sha256"] == sha256(source_text.encode("utf-8")).hexdigest()
    assert "source_text" not in repository.suggestions[0]
    assert len(repository.suggestions) == 1
    assert repository.confirmed_competencies == confirmed_before


def test_empty_source_returns_error_without_persisting_suggestion() -> None:
    repository = MemorySuggestionRepository()
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_suggestion_repository] = lambda: repository
    app.dependency_overrides[get_competency_extractor] = lambda: FixedCompetencyExtractor()

    try:
        response = _request(
            "POST",
            "/people/P-001/competency-suggestions/extract",
            {"source_text": "   "},
            state={"authorized_person_ids": ["P-001"]},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "EMPTY_SOURCE"
    assert repository.suggestions == []
    assert repository.confirmed_competencies == []


def test_extractor_failure_returns_provider_unavailable_without_persisting() -> None:
    repository = MemorySuggestionRepository()
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_suggestion_repository] = lambda: repository
    app.dependency_overrides[get_competency_extractor] = lambda: FailedCompetencyExtractor()

    try:
        response = _request(
            "POST",
            "/people/P-001/competency-suggestions/extract",
            {"source_text": "Migração do cluster Kubernetes"},
            state={"authorized_person_ids": ["P-001"]},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "PROVIDER_UNAVAILABLE"
    assert repository.suggestions == []
    assert repository.confirmed_competencies == []


def test_extractor_evidence_must_be_an_exact_source_span() -> None:
    repository = MemorySuggestionRepository()
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_suggestion_repository] = lambda: repository
    app.dependency_overrides[get_competency_extractor] = lambda: UnsupportedEvidenceExtractor()

    try:
        response = _request(
            "POST",
            "/people/P-001/competency-suggestions/extract",
            {"source_text": "Migração do cluster Kubernetes"},
            state={"authorized_person_ids": ["P-001"]},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "EVIDENCE_NOT_IN_SOURCE"
    assert repository.suggestions == []
    assert repository.confirmed_competencies == []


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


def test_authorized_reviewer_accepts_suggestion_into_confirmed_profile() -> None:
    repository = MemorySuggestionRepository()
    _pending_suggestion(repository)
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_suggestion_repository] = lambda: repository

    try:
        response = _request(
            "POST",
            "/people/P-001/competency-suggestions/SG-001/review",
            {"decision": "accept"},
            state={"authorized_person_ids": ["P-001"]},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "ACCEPTED"
    assert response.json()["reviewed_by"] == "U-001"
    assert response.json()["reviewed_level"] == 4
    assert repository.confirmed_competencies[0]["actor_id"] == "U-001"


def test_authorized_reviewer_edits_values_before_confirmation() -> None:
    repository = MemorySuggestionRepository()
    _pending_suggestion(repository)
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_suggestion_repository] = lambda: repository

    try:
        response = _request(
            "POST",
            "/people/P-001/competency-suggestions/SG-001/review",
            {
                "decision": "edit",
                "reviewed_level": 3,
                "reviewed_evidence": "Operação de cluster Kubernetes",
            },
            state={"authorized_person_ids": ["P-001"]},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "EDITED"
    assert response.json()["reviewed_level"] == 3
    assert response.json()["reviewed_evidence"] == "Operação de cluster Kubernetes"
    assert repository.confirmed_competencies[0]["proficiency_level"] == 3


def test_authorized_reviewer_rejects_without_changing_confirmed_profile() -> None:
    repository = MemorySuggestionRepository()
    _pending_suggestion(repository)
    original_profile = [row.copy() for row in repository.confirmed_competencies]
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_suggestion_repository] = lambda: repository

    try:
        response = _request(
            "POST",
            "/people/P-001/competency-suggestions/SG-001/review",
            {"decision": "reject"},
            state={"authorized_person_ids": ["P-001"]},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "REJECTED"
    assert response.json()["reviewed_by"] == "U-001"
    assert repository.confirmed_competencies == original_profile


def test_unauthorized_reviewer_cannot_change_suggestion_or_profile() -> None:
    repository = MemorySuggestionRepository()
    original_suggestion = _pending_suggestion(repository).copy()
    original_profile = [row.copy() for row in repository.confirmed_competencies]
    app.dependency_overrides[get_actor_id] = lambda: "U-999"
    app.dependency_overrides[get_suggestion_repository] = lambda: repository

    try:
        response = _request(
            "POST",
            "/people/P-001/competency-suggestions/SG-001/review",
            {"decision": "accept"},
            state={"authorized_person_ids": []},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert repository.suggestions[0] == original_suggestion
    assert repository.confirmed_competencies == original_profile


def test_authorized_review_accepts_suggestion_into_confirmed_profile() -> None:
    repository = MemorySuggestionRepository()
    repository.create_suggestion(
        person_id="P-001",
        skill_name="Kubernetes",
        proficiency_level=4,
        confidence=0.92,
        evidence_span="Migração do cluster Kubernetes",
        source_sha256="a" * 64,
        actor_id="U-001",
    )
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_suggestion_repository] = lambda: repository

    try:
        response = _request(
            "POST",
            "/people/P-001/competency-suggestions/SG-001/review",
            {"decision": "accept"},
            state={"authorized_person_ids": ["P-001"]},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "ACCEPTED"
    assert response.json()["reviewed_by"] == "U-001"
    assert response.json()["reviewed_level"] == 4
    assert repository.confirmed_competencies == [
        {
            "person_id": "P-001",
            "skill_name": "Kubernetes",
            "proficiency_level": 4,
            "evidence": "Migração do cluster Kubernetes",
            "actor_id": "U-001",
        }
    ]


def test_authorized_review_can_edit_values_before_accepting() -> None:
    repository = MemorySuggestionRepository()
    repository.create_suggestion(
        person_id="P-001",
        skill_name="Kubernetes",
        proficiency_level=4,
        confidence=0.92,
        evidence_span="Migração do cluster Kubernetes",
        source_sha256="a" * 64,
        actor_id="U-001",
    )
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_suggestion_repository] = lambda: repository

    try:
        response = _request(
            "POST",
            "/people/P-001/competency-suggestions/SG-001/review",
            {
                "decision": "edit",
                "reviewed_level": 3,
                "reviewed_evidence": "Operação do cluster",
            },
            state={"authorized_person_ids": ["P-001"]},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "EDITED"
    assert response.json()["reviewed_level"] == 3
    assert response.json()["reviewed_evidence"] == "Operação do cluster"
    assert repository.confirmed_competencies[0]["proficiency_level"] == 3


def test_authorized_rejection_does_not_change_confirmed_profile() -> None:
    repository = MemorySuggestionRepository()
    repository.create_suggestion(
        person_id="P-001",
        skill_name="Kubernetes",
        proficiency_level=4,
        confidence=0.92,
        evidence_span="Migração do cluster Kubernetes",
        source_sha256="a" * 64,
        actor_id="U-001",
    )
    original_profile = [row.copy() for row in repository.confirmed_competencies]
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_suggestion_repository] = lambda: repository

    try:
        response = _request(
            "POST",
            "/people/P-001/competency-suggestions/SG-001/review",
            {"decision": "reject"},
            state={"authorized_person_ids": ["P-001"]},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "REJECTED"
    assert response.json()["reviewed_by"] == "U-001"
    assert repository.confirmed_competencies == original_profile


def test_unauthorized_review_returns_403_without_changing_suggestion_or_profile() -> None:
    repository = MemorySuggestionRepository()
    original_suggestion = repository.create_suggestion(
        person_id="P-001",
        skill_name="Kubernetes",
        proficiency_level=4,
        confidence=0.92,
        evidence_span="Migração do cluster Kubernetes",
        source_sha256="a" * 64,
        actor_id="U-001",
    ).copy()
    app.dependency_overrides[get_actor_id] = lambda: "U-999"
    app.dependency_overrides[get_suggestion_repository] = lambda: repository

    try:
        response = _request(
            "POST",
            "/people/P-001/competency-suggestions/SG-001/review",
            {"decision": "accept"},
            state={"authorized_person_ids": []},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert repository.suggestions[0] == original_suggestion
    assert repository.confirmed_competencies == []


def test_unauthorized_competency_correction_returns_403_without_changes() -> None:
    repository = MemoryCompetencyRepository()
    repository.rows.append(_existing_competency())
    original_rows = [row.copy() for row in repository.rows]
    app.dependency_overrides[get_competency_repository] = lambda: repository

    response = _request(
        "PATCH",
        "/people/P-001/competencies/C-001",
        {
            "proficiency_level": 3,
            "evidence": "Unauthorized change",
            "review_date": "2026-11-08",
        },
        state={"actor_id": "U-999", "authorized_person_ids": []},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 403
    assert repository.rows == original_rows
    assert repository.history == []


def test_invalid_manual_competency_fields_are_rejected_without_partial_insert() -> None:
    repository = MemoryCompetencyRepository()
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_competency_repository] = lambda: repository

    try:
        invalid_level = _request(
            "POST",
            "/people/P-001/competencies",
            {
                "skill_id": "SKILL-1",
                "proficiency_level": 6,
                "evidence": "Evidence",
                "review_date": "2026-11-08",
            },
            state={"authorized_person_ids": ["P-001"]},
        )
        missing_evidence = _request(
            "POST",
            "/people/P-001/competencies",
            {
                "skill_id": "SKILL-1",
                "proficiency_level": 4,
                "evidence": "   ",
                "review_date": "2026-11-08",
            },
            state={"authorized_person_ids": ["P-001"]},
        )
    finally:
        app.dependency_overrides.clear()

    assert invalid_level.status_code == 422
    assert invalid_level.json()["detail"]["fieldErrors"] == {
        "proficiency_level": "INVALID_LEVEL"
    }
    assert missing_evidence.status_code == 422
    assert missing_evidence.json()["detail"]["fieldErrors"] == {
        "evidence": "REQUIRED_EVIDENCE"
    }
    assert repository.rows == []


def test_validation_handler_reports_leaf_field_for_nested_location() -> None:
    error = RequestValidationError(
        [
            {
                "loc": ("body", "competency", "evidence"),
                "msg": "Field required",
                "type": "missing",
            }
        ]
    )
    request = Request({"type": "http", "headers": []})

    response = asyncio.run(handle_request_validation_error(request, error))

    assert response.status_code == 422
    assert b'"evidence":"REQUIRED_EVIDENCE"' in response.body


def test_demand_routes_create_list_and_update_rows() -> None:
    repository = MemoryDemandRepository()
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_demand_repository] = lambda: repository
    payload = {
        "skill_id": "SKILL-1",
        "proficiency_level": 3,
        "period": "2026-01",
        "load_amount": 40,
        "load_unit": "hours",
    }

    try:
        created = _request("POST", "/projects/P-001/demands", payload)
        schedule = _request("GET", "/projects/P-001/demands")
        updated_payload = {**payload, "proficiency_level": 4, "load_amount": 32}
        updated = _request("PATCH", "/projects/P-001/demands/D-001", updated_payload)
    finally:
        app.dependency_overrides.clear()

    assert created.status_code == 201
    assert created.json()["project_id"] == "P-001"
    assert created.json()["actor_id"] == "U-001"
    assert schedule.status_code == 200
    assert schedule.json()[0]["period"] == "2026-01"
    assert updated.status_code == 200
    assert updated.json()["proficiency_level"] == 4
    assert updated.json()["load_amount"] == 32


def test_demand_api_preserves_repository_error_code() -> None:
    class RejectingRepository:
        def create(self, **values: object) -> dict:
            raise DemandError("INVALID_LOAD_UNIT", 422, "load_unit")

    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_demand_repository] = lambda: RejectingRepository()

    try:
        response = _request(
            "POST",
            "/projects/P-001/demands",
            {
                "skill_id": "SKILL-1",
                "proficiency_level": 3,
                "period": "2026-01",
                "load_amount": 40,
                "load_unit": "widgets",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INVALID_LOAD_UNIT"
    assert response.json()["detail"]["fieldErrors"] == {"load_unit": "INVALID_LOAD_UNIT"}


def test_invalid_payload_fields_are_reported_without_changing_schedule() -> None:
    repository = MemoryDemandRepository()
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_demand_repository] = lambda: repository
    valid_payload = {
        "skill_id": "SKILL-1",
        "proficiency_level": 3,
        "period": "2026-01",
        "load_amount": 40,
        "load_unit": "hours",
    }

    try:
        _request("POST", "/projects/P-001/demands", valid_payload)
        original_schedule = [row.copy() for row in repository.rows]
        invalid_level = _request(
            "POST",
            "/projects/P-001/demands",
            {**valid_payload, "proficiency_level": 6},
        )
        invalid_load = _request(
            "POST",
            "/projects/P-001/demands",
            {**valid_payload, "load_amount": -1},
        )
        current_schedule = _request("GET", "/projects/P-001/demands")
    finally:
        app.dependency_overrides.clear()

    assert invalid_level.status_code == 422
    assert invalid_level.json()["detail"]["fieldErrors"] == {
        "proficiency_level": "INVALID_LEVEL"
    }
    assert invalid_load.status_code == 422
    assert invalid_load.json()["detail"]["fieldErrors"] == {"load_amount": "INVALID_LOAD"}
    assert current_schedule.json() == original_schedule


def test_create_alternative_reuses_base_snapshot_and_returns_deltas() -> None:
    repository = MemoryScenarioRepository()
    base_snapshot_before = repository.base_snapshot
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_scenario_repository] = lambda: repository

    try:
        response = _request(
            "POST",
            "/scenarios/B-001/alternatives",
            {
                "name": "Alternative A",
                "deltas": {"demandOverrides": [{"period": "2026-01", "loadAmount": 48}]},
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["base_scenario_id"] == "B-001"
    assert response.json()["snapshot_id"] == "S-001"
    assert response.json()["actor_id"] == "U-001"
    assert response.json()["deltas"]["demandOverrides"][0]["loadAmount"] == 48
    assert repository.base_snapshot == base_snapshot_before


def test_create_alternative_for_missing_base_returns_stable_error() -> None:
    repository = MemoryScenarioRepository()
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_scenario_repository] = lambda: repository

    try:
        response = _request(
            "POST",
            "/scenarios/B-404/alternatives",
            {"name": "Alternative A", "deltas": {"demandOverrides": []}},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "BASE_SCENARIO_NOT_FOUND"
    assert repository.created_alternatives == []


def test_compare_scenarios_returns_assumptions_and_missing_fields() -> None:
    repository = MemoryScenarioRepository()
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_scenario_repository] = lambda: repository

    try:
        response = _request(
            "GET",
            "/scenarios/S-001/compare/S-002",
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["scenario_ids"] == ["S-001", "S-002"]
    assert response.json()["scenarios"][1]["status"] == "incomplete"
    assert response.json()["scenarios"][1]["missing"] == [
        {"period": "2026-02", "field": "availability"}
    ]
    assert "metrics" not in response.json()