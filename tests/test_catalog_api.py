import asyncio

import httpx
from conftest import app

from voskill.api.dependencies import get_catalog_repository, get_session_codec
from voskill.authentication import PortalPrincipal
from voskill.catalog import CatalogError
from voskill.session import SessionCodec


class MemoryCatalogRepository:
    def __init__(self) -> None:
        self.people = [{"person_id": "P-001", "display_name": "Alex"}]
        self.skills = [{"skill_id": "SKILL-1", "skill_name": "Python", "description": None}]

    def list_people(self) -> list[dict[str, object]]:
        return self.people.copy()

    def create_person(self, display_name: str) -> dict[str, object]:
        if not display_name.strip():
            raise CatalogError("REQUIRED_DISPLAY_NAME", 422)
        person = {"person_id": "P-NEW", "display_name": display_name}
        self.people.append(person)
        return person

    def list_skills(self) -> list[dict[str, object]]:
        return self.skills.copy()

    def create_skill(self, skill_name: str, description: str | None) -> dict[str, object]:
        if any(skill["skill_name"].casefold() == skill_name.strip().casefold() for skill in self.skills):
            raise CatalogError("SKILL_ALREADY_EXISTS", 409)
        skill = {"skill_id": "SKILL-NEW", "skill_name": skill_name, "description": description}
        self.skills.append(skill)
        return skill


def _request(
    method: str,
    path: str,
    *,
    principal: PortalPrincipal | None = None,
    payload: dict[str, object] | None = None,
    repository: MemoryCatalogRepository,
) -> httpx.Response:
    codec = SessionCodec("catalog-test-secret-0123456789-abcdef", max_age_seconds=300)
    token = codec.encode(principal) if principal is not None else None

    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            if token is not None:
                client.cookies.set("voskill_session", token)
            return await client.request(method, path, json=payload)

    app.dependency_overrides[get_session_codec] = lambda: codec
    app.dependency_overrides[get_catalog_repository] = lambda: repository
    try:
        return asyncio.run(send())
    finally:
        app.dependency_overrides.clear()


def test_catalog_lists_and_editor_creates_people_and_skills() -> None:
    repository = MemoryCatalogRepository()
    editor = PortalPrincipal("A0091250", "Alex", None, True, True)
    viewer = PortalPrincipal("A0091251", "Bea", None, True, False)

    people = _request("GET", "/people", principal=viewer, repository=repository)
    skills = _request("GET", "/skills", principal=viewer, repository=repository)
    person = _request(
        "POST", "/people", principal=editor,
        payload={"display_name": "Sam"}, repository=repository,
    )
    skill = _request(
        "POST", "/skills", principal=editor,
        payload={"skill_name": "Kubernetes", "description": "Orquestração"},
        repository=repository,
    )

    assert people.status_code == 200
    assert people.json() == [{"person_id": "P-001", "display_name": "Alex"}]
    assert skills.status_code == 200
    assert skills.json()[0]["skill_id"] == "SKILL-1"
    assert person.status_code == 201
    assert person.json() == {"person_id": "P-NEW", "display_name": "Sam"}
    assert skill.status_code == 201
    assert skill.json()["skill_id"] == "SKILL-NEW"


def test_viewer_cannot_create_catalog_records() -> None:
    repository = MemoryCatalogRepository()
    viewer = PortalPrincipal("A0091251", "Bea", None, True, False)

    person = _request(
        "POST", "/people", principal=viewer,
        payload={"display_name": "Unauthorized"}, repository=repository,
    )
    skill = _request(
        "POST", "/skills", principal=viewer,
        payload={"skill_name": "Unauthorized"}, repository=repository,
    )

    assert person.status_code == 403
    assert skill.status_code == 403
    assert len(repository.people) == 1
    assert len(repository.skills) == 1


def test_catalog_lists_require_session_before_repository_access() -> None:
    class CountingCatalogRepository(MemoryCatalogRepository):
        def __init__(self) -> None:
            super().__init__()
            self.list_calls = 0

        def list_people(self) -> list[dict[str, object]]:
            self.list_calls += 1
            return super().list_people()

        def list_skills(self) -> list[dict[str, object]]:
            self.list_calls += 1
            return super().list_skills()

    repository = CountingCatalogRepository()
    people = _request("GET", "/people", repository=repository)
    skills = _request("GET", "/skills", repository=repository)

    assert people.status_code == 401
    assert people.json()["detail"]["code"] == "AUTHENTICATION_REQUIRED"
    assert skills.status_code == 401
    assert skills.json()["detail"]["code"] == "AUTHENTICATION_REQUIRED"
    assert repository.list_calls == 0


def test_catalog_rejects_blank_person_and_duplicate_skill() -> None:
    repository = MemoryCatalogRepository()
    editor = PortalPrincipal("A0091250", "Alex", None, True, True)

    blank_person = _request(
        "POST", "/people", principal=editor,
        payload={"display_name": "   "}, repository=repository,
    )
    duplicate_skill = _request(
        "POST", "/skills", principal=editor,
        payload={"skill_name": "  python  "}, repository=repository,
    )

    assert blank_person.status_code == 422
    assert blank_person.json()["detail"]["code"] == "REQUIRED_DISPLAY_NAME"
    assert duplicate_skill.status_code == 409
    assert duplicate_skill.json()["detail"]["code"] == "SKILL_ALREADY_EXISTS"
    assert len(repository.people) == 1
    assert len(repository.skills) == 1


def test_catalog_allows_skill_without_description() -> None:
    repository = MemoryCatalogRepository()
    editor = PortalPrincipal("A0091250", "Alex", None, True, True)

    response = _request(
        "POST", "/skills", principal=editor,
        payload={"skill_name": "Terraform"}, repository=repository,
    )

    assert response.status_code == 201
    assert response.json()["skill_name"] == "Terraform"
    assert response.json()["description"] is None


def test_catalog_endpoints_require_a_session() -> None:
    repository = MemoryCatalogRepository()

    people = _request("GET", "/people", repository=repository)
    skill = _request("POST", "/skills", payload={"skill_name": "Rust"}, repository=repository)

    assert people.status_code == 401
    assert people.json()["detail"]["code"] == "AUTHENTICATION_REQUIRED"
    assert skill.status_code == 401
    assert skill.json()["detail"]["code"] == "AUTHENTICATION_REQUIRED"
    assert len(repository.people) == 1
    assert len(repository.skills) == 1


def test_catalog_validation_rejects_empty_and_overlong_names() -> None:
    repository = MemoryCatalogRepository()
    editor = PortalPrincipal("A0091250", "Alex", None, True, True)

    empty_person = _request(
        "POST", "/people", principal=editor,
        payload={"display_name": ""}, repository=repository,
    )
    overlong_person = _request(
        "POST", "/people", principal=editor,
        payload={"display_name": "P" * 201}, repository=repository,
    )
    empty_skill = _request(
        "POST", "/skills", principal=editor,
        payload={"skill_name": ""}, repository=repository,
    )
    overlong_skill = _request(
        "POST", "/skills", principal=editor,
        payload={"skill_name": "S" * 151}, repository=repository,
    )
    overlong_description = _request(
        "POST", "/skills", principal=editor,
        payload={"skill_name": "Go", "description": "D" * 1001}, repository=repository,
    )

    assert empty_person.status_code == 422
    assert empty_person.json()["detail"]["fieldErrors"] == {"display_name": "INVALID_FIELD"}
    assert overlong_person.status_code == 422
    assert overlong_person.json()["detail"]["fieldErrors"] == {"display_name": "INVALID_FIELD"}
    assert empty_skill.status_code == 422
    assert empty_skill.json()["detail"]["fieldErrors"] == {"skill_name": "INVALID_FIELD"}
    assert overlong_skill.status_code == 422
    assert overlong_skill.json()["detail"]["fieldErrors"] == {"skill_name": "INVALID_FIELD"}
    assert overlong_description.status_code == 422
    assert overlong_description.json()["detail"]["fieldErrors"] == {"description": "INVALID_FIELD"}
    assert len(repository.people) == 1
    assert len(repository.skills) == 1
