from datetime import UTC, datetime

from conftest import _request

from voskill.alternative_explanation import AlternativeNarrativeUnavailable
from voskill.api.dependencies import get_alternative_explainer
from voskill.main import app, get_actor_id, get_optimization_run_repository
from voskill.optimization_runs import OptimizationRunError


class MemoryOptimizationRunRepository:
    def __init__(self) -> None:
        self.records: dict[str, dict] = {}

    def create_run(self, **values: object) -> dict:
        record = {**values, "created_at": datetime(2026, 11, 9, tzinfo=UTC)}
        self.records[record["run_id"]] = record
        return record

    def get_run(self, run_id: str) -> dict:
        if run_id not in self.records:
            raise OptimizationRunError("RUN_NOT_FOUND", 404)
        return self.records[run_id]


class DeterministicAlternativeExplainer:
    def explain(self, **values: object) -> dict[str, object]:
        metrics = values["metrics"]
        assert isinstance(metrics, dict)
        metrics["coverage"] = 0.01
        return {
            "text": "A cobertura observada corresponde às evidências disponíveis.",
            "claims": [
                {
                    "text": "A cobertura é 0.82.",
                    "metric_references": ["coverage"],
                    "evidence_ids": ["E-001"],
                }
            ],
        }


class FailingAlternativeExplainer:
    def explain(self, **values: object) -> dict[str, object]:
        raise AlternativeNarrativeUnavailable("provider unavailable")


class UnsupportedAlternativeExplainer:
    def explain(self, **values: object) -> dict[str, object]:
        return {
            "text": "A-001 é a melhor alternativa.",
            "claims": [
                {
                    "text": "A-001 é a melhor alternativa.",
                    "metric_references": [],
                    "evidence_ids": [],
                }
            ],
        }


def _explanation_run() -> dict[str, object]:
    return {
        "run_id": "RUN-001",
        "snapshot_hash": "a" * 64,
        "algorithm_version": "pymoo-0.6.2",
        "configuration": {"seed": 42},
        "seed": 42,
        "alternatives_hash": "b" * 64,
        "result": {
            "run_metadata": {"snapshot_id": "S-001"},
            "feasible_alternatives": [
                {
                    "alternative_id": "A-001",
                    "objective_metrics": {"coverage": 0.82, "load": 0.70, "cost": 1200},
                    "evidence_ids": ["E-001", "E-002"],
                }
            ],
        },
        "actor_id": "U-001",
        "created_at": datetime(2026, 11, 9, tzinfo=UTC),
    }


def _snapshot() -> dict:
    return {
        "snapshot_id": "S-001",
        "profiles": [
            {
                "person_id": "P-001",
                "competencies": {"SKILL-1": 4},
                "availability": {"2026-01": 40},
            },
            {
                "person_id": "P-002",
                "competencies": {"SKILL-1": 2},
                "availability": {"2026-01": 50},
            },
        ],
        "demands": [
            {
                "demand_id": "D-001",
                "skill_id": "SKILL-1",
                "proficiency_level": 3,
                "period": "2026-01",
                "load_amount": 40,
            }
        ],
    }


def test_run_api_persists_metadata_and_allows_auditor_retrieval() -> None:
    repository = MemoryOptimizationRunRepository()
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_optimization_run_repository] = lambda: repository

    try:
        created = _request(
            "POST",
            "/optimization-runs",
            {"snapshot": _snapshot(), "seed": 42, "population_size": 20, "generations": 8},
        )
        run_id = created.json()["run_id"]
        retrieved = _request("GET", f"/optimization-runs/{run_id}")
    finally:
        app.dependency_overrides.clear()

    assert created.status_code == 201
    assert created.json()["snapshot_hash"]
    assert created.json()["algorithm_version"].startswith("pymoo-")
    assert created.json()["configuration"]["population_size"] == 2
    assert created.json()["configuration"]["requested_population_size"] == 20
    assert created.json()["seed"] == 42
    assert created.json()["alternatives_hash"]
    assert created.json()["created_at"]
    assert retrieved.status_code == 200
    assert retrieved.json()["run_id"] == run_id
    assert retrieved.json()["snapshot_hash"] == created.json()["snapshot_hash"]


def test_invalid_seed_returns_stable_error_without_persisting_run() -> None:
    repository = MemoryOptimizationRunRepository()
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_optimization_run_repository] = lambda: repository

    try:
        response = _request(
            "POST",
            "/optimization-runs",
            {"snapshot": _snapshot(), "seed": -1},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INVALID_SEED"
    assert repository.records == {}


def test_unknown_run_returns_stable_not_found_error() -> None:
    repository = MemoryOptimizationRunRepository()
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_optimization_run_repository] = lambda: repository

    try:
        response = _request("GET", "/optimization-runs/RUN-404")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "RUN_NOT_FOUND"


def test_only_owner_or_authorized_auditor_can_read_run() -> None:
    repository = MemoryOptimizationRunRepository()
    repository.records["RUN-001"] = {
        "run_id": "RUN-001",
        "snapshot_hash": "a" * 64,
        "algorithm_version": "pymoo-0.6.2",
        "configuration": {"seed": 42},
        "seed": 42,
        "alternatives_hash": "b" * 64,
        "result": {"status": "feasible"},
        "actor_id": "U-001",
        "created_at": datetime(2026, 11, 9, tzinfo=UTC),
    }
    app.dependency_overrides[get_actor_id] = lambda: "U-002"
    app.dependency_overrides[get_optimization_run_repository] = lambda: repository

    try:
        denied = _request("GET", "/optimization-runs/RUN-001")
        auditor = _request(
            "GET",
            "/optimization-runs/RUN-001",
            state={"can_audit_optimization_runs": True},
        )
    finally:
        app.dependency_overrides.clear()

    assert denied.status_code == 404
    assert denied.json()["detail"]["code"] == "RUN_NOT_FOUND"
    assert auditor.status_code == 200
    assert auditor.json()["run_id"] == "RUN-001"
    assert auditor.json()["actor_id"] == "U-001"


def test_explanation_references_run_snapshot_metrics_and_evidence() -> None:
    repository = MemoryOptimizationRunRepository()
    record = _explanation_run()
    repository.records["RUN-001"] = record
    explainer = DeterministicAlternativeExplainer()
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_optimization_run_repository] = lambda: repository
    app.dependency_overrides[get_alternative_explainer] = lambda: explainer

    try:
        response = _request(
            "GET",
            "/optimization-runs/RUN-001/alternatives/A-001/explanation",
        )
    finally:
        app.dependency_overrides.clear()

    body = response.json()
    assert response.status_code == 200
    assert body["run_id"] == "RUN-001"
    assert body["alternative_id"] == "A-001"
    assert body["snapshot_id"] == "S-001"
    assert body["metrics"] == {"coverage": 0.82, "load": 0.70, "cost": 1200}
    assert body["metrics_origin"] == "deterministic"
    assert body["narrative"]["origin"] == "generated"
    assert body["narrative"]["claims"][0]["evidence_ids"] == ["E-001"]
    assert body["unsupportedClaims"] == []
    assert body["uncertainty"] is False
    assert body["reason"] is None
    assert repository.records["RUN-001"]["result"] == record["result"]


def test_explanation_keeps_deterministic_metrics_when_narrative_provider_fails() -> None:
    repository = MemoryOptimizationRunRepository()
    record = _explanation_run()
    repository.records["RUN-001"] = record
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_optimization_run_repository] = lambda: repository
    app.dependency_overrides[get_alternative_explainer] = lambda: FailingAlternativeExplainer()

    try:
        response = _request(
            "GET",
            "/optimization-runs/RUN-001/alternatives/A-001/explanation",
        )
    finally:
        app.dependency_overrides.clear()

    body = response.json()
    assert response.status_code == 200
    assert body["error"] == {"code": "NARRATIVE_UNAVAILABLE"}
    assert body["narrative"] == {
        "status": "unavailable",
        "origin": "unavailable",
        "text": None,
        "claims": [],
        "reason": "narrative_unavailable",
    }
    assert body["metrics"] == {"coverage": 0.82, "load": 0.70, "cost": 1200}
    assert repository.records["RUN-001"]["result"] == record["result"]


def test_explanation_hides_run_from_non_owner() -> None:
    repository = MemoryOptimizationRunRepository()
    repository.records["RUN-001"] = _explanation_run()
    app.dependency_overrides[get_actor_id] = lambda: "U-002"
    app.dependency_overrides[get_optimization_run_repository] = lambda: repository
    app.dependency_overrides[get_alternative_explainer] = lambda: DeterministicAlternativeExplainer()

    try:
        response = _request(
            "GET",
            "/optimization-runs/RUN-001/alternatives/A-001/explanation",
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "RUN_NOT_FOUND"
    assert "E-001" not in response.text


def test_explanation_marks_missing_cost_unavailable_without_a_numeric_value() -> None:
    repository = MemoryOptimizationRunRepository()
    record = _explanation_run()
    alternative = record["result"]["feasible_alternatives"][0]
    alternative["objective_metrics"].pop("cost")
    repository.records["RUN-001"] = record
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_optimization_run_repository] = lambda: repository
    app.dependency_overrides[get_alternative_explainer] = lambda: DeterministicAlternativeExplainer()

    try:
        response = _request(
            "GET",
            "/optimization-runs/RUN-001/alternatives/A-001/explanation",
        )
    finally:
        app.dependency_overrides.clear()

    cost = response.json()["metrics"]["cost"]
    assert cost == {"status": "unavailable", "reason": "missing_cost_input"}
    assert "value" not in cost


def test_explanation_omits_claims_without_references_and_marks_uncertainty() -> None:
    repository = MemoryOptimizationRunRepository()
    repository.records["RUN-001"] = _explanation_run()
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_optimization_run_repository] = lambda: repository
    app.dependency_overrides[get_alternative_explainer] = lambda: UnsupportedAlternativeExplainer()

    try:
        response = _request(
            "GET",
            "/optimization-runs/RUN-001/alternatives/A-001/explanation",
        )
    finally:
        app.dependency_overrides.clear()

    body = response.json()
    assert body["unsupportedClaims"] == []
    assert body["uncertainty"] is True
    assert body["reason"] == "missing_evidence"
    assert body["narrative"]["claims"] == []
    assert body["narrative"]["text"] is None