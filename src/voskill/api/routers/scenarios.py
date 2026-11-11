from typing import Annotated

from fastapi import APIRouter, Depends, Request

from ...scenario_comparison import ScenarioError
from ...scenarios import ScenarioRepository
from ..dependencies import (
    get_actor_id,
    get_scenario_repository,
    require_scenario_people_access,
)
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
    request: Request,
    repository: Annotated[ScenarioRepository, Depends(get_scenario_repository)],
) -> dict[str, object]:
    try:
        first = repository.get_competency_snapshot(first_scenario_id)
        second = repository.get_competency_snapshot(second_scenario_id)
        snapshots = (first["snapshot"], second["snapshot"])
        person_ids = {
            str(person_id)
            for snapshot in snapshots
            for assumptions in snapshot["periods"].values()
            if isinstance(assumptions, dict)
            for person_id in assumptions.get("availability", {})
        }
        require_scenario_people_access(
            request=request,
            actor_id=actor_id,
            scenario_id=f"{first_scenario_id},{second_scenario_id}",
            project_id={str(first["project_id"]), str(second["project_id"])},
            person_ids=person_ids,
            action="compare_scenarios",
        )
        return repository.compare(first_scenario_id, second_scenario_id)
    except ScenarioError as error:
        raise_scenario_error(error)