from collections.abc import Mapping, Sequence
from decimal import Decimal
from itertools import product
from typing import Any

import numpy as np
from pymoo.core.problem import ElementwiseProblem
from pymoo.core.sampling import Sampling
from pymoo.operators.sampling.rnd import IntegerRandomSampling


class AssignmentSampling(Sampling):
    def __init__(self, profile_count: int, demand_count: int) -> None:
        super().__init__()
        self._profile_count = profile_count
        self._demand_count = demand_count

    def _do(self, problem: Any, n_samples: int, **kwargs: Any) -> np.ndarray:
        combination_count = self._profile_count**self._demand_count
        if combination_count <= 4096:
            return np.asarray(
                list(product(range(self._profile_count), repeat=self._demand_count)),
                dtype=int,
            )
        return IntegerRandomSampling()._do(problem, n_samples, **kwargs)


class AssignmentProblem(ElementwiseProblem):
    def __init__(
        self,
        profiles: Sequence[Mapping[str, Any]],
        demands: Sequence[Mapping[str, Any]],
    ) -> None:
        self.profiles = profiles
        self.demands = demands
        periods = sorted({str(demand["period"]) for demand in demands})
        self.capacity_slots = [
            (str(profile["person_id"]), period)
            for profile in profiles
            for period in periods
        ]
        super().__init__(
            n_var=len(demands),
            n_obj=2,
            n_ieq_constr=len(self.capacity_slots),
            xl=0,
            xu=len(profiles) - 1,
            vtype=int,
        )

    def _evaluate(self, decision: np.ndarray, out: dict[str, Any], **kwargs: Any) -> None:
        assignments = build_assignments(self.profiles, self.demands, decision)
        out["F"] = objective_values(self.profiles, assignments)

        load_by_slot: dict[tuple[str, str], Decimal] = {}
        for assignment in assignments:
            key = (assignment["person_id"], assignment["period"])
            load_by_slot[key] = load_by_slot.get(key, Decimal(0)) + Decimal(
                str(assignment["load_amount"])
            )

        violations = []
        profiles_by_id = {str(profile["person_id"]): profile for profile in self.profiles}
        for person_id, period in self.capacity_slots:
            assigned = load_by_slot.get((person_id, period), Decimal(0))
            availability = profiles_by_id[person_id].get("availability", {}).get(period)
            if availability is None:
                violations.append(float(assigned > 0))
            else:
                violations.append(float(assigned - Decimal(str(availability))))
        out["G"] = violations


def unique_decisions(vectors: object) -> list[tuple[int, ...]]:
    if vectors is None:
        return []
    matrix = np.atleast_2d(vectors)
    return sorted({tuple(round(float(value)) for value in row) for row in matrix})


def build_assignments(
    profiles: Sequence[Mapping[str, Any]],
    demands: Sequence[Mapping[str, Any]],
    decision: Sequence[int],
) -> list[dict[str, Any]]:
    return [
        {
            "demand_id": str(demand["demand_id"]),
            "person_id": str(profiles[int(profile_index)]["person_id"]),
            "skill_id": str(demand["skill_id"]),
            "period": str(demand["period"]),
            "required_level": int(demand["proficiency_level"]),
            "load_amount": demand["load_amount"],
        }
        for demand, profile_index in zip(demands, decision, strict=True)
    ]


def objective_values(
    profiles: Sequence[Mapping[str, Any]],
    assignments: Sequence[Mapping[str, Any]],
) -> list[float]:
    metrics = objective_metric_record(profiles, assignments)
    return [metrics["skill_gap_hours"], metrics["peak_utilization"]]


def objective_metric_record(
    profiles: Sequence[Mapping[str, Any]],
    assignments: Sequence[Mapping[str, Any]],
) -> dict[str, float]:
    profile_by_id = {str(profile["person_id"]): profile for profile in profiles}
    load_by_slot: dict[tuple[str, str], Decimal] = {}
    skill_gap_hours = Decimal(0)
    for assignment in assignments:
        profile = profile_by_id[assignment["person_id"]]
        competencies = profile.get("competencies", {})
        proficiency = int(competencies.get(assignment["skill_id"], 0))
        required_level = int(assignment["required_level"])
        load_amount = Decimal(str(assignment["load_amount"]))
        skill_gap_hours += Decimal(max(0, required_level - proficiency)) * load_amount
        slot = (assignment["person_id"], assignment["period"])
        load_by_slot[slot] = load_by_slot.get(slot, Decimal(0)) + load_amount

    peak_utilization = Decimal(0)
    for (person_id, period), load_amount in load_by_slot.items():
        available = profile_by_id[person_id].get("availability", {}).get(period)
        if available is not None and Decimal(str(available)) > 0:
            peak_utilization = max(peak_utilization, load_amount / Decimal(str(available)))
        elif load_amount > 0:
            peak_utilization = max(peak_utilization, Decimal(1))

    return {
        "skill_gap_hours": round(float(skill_gap_hours), 6),
        "peak_utilization": round(float(peak_utilization), 6),
    }


def development_actions(
    profiles: Sequence[Mapping[str, Any]],
    demands: Sequence[Mapping[str, Any]],
    decision: Sequence[int],
) -> list[dict[str, Any]]:
    actions = []
    for demand, profile_index in zip(demands, decision, strict=True):
        profile = profiles[int(profile_index)]
        competencies = profile.get("competencies", {})
        current_level = int(competencies.get(str(demand["skill_id"]), 0))
        required_level = int(demand["proficiency_level"])
        if current_level < required_level:
            actions.append(
                {
                    "person_id": str(profile["person_id"]),
                    "skill_id": str(demand["skill_id"]),
                    "from_level": current_level,
                    "target_level": required_level,
                }
            )
    return actions