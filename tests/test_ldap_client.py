import ssl
from pathlib import Path
from unittest.mock import Mock

from dotenv import dotenv_values

from voskill.ldap_client import LDAPAuthenticator, ldap3


def test_ldap_url_uses_plain_bind_when_portal_url_is_ldap(monkeypatch) -> None:
    server = Mock()
    connection = Mock()
    connection.bind.return_value = True
    monkeypatch.setattr(ldap3, "Server", Mock(return_value=server))
    monkeypatch.setattr(ldap3, "Connection", Mock(return_value=connection))

    authenticated = LDAPAuthenticator(
        "ldap://ldap.example.invalid:389",
        domain="EMPRESA\\",
    ).authenticate("a0091250", "secret")

    assert authenticated is True
    ldap3.Server.assert_called_once_with(
        "ldap.example.invalid",
        port=389,
        use_ssl=False,
        connect_timeout=10,
    )
    ldap3.Connection.assert_called_once_with(
        server,
        user="EMPRESA\\A0091250",
        password="secret",
        auto_bind=False,
        receive_timeout=10,
        auto_referrals=False,
        raise_exceptions=False,
    )
    connection.unbind.assert_called_once()


def test_plain_ldap_example_warns_about_unencrypted_credentials() -> None:
    example = Path(__file__).resolve().parents[1] / ".env.example"
    contents = example.read_text(encoding="utf-8").lower()

    assert "ldap://ldap.example.invalid:389" in contents
    assert "credentials are sent without transport encryption" in contents
    assert dotenv_values(example)["LDAP_FOLLOW_REFERRALS"] == "false"


def test_ldaps_bind_requires_validated_tls_and_does_not_trim_password(monkeypatch) -> None:
    tls = Mock()
    server = Mock()
    connection = Mock()
    connection.bind.return_value = True
    monkeypatch.setattr(ldap3, "Tls", Mock(return_value=tls))
    monkeypatch.setattr(ldap3, "Server", Mock(return_value=server))
    connection_factory = Mock(return_value=connection)
    monkeypatch.setattr(ldap3, "Connection", connection_factory)

    authenticated = LDAPAuthenticator(
        "ldaps://ldap.example.invalid:636",
        user_prefix="corp\\",
        ca_cert_file="C:/certs/corp-ca.pem",
    ).authenticate("a0091250", " pass with spaces ")

    assert authenticated is True
    ldap3.Tls.assert_called_once_with(
        validate=ssl.CERT_REQUIRED,
        ca_certs_file="C:/certs/corp-ca.pem",
    )
    ldap3.Server.assert_called_once_with(
        "ldap.example.invalid",
        port=636,
        use_ssl=True,
        tls=tls,
        connect_timeout=10,
    )
    connection_factory.assert_called_once_with(
        server,
        user="corp\\A0091250",
        password=" pass with spaces ",
        auto_bind=False,
        receive_timeout=10,
        auto_referrals=False,
        raise_exceptions=False,
    )
    connection.unbind.assert_called_once()


def test_ldap_configuration_uses_portal_domain_timeouts_and_referral_setting(monkeypatch) -> None:
    monkeypatch.setenv("LDAP_URL", "ldaps://ldap.example.invalid:636")
    monkeypatch.setenv("LDAP_DOMAIN", "EMPRESA\\")
    monkeypatch.setenv("LDAP_USER_PREFIX", "legacy\\")
    monkeypatch.setenv("LDAP_TIMEOUT", "15000")
    monkeypatch.setenv("LDAP_CONNECT_TIMEOUT", "2500")
    monkeypatch.setenv("LDAP_FOLLOW_REFERRALS", "false")
    tls = Mock()
    server = Mock()
    connection = Mock()
    connection.bind.return_value = True
    monkeypatch.setattr(ldap3, "Tls", Mock(return_value=tls))
    monkeypatch.setattr(ldap3, "Server", Mock(return_value=server))
    connection_factory = Mock(return_value=connection)
    monkeypatch.setattr(ldap3, "Connection", connection_factory)

    from voskill.authentication import create_authentication_service

    service = create_authentication_service()
    assert service._ldap.authenticate("a0091250", "secret")

    ldap3.Server.assert_called_once_with(
        "ldap.example.invalid",
        port=636,
        use_ssl=True,
        tls=tls,
        connect_timeout=2.5,
    )
    connection_factory.assert_called_once_with(
        server,
        user="EMPRESA\\A0091250",
        password="secret",
        auto_bind=False,
        receive_timeout=15,
        auto_referrals=False,
        raise_exceptions=False,
    )
