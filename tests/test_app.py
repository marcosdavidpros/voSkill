import asyncio

import httpx
from fastapi.exceptions import RequestValidationError
from starlette.requests import Request

from voskill.api.routers import competencies as competencies_router
from voskill.api.routers import demands as demands_router
from voskill.api.routers import scenarios as scenarios_router
from voskill.api.routers import skill_relations as skill_relations_router
from voskill.api.routers import suggestions as suggestions_router
from voskill.main import app, handle_request_validation_error


def test_health_endpoint_does_not_require_oracle() -> None:
    async def get_health() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/health")

    response = asyncio.run(get_health())

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_competency_and_suggestion_routes_are_owned_by_domain_routers() -> None:
    expected_owners = {
        "/people/{person_id}/competencies": "voskill.api.routers.competencies",
        "/people/{person_id}/competencies/{competency_id}": "voskill.api.routers.competencies",
        "/people/{person_id}/skill-inference/{target_skill_id}": "voskill.api.routers.competencies",
        "/people/{person_id}/competency-suggestions/extract": "voskill.api.routers.suggestions",
        "/people/{person_id}/competency-suggestions/{suggestion_id}/review": "voskill.api.routers.suggestions",
    }
    routes = [*competencies_router.routes, *suggestions_router.routes]
    openapi_paths = app.openapi()["paths"]

    for path, owner in expected_owners.items():
        matching_routes = [route for route in routes if route.path == path]
        assert path in openapi_paths
        assert all(route.endpoint.__module__ == owner for route in matching_routes)

def test_demand_scenario_and_relation_routes_are_owned_by_domain_routers() -> None:
    expected_owners = {
        "/projects/{project_id}/demands": "voskill.api.routers.demands",
        "/projects/{project_id}/demands/{demand_id}": "voskill.api.routers.demands",
        "/scenarios/{base_scenario_id}/alternatives": "voskill.api.routers.scenarios",
        "/scenarios/{first_scenario_id}/compare/{second_scenario_id}": "voskill.api.routers.scenarios",
        "/skill-relations": "voskill.api.routers.skill_relations",
    }
    routers = [demands_router, scenarios_router, skill_relations_router]
    routes = [route for router in routers for route in router.routes]
    openapi_paths = app.openapi()["paths"]

    for path, owner in expected_owners.items():
        matching_routes = [route for route in routes if route.path == path]
        assert path in openapi_paths
        assert matching_routes
        assert all(route.endpoint.__module__ == owner for route in matching_routes)

def test_validation_handler_reports_leaf_field_for_nested_location() -> None:
    error = RequestValidationError(
        [
            {
                "loc": ("body", "competency", "evidence"),
                "msg": "Field required",
                "type": "missing",
            }
        ]
    )
    request = Request({"type": "http", "headers": []})

    response = asyncio.run(handle_request_validation_error(request, error))

    assert response.status_code == 422
    assert b'"evidence":"REQUIRED_EVIDENCE"' in response.body