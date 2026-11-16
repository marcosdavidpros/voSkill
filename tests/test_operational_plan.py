import json

from conftest import _request

from voskill.api.dependencies import get_actor_id, get_optimization_run_repository
from voskill.main import app
from voskill.operational_plan import SAFETY_RULE, build_operational_plans
from voskill.optimization_runs import OptimizationRunError

SNAPSHOT = {
    "snapshot_id": "SNP-1",
    "profiles": [
        {"person_id": "P-001", "competencies": {"SK-1": 3, "SK-2": 1}, "availability": {"2026-01": 100}},
        {"person_id": "P-002", "competencies": {"SK-1": 1}, "availability": {"2026-01": 100, "2026-02": 0}},
    ],
    "demands": [
        {"demand_id": "D-1", "skill_id": "SK-1", "proficiency_level": 2, "period": "2026-01", "load_amount": 80, "title": "Integração", "epic": "Pagamentos"},
        {"demand_id": "D-2", "skill_id": "SK-2", "proficiency_level": 2, "period": "2026-01", "load_amount": 60},
        {"demand_id": "D-3", "skill_id": "SK-3", "proficiency_level": 1, "period": "2026-01", "load_amount": 30},
    ],
}


def _assignment(demand_id: str, person_id: str, skill_id: str, level: int, load: float, period: str = "2026-01") -> dict:
    return {"demand_id": demand_id, "person_id": person_id, "skill_id": skill_id, "period": period, "required_level": level, "load_amount": load}


ALTERNATIVES = [
    {
        "alternative_id": "A-001",
        "allocation": [
            _assignment("D-1", "P-001", "SK-1", 2, 80),
            _assignment("D-2", "P-001", "SK-2", 2, 60),
            _assignment("D-3", "P-002", "SK-3", 1, 30),
        ],
        "objective_metrics": {"skill_gap_hours": 90, "peak_utilization": 1.4},
    },
    {
        "alternative_id": "A-002",
        "allocation": [
            _assignment("D-1", "P-001", "SK-1", 2, 80),
            _assignment("D-2", "P-002", "SK-2", 2, 60),
            _assignment("D-3", "P-002", "SK-3", 1, 30),
        ],
        "objective_metrics": {"skill_gap_hours": 150, "peak_utilization": 0.9},
    },
]


def test_plan_tells_who_does_each_task_and_flags_competency_status() -> None:
    result = build_operational_plans(ALTERNATIVES, SNAPSHOT)
    plan = next(item for item in result["plans"] if item["alternative_id"] == "A-001")

    assert [(a["demand_id"], a["person_id"], a["status"]) for a in plan["assignments"]] == [
        ("D-1", "P-001", "ok"),
        ("D-2", "P-001", "below_level"),
        ("D-3", "P-002", "no_competency"),
    ]
    first = plan["assignments"][0]
    assert (first["title"], first["epic"], first["person_level"], first["required_level"]) == ("Integração", "Pagamentos", 3, 2)
    assert plan["assignments"][1]["person_level"] == 1
    assert plan["assignments"][2]["person_level"] == 0


def test_plan_flags_overloaded_people_by_month_with_excess_hours() -> None:
    result = build_operational_plans(ALTERNATIVES, SNAPSHOT)
    plan = next(item for item in result["plans"] if item["alternative_id"] == "A-001")

    slot = next(item for item in plan["slots"] if item["person_id"] == "P-001")
    assert (slot["period"], slot["assigned_hours"], slot["available_hours"]) == ("2026-01", 140, 100)
    assert (slot["utilization"], slot["status"], slot["excess_hours"]) == (1.4, "overloaded", 40)
    assert plan["summary"] == {
        "tasks": 3,
        "tasks_ok": 1,
        "tasks_below_level": 1,
        "tasks_without_competency": 1,
        "overloaded_slots": 1,
        "unavailable_slots": 0,
        "excess_hours": 40,
        "peak_utilization": 1.4,
        "skill_gap_hours": 90,
    }
    assert plan["executable"] is False
    assert [issue["code"] for issue in plan["issues"]] == ["overload", "below_level", "no_competency"]
    assert plan["issues"][0]["excess_hours"] == 40


def test_unavailable_person_month_is_reported_and_counts_as_excess() -> None:
    alternative = {
        "alternative_id": "A-009",
        "allocation": [_assignment("D-1", "P-002", "SK-1", 1, 40, "2026-02")],
        "objective_metrics": {"skill_gap_hours": 0, "peak_utilization": 1.0},
    }
    result = build_operational_plans([alternative], SNAPSHOT)
    plan = result["plans"][0]

    assert plan["slots"][0]["status"] == "no_availability"
    assert plan["slots"][0]["utilization"] is None
    assert plan["summary"]["unavailable_slots"] == 1
    assert plan["summary"]["excess_hours"] == 40
    assert plan["issues"][0]["code"] == "no_availability"


def test_safest_alternative_follows_explicit_rule_and_executable_plan_has_no_issues() -> None:
    result = build_operational_plans(ALTERNATIVES, SNAPSHOT)

    assert result["recommended_alternative_id"] == "A-002"
    assert result["recommendation_rule"] == list(SAFETY_RULE)
    assert [plan["alternative_id"] for plan in result["plans"]] == ["A-002", "A-001"]

    clean = {
        "alternative_id": "A-010",
        "allocation": [_assignment("D-1", "P-001", "SK-1", 2, 80)],
        "objective_metrics": {"skill_gap_hours": 0, "peak_utilization": 0.8},
    }
    plan = build_operational_plans([clean], SNAPSHOT)["plans"][0]
    assert plan["executable"] is True
    assert plan["issues"] == []


def test_demands_nobody_in_the_scenario_can_cover_are_listed_with_best_level() -> None:
    result = build_operational_plans(ALTERNATIVES, SNAPSHOT)

    assert [(item["demand_id"], item["required_level"], item["best_level"]) for item in result["uncovered_demands"]] == [
        ("D-2", 2, 1),
        ("D-3", 1, 0),
    ]
    assert result["uncovered_demands"][0]["skill_id"] == "SK-2"


def test_task_missing_from_snapshot_is_still_listed_without_title() -> None:
    alternative = {
        "alternative_id": "A-011",
        "allocation": [_assignment("D-404", "P-001", "SK-1", 2, 10)],
        "objective_metrics": {"skill_gap_hours": 0, "peak_utilization": 0.1},
    }
    plan = build_operational_plans([alternative], SNAPSHOT)["plans"][0]

    assert plan["assignments"][0]["title"] is None
    assert plan["assignments"][0]["epic"] is None


class MemoryRunRepository:
    def __init__(self, snapshot: dict | None = SNAPSHOT) -> None:
        self.snapshot = snapshot
        self.record = {
            "run_id": "RUN-1",
            "actor_id": "U-001",
            "result": {
                "feasible_alternatives": ALTERNATIVES,
                "run_metadata": {"snapshot_id": "SNP-1"},
            },
        }

    def get_run(self, run_id: str) -> dict:
        if run_id != "RUN-1":
            raise OptimizationRunError("RUN_NOT_FOUND", 404)
        return self.record

    def get_scenario_snapshot(self, snapshot_id: str) -> dict:
        if self.snapshot is None or snapshot_id != "SNP-1":
            raise OptimizationRunError("SNAPSHOT_NOT_FOUND", 404)
        return self.snapshot


def _get(actor: str, repository: MemoryRunRepository, run_id: str = "RUN-1"):
    app.dependency_overrides[get_actor_id] = lambda: actor
    app.dependency_overrides[get_optimization_run_repository] = lambda: repository
    try:
        return _request("GET", f"/optimization-runs/{run_id}/operational-plan")
    finally:
        app.dependency_overrides.clear()


def test_operational_plan_endpoint_returns_plans_for_the_run_owner() -> None:
    response = _get("U-001", MemoryRunRepository())

    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == "RUN-1"
    assert body["snapshot_id"] == "SNP-1"
    assert body["recommended_alternative_id"] == "A-002"
    assert json.dumps(body["plans"][0]["summary"])


def test_operational_plan_endpoint_hides_runs_of_other_actors() -> None:
    assert _get("U-002", MemoryRunRepository()).status_code == 404


def test_operational_plan_endpoint_reports_missing_snapshot() -> None:
    response = _get("U-001", MemoryRunRepository(snapshot=None))

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "SNAPSHOT_NOT_FOUND"


def test_operational_plan_endpoint_requires_authentication() -> None:
    assert _request("GET", "/optimization-runs/RUN-1/operational-plan").status_code == 401
