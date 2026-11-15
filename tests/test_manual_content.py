from pathlib import Path

MANUAL = Path(__file__).resolve().parents[1] / "docs" / "MANUAL_TESTE_MVP.md"


def test_manual_documents_setup_and_configuration() -> None:
    text = MANUAL.read_text(encoding="utf-8")
    required = (
        "--env-file .env",
        "npm run dev --prefix frontend",
        "LDAP_URL",
        "LDAP_DOMAIN",
        "PORTAL_ORACLE_DSN",
        "VOSKILL_SESSION_SECRET",
    )
    assert all(item in text for item in required)


def test_manual_contains_end_to_end_example_data() -> None:
    text = MANUAL.read_text(encoding="utf-8")
    required = (
        "P-001",
        "SKILL-1",
        "PRJ-001",
        "SCN-001",
        "2026-01",
        "seed 42",
        "população 20",
        "12 gerações",
    )
    assert all(item in text for item in required)


def test_manual_explains_errors_and_optional_ai() -> None:
    text = MANUAL.read_text(encoding="utf-8")
    required = (
        "401",
        "403",
        "422",
        "503",
        "não precisam de token",
    )
    assert all(item in text for item in required)