from typing import Annotated

from fastapi import APIRouter, Depends, Request

from ...competencies import CompetencyRepository
from ...competency_map import build_competency_map
from ...scenario_comparison import ScenarioError
from ...scenarios import ScenarioRepository
from ...skill_relations import SkillRelationRepository
from ..dependencies import (
    get_actor_id,
    get_competency_repository,
    get_scenario_repository,
    get_skill_relation_repository,
    require_scenario_people_access,
)
from ..errors import raise_scenario_error
from ..schemas import CompetencyMapResponse

router = APIRouter()


@router.get(
    "/scenarios/{scenario_id}/competency-map",
    response_model=CompetencyMapResponse,
)
def get_scenario_competency_map(
    scenario_id: str,
    actor_id: Annotated[str, Depends(get_actor_id)],
    request: Request,
    scenario_repository: Annotated[ScenarioRepository, Depends(get_scenario_repository)],
    competency_repository: Annotated[CompetencyRepository, Depends(get_competency_repository)],
    relation_repository: Annotated[SkillRelationRepository, Depends(get_skill_relation_repository)],
) -> dict[str, object]:
    try:
        scenario = scenario_repository.get_competency_snapshot(scenario_id)
        periods = scenario["snapshot"]["periods"]
        person_ids = sorted(
            {
                str(person_id)
                for assumptions in periods.values()
                if isinstance(assumptions, dict)
                for period in (assumptions,)
                for person_id in period.get("availability", {})
            }
        )
        require_scenario_people_access(
            request=request,
            actor_id=actor_id,
            scenario_id=scenario_id,
            project_id=str(scenario["project_id"]),
            person_ids=set(person_ids),
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

        return build_competency_map(
            scenario_id=scenario_id,
            project_id=str(scenario["project_id"]),
            snapshot=scenario["snapshot"],
            confirmed_by_person=confirmed_by_person,
            inferences=inferences,
        )
    except ScenarioError as error:
        raise_scenario_error(error)