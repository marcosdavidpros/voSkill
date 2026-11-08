from unittest.mock import patch

from voskill.config import OracleCredentials
from voskill.database import open_oracle_connection


def test_open_oracle_connection_uses_explicit_credentials() -> None:
    credentials = OracleCredentials(
        user="app_user",
        password="secret",
        dsn="//db.example:1521/service",
    )
    connection = object()

    with patch("voskill.database.oracledb.connect", return_value=connection) as connect:
        result = open_oracle_connection(credentials)

    assert result is connection
    connect.assert_called_once_with(
        user="app_user",
        password="secret",
        dsn="//db.example:1521/service",
    )