import logging
from typing import Annotated, Protocol

from fastapi import Depends, HTTPException, Request

from ..alternative_explanation import AlternativeExplainer, UnavailableAlternativeExplainer
from ..authentication import (
    AuthenticationService,
    AuthenticationUnavailable,
    PortalPrincipal,
    create_authentication_service,
)
from ..base_scenarios import BaseScenarioRepository
from ..catalog import CatalogRepository
from ..competencies import CompetencyRepository
from ..demands import DemandRepository
from ..optimization_runs import OptimizationRunRepository
from ..projects import ProjectRepository
from ..risk_thresholds import RiskThresholdRepository
from ..scenarios import ScenarioRepository
from ..session import InvalidSession, SessionCodec
from ..skill_relations import SkillRelationRepository
from ..suggestion_review import SuggestionReviewRepository
from ..suggestions import SuggestionError
from .schemas import ExtractedCompetency


class CompetencyExtractor(Protocol):
    def extract(self, source_text: str) -> ExtractedCompetency: ...


class UnavailableCompetencyExtractor:
    def extract(self, source_text: str) -> ExtractedCompetency:
        raise SuggestionError("PROVIDER_UNAVAILABLE", 503)


def get_session_codec() -> SessionCodec | None:
    try:
        return SessionCodec.from_environment()
    except AuthenticationUnavailable:
        return None


def get_authentication_service() -> AuthenticationService:
    try:
        return create_authentication_service()
    except AuthenticationUnavailable as error:
        raise HTTPException(
            status_code=503,
            detail={"code": "AUTHENTICATION_UNAVAILABLE"},
        ) from error


def get_session_principal(
    request: Request,
    codec: Annotated[SessionCodec | None, Depends(get_session_codec)],
) -> PortalPrincipal:
    token = request.cookies.get("voskill_session")
    if not token:
        raise HTTPException(
            status_code=401,
            detail={"code": "AUTHENTICATION_REQUIRED"},
        )
    if codec is None:
        raise HTTPException(
            status_code=503,
            detail={"code": "AUTHENTICATION_UNAVAILABLE"},
        )
    try:
        principal = codec.decode(token)
    except InvalidSession as error:
        raise HTTPException(
            status_code=401,
            detail={"code": "AUTHENTICATION_REQUIRED"},
        ) from error
    request.state.actor_id = principal.actor_id
    request.state.can_view = principal.can_view
    request.state.can_edit = principal.can_edit
    request.state.can_view_scenario_data = principal.can_view
    request.state.can_audit_optimization_runs = principal.can_view
    request.state.can_manage_risk_thresholds = principal.can_edit
    request.state.can_manage_skill_relations = principal.can_edit
    return principal


def get_actor_id(
    request: Request,
    principal: Annotated[PortalPrincipal, Depends(get_session_principal)],
) -> str:
    route = request.scope.get("route")
    route_path = getattr(route, "path", "")
    read_only_post = (
        request.method == "POST"
        and route_path == "/optimization-runs/{run_id}/alternatives/compare"
    )
    if request.method in {"GET", "HEAD", "OPTIONS"} or read_only_post:
        if not principal.can_view:
            raise HTTPException(status_code=403, detail={"code": "FORBIDDEN"})
    elif not principal.can_edit:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN"})
    return principal.actor_id


def get_competency_editor(
    request: Request,
    person_id: str,
    actor_id: Annotated[str, Depends(get_actor_id)],
) -> str:
    action = (
        "view_person_competencies"
        if request.method == "GET"
        else "modify_person_competencies"
    )
    return _require_person_access(request, person_id, actor_id, action)


def get_competency_exporter(
    request: Request,
    person_id: str,
    actor_id: Annotated[str, Depends(get_actor_id)],
) -> str:
    return _require_person_access(
        request,
        person_id,
        actor_id,
        "export_person_competencies",
    )


def _require_person_access(
    request: Request,
    person_id: str,
    actor_id: str,
    action: str,
) -> str:
    authorized_person_ids = getattr(request.state, "authorized_person_ids", ())
    authenticated_person_id = getattr(request.state, "person_id", None)
    allowed = getattr(request.state, "can_view_scenario_data", False) is True or (
        actor_id == person_id
        or authenticated_person_id == person_id
        or person_id in authorized_person_ids
    )
    if allowed:
        return actor_id
    logging.getLogger("voskill.audit").warning(
        "access_denied",
        extra={
            "actor_id": actor_id,
            "resource_id": person_id,
            "action": action,
            "outcome": "denied",
        },
    )
    raise HTTPException(status_code=403, detail={"code": "FORBIDDEN"})


def get_competency_reviewer(
    request: Request,
    person_id: str,
    actor_id: Annotated[str, Depends(get_actor_id)],
) -> str:
    if getattr(request.state, "can_edit", False) is True:
        return actor_id
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


def get_project_repository() -> ProjectRepository:
    return ProjectRepository()


def get_competency_repository() -> CompetencyRepository:
    return CompetencyRepository()


def get_catalog_repository() -> CatalogRepository:
    return CatalogRepository()


def get_suggestion_repository() -> SuggestionReviewRepository:
    return SuggestionReviewRepository()


def get_competency_extractor() -> CompetencyExtractor:
    return UnavailableCompetencyExtractor()


def get_scenario_repository() -> ScenarioRepository:
    return ScenarioRepository()


def get_base_scenario_repository() -> BaseScenarioRepository:
    return BaseScenarioRepository()


def get_skill_relation_repository() -> SkillRelationRepository:
    return SkillRelationRepository()


def get_optimization_run_repository() -> OptimizationRunRepository:
    return OptimizationRunRepository()


def get_risk_threshold_repository() -> RiskThresholdRepository:
    return RiskThresholdRepository()


def get_alternative_explainer() -> AlternativeExplainer:
    return UnavailableAlternativeExplainer()


def get_optimization_run_access(
    request: Request,
    actor_id: Annotated[str, Depends(get_actor_id)],
) -> tuple[str, bool]:
    can_audit = getattr(request.state, "can_audit_optimization_runs", False) is True
    return actor_id, can_audit


def require_scenario_people_access(
    request: Request,
    actor_id: str,
    scenario_id: str,
    project_id: str | set[str],
    person_ids: set[str],
    action: str = "view_competency_map",
) -> None:
    authorized_people = set(getattr(request.state, "authorized_person_ids", ()))
    authenticated_person_id = getattr(request.state, "person_id", None)
    authorized_projects = set(getattr(request.state, "authorized_project_ids", ()))
    can_view_all = getattr(request.state, "can_view_scenario_data", False) is True
    project_ids = {project_id} if isinstance(project_id, str) else project_id
    all_projects_authorized = bool(project_ids) and project_ids.issubset(authorized_projects)
    all_people_authorized = bool(person_ids) and all(
        person_id in authorized_people or person_id == authenticated_person_id
        for person_id in person_ids
    )
    if can_view_all or all_projects_authorized or all_people_authorized:
        return

    logging.getLogger("voskill.audit").warning(
        "access_denied",
        extra={
            "actor_id": actor_id,
            "resource_id": scenario_id,
            "action": action,
            "outcome": "denied",
        },
    )
    raise HTTPException(status_code=403, detail={"code": "FORBIDDEN"})


def require_project_risk_manager(request: Request, actor_id: str, project_id: str) -> None:
    authorized_projects = set(getattr(request.state, "authorized_project_ids", ()))
    can_manage_thresholds = getattr(request.state, "can_manage_risk_thresholds", False) is True
    if project_id in authorized_projects or can_manage_thresholds:
        return

    logging.getLogger("voskill.audit").warning(
        "access_denied",
        extra={
            "actor_id": actor_id,
            "resource_id": project_id,
            "action": "manage_critical_skill_thresholds",
            "outcome": "denied",
        },
    )
    raise HTTPException(status_code=403, detail={"code": "FORBIDDEN"})