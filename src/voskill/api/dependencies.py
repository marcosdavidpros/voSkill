import logging
from typing import Annotated, Protocol

from fastapi import Depends, HTTPException, Request

from ..competencies import CompetencyRepository
from ..demands import DemandRepository
from ..optimization_runs import OptimizationRunRepository
from ..scenarios import ScenarioRepository
from ..skill_relations import SkillRelationRepository
from ..suggestion_review import SuggestionReviewRepository
from ..suggestions import SuggestionError
from .schemas import ExtractedCompetency


class CompetencyExtractor(Protocol):
    def extract(self, source_text: str) -> ExtractedCompetency: ...


class UnavailableCompetencyExtractor:
    def extract(self, source_text: str) -> ExtractedCompetency:
        raise SuggestionError("PROVIDER_UNAVAILABLE", 503)


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
    logging.getLogger("voskill.audit").warning(
        "access_denied",
        extra={
            "actor_id": actor_id,
            "resource_id": person_id,
            "action": (
                "view_person_competencies"
                if request.method == "GET"
                else "modify_person_competencies"
            ),
            "outcome": "denied",
        },
    )
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


def get_optimization_run_repository() -> OptimizationRunRepository:
    return OptimizationRunRepository()


def get_optimization_run_access(
    request: Request,
    actor_id: Annotated[str, Depends(get_actor_id)],
) -> tuple[str, bool]:
    can_audit = getattr(request.state, "can_audit_optimization_runs", False) is True
    return actor_id, can_audit