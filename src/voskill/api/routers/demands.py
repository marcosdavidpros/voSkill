from typing import Annotated

from fastapi import APIRouter, Depends

from ...demands import DemandError, DemandRepository
from ..dependencies import get_actor_id, get_demand_repository
from ..errors import raise_demand_error
from ..schemas import DemandPayload, DemandResponse

router = APIRouter()


@router.post("/projects/{project_id}/demands", status_code=201, response_model=DemandResponse)
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
        raise_demand_error(error)


@router.get("/projects/{project_id}/demands", response_model=list[DemandResponse])
def list_project_demands(
    project_id: str,
    actor_id: Annotated[str, Depends(get_actor_id)],
    repository: Annotated[DemandRepository, Depends(get_demand_repository)],
) -> list[dict[str, object]]:
    try:
        return repository.list_for_project(project_id)
    except DemandError as error:
        raise_demand_error(error)


@router.patch("/projects/{project_id}/demands/{demand_id}", response_model=DemandResponse)
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
        raise_demand_error(error)