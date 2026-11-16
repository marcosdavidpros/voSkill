from typing import Annotated

from fastapi import APIRouter, Depends

from ...base_scenarios import BaseScenarioRepository
from ...scenario_comparison import ScenarioError
from ..dependencies import get_actor_id, get_base_scenario_repository
from ..errors import raise_scenario_error
from ..schemas import (
    BaseScenarioCreatePayload,
    BaseScenarioResponse,
    OptimizerSnapshotResponse,
    ScenarioListItemResponse,
)

router = APIRouter()


@router.post(
    "/projects/{project_id}/scenarios",
    status_code=201,
    response_model=BaseScenarioResponse,
)
def create_project_base_scenario(
    project_id: str,
    payload: BaseScenarioCreatePayload,
    actor_id: Annotated[str, Depends(get_actor_id)],
    repository: Annotated[BaseScenarioRepository, Depends(get_base_scenario_repository)],
) -> dict[str, object]:
    try:
        return repository.create_base_scenario(
            project_id=project_id,
            scenario_name=payload.scenario_name,
            participants=[participant.model_dump() for participant in payload.participants],
            actor_id=actor_id,
        )
    except ScenarioError as error:
        raise_scenario_error(error)


@router.put("/scenarios/{scenario_id}", response_model=BaseScenarioResponse)
def update_base_scenario(
    scenario_id: str,
    payload: BaseScenarioCreatePayload,
    actor_id: Annotated[str, Depends(get_actor_id)],
    repository: Annotated[BaseScenarioRepository, Depends(get_base_scenario_repository)],
) -> dict[str, object]:
    try:
        return repository.update_base_scenario(
            scenario_id=scenario_id,
            scenario_name=payload.scenario_name,
            participants=[participant.model_dump() for participant in payload.participants],
            actor_id=actor_id,
        )
    except ScenarioError as error:
        raise_scenario_error(error)


@router.get("/scenarios", response_model=list[ScenarioListItemResponse])
def list_scenarios(
    _actor_id: Annotated[str, Depends(get_actor_id)],
    repository: Annotated[BaseScenarioRepository, Depends(get_base_scenario_repository)],
) -> list[dict[str, object]]:
    try:
        return repository.list_scenarios()
    except ScenarioError as error:
        raise_scenario_error(error)


@router.get(
    "/scenarios/{scenario_id}/optimization-snapshot",
    response_model=OptimizerSnapshotResponse,
)
def get_optimization_snapshot(
    scenario_id: str,
    _actor_id: Annotated[str, Depends(get_actor_id)],
    repository: Annotated[BaseScenarioRepository, Depends(get_base_scenario_repository)],
) -> dict[str, object]:
    try:
        return repository.get_optimization_snapshot(scenario_id)
    except ScenarioError as error:
        raise_scenario_error(error)