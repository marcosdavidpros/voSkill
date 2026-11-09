from typing import Annotated

from fastapi import APIRouter, Depends

from ...scenario_comparison import ScenarioError
from ...scenarios import ScenarioRepository
from ..dependencies import get_actor_id, get_scenario_repository
from ..errors import raise_scenario_error
from ..schemas import AlternativePayload, AlternativeResponse

router = APIRouter()


@router.post(
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
        raise_scenario_error(error)


@router.get("/scenarios/{first_scenario_id}/compare/{second_scenario_id}")
def compare_scenarios(
    first_scenario_id: str,
    second_scenario_id: str,
    actor_id: Annotated[str, Depends(get_actor_id)],
    repository: Annotated[ScenarioRepository, Depends(get_scenario_repository)],
) -> dict[str, object]:
    try:
        return repository.compare(first_scenario_id, second_scenario_id)
    except ScenarioError as error:
        raise_scenario_error(error)