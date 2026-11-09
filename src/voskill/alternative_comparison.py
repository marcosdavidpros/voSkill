from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Any, Literal

ObjectiveDirection = Literal["maximize", "minimize"]


class AlternativeComparisonError(ValueError):
    def __init__(self, code: str, status_code: int) -> None:
        self.code = code
        self.status_code = status_code
        super().__init__(code)


def compare_alternatives(
    alternatives: Sequence[Mapping[str, Any]],
    alternative_ids: Sequence[str],
    objective_names: Sequence[str],
    objective_directions: Mapping[str, ObjectiveDirection],
    objective_metadata: Mapping[str, Mapping[str, str]] | None = None,
) -> dict[str, Any]:
    alternatives_by_id = {str(item["alternative_id"]): item for item in alternatives}
    if any(alternative_id not in alternatives_by_id for alternative_id in alternative_ids):
        raise AlternativeComparisonError("UNKNOWN_ALTERNATIVE", 404)

    selected = []
    for alternative_id in alternative_ids:
        source = alternatives_by_id[alternative_id]
        source_metrics = source.get("objective_metrics", {})
        metrics = {
            name: _present_metric(
                name,
                source_metrics.get(name),
                name in source_metrics,
                (objective_metadata or {}).get(name),
            )
            for name in objective_names
        }
        selected.append({**source, "objective_metrics": metrics})

    trade_offs = []
    for first_index, first in enumerate(selected):
        for second in selected[first_index + 1 :]:
            first_advantages = []
            second_advantages = []
            for name in objective_names:
                first_value = _metric_value(first["objective_metrics"][name])
                second_value = _metric_value(second["objective_metrics"][name])
                if first_value is None or second_value is None or first_value == second_value:
                    continue
                direction = objective_directions[name]
                first_is_better = first_value > second_value if direction == "maximize" else first_value < second_value
                (first_advantages if first_is_better else second_advantages).append(name)

            if first_advantages and second_advantages:
                trade_offs.append(
                    {
                        "alternative_ids": [first["alternative_id"], second["alternative_id"]],
                        "objectives": sorted(first_advantages + second_advantages),
                    }
                )

    return {"alternatives": selected, "trade_offs": trade_offs}


def _metric_value(metric: object) -> Decimal | None:
    if isinstance(metric, Mapping):
        if metric.get("status") != "available":
            return None
        metric = metric.get("value")
    if isinstance(metric, bool) or not isinstance(metric, int | float | Decimal):
        return None
    return Decimal(str(metric))


def _present_metric(
    name: str,
    metric: object,
    available: bool,
    metadata: Mapping[str, str] | None,
) -> object:
    if not available:
        return {"status": "unavailable", "reason": f"missing_{name}_input"}
    if isinstance(metric, Mapping) and metric.get("status") == "unavailable":
        return {
            "status": "unavailable",
            "reason": metric.get("reason", f"missing_{name}_input"),
        }
    if isinstance(metric, Mapping):
        result = dict(metric)
    elif metadata:
        result = {"status": "available", "value": metric}
    else:
        return metric

    if metadata:
        for field in ("unit", "source"):
            if field in metadata:
                result.setdefault(field, metadata[field])
    return result