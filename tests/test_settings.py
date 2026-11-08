import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import cast

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from voskill.config import OracleConfigurationError, load_settings


class OracleEnvironmentTemplateTests(unittest.TestCase):
    def test_example_declares_oracle_connection_fields(self) -> None:
        template = ROOT / ".env.example"

        self.assertTrue(template.is_file(), ".env.example must exist")
        keys = {
            line.split("=", maxsplit=1)[0]
            for line in template.read_text(encoding="utf-8").splitlines()
            if line and not line.startswith("#") and "=" in line
        }

        self.assertTrue({"ORACLE_USER", "ORACLE_PASSWORD", "ORACLE_DSN"} <= keys)

    def test_local_env_file_is_ignored_by_git(self) -> None:
        ignored_patterns = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()

        self.assertIn(".env", ignored_patterns)

    def test_environment_overrides_values_from_env_file(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            env_file = Path(temporary_directory) / ".env"
            env_file.write_text(
                "ORACLE_USER=file_user\n"
                "ORACLE_PASSWORD=file_password\n"
                "ORACLE_DSN=file_dsn\n",
                encoding="utf-8",
            )

            settings = load_settings(env_file, {"ORACLE_USER": "environment_user"})

        self.assertEqual(settings.oracle_user, "environment_user")
        self.assertEqual(settings.oracle_password, "file_password")
        self.assertEqual(settings.oracle_dsn, "file_dsn")

    def test_missing_configuration_reports_only_missing_field_names(self) -> None:
        settings = load_settings(Path("missing.env"), {})

        with self.assertRaises(OracleConfigurationError) as raised:
            settings.require_oracle()

        self.assertEqual(
            set(cast(OracleConfigurationError, raised.exception).missing_fields),
            {"ORACLE_USER", "ORACLE_PASSWORD", "ORACLE_DSN"},
        )


if __name__ == "__main__":
    unittest.main()