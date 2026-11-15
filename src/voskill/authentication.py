from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass

import oracledb

from .auth_errors import AuthenticationUnavailable
from .ldap_client import LDAPAuthenticator


class AuthenticationFailed(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class PortalPrincipal:
    actor_id: str
    display_name: str
    email: str | None
    can_view: bool
    can_edit: bool


class PortalAuthorizationRepository:
    def __init__(
        self,
        connection_factory: Callable[[], oracledb.Connection] | None = None,
    ) -> None:
        self._connection_factory = connection_factory or _open_portal_connection

    def authorize(self, matricula: str) -> PortalPrincipal | None:
        connection = self._connection_factory()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT ID, RE, NOME, EMAIL
                      FROM PARAM_USUARIOS
                     WHERE UPPER(TRIM(RE)) = :matricula
                       AND ATIVO = 'S'
                    """,
                    matricula=matricula,
                )
                user = cursor.fetchone()
                if user is None:
                    return None

                cursor.execute(
                    """
                    SELECT MAX(CASE WHEN PT.PODE_VISUALIZAR = 'S' THEN 1 ELSE 0 END),
                           MAX(CASE WHEN PT.PODE_EDITAR = 'S' THEN 1 ELSE 0 END)
                      FROM PARAM_TELAS T
                      JOIN PARAM_PERFIL_TELAS PT ON PT.TELA_ID = T.ID
                      JOIN PARAM_PERFIS P ON P.ID = PT.PERFIL_ID
                      JOIN PARAM_USUARIO_PERFIS UP ON UP.PERFIL_ID = P.ID
                     WHERE UP.USUARIO_ID = :user_id
                       AND UP.ATIVO = 'S'
                       AND P.ATIVO = 'S'
                       AND T.ATIVO = 'S'
                       AND (UP.DATA_EXPIRACAO IS NULL OR UP.DATA_EXPIRACAO > SYSDATE)
                       AND UPPER(TRIM(T.CODIGO)) = :screen_code
                    """,
                    user_id=user[0],
                    screen_code="VOSKILL",
                )
                permissions = cursor.fetchone()
                can_view = bool(permissions and permissions[0] == 1)
                can_edit = bool(can_view and permissions[1] == 1)
                if not can_view:
                    return None

                cursor.execute(
                    """
                    UPDATE PARAM_USUARIOS
                       SET ULTIMO_LOGIN = SYSDATE
                     WHERE ID = :user_id
                       AND ATIVO = 'S'
                    """,
                    user_id=user[0],
                )
                connection.commit()
                actor_id = str(user[1]).strip().upper()
                return PortalPrincipal(
                    actor_id=actor_id,
                    display_name=str(user[2]).strip(),
                    email=str(user[3]).strip() if user[3] else None,
                    can_view=can_view,
                    can_edit=can_edit,
                )
        except oracledb.Error as error:
            connection.rollback()
            raise AuthenticationUnavailable("Portal authorization database is unavailable") from error
        finally:
            connection.close()


class AuthenticationService:
    def __init__(
        self,
        ldap_authenticator: LDAPAuthenticator,
        portal_repository: PortalAuthorizationRepository,
    ) -> None:
        self._ldap = ldap_authenticator
        self._portal = portal_repository

    def authenticate(self, username: str, password: str) -> PortalPrincipal:
        matricula = username.strip().upper() if isinstance(username, str) else ""
        if not matricula or not isinstance(password, str) or not password:
            raise AuthenticationFailed("Invalid credentials")
        if not self._ldap.authenticate(matricula, password):
            raise AuthenticationFailed("Invalid credentials")

        principal = self._portal.authorize(matricula)
        if principal is None:
            raise AuthenticationFailed("Invalid credentials")
        return principal


def create_authentication_service() -> AuthenticationService:
    ldap_url = os.environ.get("LDAP_URL", "").strip()
    domain = os.environ.get("LDAP_DOMAIN")
    if domain is None:
        domain = os.environ.get("LDAP_USER_PREFIX", "")
    if not ldap_url or not domain:
        raise AuthenticationUnavailable("LDAP configuration is incomplete")
    try:
        timeout = _ldap_timeout_seconds("LDAP_TIMEOUT")
        connect_timeout = _ldap_timeout_seconds("LDAP_CONNECT_TIMEOUT")
        referrals_value = os.environ.get("LDAP_FOLLOW_REFERRALS", "false").strip().lower()
        if referrals_value not in {"true", "false"}:
            raise ValueError("LDAP_FOLLOW_REFERRALS must be true or false")
    except ValueError as error:
        raise AuthenticationUnavailable("LDAP connection configuration is invalid") from error
    return AuthenticationService(
        LDAPAuthenticator(
            ldap_url,
            domain=domain,
            ca_cert_file=os.environ.get("LDAP_CA_CERT"),
            timeout=timeout,
            connect_timeout=connect_timeout,
            follow_referrals=referrals_value == "true",
        ),
        PortalAuthorizationRepository(),
    )


def _ldap_timeout_seconds(variable: str, default_milliseconds: int = 10000) -> float:
    value = os.environ.get(variable, "").strip()
    milliseconds = int(value) if value else default_milliseconds
    if not 100 <= milliseconds <= 120000:
        raise ValueError(f"{variable} must be between 100 and 120000 milliseconds")
    return milliseconds / 1000


def _open_portal_connection() -> oracledb.Connection:
    values = {
        "PORTAL_ORACLE_USER": os.environ.get("PORTAL_ORACLE_USER"),
        "PORTAL_ORACLE_PASSWORD": os.environ.get("PORTAL_ORACLE_PASSWORD"),
        "PORTAL_ORACLE_DSN": os.environ.get("PORTAL_ORACLE_DSN"),
    }
    if any(not value for value in values.values()):
        raise AuthenticationUnavailable("Portal Oracle configuration is incomplete")
    try:
        return oracledb.connect(
            user=values["PORTAL_ORACLE_USER"],
            password=values["PORTAL_ORACLE_PASSWORD"],
            dsn=values["PORTAL_ORACLE_DSN"],
        )
    except oracledb.Error as error:
        raise AuthenticationUnavailable("Portal authorization database is unavailable") from error