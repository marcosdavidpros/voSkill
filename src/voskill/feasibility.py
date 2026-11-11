from collections.abc import Mapping, Sequence
from decimal import Decimal

HARD_CONSTRAINT_CODES = ("availability_missing", "capacity_exceeded")


def filter_capacity_feasible(
    candidates: Sequence[Mapping[str, object]],
    availability: Mapping[tuple[str, str], Decimal | int | float],
) -> dict[str, object]:
    feasible_alternatives: list[Mapping[str, object]] = []
    rejected_alternatives: list[dict[str, object]] = []
    conflicting_constraint_ids: set[str] = set()
    soft_preference_metrics = [
        {
            "alternative_id": str(candidate["alternative_id"]),
            "metrics": dict(candidate["preference_metrics"]),
        }
        for candidate in candidates
        if candidate.get("preference_metrics")
    ]

    for candidate in candidates:
        candidate_id = str(candidate["alternative_id"])
        violations: list[dict[str, object]] = []

        for assignment in candidate["assignments"]:
            person_id = str(assignment["person_id"])
            period = str(assignment["period"])
            assigned_hours = assignment["load_amount"]
            constraint_id = f"capacity:{person_id}:{period}"
            available_hours = availability.get((person_id, period))

            if available_hours is None:
                violations.append(
                    {
                        "constraint_id": f"availability:{person_id}:{period}",
                        "code": "availability_missing",
                        "person_id": person_id,
                        "period": period,
                    }
                )
                continue

            if Decimal(str(assigned_hours)) > Decimal(str(available_hours)):
                violations.append(
                    {
                        "constraint_id": constraint_id,
                        "code": "capacity_exceeded",
                        "person_id": person_id,
                        "period": period,
                        "assigned_hours": assigned_hours,
                        "available_hours": available_hours,
                    }
                )

        if violations:
            rejected_alternatives.append(
                {"alternative_id": candidate_id, "violations": violations}
            )
            conflicting_constraint_ids.update(
                str(violation["constraint_id"]) for violation in violations
            )
        else:
            feasible_alternatives.append(candidate)

    return {
        "status": "feasible" if feasible_alternatives else "infeasible",
        "feasible_alternatives": feasible_alternatives,
        "rejected_alternatives": rejected_alternatives,
        "conflicting_constraint_ids": sorted(conflicting_constraint_ids),
        "checked_hard_constraints": list(HARD_CONSTRAINT_CODES),
        "soft_preference_metrics": soft_preference_metrics,
    }