from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any, Protocol

from .optimization_runs import OptimizationRunError


class AlternativeNarrativeUnavailable(RuntimeError):
    pass


METRIC_DEFINITIONS: dict[str, dict[str, str]] = {
    "skill_gap_hours": {
        "label": "Lacuna ponderada de competência",
        "definition": "Soma do déficit entre nível exigido e confirmado multiplicado pela carga atribuída.",
        "unit": "proficiency-level × configured load unit",
        "source": "OptimizationRun.result.feasible_alternatives.objective_metrics.skill_gap_hours",
        "direction": "minimize",
    },
    "peak_utilization": {
        "label": "Pico de utilização",
        "definition": "Maior razão entre carga atribuída e disponibilidade por pessoa e período.",
        "unit": "ratio",
        "source": "OptimizationRun.result.feasible_alternatives.objective_metrics.peak_utilization",
        "direction": "minimize",
    },
}


class AlternativeExplainer(Protocol):
    def explain(
        self,
        *,
        run_id: str,
        alternative_id: str,
        snapshot_id: str,
        metrics: Mapping[str, object],
        evidence_ids: Sequence[str],
    ) -> Mapping[str, object]: ...


class UnavailableAlternativeExplainer:
    def explain(
        self,
        *,
        run_id: str,
        alternative_id: str,
        snapshot_id: str,
        metrics: Mapping[str, object],
        evidence_ids: Sequence[str],
    ) -> Mapping[str, object]:
        raise AlternativeNarrativeUnavailable("Narrative provider is unavailable")


def explain_alternative(
    run: Mapping[str, Any],
    alternative_id: str,
    explainer: AlternativeExplainer,
) -> dict[str, object]:
    result = run.get("result")
    metadata = result.get("run_metadata", {}) if isinstance(result, Mapping) else {}
    alternatives = result.get("feasible_alternatives", []) if isinstance(result, Mapping) else []
    alternative = next(
        (
            item
            for item in alternatives
            if isinstance(item, Mapping) and item.get("alternative_id") == alternative_id
        ),
        None,
    )
    if not isinstance(alternative, Mapping) or not isinstance(metadata, Mapping):
        raise OptimizationRunError("ALTERNATIVE_NOT_FOUND", 404)

    snapshot_id = metadata.get("snapshot_id")
    metrics = alternative.get("objective_metrics", {})
    evidence_ids = alternative.get("evidence_ids", [])
    if not isinstance(snapshot_id, str) or not isinstance(metrics, Mapping):
        raise OptimizationRunError("ALTERNATIVE_NOT_FOUND", 404)
    if not isinstance(evidence_ids, Sequence) or isinstance(evidence_ids, str):
        evidence_ids = []

    deterministic_metrics = deepcopy(dict(metrics))
    if deterministic_metrics.get("cost") is None:
        deterministic_metrics["cost"] = {
            "status": "unavailable",
            "reason": "missing_cost_input",
        }
    available_metric_names = {
        name
        for name, value in deterministic_metrics.items()
        if (
            value.get("status") == "available" and value.get("value") is not None
            if isinstance(value, Mapping)
            else value is not None
        )
    }
    allowed_evidence_ids = {str(value) for value in evidence_ids}
    unsupported_claim = False
    try:
        generated = explainer.explain(
            run_id=str(run["run_id"]),
            alternative_id=alternative_id,
            snapshot_id=snapshot_id,
            metrics=deepcopy(deterministic_metrics),
            evidence_ids=tuple(sorted(allowed_evidence_ids)),
        )
        if not isinstance(generated, Mapping):
            generated = {}
            unsupported_claim = True
        raw_claims = generated.get("claims", [])
        claims = []
        if isinstance(raw_claims, Sequence) and not isinstance(raw_claims, str):
            for claim in raw_claims:
                if (
                    not isinstance(claim, Mapping)
                    or not isinstance(claim.get("text"), str)
                    or not claim["text"].strip()
                ):
                    unsupported_claim = True
                    continue
                metric_references = claim.get("metric_references", [])
                claim_evidence_ids = claim.get("evidence_ids", [])
                if (
                    not isinstance(metric_references, Sequence)
                    or isinstance(metric_references, str)
                    or not isinstance(claim_evidence_ids, Sequence)
                    or isinstance(claim_evidence_ids, str)
                ):
                    unsupported_claim = True
                    continue
                metric_references = [
                    str(value)
                    for value in metric_references
                    if str(value) in available_metric_names
                ]
                claim_evidence_ids = [
                    str(value)
                    for value in claim_evidence_ids
                    if str(value) in allowed_evidence_ids
                ]
                if not metric_references and not claim_evidence_ids:
                    unsupported_claim = True
                    continue
                claims.append(
                    {
                        "text": claim["text"],
                        "metric_references": metric_references,
                        "evidence_ids": claim_evidence_ids,
                    }
                )
        elif raw_claims:
            unsupported_claim = True
        generated_text = generated.get("text")
        if generated_text is not None and not isinstance(generated_text, str):
            generated_text = None
            unsupported_claim = True
        if generated_text and not claims:
            unsupported_claim = True
        narrative = {
            "status": "generated",
            "origin": "generated",
            "text": None if unsupported_claim else generated_text,
            "claims": claims,
            "reason": None,
        }
        error = None
    except AlternativeNarrativeUnavailable:
        narrative = {
            "status": "unavailable",
            "origin": "unavailable",
            "text": None,
            "claims": [],
            "reason": "narrative_unavailable",
        }
        error = {"code": "NARRATIVE_UNAVAILABLE"}

    unavailable_metrics = any(
        isinstance(value, Mapping) and value.get("status") == "unavailable"
        for value in deterministic_metrics.values()
    )
    uncertainty = unsupported_claim or unavailable_metrics or error is not None
    reason = (
        "missing_evidence"
        if unsupported_claim
        else "missing_cost_input"
        if unavailable_metrics
        else "narrative_unavailable"
        if error is not None
        else None
    )
    return {
        "run_id": str(run["run_id"]),
        "alternative_id": alternative_id,
        "decision_support": True,
        "operational_status": "pending_human_approval",
        "snapshot_id": snapshot_id,
        "metrics": deterministic_metrics,
        "metric_definitions": {
            name: dict(METRIC_DEFINITIONS[name])
            for name in sorted(deterministic_metrics)
            if name in METRIC_DEFINITIONS
        },
        "metrics_origin": "deterministic",
        "narrative": narrative,
        "unsupported_claims": [],
        "uncertainty": uncertainty,
        "reason": reason,
        "error": error,
    }