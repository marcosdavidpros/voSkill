from unittest.mock import Mock

import pytest

from voskill.authentication import (
    AuthenticationFailed,
    AuthenticationService,
    PortalAuthorizationRepository,
    PortalPrincipal,
)
from voskill.session import InvalidSession, SessionCodec


def test_authentication_uses_canonical_matricula_and_preserves_password() -> None:
    ldap = Mock()
    ldap.authenticate.return_value = True
    principal = PortalPrincipal(
        actor_id="A0091250",
        display_name="Alex",
        email="alex@example.invalid",
        can_view=True,
        can_edit=False,
    )
    portal = Mock()
    portal.authorize.return_value = principal

    result = AuthenticationService(ldap, portal).authenticate(" a0091250 ", " p a s s ")

    ldap.authenticate.assert_called_once_with("A0091250", " p a s s ")
    portal.authorize.assert_called_once_with("A0091250")
    assert result == principal


def test_invalid_ldap_credentials_do_not_query_portal() -> None:
    ldap = Mock()
    ldap.authenticate.return_value = False
    portal = Mock()

    with pytest.raises(AuthenticationFailed):
        AuthenticationService(ldap, portal).authenticate("A0091250", "wrong")

    portal.authorize.assert_not_called()


def test_portal_user_without_active_voskill_view_permission_is_denied() -> None:
    ldap = Mock()
    ldap.authenticate.return_value = True
    portal = Mock()
    portal.authorize.return_value = None

    with pytest.raises(AuthenticationFailed):
        AuthenticationService(ldap, portal).authenticate("A0091250", "correct")


class _FakeCursor:
    def __init__(self) -> None:
        self.statements: list[tuple[str, dict[str, object]]] = []
        self.next_row: tuple[object, ...] | None = None

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def execute(self, statement: str, **binds: object) -> None:
        self.statements.append((statement, binds))
        if "FROM PARAM_USUARIOS" in statement:
            self.next_row = (42, "A0091250", "Alex", "alex@example.invalid")
        elif "FROM PARAM_TELAS T" in statement:
            self.next_row = (1, 0)
        else:
            self.next_row = None

    def fetchone(self):
        return self.next_row


class _FakeConnection:
    def __init__(self) -> None:
        self.cursor_value = _FakeCursor()
        self.committed = False
        self.closed = False

    def cursor(self):
        return self.cursor_value

    def commit(self) -> None:
        self.committed = True

    def close(self) -> None:
        self.closed = True


def test_portal_authorization_requires_active_user_profile_and_voskill_permission() -> None:
    connection = _FakeConnection()
    repository = PortalAuthorizationRepository(lambda: connection)

    principal = repository.authorize("A0091250")

    assert principal == PortalPrincipal(
        actor_id="A0091250",
        display_name="Alex",
        email="alex@example.invalid",
        can_view=True,
        can_edit=False,
    )
    assert len(connection.cursor_value.statements) == 3
    user_query, user_binds = connection.cursor_value.statements[0]
    assert "ATIVO = 'S'" in user_query
    assert user_binds == {"matricula": "A0091250"}
    permission_query, permission_binds = connection.cursor_value.statements[1]
    assert "PARAM_USUARIO_PERFIS" in permission_query
    assert "PARAM_PERFIL_TELAS" in permission_query
    assert "DATA_EXPIRACAO IS NULL" in permission_query
    assert permission_binds == {"user_id": 42, "screen_code": "VOSKILL"}
    assert connection.committed is True
    assert connection.closed is True


def test_session_codec_round_trips_permissions_and_rejects_tampering() -> None:
    codec = SessionCodec("s" * 32, max_age_seconds=300, clock=lambda: 1_000)
    principal = PortalPrincipal("A0091250", "Alex", None, True, False)

    token = codec.encode(principal)

    assert codec.decode(token) == PortalPrincipal("A0091250", "", None, True, False)
    payload, signature = token.split(".")
    invalid_signature = f"{'A' if signature[0] != 'A' else 'B'}{signature[1:]}"
    tampered = f"{payload}.{invalid_signature}"
    with pytest.raises(InvalidSession):
        codec.decode(tampered)


def test_session_codec_rejects_expired_cookie() -> None:
    current_time = [1_000]
    codec = SessionCodec("s" * 32, max_age_seconds=300, clock=lambda: current_time[0])
    token = codec.encode(PortalPrincipal("A0091250", "Alex", None, True, True))
    current_time[0] = 1_300

    with pytest.raises(InvalidSession):
        codec.decode(token)