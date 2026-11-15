from __future__ import annotations

import logging
import ssl
from urllib.parse import urlsplit

import ldap3
from ldap3.core.exceptions import LDAPException

from .auth_errors import AuthenticationUnavailable


class LDAPAuthenticator:
    def __init__(
        self,
        url: str,
        *,
        user_prefix: str | None = None,
        domain: str | None = None,
        ca_cert_file: str | None = None,
        timeout: float = 10,
        connect_timeout: float | None = None,
        follow_referrals: bool = False,
    ) -> None:
        parsed_url = urlsplit(url)
        scheme = parsed_url.scheme.lower()
        if scheme not in {"ldap", "ldaps"} or not parsed_url.hostname:
            raise ValueError("LDAP_URL must use ldap:// or ldaps:// with a hostname")
        if parsed_url.path not in {"", "/"} or parsed_url.query or parsed_url.fragment:
            raise ValueError("LDAP_URL must not contain a path, query or fragment")
        self._host = parsed_url.hostname
        self._use_ssl = scheme == "ldaps"
        self._port = parsed_url.port or (636 if self._use_ssl else 389)
        self._user_prefix = domain if domain is not None else user_prefix
        if not self._user_prefix:
            raise ValueError("LDAP_DOMAIN is required")
        self._ca_cert_file = ca_cert_file or None
        self._timeout = timeout
        self._connect_timeout = connect_timeout if connect_timeout is not None else timeout
        self._follow_referrals = follow_referrals

    def authenticate(self, matricula: str, password: str) -> bool:
        matricula = matricula.strip().upper()
        if not matricula or not password:
            return False
        if not self._use_ssl:
            logging.getLogger("voskill.auth").warning(
                "LDAP_URL uses unencrypted LDAP; credentials are not protected in transit"
            )
        server_options = {
            "port": self._port,
            "use_ssl": self._use_ssl,
            "connect_timeout": self._connect_timeout,
        }
        if self._use_ssl:
            server_options["tls"] = ldap3.Tls(
                validate=ssl.CERT_REQUIRED,
                ca_certs_file=self._ca_cert_file,
            )
        server = ldap3.Server(self._host, **server_options)
        connection = None
        try:
            connection = ldap3.Connection(
                server,
                user=f"{self._user_prefix}{matricula}",
                password=password,
                auto_bind=False,
                receive_timeout=self._timeout,
                auto_referrals=self._follow_referrals,
                raise_exceptions=False,
            )
            return bool(connection.bind())
        except LDAPException as error:
            raise AuthenticationUnavailable("LDAP service is unavailable") from error
        finally:
            if connection is not None:
                connection.unbind()
