from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from .api.dependencies import (
    get_actor_id,
    get_competency_extractor,
    get_competency_repository,
    get_demand_repository,
    get_optimization_run_repository,
    get_risk_threshold_repository,
    get_scenario_repository,
    get_skill_relation_repository,
    get_suggestion_repository,
)
from .api.errors import handle_request_validation_error
from .api.routers import competencies as competencies_router
from .api.routers import competency_map as competency_map_router
from .api.routers import demands as demands_router
from .api.routers import optimization_runs as optimization_runs_router
from .api.routers import risk_panel as risk_panel_router
from .api.routers import scenarios as scenarios_router
from .api.routers import skill_relations as skill_relations_router
from .api.routers import suggestions as suggestions_router

__all__ = [
    "app",
    "get_actor_id",
    "get_competency_extractor",
    "get_competency_repository",
    "get_demand_repository",
    "get_optimization_run_repository",
    "get_risk_threshold_repository",
    "get_scenario_repository",
    "get_skill_relation_repository",
    "get_suggestion_repository",
    "handle_request_validation_error",
]

app = FastAPI(title="voSkill API")
app.add_exception_handler(RequestValidationError, handle_request_validation_error)
app.include_router(competencies_router)
app.include_router(competency_map_router)
app.include_router(demands_router)
app.include_router(optimization_runs_router)
app.include_router(risk_panel_router)
app.include_router(scenarios_router)
app.include_router(skill_relations_router)
app.include_router(suggestions_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
