from conftest import _request

from voskill.api.dependencies import (
    get_actor_id,
    get_competency_repository,
    get_risk_threshold_repository,
    get_scenario_repository,
    get_skill_relation_repository,
)
from voskill.main import app
from voskill.risk_thresholds import RiskThresholdError


class MemoryScenarioRepository:
    def get_competency_snapshot(self, scenario_id: str) -> dict:
        return {
            "scenario_id": scenario_id,
            "project_id": "P-001",
            "snapshot_id": "SNAP-001",
            "snapshot": {
                "periods": {
                    "2026-01": {
                        "demand": {
                            "KUBERNETES": {"level": 3, "loadAmount": 40},
                        },
                        "availability": {"P-001": {"hours": 40}},
                    }
                }
            },
        }


class MemoryCompetencyRepository:
    def list_for_person(self, person_id: str) -> list[dict]:
        if person_id != "P-001":
            return []
        return [
            {
                "person_id": "P-001",
                "skill_id": "KUBERNETES",
                "skill_name": "Kubernetes",
                "proficiency_level": 4,
                "evidence": "Operação de cluster Kubernetes",
                "origin_type": "MANUAL",
                "review_date": "2026-11-09",
            }
        ]


class MemorySkillRelationRepository:
    def infer_for_person(self, person_id: str, target_skill_id: str) -> dict:
        return {
            "status": "insufficient_evidence",
            "inferred_level": None,
            "source_skill_id": None,
            "relation_id": None,
            "confidence": None,
            "reason": "insufficient_evidence",
        }


class MemoryRiskThresholdRepository:
    def __init__(self) -> None:
        self.thresholds = {("P-001", "KUBERNETES"): 2}

    def list_for_project(self, project_id: str) -> dict[str, int]:
        return {
            skill_id: threshold
            for (stored_project_id, skill_id), threshold in self.thresholds.items()
            if stored_project_id == project_id
        }

    def save(self, project_id: str, skill_id: str, threshold: int, actor_id: str) -> dict:
        if isinstance(threshold, bool) or threshold < 1:
            raise RiskThresholdError("INVALID_RISK_THRESHOLD", 422)
        self.thresholds[(project_id, skill_id)] = threshold
        return {
            "project_id": project_id,
            "skill_id": skill_id,
            "threshold": threshold,
            "actor_id": actor_id,
        }


def test_risk_panel_reports_confirmed_people_threshold_and_evidence() -> None:
    thresholds = MemoryRiskThresholdRepository()
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_scenario_repository] = lambda: MemoryScenarioRepository()
    app.dependency_overrides[get_competency_repository] = lambda: MemoryCompetencyRepository()
    app.dependency_overrides[get_skill_relation_repository] = lambda: MemorySkillRelationRepository()
    app.dependency_overrides[get_risk_threshold_repository] = lambda: thresholds

    try:
        response = _request(
            "GET",
            "/scenarios/S-001/risk-panel",
            state={"actor_id": "U-001", "authorized_project_ids": ["P-001"]},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["risks"] == [
        {
            "skill_id": "KUBERNETES",
            "skill_name": "Kubernetes",
            "confirmed_count": 1,
            "threshold": 2,
            "people": [
                {
                    "person_id": "P-001",
                    "evidence": "Operação de cluster Kubernetes",
                }
            ],
        }
    ]


def test_zero_threshold_is_rejected_without_overwriting_previous_value() -> None:
    thresholds = MemoryRiskThresholdRepository()
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_risk_threshold_repository] = lambda: thresholds

    try:
        response = _request(
            "PUT",
            "/projects/P-001/critical-skill-thresholds/KUBERNETES",
            {"threshold": 0},
            state={"actor_id": "U-001", "authorized_project_ids": ["P-001"]},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INVALID_RISK_THRESHOLD"
    assert thresholds.thresholds[("P-001", "KUBERNETES")] == 2