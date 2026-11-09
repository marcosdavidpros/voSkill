from copy import deepcopy


class ScenarioError(ValueError):
    def __init__(self, code: str, status_code: int) -> None:
        self.code = code
        self.status_code = status_code
        super().__init__(code)


def compare_scenarios(
    first_scenario_id: str,
    first_snapshot: object,
    first_deltas: object,
    second_scenario_id: str,
    second_snapshot: object,
    second_deltas: object,
) -> dict[str, object]:
    if first_scenario_id == second_scenario_id:
        raise ScenarioError("DUPLICATE_SCENARIO", 422)

    effective_periods: dict[str, dict[str, object]] = {}
    for scenario_id, snapshot, deltas in (
        (first_scenario_id, first_snapshot, first_deltas),
        (second_scenario_id, second_snapshot, second_deltas),
    ):
        effective = _merge_json(snapshot, deltas)
        periods = effective.get("periods") if isinstance(effective, dict) else None
        if not isinstance(periods, dict):
            raise ScenarioError("INVALID_SCENARIO_SNAPSHOT", 422)
        effective_periods[scenario_id] = periods

    period_ids = sorted(
        {
            period_id
            for periods in effective_periods.values()
            for period_id in periods
        }
    )
    required_periods = {
        period_id
        for periods in effective_periods.values()
        for period_id, assumptions in periods.items()
        if isinstance(assumptions, dict) and assumptions.get("demand")
    }

    scenario_statuses: list[dict[str, object]] = []
    for scenario_id in (first_scenario_id, second_scenario_id):
        missing = []
        periods = effective_periods[scenario_id]
        for period_id in sorted(required_periods):
            assumptions = periods.get(period_id)
            availability = (
                assumptions.get("availability")
                if isinstance(assumptions, dict)
                else None
            )
            if not availability:
                missing.append({"period": period_id, "field": "availability"})
        scenario_statuses.append(
            {
                "scenario_id": scenario_id,
                "status": "incomplete" if missing else "complete",
                "missing": missing,
            }
        )

    period_comparisons = []
    for period_id in period_ids:
        assumptions_by_scenario = {
            scenario_id: effective_periods[scenario_id].get(period_id, {})
            for scenario_id in (first_scenario_id, second_scenario_id)
        }
        fields = {
            field
            for assumptions in assumptions_by_scenario.values()
            if isinstance(assumptions, dict)
            for field in assumptions
        }
        changed_values = {}
        for field in sorted(fields):
            values = {
                scenario_id: (
                    assumptions.get(field) if isinstance(assumptions, dict) else None
                )
                for scenario_id, assumptions in assumptions_by_scenario.items()
            }
            if values[first_scenario_id] != values[second_scenario_id]:
                changed_values[field] = values
        period_comparisons.append(
            {
                "period": period_id,
                "assumptions": assumptions_by_scenario,
                "changed_values": changed_values,
            }
        )

    return {
        "scenario_ids": [first_scenario_id, second_scenario_id],
        "scenarios": scenario_statuses,
        "periods": period_comparisons,
    }


def _merge_json(base: object, delta: object) -> object:
    if isinstance(base, dict) and isinstance(delta, dict):
        merged = deepcopy(base)
        for key, value in delta.items():
            merged[key] = _merge_json(merged.get(key), value)
        return merged
    return deepcopy(delta)