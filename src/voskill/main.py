from datetime import date, datetime
from decimal import Decimal
from hashlib import sha256
from typing import Annotated, Literal, Protocol

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field, ValidationError
from starlette.responses import JSONResponse

from .database import (
    CompetencyError,
    CompetencyRepository,
    DemandError,
    DemandRepository,
    ScenarioError,
    ScenarioRepository,
)
from .skill_relations import RelationError, SkillRelationRepository
from .suggestion_review import SuggestionReviewRepository
from .suggestions import SuggestionError

app = FastAPI(title="voSkill API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


class DemandPayload(BaseModel):
    skill_id: str = Field(min_length=1)
    proficiency_level: int = Field(ge=1, le=5)
    period: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    load_amount: Decimal = Field(ge=0)
    load_unit: str = Field(min_length=1)

    @property
    def period_start(self) -> date:
        year, month = (int(value) for value in self.period.split("-"))
        return date(year, month, 1)


class CompetencyPayload(BaseModel):
    skill_id: str = Field(min_length=1)
    proficiency_level: int = Field(ge=1, le=5)
    evidence: str = Field(min_length=1)
    review_date: date


class CompetencyCorrectionPayload(BaseModel):
    proficiency_level: int = Field(ge=1, le=5)
    evidence: str = Field(min_length=1)
    review_date: date


class ExtractionPayload(BaseModel):
    source_text: str = Field(max_length=20000)


class ExtractedCompetency(BaseModel):
    skill_name: str = Field(min_length=1, max_length=150)
    proficiency_level: int = Field(ge=1, le=5)
    confidence: float = Field(ge=0, le=1)
    evidence_span: str = Field(min_length=1, max_length=4000)


class SuggestionReviewPayload(BaseModel):
    decision: Literal["accept", "edit", "reject"]
    reviewed_level: int | None = Field(default=None, ge=1, le=5)
    reviewed_evidence: str | None = Field(default=None, min_length=1)


class SkillRelationPayload(BaseModel):
    source_skill_id: str = Field(min_length=1)
    target_skill_id: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)


class CompetencyExtractor(Protocol):
    def extract(self, source_text: str) -> ExtractedCompetency: ...


class UnavailableCompetencyExtractor:
    def extract(self, source_text: str) -> ExtractedCompetency:
        raise SuggestionError("PROVIDER_UNAVAILABLE", 503)


class DemandResponse(BaseModel):
    demand_id: str
    project_id: str
    skill_id: str
    proficiency_level: int
    period: str
    load_amount: float
    load_unit: str
    actor_id: str


class CompetencyResponse(BaseModel):
    competency_id: str
    person_id: str
    skill_id: str
    skill_name: str
    proficiency_level: int
    evidence: str
    origin_type: str
    actor_id: str
    review_date: date


class SuggestionResponse(BaseModel):
    suggestion_id: str
    person_id: str
    skill_name: str
    proficiency_level: int
    confidence: float
    evidence_span: str
    source_sha256: str
    status: str
    actor_id: str
    created_at: datetime


class SuggestionReviewResponse(SuggestionResponse):
    reviewed_by: str
    reviewed_at: datetime
    reviewed_level: int | None
    reviewed_evidence: str | None
    competency_id: str | None = None


class SkillRelationResponse(BaseModel):
    relation_id: str
    source_skill_id: str
    target_skill_id: str
    confidence: float
    active: bool
    actor_id: str


class SkillInferenceResponse(BaseModel):
    status: Literal["inferred", "insufficient_evidence"]
    person_id: str
    target_skill_id: str
    inferred_level: int | None
    source_skill_id: str | None
    relation_id: str | None = Field(serialization_alias="relationId")
    confidence: float | None = Field(default=None, ge=0, le=1)
    reason: Literal["insufficient_evidence"] | None


class AlternativePayload(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    deltas: dict[str, object] = Field(min_length=1)


class AlternativeResponse(BaseModel):
    scenario_id: str
    base_scenario_id: str
    project_id: str
    snapshot_id: str
    name: str
    actor_id: str
    created_at: datetime
    deltas: dict[str, object]


def get_actor_id(request: Request) -> str:
    actor_id = getattr(request.state, "actor_id", None)
    if not isinstance(actor_id, str) or not actor_id.strip():
        raise HTTPException(
            status_code=401,
            detail={"code": "AUTHENTICATION_REQUIRED"},
        )
    return actor_id


def get_competency_editor(
    request: Request,
    person_id: str,
    actor_id: Annotated[str, Depends(get_actor_id)],
) -> str:
    authorized_person_ids = getattr(request.state, "authorized_person_ids", ())
    authenticated_person_id = getattr(request.state, "person_id", None)
    if (
        actor_id == person_id
        or authenticated_person_id == person_id
        or person_id in authorized_person_ids
    ):
        return actor_id
    raise HTTPException(status_code=403, detail={"code": "FORBIDDEN"})


def get_competency_reviewer(
    request: Request,
    person_id: str,
    actor_id: Annotated[str, Depends(get_actor_id)],
) -> str:
    reviewer_person_ids = getattr(request.state, "authorized_person_ids", ())
    if person_id in reviewer_person_ids:
        return actor_id
    raise HTTPException(status_code=403, detail={"code": "FORBIDDEN"})


def get_skill_relation_editor(
    request: Request,
    actor_id: Annotated[str, Depends(get_actor_id)],
) -> str:
    if getattr(request.state, "can_manage_skill_relations", False) is True:
        return actor_id
    raise HTTPException(status_code=403, detail={"code": "FORBIDDEN"})


def get_demand_repository() -> DemandRepository:
    return DemandRepository()


def get_competency_repository() -> CompetencyRepository:
    return CompetencyRepository()


def get_suggestion_repository() -> SuggestionReviewRepository:
    return SuggestionReviewRepository()


def get_competency_extractor() -> CompetencyExtractor:
    return UnavailableCompetencyExtractor()


def get_scenario_repository() -> ScenarioRepository:
    return ScenarioRepository()


def get_skill_relation_repository() -> SkillRelationRepository:
    return SkillRelationRepository()


def _raise_demand_error(error: DemandError) -> None:
    detail: dict[str, object] = {"code": error.code}
    if error.field:
        detail["fieldErrors"] = {error.field: error.code}
    raise HTTPException(
        status_code=error.status_code,
        detail=detail,
    ) from error


def _raise_competency_error(error: CompetencyError) -> None:
    detail: dict[str, object] = {"code": error.code}
    if error.field:
        detail["fieldErrors"] = {error.field: error.code}
    raise HTTPException(status_code=error.status_code, detail=detail) from error


def _raise_suggestion_error(error: SuggestionError) -> None:
    detail: dict[str, object] = {"code": error.code}
    if error.field:
        detail["fieldErrors"] = {error.field: error.code}
    raise HTTPException(status_code=error.status_code, detail=detail) from error


def _raise_scenario_error(error: ScenarioError) -> None:
    raise HTTPException(
        status_code=error.status_code,
        detail={"code": error.code},
    ) from error


def _raise_relation_error(error: RelationError) -> None:
    detail: dict[str, object] = {"code": error.code}
    if error.field:
        detail["fieldErrors"] = {error.field: error.code}
    raise HTTPException(status_code=error.status_code, detail=detail) from error


@app.exception_handler(RequestValidationError)
async def handle_request_validation_error(
    request: Request,
    error: RequestValidationError,
) -> JSONResponse:
    field_errors: dict[str, str] = {}
    error_codes = {
        "proficiency_level": "INVALID_LEVEL",
        "load_amount": "INVALID_LOAD",
        "period": "INVALID_PERIOD",
        "skill_id": "INVALID_SKILL",
        "load_unit": "INVALID_LOAD_UNIT",
        "evidence": "REQUIRED_EVIDENCE",
        "source_text": "EMPTY_SOURCE",
        "reviewed_level": "INVALID_LEVEL",
        "reviewed_evidence": "REQUIRED_EVIDENCE",
        "decision": "INVALID_REVIEW_DECISION",
        "confidence": "INVALID_CONFIDENCE",
    }
    for issue in error.errors():
        field = str(issue["loc"][-1])
        field_errors[field] = error_codes.get(field, "INVALID_FIELD")
    return JSONResponse(
        status_code=422,
        content={"detail": {"code": "VALIDATION_ERROR", "fieldErrors": field_errors}},
    )


@app.post("/skill-relations", status_code=201, response_model=SkillRelationResponse)
def create_skill_relation(
    payload: SkillRelationPayload,
    actor_id: Annotated[str, Depends(get_skill_relation_editor)],
    repository: Annotated[SkillRelationRepository, Depends(get_skill_relation_repository)],
) -> dict[str, object]:
    try:
        return repository.create(
            source_skill_id=payload.source_skill_id,
            target_skill_id=payload.target_skill_id,
            confidence=payload.confidence,
            actor_id=actor_id,
        )
    except RelationError as error:
        _raise_relation_error(error)


@app.post("/people/{person_id}/competencies", status_code=201, response_model=CompetencyResponse)
def create_person_competency(
    person_id: str,
    payload: CompetencyPayload,
    actor_id: Annotated[str, Depends(get_competency_editor)],
    repository: Annotated[CompetencyRepository, Depends(get_competency_repository)],
) -> dict[str, object]:
    try:
        return repository.create(
            person_id=person_id,
            skill_id=payload.skill_id,
            proficiency_level=payload.proficiency_level,
            evidence=payload.evidence,
            review_date=payload.review_date,
            actor_id=actor_id,
        )
    except CompetencyError as error:
        _raise_competency_error(error)


@app.get(
    "/people/{person_id}/skill-inference/{target_skill_id}",
    response_model=SkillInferenceResponse,
)
def infer_person_skill(
    person_id: str,
    target_skill_id: str,
    _actor_id: Annotated[str, Depends(get_competency_editor)],
    repository: Annotated[SkillRelationRepository, Depends(get_skill_relation_repository)],
) -> dict[str, object]:
    return repository.infer_for_person(person_id, target_skill_id)


@app.get("/people/{person_id}/competencies", response_model=list[CompetencyResponse])
def list_person_competencies(
    person_id: str,
    actor_id: Annotated[str, Depends(get_actor_id)],
    repository: Annotated[CompetencyRepository, Depends(get_competency_repository)],
) -> list[dict[str, object]]:
    try:
        return repository.list_for_person(person_id)
    except CompetencyError as error:
        _raise_competency_error(error)


@app.patch(
    "/people/{person_id}/competencies/{competency_id}",
    response_model=CompetencyResponse,
)
def correct_person_competency(
    person_id: str,
    competency_id: str,
    payload: CompetencyCorrectionPayload,
    actor_id: Annotated[str, Depends(get_competency_editor)],
    repository: Annotated[CompetencyRepository, Depends(get_competency_repository)],
) -> dict[str, object]:
    try:
        return repository.correct(
            person_id=person_id,
            competency_id=competency_id,
            proficiency_level=payload.proficiency_level,
            evidence=payload.evidence,
            review_date=payload.review_date,
            actor_id=actor_id,
        )
    except CompetencyError as error:
        _raise_competency_error(error)


@app.post(
    "/people/{person_id}/competency-suggestions/extract",
    status_code=201,
    response_model=SuggestionResponse,
)
def extract_person_competency_suggestion(
    person_id: str,
    payload: ExtractionPayload,
    actor_id: Annotated[str, Depends(get_competency_editor)],
    extractor: Annotated[CompetencyExtractor, Depends(get_competency_extractor)],
    repository: Annotated[SuggestionReviewRepository, Depends(get_suggestion_repository)],
) -> dict[str, object]:
    if not payload.source_text.strip():
        raise HTTPException(status_code=422, detail={"code": "EMPTY_SOURCE"})

    try:
        extracted = ExtractedCompetency.model_validate(extractor.extract(payload.source_text))
    except SuggestionError as error:
        _raise_suggestion_error(error)
    except ValidationError:
        _raise_suggestion_error(SuggestionError("INVALID_EXTRACTOR_OUTPUT", 502))

    if extracted.evidence_span not in payload.source_text:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "EVIDENCE_NOT_IN_SOURCE",
                "fieldErrors": {"evidence_span": "EVIDENCE_NOT_IN_SOURCE"},
            },
        )

    try:
        return repository.create_suggestion(
            person_id=person_id,
            skill_name=extracted.skill_name,
            proficiency_level=extracted.proficiency_level,
            confidence=extracted.confidence,
            evidence_span=extracted.evidence_span,
            source_sha256=sha256(payload.source_text.encode("utf-8")).hexdigest(),
            actor_id=actor_id,
        )
    except SuggestionError as error:
        _raise_suggestion_error(error)


@app.post(
    "/people/{person_id}/competency-suggestions/{suggestion_id}/review",
    response_model=SuggestionReviewResponse,
)
def review_person_competency_suggestion(
    person_id: str,
    suggestion_id: str,
    payload: SuggestionReviewPayload,
    reviewer_id: Annotated[str, Depends(get_competency_reviewer)],
    repository: Annotated[SuggestionReviewRepository, Depends(get_suggestion_repository)],
) -> dict[str, object]:
    try:
        return repository.review_suggestion(
            person_id=person_id,
            suggestion_id=suggestion_id,
            decision=payload.decision,
            reviewer_id=reviewer_id,
            reviewed_level=payload.reviewed_level,
            reviewed_evidence=payload.reviewed_evidence,
        )
    except SuggestionError as error:
        _raise_suggestion_error(error)


@app.post("/projects/{project_id}/demands", status_code=201, response_model=DemandResponse)
def create_project_demand(
    project_id: str,
    payload: DemandPayload,
    actor_id: Annotated[str, Depends(get_actor_id)],
    repository: Annotated[DemandRepository, Depends(get_demand_repository)],
) -> dict[str, object]:
    try:
        return repository.create(
            project_id=project_id,
            skill_id=payload.skill_id,
            proficiency_level=payload.proficiency_level,
            period_start=payload.period_start,
            load_amount=payload.load_amount,
            load_unit=payload.load_unit,
            actor_id=actor_id,
        )
    except DemandError as error:
        _raise_demand_error(error)


@app.get("/projects/{project_id}/demands", response_model=list[DemandResponse])
def list_project_demands(
    project_id: str,
    actor_id: Annotated[str, Depends(get_actor_id)],
    repository: Annotated[DemandRepository, Depends(get_demand_repository)],
) -> list[dict[str, object]]:
    try:
        return repository.list_for_project(project_id)
    except DemandError as error:
        _raise_demand_error(error)


@app.patch("/projects/{project_id}/demands/{demand_id}", response_model=DemandResponse)
def update_project_demand(
    project_id: str,
    demand_id: str,
    payload: DemandPayload,
    actor_id: Annotated[str, Depends(get_actor_id)],
    repository: Annotated[DemandRepository, Depends(get_demand_repository)],
) -> dict[str, object]:
    try:
        return repository.update(
            demand_id=demand_id,
            project_id=project_id,
            skill_id=payload.skill_id,
            proficiency_level=payload.proficiency_level,
            period_start=payload.period_start,
            load_amount=payload.load_amount,
            load_unit=payload.load_unit,
            actor_id=actor_id,
        )
    except DemandError as error:
        _raise_demand_error(error)


@app.post(
    "/scenarios/{base_scenario_id}/alternatives",
    status_code=201,
    response_model=AlternativeResponse,
)
def create_scenario_alternative(
    base_scenario_id: str,
    payload: AlternativePayload,
    actor_id: Annotated[str, Depends(get_actor_id)],
    repository: Annotated[ScenarioRepository, Depends(get_scenario_repository)],
) -> dict[str, object]:
    try:
        return repository.create_alternative(
            base_scenario_id=base_scenario_id,
            name=payload.name,
            deltas=payload.deltas,
            actor_id=actor_id,
        )
    except ScenarioError as error:
        _raise_scenario_error(error)


@app.get("/scenarios/{first_scenario_id}/compare/{second_scenario_id}")
def compare_scenarios(
    first_scenario_id: str,
    second_scenario_id: str,
    actor_id: Annotated[str, Depends(get_actor_id)],
    repository: Annotated[ScenarioRepository, Depends(get_scenario_repository)],
) -> dict[str, object]:
    try:
        return repository.compare(first_scenario_id, second_scenario_id)
    except ScenarioError as error:
        _raise_scenario_error(error)