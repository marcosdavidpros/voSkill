from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class OracleConfigurationError(ValueError):
    def __init__(self, missing_fields: tuple[str, ...]) -> None:
        self.missing_fields = missing_fields
        super().__init__(f"Missing Oracle configuration: {', '.join(missing_fields)}")


@dataclass(frozen=True, slots=True)
class OracleCredentials:
    user: str
    password: str
    dsn: str


@dataclass(frozen=True, slots=True)
class Settings:
    oracle_user: str | None
    oracle_password: str | None
    oracle_dsn: str | None

    def require_oracle(self) -> OracleCredentials:
        values = {
            "ORACLE_USER": self.oracle_user,
            "ORACLE_PASSWORD": self.oracle_password,
            "ORACLE_DSN": self.oracle_dsn,
        }
        missing_fields = tuple(name for name, value in values.items() if not value)
        if missing_fields:
            raise OracleConfigurationError(missing_fields)

        assert self.oracle_user is not None
        assert self.oracle_password is not None
        assert self.oracle_dsn is not None
        return OracleCredentials(
            user=self.oracle_user,
            password=self.oracle_password,
            dsn=self.oracle_dsn,
        )


def load_settings(
    env_file: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> Settings:
    file_values = dotenv_values(env_file or PROJECT_ROOT / ".env")
    values = {key: value for key, value in file_values.items() if value is not None}
    values.update(os.environ if environ is None else environ)

    def read_value(name: str) -> str | None:
        value = values.get(name)
        normalized = value.strip() if value else ""
        return normalized or None

    return Settings(
        oracle_user=read_value("ORACLE_USER"),
        oracle_password=read_value("ORACLE_PASSWORD"),
        oracle_dsn=read_value("ORACLE_DSN"),
    )