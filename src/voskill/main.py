from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
from starlette.responses import JSONResponse

from .database import (
    CompetencyError,
    CompetencyRepository,
    DemandError,
    DemandRepository,
    ScenarioError,
    ScenarioRepository,
)

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


def get_demand_repository() -> DemandRepository:
    return DemandRepository()


def get_competency_repository() -> CompetencyRepository:
    return CompetencyRepository()


def get_scenario_repository() -> ScenarioRepository:
    return ScenarioRepository()


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


def _raise_scenario_error(error: ScenarioError) -> None:
    raise HTTPException(
        status_code=error.status_code,
        detail={"code": error.code},
    ) from error


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
    }
    for issue in error.errors():
        field = str(issue["loc"][-1])
        field_errors[field] = error_codes.get(field, "INVALID_FIELD")
    return JSONResponse(
        status_code=422,
        content={"detail": {"code": "VALIDATION_ERROR", "fieldErrors": field_errors}},
    )


@app.post("/people/{person_id}/competencies", status_code=201, response_model=CompetencyResponse)
def create_person_competency(
    person_id: str,
    payload: CompetencyPayload,
    actor_id: Annotated[str, Depends(get_actor_id)],
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