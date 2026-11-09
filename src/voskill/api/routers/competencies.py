from typing import Annotated

from fastapi import APIRouter, Depends

from ...competencies import CompetencyError, CompetencyRepository
from ...skill_relations import SkillRelationRepository
from ..dependencies import (
    get_competency_editor,
    get_competency_repository,
    get_skill_relation_repository,
)
from ..errors import raise_competency_error
from ..schemas import (
    CompetencyCorrectionPayload,
    CompetencyPayload,
    CompetencyResponse,
    SkillInferenceResponse,
)

router = APIRouter()


@router.post("/people/{person_id}/competencies", status_code=201, response_model=CompetencyResponse)
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
        raise_competency_error(error)


@router.get("/people/{person_id}/competencies", response_model=list[CompetencyResponse])
def list_person_competencies(
    person_id: str,
    actor_id: Annotated[str, Depends(get_competency_editor)],
    repository: Annotated[CompetencyRepository, Depends(get_competency_repository)],
) -> list[dict[str, object]]:
    try:
        return repository.list_for_person(person_id)
    except CompetencyError as error:
        raise_competency_error(error)


@router.patch(
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
        raise_competency_error(error)


@router.get(
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