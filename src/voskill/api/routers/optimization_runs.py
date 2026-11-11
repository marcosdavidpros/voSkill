from collections.abc import Mapping, Sequence
from typing import Annotated

from fastapi import APIRouter, Depends

from ...alternative_comparison import AlternativeComparisonError, compare_alternatives
from ...alternative_explanation import (
    METRIC_DEFINITIONS,
    AlternativeExplainer,
    explain_alternative,
)
from ...optimization_runs import (
    OptimizationRunError,
    OptimizationRunRepository,
    run_optimization,
)
from ..dependencies import (
    get_actor_id,
    get_alternative_explainer,
    get_optimization_run_access,
    get_optimization_run_repository,
)
from ..errors import raise_optimization_run_error
from ..schemas import (
    AlternativeComparisonPayload,
    AlternativeComparisonResponse,
    AlternativeExplanationResponse,
    OptimizationRunPayload,
    OptimizationRunResponse,
)

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


@router.post(
    "/optimization-runs/{run_id}/alternatives/compare",
    response_model=AlternativeComparisonResponse,
)
def compare_run_alternatives(
    run_id: str,
    payload: AlternativeComparisonPayload,
    access: Annotated[tuple[str, bool], Depends(get_optimization_run_access)],
    repository: Annotated[OptimizationRunRepository, Depends(get_optimization_run_repository)],
) -> dict[str, object]:
    try:
        record = repository.get_run(run_id)
        actor_id, can_audit = access
        if record["actor_id"] != actor_id and not can_audit:
            raise OptimizationRunError("RUN_NOT_FOUND", 404)

        configuration = record.get("configuration")
        result = record.get("result")
        if not isinstance(configuration, Mapping) or not isinstance(result, Mapping):
            raise OptimizationRunError("RUN_NOT_FOUND", 404)
        objective_names = configuration.get("objectives")
        alternatives = result.get("feasible_alternatives")
        if (
            not isinstance(objective_names, Sequence)
            or isinstance(objective_names, str)
            or not all(isinstance(name, str) and name in METRIC_DEFINITIONS for name in objective_names)
            or not isinstance(alternatives, Sequence)
            or isinstance(alternatives, str)
        ):
            raise OptimizationRunError("COMPARISON_UNAVAILABLE", 409)

        definitions = {name: METRIC_DEFINITIONS[name] for name in objective_names}
        comparison = compare_alternatives(
            alternatives=alternatives,
            alternative_ids=payload.alternative_ids,
            objective_names=objective_names,
            objective_directions={name: definitions[name]["direction"] for name in objective_names},
            objective_metadata={
                name: {field: definitions[name][field] for field in ("unit", "source")}
                for name in objective_names
            },
        )
        run_metadata = result.get("run_metadata")
        run_metadata = run_metadata if isinstance(run_metadata, Mapping) else {}
        constraint_evaluation = result.get("constraint_evaluation")
        constraint_evaluation = constraint_evaluation if isinstance(constraint_evaluation, Mapping) else {}
        constraint_ids = constraint_evaluation.get(
            "conflicting_constraint_ids",
            result.get("conflicting_constraint_ids", []),
        )
        rejected_alternatives = constraint_evaluation.get(
            "rejected_alternatives",
            result.get("rejected_alternatives", []),
        )
        checked_hard_constraints = constraint_evaluation.get("checked_hard_constraints", [])
        soft_preference_metrics = constraint_evaluation.get("soft_preference_metrics", [])
        return {
            "run_id": run_id,
            "run_premises": {
                "snapshot_id": run_metadata.get("snapshot_id"),
                "algorithm": run_metadata.get("algorithm"),
                "algorithm_version": record.get("algorithm_version"),
                "seed": record.get("seed"),
                "configuration": record.get("configuration", {}),
            },
            "constraint_trace": {
                "checked_hard_constraints": checked_hard_constraints if isinstance(checked_hard_constraints, list) else [],
                "conflicting_constraint_ids": constraint_ids if isinstance(constraint_ids, list) else [],
                "rejected_alternatives": rejected_alternatives if isinstance(rejected_alternatives, list) else [],
                "soft_preference_metrics": soft_preference_metrics if isinstance(soft_preference_metrics, list) else [],
            },
            "alternatives": [
                {
                    "alternative_id": alternative["alternative_id"],
                    "objective_metrics": alternative["objective_metrics"],
                }
                for alternative in comparison["alternatives"]
            ],
            "trade_offs": comparison["trade_offs"],
            "metric_definitions": definitions,
        }
    except AlternativeComparisonError as error:
        raise_optimization_run_error(OptimizationRunError(error.code, error.status_code))
    except OptimizationRunError as error:
        raise_optimization_run_error(error)


@router.get(
    "/optimization-runs/{run_id}/alternatives/{alternative_id}/explanation",
    response_model=AlternativeExplanationResponse,
)
def get_alternative_explanation(
    run_id: str,
    alternative_id: str,
    access: Annotated[tuple[str, bool], Depends(get_optimization_run_access)],
    repository: Annotated[OptimizationRunRepository, Depends(get_optimization_run_repository)],
    explainer: Annotated[AlternativeExplainer, Depends(get_alternative_explainer)],
) -> dict[str, object]:
    try:
        record = repository.get_run(run_id)
        actor_id, can_audit = access
        if record["actor_id"] != actor_id and not can_audit:
            raise OptimizationRunError("RUN_NOT_FOUND", 404)
        return explain_alternative(record, alternative_id, explainer)
    except OptimizationRunError as error:
        raise_optimization_run_error(error)


@router.post("/optimization-runs/{run_id}/alternatives/{alternative_id}/apply")
def apply_alternative(
    run_id: str,
    alternative_id: str,
    access: Annotated[tuple[str, bool], Depends(get_optimization_run_access)],
    repository: Annotated[OptimizationRunRepository, Depends(get_optimization_run_repository)],
) -> None:
    try:
        record = repository.get_run(run_id)
        actor_id, can_audit = access
        if record["actor_id"] != actor_id and not can_audit:
            raise OptimizationRunError("RUN_NOT_FOUND", 404)

        result = record.get("result")
        alternatives = result.get("feasible_alternatives", []) if isinstance(result, dict) else []
        if not any(
            isinstance(alternative, dict)
            and alternative.get("alternative_id") == alternative_id
            for alternative in alternatives
        ):
            raise OptimizationRunError("ALTERNATIVE_NOT_FOUND", 404)

        raise OptimizationRunError("HUMAN_APPROVAL_REQUIRED", 409)
    except OptimizationRunError as error:
        raise_optimization_run_error(error)