from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from ...catalog import CatalogError, CatalogRepository
from ..dependencies import get_actor_id, get_catalog_repository
from ..schemas import (
    PersonCatalogResponse,
    PersonCreatePayload,
    SkillCatalogResponse,
    SkillCreatePayload,
)

router = APIRouter()


@router.get("/people", response_model=list[PersonCatalogResponse])
def list_people(
    _actor_id: Annotated[str, Depends(get_actor_id)],
    repository: Annotated[CatalogRepository, Depends(get_catalog_repository)],
) -> list[dict[str, object]]:
    return repository.list_people()


@router.post("/people", status_code=201, response_model=PersonCatalogResponse)
def create_person(
    payload: PersonCreatePayload,
    _actor_id: Annotated[str, Depends(get_actor_id)],
    repository: Annotated[CatalogRepository, Depends(get_catalog_repository)],
) -> dict[str, object]:
    try:
        return repository.create_person(payload.display_name)
    except CatalogError as error:
        raise HTTPException(status_code=error.status_code, detail={"code": error.code}) from error


@router.get("/skills", response_model=list[SkillCatalogResponse])
def list_skills(
    _actor_id: Annotated[str, Depends(get_actor_id)],
    repository: Annotated[CatalogRepository, Depends(get_catalog_repository)],
) -> list[dict[str, object]]:
    return repository.list_skills()


@router.post("/skills", status_code=201, response_model=SkillCatalogResponse)
def create_skill(
    payload: SkillCreatePayload,
    _actor_id: Annotated[str, Depends(get_actor_id)],
    repository: Annotated[CatalogRepository, Depends(get_catalog_repository)],
) -> dict[str, object]:
    try:
        return repository.create_skill(payload.skill_name, payload.description)
    except CatalogError as error:
        raise HTTPException(status_code=error.status_code, detail={"code": error.code}) from error


@router.patch("/skills/{skill_id}", response_model=SkillCatalogResponse)
def update_skill(
    skill_id: str,
    payload: SkillCreatePayload,
    _actor_id: Annotated[str, Depends(get_actor_id)],
    repository: Annotated[CatalogRepository, Depends(get_catalog_repository)],
) -> dict[str, object]:
    try:
        return repository.update_skill(skill_id, payload.skill_name, payload.description)
    except CatalogError as error:
        raise HTTPException(status_code=error.status_code, detail={"code": error.code}) from error