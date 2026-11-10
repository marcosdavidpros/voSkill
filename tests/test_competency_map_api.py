from conftest import _request

from voskill.main import (
    app,
    get_actor_id,
    get_competency_repository,
    get_scenario_repository,
    get_skill_relation_repository,
)
from voskill.scenario_comparison import ScenarioError


class MemoryScenarioRepository:
    def get_competency_snapshot(self, scenario_id: str) -> dict:
        if scenario_id != "S-001":
            raise ScenarioError("SCENARIO_NOT_FOUND", 404)
        return {
            "scenario_id": scenario_id,
            "project_id": "P-001",
            "snapshot_id": "SNAP-001",
            "snapshot": {
                "periods": {
                    "2026-01": {
                        "demand": {
                            "JAVA": {"level": 4, "loadAmount": 40},
                            "OPENSHIFT": {"level": 3, "loadAmount": 20},
                            "CLOUD": {"level": 2, "loadAmount": 10},
                        },
                        "availability": {"P-001": {"hours": 40}},
                    }
                }
            },
        }


class MemoryCompetencyRepository:
    def __init__(self) -> None:
        self.list_calls: list[str] = []

    def list_for_person(self, person_id: str) -> list[dict]:
        self.list_calls.append(person_id)
        if person_id != "P-001":
            return []
        return [
            {
                "person_id": "P-001",
                "skill_id": "JAVA",
                "skill_name": "Java",
                "proficiency_level": 4,
                "evidence": "Java delivery evidence",
                "origin_type": "MANUAL",
                "review_date": "2026-11-09",
            }
        ]


class MemorySkillRelationRepository:
    def infer_for_person(self, person_id: str, target_skill_id: str) -> dict:
        if person_id == "P-001" and target_skill_id == "OPENSHIFT":
            return {
                "status": "inferred",
                "inferred_level": 3,
                "source_skill_id": "JAVA",
                "relation_id": "REL-001",
                "confidence": 0.65,
                "reason": None,
            }
        return {
            "status": "insufficient_evidence",
            "inferred_level": None,
            "source_skill_id": None,
            "relation_id": None,
            "confidence": None,
            "reason": "insufficient_evidence",
        }


def test_competency_map_distinguishes_confirmed_inferred_uncovered_and_counts_only_confirmed() -> None:
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_scenario_repository] = lambda: MemoryScenarioRepository()
    app.dependency_overrides[get_competency_repository] = lambda: MemoryCompetencyRepository()
    app.dependency_overrides[get_skill_relation_repository] = lambda: MemorySkillRelationRepository()

    try:
        response = _request(
            "GET",
            "/scenarios/S-001/competency-map",
            state={"actor_id": "U-001", "authorized_person_ids": ["P-001"]},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    result = response.json()
    assert result["scenario_id"] == "S-001"
    assert result["coverage"] == {"confirmed_count": 1, "skill_count": 3, "ratio": 1 / 3}
    skills = {skill["skill_id"]: skill for skill in result["skills"]}
    assert skills["JAVA"]["status"] == "confirmed"
    assert skills["JAVA"]["holders"][0]["person_id"] == "P-001"
    assert skills["OPENSHIFT"]["status"] == "inferred"
    assert skills["OPENSHIFT"]["holders"][0]["confidence"] == 0.65
    assert skills["OPENSHIFT"]["holders"][0]["review_state"] == "pending_review"
    assert skills["CLOUD"]["status"] == "uncovered"


def test_competency_map_returns_scenario_not_found_without_stale_data() -> None:
    app.dependency_overrides[get_actor_id] = lambda: "U-001"
    app.dependency_overrides[get_scenario_repository] = lambda: MemoryScenarioRepository()

    try:
        response = _request("GET", "/scenarios/S-404/competency-map")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "SCENARIO_NOT_FOUND"


def test_competency_map_denies_scenario_without_person_access_before_loading_profiles() -> None:
    competencies = MemoryCompetencyRepository()
    app.dependency_overrides[get_actor_id] = lambda: "U-999"
    app.dependency_overrides[get_scenario_repository] = lambda: MemoryScenarioRepository()
    app.dependency_overrides[get_competency_repository] = lambda: competencies

    try:
        response = _request(
            "GET",
            "/scenarios/S-001/competency-map",
            state={"actor_id": "U-999", "authorized_person_ids": []},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "FORBIDDEN"
    assert "Java delivery evidence" not in response.text
    assert competencies.list_calls == []