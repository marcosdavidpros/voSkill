from typing import Annotated

from fastapi import APIRouter, Depends, Request

from ...competencies import CompetencyRepository
from ...competency_map import build_competency_map
from ...risk_thresholds import RiskThresholdError, RiskThresholdRepository
from ...scenario_comparison import ScenarioError
from ...scenarios import ScenarioRepository
from ...skill_relations import SkillRelationRepository
from ..dependencies import (
    get_actor_id,
    get_competency_repository,
    get_risk_threshold_repository,
    get_scenario_repository,
    get_skill_relation_repository,
    require_project_risk_manager,
)
from ..errors import raise_risk_threshold_error, raise_scenario_error
from ..schemas import (
    CriticalSkillThresholdPayload,
    CriticalSkillThresholdResponse,
    RiskPanelResponse,
)

router = APIRouter()


@router.get("/scenarios/{scenario_id}/risk-panel", response_model=RiskPanelResponse)
def get_scenario_risk_panel(
    scenario_id: str,
    request: Request,
    actor_id: Annotated[str, Depends(get_actor_id)],
    scenario_repository: Annotated[ScenarioRepository, Depends(get_scenario_repository)],
    competency_repository: Annotated[CompetencyRepository, Depends(get_competency_repository)],
    relation_repository: Annotated[SkillRelationRepository, Depends(get_skill_relation_repository)],
    threshold_repository: Annotated[RiskThresholdRepository, Depends(get_risk_threshold_repository)],
) -> dict[str, object]:
    try:
        scenario = scenario_repository.get_competency_snapshot(scenario_id)
        project_id = str(scenario["project_id"])
        require_project_risk_manager(request, actor_id, project_id)
        snapshot = scenario["snapshot"]
        periods = snapshot["periods"]
        person_ids = sorted(
            {
                str(person_id)
                for assumptions in periods.values()
                if isinstance(assumptions, dict)
                for person_id in assumptions.get("availability", {})
            }
        )
        skill_ids = sorted(
            {
                str(skill_id)
                for assumptions in periods.values()
                if isinstance(assumptions, dict)
                for skill_id in assumptions.get("demand", {})
            }
        )
        confirmed_by_person = {
            person_id: competency_repository.list_for_person(person_id)
            for person_id in person_ids
        }
        inferences = {}
        for person_id in person_ids:
            confirmed_skill_ids = {
                str(item["skill_id"]) for item in confirmed_by_person[person_id]
            }
            for skill_id in set(skill_ids) - confirmed_skill_ids:
                inferences[(person_id, skill_id)] = relation_repository.infer_for_person(
                    person_id,
                    skill_id,
                )

        competency_map = build_competency_map(
            scenario_id=scenario_id,
            project_id=project_id,
            snapshot=snapshot,
            confirmed_by_person=confirmed_by_person,
            inferences=inferences,
        )
        thresholds = threshold_repository.list_for_project(project_id)
        risks = []
        for skill in competency_map["skills"]:
            threshold = thresholds.get(skill["skill_id"])
            if threshold is None or skill["confirmed_count"] >= threshold:
                continue
            confirmed_holders = [
                holder for holder in skill["holders"] if holder["status"] == "confirmed"
            ]
            risks.append(
                {
                    "skill_id": skill["skill_id"],
                    "skill_name": next(
                        (holder["skill_name"] for holder in confirmed_holders),
                        skill["skill_id"],
                    ),
                    "confirmed_count": skill["confirmed_count"],
                    "threshold": threshold,
                    "people": [
                        {"person_id": holder["person_id"], "evidence": holder["evidence"]}
                        for holder in confirmed_holders
                    ],
                }
            )
        return {
            "scenario_id": scenario_id,
            "project_id": project_id,
            "thresholds": thresholds,
            "risks": risks,
        }
    except ScenarioError as error:
        raise_scenario_error(error)


@router.put(
    "/projects/{project_id}/critical-skill-thresholds/{skill_id}",
    response_model=CriticalSkillThresholdResponse,
)
def save_critical_skill_threshold(
    project_id: str,
    skill_id: str,
    payload: CriticalSkillThresholdPayload,
    request: Request,
    actor_id: Annotated[str, Depends(get_actor_id)],
    repository: Annotated[RiskThresholdRepository, Depends(get_risk_threshold_repository)],
) -> dict[str, object]:
    require_project_risk_manager(request, actor_id, project_id)
    try:
        return repository.save(project_id, skill_id, payload.threshold, actor_id)
    except RiskThresholdError as error:
        raise_risk_threshold_error(error)