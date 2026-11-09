import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_initial_oracle_schema_contains_core_entities_and_constraints() -> None:
    schema_file = ROOT / "database" / "oracle" / "001_initial_schema.sql"

    assert schema_file.is_file()
    ddl = schema_file.read_text(encoding="utf-8").upper()

    for table in (
        "VSK_PERSONS",
        "VSK_SKILLS",
        "VSK_PERSON_COMPETENCIES",
        "VSK_PERSON_COMPETENCY_HISTORY",
        "VSK_PROJECTS",
        "VSK_PROJECT_DEMANDS",
    ):
        assert re.search(rf"CREATE\s+TABLE\s+{table}\b", ddl)

    created_names = re.findall(
        r"^\s*CREATE\s+(?:OR\s+REPLACE\s+)?(?:TABLE|INDEX|TRIGGER)\s+([A-Z0-9_]+)",
        ddl,
        flags=re.MULTILINE,
    )
    constraint_names = re.findall(r"\bCONSTRAINT\s+([A-Z0-9_]+)", ddl)
    referenced_tables = re.findall(r"\bREFERENCES\s+([A-Z0-9_]+)", ddl)

    assert created_names
    assert all(name.startswith("VSK_") for name in created_names)
    assert all(name.startswith("VSK_") for name in constraint_names)
    assert all(name.startswith("VSK_") for name in referenced_tables)
    assert all(len(name) <= 30 for name in (*created_names, *constraint_names))
    assert "FOREIGN KEY" in ddl
    assert "CHECK" in ddl
    assert "VSK_TRG_PROJECT_DEMAND_HORIZON" in ddl
    assert "SESSION_USER" in ddl
    assert "ITB2CTRF" in ddl
    assert ddl.index("SESSION_USER") < ddl.index("CREATE TABLE")
    assert "-20010" in ddl
    assert not re.search(r"\bDROP\s+(TABLE|TRIGGER|SEQUENCE)\b", ddl)


def test_oracle_owner_is_documented_without_changing_local_credentials() -> None:
    env_template = (ROOT / ".env.example").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert re.search(r"^ORACLE_USER=ITB2CTRF$", env_template, flags=re.MULTILINE)
    assert "sqlplus ITB2CTRF@" in readme


def test_scenario_migration_preserves_immutable_snapshots() -> None:
    migration_file = ROOT / "database" / "oracle" / "002_scenarios.sql"

    assert migration_file.is_file()
    ddl = migration_file.read_text(encoding="utf-8").upper()

    assert re.search(r"CREATE\s+TABLE\s+VSK_SCENARIO_SNAPSHOTS\b", ddl)
    assert re.search(r"CREATE\s+TABLE\s+VSK_SCENARIOS\b", ddl)
    assert "SNAPSHOT_JSON IS JSON" in ddl
    assert "DELTAS_JSON IS JSON" in ddl
    assert "VSK_TRG_SCN_SNAPSHOT_IMM" in ddl
    assert "-20020" in ddl
    assert "SESSION_USER" in ddl
    assert "ITB2CTRF" in ddl

    created_names = re.findall(
        r"^\s*CREATE\s+(?:OR\s+REPLACE\s+)?(?:TABLE|INDEX|TRIGGER)\s+([A-Z0-9_]+)",
        ddl,
        flags=re.MULTILINE,
    )
    constraint_names = re.findall(r"\bCONSTRAINT\s+([A-Z0-9_]+)", ddl)
    assert created_names
    assert all(name.startswith("VSK_") for name in (*created_names, *constraint_names))
    assert all(len(name) <= 30 for name in (*created_names, *constraint_names))
    assert not re.search(r"\bDROP\s+(TABLE|TRIGGER|SEQUENCE)\b", ddl)


def test_suggestion_migration_stores_evidence_not_full_source() -> None:
    migration_file = ROOT / "database" / "oracle" / "003_competency_suggestions.sql"

    assert migration_file.is_file()
    ddl = migration_file.read_text(encoding="utf-8").upper()

    assert re.search(r"CREATE\s+TABLE\s+VSK_SKILL_SUGGESTIONS\b", ddl)
    assert "SUGGESTED_SKILL_NAME" in ddl
    assert "SUGGESTED_LEVEL" in ddl
    assert "CONFIDENCE" in ddl
    assert "EVIDENCE_SPAN" in ddl
    assert "SOURCE_SHA256" in ddl
    assert "PENDING_REVIEW" in ddl
    assert "SOURCE_TEXT" not in ddl
    assert "SESSION_USER" in ddl
    assert "ITB2CTRF" in ddl
    assert not re.search(r"\bDROP\s+(TABLE|TRIGGER|SEQUENCE)\b", ddl)


def test_suggestion_review_migration_keeps_reviewed_values_and_competency_link() -> None:
    migration_file = ROOT / "database" / "oracle" / "004_suggestion_review.sql"

    assert migration_file.is_file()
    ddl = migration_file.read_text(encoding="utf-8").upper()

    assert re.search(r"ALTER\s+TABLE\s+VSK_SKILL_SUGGESTIONS\s+ADD", ddl)
    assert "REVIEWED_LEVEL" in ddl
    assert "REVIEWED_EVIDENCE" in ddl
    assert "COMPETENCY_ID" in ddl
    assert "VSK_FK_SUG_COMPETENCY" in ddl
    assert "VSK_CK_SUG_REVIEW_STATE" in ddl
    assert re.search(r"IF\s+UPPER\(L_SESSION_USER\)\s*<>\s*'ITB2CTRF'\s+THEN", ddl)
    assert re.search(
        r"L_EXISTING_COLUMNS\s*>\s*0\s+OR\s+L_EXISTING_CONSTRAINTS\s*>\s*0",
        ddl,
    )
    assert "-20010" in ddl
    assert "-20012" in ddl