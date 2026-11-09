import oracledb

from .config import OracleCredentials, load_settings


def open_oracle_connection(
    credentials: OracleCredentials | None = None,
) -> oracledb.Connection:
    connection_details = credentials or load_settings().require_oracle()
    return oracledb.connect(
        user=connection_details.user,
        password=connection_details.password,
        dsn=connection_details.dsn,
    )