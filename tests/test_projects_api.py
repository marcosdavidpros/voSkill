
from conftest import _request

from voskill.api.dependencies import get_project_repository
from voskill.main import app, get_actor_id


class MemoryProjectRepository:
    def __init__(self) -> None:
        self.projects: list[dict[str, object]] = []

    def list_projects(self) -> list[dict[str, object]]:
        return self.projects.copy()

    def create_project(self, **values: object) -> dict[str, object]:
        project = {
            "project_id": "PRJ-001",
            "project_name": values["project_name"],
            "horizon_start": values["horizon_start"].isoformat(),
            "horizon_end": values["horizon_end"].isoformat(),
            "load_unit": values["load_unit"],
        }
        self.projects.append(project)
        return project


def test_authenticated_user_lists_and_creates_projects() -> None:
    repository = MemoryProjectRepository()
    app.dependency_overrides[get_actor_id] = lambda: "A0091250"
    app.dependency_overrides[get_project_repository] = lambda: repository
    try:
        created = _request(
            "POST",
            "/projects",
            {
                "project_name": "Atlas",
                "horizon_start": "2026-01-01",
                "horizon_end": "2026-12-01",
                "load_unit": "hours",
            },
        )
        listed = _request("GET", "/projects")
    finally:
        app.dependency_overrides.clear()

    assert created.status_code == 201
    assert created.json() == {
        "project_id": "PRJ-001",
        "project_name": "Atlas",
        "horizon_start": "2026-01-01",
        "horizon_end": "2026-12-01",
        "load_unit": "hours",
    }
    assert listed.status_code == 200
    assert listed.json() == [created.json()]


def test_invalid_project_horizon_and_load_unit_are_rejected() -> None:
    repository = MemoryProjectRepository()
    app.dependency_overrides[get_actor_id] = lambda: "A0091250"
    app.dependency_overrides[get_project_repository] = lambda: repository
    try:
        invalid_start = _request(
            "POST",
            "/projects",
            {"project_name": "Invalid", "horizon_start": "2026-01-02", "horizon_end": "2026-12-01", "load_unit": "hours"},
        )
        invalid_unit = _request(
            "POST",
            "/projects",
            {"project_name": "Invalid", "horizon_start": "2026-01-01", "horizon_end": "2026-12-01", "load_unit": "points"},
        )
    finally:
        app.dependency_overrides.clear()

    assert invalid_start.status_code == 422
    assert invalid_unit.status_code == 422
    assert repository.projects == []
