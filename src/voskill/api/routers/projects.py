from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from ...projects import ProjectError, ProjectRepository
from ..dependencies import get_actor_id, get_project_repository
from ..schemas import ProjectCatalogResponse, ProjectCreatePayload

router = APIRouter()


@router.get("/projects", response_model=list[ProjectCatalogResponse])
def list_projects(
    _actor_id: Annotated[str, Depends(get_actor_id)],
    repository: Annotated[ProjectRepository, Depends(get_project_repository)],
) -> list[dict[str, object]]:
    return repository.list_projects()


@router.post("/projects", status_code=201, response_model=ProjectCatalogResponse)
def create_project(
    payload: ProjectCreatePayload,
    actor_id: Annotated[str, Depends(get_actor_id)],
    repository: Annotated[ProjectRepository, Depends(get_project_repository)],
) -> dict[str, object]:
    try:
        return repository.create_project(
            project_name=payload.project_name,
            horizon_start=payload.horizon_start,
            horizon_end=payload.horizon_end,
            load_unit=payload.load_unit,
        )
    except ProjectError as error:
        detail: dict[str, object] = {"code": error.code}
        if error.field:
            detail["fieldErrors"] = {error.field: error.code}
        raise HTTPException(status_code=error.status_code, detail=detail) from error


@router.patch("/projects/{project_id}", response_model=ProjectCatalogResponse)
def update_project(
    project_id: str,
    payload: ProjectCreatePayload,
    _actor_id: Annotated[str, Depends(get_actor_id)],
    repository: Annotated[ProjectRepository, Depends(get_project_repository)],
) -> dict[str, object]:
    try:
        return repository.update_project(
            project_id=project_id,
            project_name=payload.project_name,
            horizon_start=payload.horizon_start,
            horizon_end=payload.horizon_end,
            load_unit=payload.load_unit,
        )
    except ProjectError as error:
        detail = {"code": error.code}
        if error.field:
            detail["fieldErrors"] = {error.field: error.code}
        raise HTTPException(status_code=error.status_code, detail=detail) from error