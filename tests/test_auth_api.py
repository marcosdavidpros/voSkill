import asyncio

import httpx
from api_helpers import MemoryDemandRepository
from conftest import app

from voskill.api.dependencies import get_authentication_service, get_session_codec
from voskill.authentication import AuthenticationFailed, PortalPrincipal
from voskill.main import (
    get_competency_repository,
    get_demand_repository,
    get_scenario_repository,
    get_skill_relation_repository,
)
from voskill.session import SessionCodec


class StubAuthenticationService:
    def __init__(self, principal: PortalPrincipal | None) -> None:
        self.principal = principal

    def authenticate(self, username: str, password: str) -> PortalPrincipal:
        if self.principal is None:
            raise AuthenticationFailed("Invalid credentials")
        return self.principal


class StubDemandRepository:
    def list_for_project(self, project_id: str) -> list[dict[str, object]]:
        return []

    def create(self, **_values: object) -> dict[str, object]:
        raise AssertionError("write must be denied before repository call")


class StubScenarioRepository:
    def get_competency_snapshot(self, _scenario_id: str) -> dict[str, object]:
        return {
            "project_id": "P-001",
            "snapshot": {
                "periods": {
                    "2026-11": {
                        "demand": {"SKILL-1": {"level": 3, "loadAmount": 10}},
                        "availability": {"P-001": {"hours": 20}},
                    }
                }
            },
        }


class StubCompetencyRepository:
    def list_for_person(self, _person_id: str) -> list[dict[str, object]]:
        return []


class StubSkillRelationRepository:
    def infer_for_person(self, _person_id: str, target_skill_id: str) -> dict[str, object]:
        return {
            "status": "insufficient_evidence",
            "target_skill_id": target_skill_id,
            "inferred_level": None,
            "source_skill_id": None,
            "relation_id": None,
            "confidence": None,
            "reason": "insufficient_evidence",
        }


def _request(
    method: str,
    path: str,
    payload: dict[str, object] | None = None,
    cookies: dict[str, str] | None = None,
) -> httpx.Response:
    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            if cookies:
                client.cookies.update(cookies)
            return await client.request(method, path, json=payload)

    return asyncio.run(send())


def test_protected_route_rejects_missing_session() -> None:
    response = _request("GET", "/scenarios/S-001/competency-map")

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTHENTICATION_REQUIRED"


def test_invalid_or_expired_session_is_rejected_by_protected_routes() -> None:
    principal = PortalPrincipal("A0091250", "Alex", None, True, False)
    current_codec = SessionCodec("x" * 32, max_age_seconds=60)
    valid_token = current_codec.encode(principal)
    token_payload, token_signature = valid_token.split(".")
    invalid_signature = f"{'A' if token_signature[0] != 'A' else 'B'}{token_signature[1:]}"
    invalid_token = f"{token_payload}.{invalid_signature}"
    expired_token = SessionCodec("x" * 32, max_age_seconds=60, clock=lambda: 0).encode(principal)
    app.dependency_overrides[get_session_codec] = lambda: current_codec
    try:
        invalid_response = _request(
            "GET",
            "/scenarios/S-001/competency-map",
            cookies={"voskill_session": invalid_token},
        )
        expired_response = _request(
            "GET",
            "/projects/P-001/demands",
            cookies={"voskill_session": expired_token},
        )
    finally:
        app.dependency_overrides.clear()

    for response in (invalid_response, expired_response):
        assert response.status_code == 401
        assert response.json()["detail"]["code"] == "AUTHENTICATION_REQUIRED"


def test_login_sets_http_only_cookie_and_me_returns_canonical_matricula() -> None:
    principal = PortalPrincipal("A0091250", "Alex", None, True, False)
    app.dependency_overrides[get_authentication_service] = lambda: StubAuthenticationService(principal)
    app.dependency_overrides[get_session_codec] = lambda: SessionCodec("x" * 32, max_age_seconds=60)
    try:
        login = _request("POST", "/auth/login", {"username": "a0091250", "password": "secret"})
        cookie = login.cookies.get("voskill_session")
        current = _request("GET", "/auth/me", cookies={"voskill_session": cookie})
    finally:
        app.dependency_overrides.clear()

    assert login.status_code == 204
    assert "httponly" in login.headers["set-cookie"].lower()
    assert "samesite=lax" in login.headers["set-cookie"].lower()
    assert cookie
    assert current.status_code == 200
    assert current.json() == {"actor_id": "A0091250", "can_view": True, "can_edit": False}


def test_invalid_credentials_do_not_issue_cookie() -> None:
    app.dependency_overrides[get_authentication_service] = lambda: StubAuthenticationService(None)
    app.dependency_overrides[get_session_codec] = lambda: SessionCodec("x" * 32, max_age_seconds=60)
    try:
        response = _request("POST", "/auth/login", {"username": "A0091250", "password": "wrong"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
    assert "set-cookie" not in response.headers


def test_view_only_session_allows_get_and_denies_post() -> None:
    principal = PortalPrincipal("A0091250", "Alex", None, True, False)
    app.dependency_overrides[get_authentication_service] = lambda: StubAuthenticationService(principal)
    app.dependency_overrides[get_session_codec] = lambda: SessionCodec("x" * 32, max_age_seconds=60)
    app.dependency_overrides[get_demand_repository] = StubDemandRepository
    try:
        login = _request("POST", "/auth/login", {"username": "A0091250", "password": "secret"})
        cookie = {"voskill_session": login.cookies["voskill_session"]}
        read_response = _request("GET", "/projects/P-001/demands", cookies=cookie)
        write_response = _request(
            "POST",
            "/projects/P-001/demands",
            {"skill_id": "SKILL-1", "proficiency_level": 3, "period": "2026-11", "load_amount": 10, "load_unit": "hours"},
            cookies=cookie,
        )
    finally:
        app.dependency_overrides.clear()

    assert read_response.status_code == 200
    assert write_response.status_code == 403


def test_view_only_portal_session_can_load_competency_map() -> None:
    principal = PortalPrincipal("A0091250", "Alex", None, True, False)
    app.dependency_overrides[get_authentication_service] = lambda: StubAuthenticationService(principal)
    app.dependency_overrides[get_session_codec] = lambda: SessionCodec("x" * 32, max_age_seconds=60)
    app.dependency_overrides[get_scenario_repository] = StubScenarioRepository
    app.dependency_overrides[get_competency_repository] = StubCompetencyRepository
    app.dependency_overrides[get_skill_relation_repository] = StubSkillRelationRepository
    try:
        login = _request("POST", "/auth/login", {"username": "A0091250", "password": "secret"})
        response = _request(
            "GET",
            "/scenarios/S-001/competency-map",
            cookies={"voskill_session": login.cookies["voskill_session"]},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["project_id"] == "P-001"


def test_edit_session_attributes_new_demand_to_canonical_matricula() -> None:
    principal = PortalPrincipal("A0091250", "Alex", None, True, True)
    repository = MemoryDemandRepository()
    app.dependency_overrides[get_authentication_service] = lambda: StubAuthenticationService(principal)
    app.dependency_overrides[get_session_codec] = lambda: SessionCodec("x" * 32, max_age_seconds=60)
    app.dependency_overrides[get_demand_repository] = lambda: repository
    try:
        login = _request("POST", "/auth/login", {"username": "A0091250", "password": "secret"})
        response = _request(
            "POST",
            "/projects/P-001/demands",
            {"skill_id": "SKILL-1", "proficiency_level": 3, "period": "2026-11", "load_amount": 10, "load_unit": "hours"},
            cookies={"voskill_session": login.cookies["voskill_session"]},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["actor_id"] == "A0091250"
    assert repository.rows[0]["actor_id"] == "A0091250"


def test_logout_clears_session_cookie() -> None:
    response = _request("POST", "/auth/logout", cookies={"voskill_session": "invalid"})

    assert response.status_code == 204
    assert "max-age=0" in response.headers["set-cookie"].lower()
