from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse

from ..competencies import CompetencyError
from ..demands import DemandError
from ..optimization_runs import OptimizationRunError
from ..risk_thresholds import RiskThresholdError
from ..scenario_comparison import ScenarioError
from ..skill_relations import RelationError
from ..suggestions import SuggestionError


def raise_demand_error(error: DemandError) -> None:
    detail: dict[str, object] = {"code": error.code}
    if error.field:
        detail["fieldErrors"] = {error.field: error.code}
    raise HTTPException(status_code=error.status_code, detail=detail) from error


def raise_competency_error(error: CompetencyError) -> None:
    detail: dict[str, object] = {"code": error.code}
    if error.field:
        detail["fieldErrors"] = {error.field: error.code}
    raise HTTPException(status_code=error.status_code, detail=detail) from error


def raise_suggestion_error(error: SuggestionError) -> None:
    detail: dict[str, object] = {"code": error.code}
    if error.field:
        detail["fieldErrors"] = {error.field: error.code}
    raise HTTPException(status_code=error.status_code, detail=detail) from error


def raise_scenario_error(error: ScenarioError) -> None:
    raise HTTPException(
        status_code=error.status_code,
        detail={"code": error.code},
    ) from error


def raise_relation_error(error: RelationError) -> None:
    detail: dict[str, object] = {"code": error.code}
    if error.field:
        detail["fieldErrors"] = {error.field: error.code}
    raise HTTPException(status_code=error.status_code, detail=detail) from error


def raise_optimization_run_error(error: OptimizationRunError) -> None:
    raise HTTPException(
        status_code=error.status_code,
        detail={"code": error.code},
    ) from error


def raise_risk_threshold_error(error: RiskThresholdError) -> None:
    raise HTTPException(
        status_code=error.status_code,
        detail={"code": error.code},
    ) from error


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