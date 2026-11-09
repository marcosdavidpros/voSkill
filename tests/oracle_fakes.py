from datetime import UTC, date, datetime
from typing import Self


class FakeCursor:
    def __init__(self, demand_rows: list[tuple] | None = None) -> None:
        self.project = (date(2026, 1, 1), date(2026, 6, 1), "hours")
        self.person_exists = True
        self.current_competency: tuple | None = (
            "C-001",
            "SKILL-1",
            4,
            "Old evidence",
            "MANUAL",
        )
        self.base_scenario = ("B-001", "P-001", "S-001")
        self.skill_exists = True
        self.skill_ids = {"SKILL-1"}
        self.demand_rows = demand_rows or []
        self.statements: list[tuple[str, dict]] = []
        self.current_one = None
        self.current_rows: list[tuple] = []
        self.insert_params: dict | None = None
        self.update_params: dict | None = None
        self.scenario_insert_params: dict | None = None
        self.scenario_records: list[tuple] = []
        self.competency_rows: list[tuple] = []
        self.competency_insert_params: dict | None = None
        self.suggestion_insert_params: dict | None = None
        self.suggestion_record: tuple | None = (
            "SG-001",
            "P-001",
            "Kubernetes",
            4,
            0.92,
            "Migração do cluster Kubernetes",
            "a" * 64,
            "PENDING_REVIEW",
            "U-001",
            datetime(2026, 11, 8, tzinfo=UTC),
        )
        self.suggestion_update_params: dict | None = None
        self.skill_insert_params: dict | None = None
        self.competency_update_params: dict | None = None
        self.history_insert_params: dict | None = None
        self.relation_insert_params: dict | None = None
        self.inference_record: tuple | None = None
        self.rowcount = 1

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, statement: str, parameters: dict | None = None, **kwargs: object) -> None:
        bound = dict(parameters or {})
        bound.update(kwargs)
        normalized = " ".join(statement.upper().split())
        self.statements.append((normalized, bound))

        if "FROM VSK_PROJECTS" in normalized:
            self.current_one = self.project
        elif "JOIN VSK_SKILLS" in normalized and "VSK_PERSON_COMPETENCIES" in normalized:
            self.current_rows = self.competency_rows
        elif "FROM VSK_PERSONS" in normalized:
            self.current_one = (bound.get("person_id"),) if self.person_exists else None
        elif "FROM VSK_SKILL_SUGGESTIONS" in normalized:
            self.current_one = self.suggestion_record
        elif "FROM VSK_SKILL_RELATIONS" in normalized:
            self.current_one = (
                self.inference_record
                if "VSK_PERSON_COMPETENCIES" in normalized
                else None
            )
        elif "FROM VSK_PERSON_COMPETENCIES" in normalized:
            if normalized.startswith("SELECT COMPETENCY_ID FROM"):
                self.current_one = None
            elif normalized.startswith("SELECT COMPETENCY_ID, PROFICIENCY_LEVEL"):
                self.current_one = (
                    (self.current_competency[0], self.current_competency[2], self.current_competency[3])
                    if self.current_competency is not None
                    else None
                )
            else:
                self.current_one = self.current_competency
        elif "FROM VSK_SKILLS" in normalized:
            skill_id = bound.get("skill_id")
            self.current_one = (
                (skill_id, "Kubernetes" if skill_id == "SKILL-1" else "OpenShift")
                if self.skill_exists and skill_id in self.skill_ids
                else None
            )
        elif normalized.startswith("SELECT DEMAND_ID"):
            self.current_rows = self.demand_rows
        elif normalized.startswith("INSERT INTO VSK_PROJECT_DEMANDS"):
            self.insert_params = bound
        elif normalized.startswith("UPDATE VSK_PROJECT_DEMANDS"):
            self.update_params = bound
        elif normalized.startswith("INSERT INTO VSK_PERSON_COMPETENCIES"):
            self.competency_insert_params = bound
        elif normalized.startswith("INSERT INTO VSK_SKILL_SUGGESTIONS"):
            self.suggestion_insert_params = bound
        elif normalized.startswith("INSERT INTO VSK_SKILL_RELATIONS"):
            self.relation_insert_params = bound
        elif normalized.startswith("UPDATE VSK_SKILL_SUGGESTIONS"):
            self.suggestion_update_params = bound
        elif normalized.startswith("INSERT INTO VSK_SKILLS"):
            self.skill_insert_params = bound
        elif normalized.startswith("UPDATE VSK_SKILL_SUGGESTIONS"):
            self.suggestion_update_params = bound
        elif normalized.startswith("INSERT INTO VSK_SKILLS"):
            self.skill_insert_params = bound
        elif normalized.startswith("UPDATE VSK_PERSON_COMPETENCIES"):
            self.competency_update_params = bound
        elif normalized.startswith("INSERT INTO VSK_PERSON_COMPETENCY_HISTORY"):
            self.history_insert_params = bound
        elif "JOIN VSK_SCENARIO_SNAPSHOTS" in normalized:
            self.current_rows = self.scenario_records
        elif "FROM VSK_SCENARIOS" in normalized:
            self.current_one = (
                self.base_scenario
                if self.base_scenario is not None
                and bound.get("base_scenario_id") == self.base_scenario[0]
                else None
            )
        elif normalized.startswith("INSERT INTO VSK_SCENARIOS"):
            self.scenario_insert_params = bound

    def fetchone(self) -> tuple | None:
        return self.current_one

    def fetchall(self) -> list[tuple]:
        return self.current_rows

class FakeConnection:
    def __init__(self, cursor: FakeCursor) -> None:
        self.fake_cursor = cursor
        self.commit_count = 0
        self.rollback_count = 0
        self.closed = False

    def cursor(self) -> FakeCursor:
        return self.fake_cursor

    def commit(self) -> None:
        self.commit_count += 1

    def rollback(self) -> None:
        self.rollback_count += 1

    def close(self) -> None:
        self.closed = True