from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Any

# Ordem de desempate para "mais segura"; não é uma nota agregada.
SAFETY_RULE = (
    "Menor excesso de horas acima da disponibilidade",
    "Menos tarefas sem ninguém com a competência",
    "Menos tarefas abaixo do nível exigido",
    "Menor lacuna ponderada de competência",
)


def _number(value: object) -> Decimal:
    return Decimal(str(value))


def _plain(value: Decimal) -> int | float:
    return int(value) if value == value.to_integral_value() else float(value)


def _plan(alternative: Mapping[str, Any], snapshot: Mapping[str, Any]) -> dict[str, object]:
    profiles = {str(profile["person_id"]): profile for profile in snapshot.get("profiles", [])}
    demands = {str(demand["demand_id"]): demand for demand in snapshot.get("demands", [])}

    assignments: list[dict[str, object]] = []
    issues: list[dict[str, object]] = []
    load_by_slot: dict[tuple[str, str], Decimal] = {}
    below_level = 0
    without_competency = 0

    for item in alternative.get("allocation", []):
        person_id = str(item["person_id"])
        skill_id = str(item["skill_id"])
        period = str(item["period"])
        required = int(item["required_level"])
        load = _number(item["load_amount"])
        competencies = profiles.get(person_id, {}).get("competencies", {})
        level = int(competencies.get(skill_id, 0))
        status = "ok" if level >= required else "no_competency" if level == 0 else "below_level"
        demand = demands.get(str(item["demand_id"]), {})
        row = {
            "demand_id": str(item["demand_id"]),
            "title": demand.get("title"),
            "epic": demand.get("epic"),
            "skill_id": skill_id,
            "period": period,
            "load_amount": _plain(load),
            "required_level": required,
            "person_id": person_id,
            "person_level": level,
            "status": status,
        }
        assignments.append(row)
        load_by_slot[(person_id, period)] = load_by_slot.get((person_id, period), Decimal(0)) + load
        if status != "ok":
            below_level += status == "below_level"
            without_competency += status == "no_competency"

    slots: list[dict[str, object]] = []
    overload_issues: list[dict[str, object]] = []
    unavailable_issues: list[dict[str, object]] = []
    excess_total = Decimal(0)
    peak = Decimal(0)
    overloaded = 0
    unavailable = 0
    for (person_id, period), assigned in sorted(load_by_slot.items()):
        raw = profiles.get(person_id, {}).get("availability", {}).get(period)
        available = _number(raw) if raw is not None else None
        if available is None or available <= 0:
            status, utilization, excess = "no_availability", None, assigned
            unavailable += 1
            unavailable_issues.append(
                {"code": "no_availability", "person_id": person_id, "period": period, "assigned_hours": _plain(assigned)}
            )
        else:
            ratio = assigned / available
            peak = max(peak, ratio)
            utilization = round(float(ratio), 4)
            excess = max(Decimal(0), assigned - available)
            status = "overloaded" if excess > 0 else "ok"
            if excess > 0:
                overloaded += 1
                overload_issues.append(
                    {
                        "code": "overload",
                        "person_id": person_id,
                        "period": period,
                        "assigned_hours": _plain(assigned),
                        "available_hours": _plain(available),
                        "excess_hours": _plain(excess),
                    }
                )
        excess_total += excess
        slots.append(
            {
                "person_id": person_id,
                "period": period,
                "assigned_hours": _plain(assigned),
                "available_hours": _plain(available) if available is not None else None,
                "utilization": utilization,
                "status": status,
                "excess_hours": _plain(excess),
            }
        )

    task_issues = [
        {"code": row["status"], **{key: row[key] for key in ("demand_id", "title", "epic", "skill_id", "period", "person_id", "person_level", "required_level")}}
        for row in assignments
        if row["status"] != "ok"
    ]
    # Ordem de leitura: capacidade, depois nível, depois falta total de competência.
    task_issues.sort(key=lambda issue: issue["code"] != "below_level")
    all_issues = overload_issues + unavailable_issues + task_issues

    metrics = alternative.get("objective_metrics", {})
    summary = {
        "tasks": len(assignments),
        "tasks_ok": len(assignments) - below_level - without_competency,
        "tasks_below_level": below_level,
        "tasks_without_competency": without_competency,
        "overloaded_slots": overloaded,
        "unavailable_slots": unavailable,
        "excess_hours": _plain(excess_total),
        "peak_utilization": round(float(peak), 4) if peak else 0,
        "skill_gap_hours": metrics.get("skill_gap_hours"),
    }
    return {
        "alternative_id": str(alternative["alternative_id"]),
        "assignments": assignments,
        "slots": slots,
        "issues": all_issues,
        "summary": summary,
        "executable": not all_issues,
    }


def _safety_key(plan: Mapping[str, Any]) -> tuple[Any, ...]:
    summary = plan["summary"]
    return (
        summary["excess_hours"],
        summary["tasks_without_competency"],
        summary["tasks_below_level"],
        summary["skill_gap_hours"] if summary["skill_gap_hours"] is not None else float("inf"),
        plan["alternative_id"],
    )


def _uncovered_demands(snapshot: Mapping[str, Any]) -> list[dict[str, object]]:
    profiles = snapshot.get("profiles", [])
    uncovered: list[dict[str, object]] = []
    for demand in snapshot.get("demands", []):
        skill_id = str(demand["skill_id"])
        best = max((int(profile.get("competencies", {}).get(skill_id, 0)) for profile in profiles), default=0)
        required = int(demand["proficiency_level"])
        if best < required:
            uncovered.append(
                {
                    "demand_id": str(demand["demand_id"]),
                    "title": demand.get("title"),
                    "epic": demand.get("epic"),
                    "skill_id": skill_id,
                    "period": str(demand["period"]),
                    "load_amount": _plain(_number(demand["load_amount"])),
                    "required_level": required,
                    "best_level": best,
                }
            )
    return sorted(uncovered, key=lambda item: (str(item["period"]), str(item["demand_id"])))


def build_operational_plans(
    alternatives: Sequence[Mapping[str, Any]],
    snapshot: Mapping[str, Any],
) -> dict[str, object]:
    plans = sorted((_plan(alternative, snapshot) for alternative in alternatives), key=_safety_key)
    return {
        "snapshot_id": snapshot.get("snapshot_id"),
        "recommended_alternative_id": plans[0]["alternative_id"] if plans else None,
        "recommendation_rule": list(SAFETY_RULE),
        "uncovered_demands": _uncovered_demands(snapshot),
        "plans": plans,
    }
