from typing import Annotated

from fastapi import APIRouter, Depends

from ...optimization_runs import (
    OptimizationRunError,
    OptimizationRunRepository,
    run_optimization,
)
from ..dependencies import (
    get_actor_id,
    get_optimization_run_access,
    get_optimization_run_repository,
)
from ..errors import raise_optimization_run_error
from ..schemas import OptimizationRunPayload, OptimizationRunResponse

router = APIRouter()


@router.post(
    "/optimization-runs",
    status_code=201,
    response_model=OptimizationRunResponse,
)
def create_optimization_run(
    payload: OptimizationRunPayload,
    actor_id: Annotated[str, Depends(get_actor_id)],
    repository: Annotated[OptimizationRunRepository, Depends(get_optimization_run_repository)],
) -> dict[str, object]:
    try:
        return run_optimization(
            snapshot=payload.snapshot,
            seed=payload.seed,
            actor_id=actor_id,
            repository=repository,
            population_size=payload.population_size,
            generations=payload.generations,
        )
    except OptimizationRunError as error:
        raise_optimization_run_error(error)
    except ValueError:
        raise_optimization_run_error(OptimizationRunError("INVALID_OPTIMIZATION_INPUT", 422))


@router.get("/optimization-runs/{run_id}", response_model=OptimizationRunResponse)
def get_optimization_run(
    run_id: str,
    access: Annotated[tuple[str, bool], Depends(get_optimization_run_access)],
    repository: Annotated[OptimizationRunRepository, Depends(get_optimization_run_repository)],
) -> dict[str, object]:
    try:
        record = repository.get_run(run_id)
        actor_id, can_audit = access
        if record["actor_id"] != actor_id and not can_audit:
            raise OptimizationRunError("RUN_NOT_FOUND", 404)
        return record
    except OptimizationRunError as error:
        raise_optimization_run_error(error)