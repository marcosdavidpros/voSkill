from collections.abc import Mapping
from typing import Any

import pymoo
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.operators.repair.rounding import RoundingRepair
from pymoo.optimize import minimize

from .feasibility import filter_capacity_feasible
from .optimization_problem import (
    AssignmentProblem,
    AssignmentSampling,
    build_assignments,
    development_actions,
    objective_metric_record,
    unique_decisions,
)


def optimize_snapshot(
    snapshot: Mapping[str, Any],
    *,
    seed: int,
    population_size: int = 64,
    generations: int = 40,
) -> dict[str, Any]:
    snapshot_id = str(snapshot["snapshot_id"])
    profiles = snapshot["profiles"]
    demands = snapshot["demands"]
    if not profiles or not demands:
        raise ValueError("snapshot must include at least one profile and one demand")
    if seed < 0:
        raise ValueError("seed must be non-negative")
    if population_size < 2 or generations < 1:
        raise ValueError("population_size must be at least 2 and generations must be positive")

    combination_count = len(profiles) ** len(demands)
    actual_population_size = min(population_size, combination_count)
    problem = AssignmentProblem(profiles, demands)
    algorithm = NSGA2(
        pop_size=actual_population_size,
        sampling=AssignmentSampling(len(profiles), len(demands)),
        crossover=SBX(prob=0.9, eta=15, vtype=float, repair=RoundingRepair()),
        mutation=PM(eta=20, vtype=float, repair=RoundingRepair()),
        eliminate_duplicates=True,
    )
    result = minimize(
        problem,
        algorithm,
        termination=("n_gen", generations),
        seed=seed,
        verbose=False,
    )

    vectors = result.X
    if vectors is None:
        vectors = result.pop.get("X") if result.pop is not None else None
    decisions = unique_decisions(vectors)
    candidates = []
    for index, decision in enumerate(decisions, start=1):
        assignments = build_assignments(profiles, demands, decision)
        candidates.append(
            {
                "alternative_id": f"A-{index:03d}",
                "assignments": assignments,
                "allocation": assignments,
                "development_actions": development_actions(profiles, demands, decision),
                "objective_metrics": objective_metric_record(profiles, assignments),
            }
        )

    availability = {
        (str(profile["person_id"]), str(period)): hours
        for profile in profiles
        for period, hours in profile.get("availability", {}).items()
    }
    feasibility = filter_capacity_feasible(candidates, availability)
    feasible_alternatives = [
        {
            "alternative_id": candidate["alternative_id"],
            "status": "feasible",
            "allocation": candidate["allocation"],
            "development_actions": candidate["development_actions"],
            "objective_metrics": candidate["objective_metrics"],
        }
        for candidate in feasibility["feasible_alternatives"]
    ]

    return {
        "status": "feasible" if feasible_alternatives else "infeasible",
        "feasible_alternatives": feasible_alternatives,
        "rejected_alternatives": feasibility["rejected_alternatives"],
        "conflicting_constraint_ids": feasibility["conflicting_constraint_ids"],
        "run_metadata": {
            "snapshot_id": snapshot_id,
            "seed": seed,
            "algorithm": "NSGA-II",
            "algorithm_version": f"pymoo-{pymoo.__version__}",
            "configuration": {
                "population_size": actual_population_size,
                "requested_population_size": population_size,
                "generations": generations,
                "objectives": ["skill_gap_hours", "peak_utilization"],
            },
        },
    }