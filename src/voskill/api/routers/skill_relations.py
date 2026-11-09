from typing import Annotated

from fastapi import APIRouter, Depends

from ...skill_relations import RelationError, SkillRelationRepository
from ..dependencies import get_skill_relation_editor, get_skill_relation_repository
from ..errors import raise_relation_error
from ..schemas import SkillRelationPayload, SkillRelationResponse

router = APIRouter()


@router.post("/skill-relations", status_code=201, response_model=SkillRelationResponse)
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
        raise_relation_error(error)