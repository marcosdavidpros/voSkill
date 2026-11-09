import json
from collections.abc import Callable
from copy import deepcopy
from datetime import UTC, date, datetime, time
from decimal import Decimal
from uuid import uuid4

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


class CompetencyError(ValueError):
    def __init__(self, code: str, status_code: int, field: str | None = None) -> None:
        self.code = code
        self.status_code = status_code
        self.field = field
        super().__init__(code)


class CompetencyRepository:
    def __init__(
        self,
        connection_factory: Callable[[], oracledb.Connection] = open_oracle_connection,
    ) -> None:
        self._connection_factory = connection_factory

    def create(
        self,
        person_id: str,
        skill_id: str,
        proficiency_level: int,
        evidence: str,
        review_date: date,
        actor_id: str,
    ) -> dict[str, object]:
        connection = self._connection_factory()
        try:
            with connection.cursor() as cursor:
                if not 1 <= proficiency_level <= 5:
                    raise CompetencyError("INVALID_LEVEL", 422, "proficiency_level")
                if not evidence.strip():
                    raise CompetencyError("REQUIRED_EVIDENCE", 422, "evidence")

                cursor.execute(
                    "SELECT PERSON_ID FROM VSK_PERSONS WHERE PERSON_ID = :person_id",
                    person_id=person_id,
                )
                if cursor.fetchone() is None:
                    raise CompetencyError("PERSON_NOT_FOUND", 404, "person_id")

                cursor.execute(
                    "SELECT SKILL_ID, SKILL_NAME FROM VSK_SKILLS WHERE SKILL_ID = :skill_id",
                    skill_id=skill_id,
                )
                skill = cursor.fetchone()
                if skill is None:
                    raise CompetencyError("UNKNOWN_SKILL", 422, "skill_id")

                cursor.execute(
                    """
                    SELECT COMPETENCY_ID
                      FROM VSK_PERSON_COMPETENCIES
                     WHERE PERSON_ID = :person_id AND SKILL_ID = :skill_id
                    """,
                    person_id=person_id,
                    skill_id=skill_id,
                )
                if cursor.fetchone() is not None:
                    raise CompetencyError("COMPETENCY_ALREADY_EXISTS", 409)

                competency_id = str(uuid4())
                reviewed_at = datetime.combine(review_date, time.min, tzinfo=UTC)
                cursor.execute(
                    """
                    INSERT INTO VSK_PERSON_COMPETENCIES (
                        COMPETENCY_ID, PERSON_ID, SKILL_ID, PROFICIENCY_LEVEL,
                        EVIDENCE, ORIGIN_TYPE, ACTOR_ID, REVIEWED_AT
                    ) VALUES (
                        :competency_id, :person_id, :skill_id, :proficiency_level,
                        :evidence, :origin_type, :actor_id, :reviewed_at
                    )
                    """,
                    competency_id=competency_id,
                    person_id=person_id,
                    skill_id=skill_id,
                    proficiency_level=proficiency_level,
                    evidence=evidence.strip(),
                    origin_type="MANUAL",
                    actor_id=actor_id,
                    reviewed_at=reviewed_at,
                )
                connection.commit()
                return {
                    "competency_id": competency_id,
                    "person_id": person_id,
                    "skill_id": skill[0],
                    "skill_name": skill[1],
                    "proficiency_level": proficiency_level,
                    "evidence": evidence.strip(),
                    "origin_type": "MANUAL",
                    "actor_id": actor_id,
                    "review_date": review_date.isoformat(),
                }
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def list_for_person(self, person_id: str) -> list[dict[str, object]]:
        connection = self._connection_factory()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT PERSON_ID FROM VSK_PERSONS WHERE PERSON_ID = :person_id",
                    person_id=person_id,
                )
                if cursor.fetchone() is None:
                    raise CompetencyError("PERSON_NOT_FOUND", 404, "person_id")

                cursor.execute(
                    """
                    SELECT C.COMPETENCY_ID, C.PERSON_ID, C.SKILL_ID, S.SKILL_NAME,
                           C.PROFICIENCY_LEVEL, C.EVIDENCE, C.ORIGIN_TYPE,
                           C.ACTOR_ID, C.REVIEWED_AT
                      FROM VSK_PERSON_COMPETENCIES C
                      JOIN VSK_SKILLS S ON S.SKILL_ID = C.SKILL_ID
                     WHERE C.PERSON_ID = :person_id
                     ORDER BY S.SKILL_NAME
                    """,
                    person_id=person_id,
                )
                return [self._record(row) for row in cursor.fetchall()]
        finally:
            connection.close()

    def correct(
        self,
        person_id: str,
        competency_id: str,
        proficiency_level: int,
        evidence: str,
        review_date: date,
        actor_id: str,
    ) -> dict[str, object]:
        if not 1 <= proficiency_level <= 5:
            raise CompetencyError("INVALID_LEVEL", 422, "proficiency_level")
        if not evidence.strip():
            raise CompetencyError("REQUIRED_EVIDENCE", 422, "evidence")

        connection = self._connection_factory()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT COMPETENCY_ID, SKILL_ID, PROFICIENCY_LEVEL, EVIDENCE, ORIGIN_TYPE
                      FROM VSK_PERSON_COMPETENCIES
                     WHERE COMPETENCY_ID = :competency_id AND PERSON_ID = :person_id
                     FOR UPDATE
                    """,
                    competency_id=competency_id,
                    person_id=person_id,
                )
                current = cursor.fetchone()
                if current is None:
                    raise CompetencyError("COMPETENCY_NOT_FOUND", 404)

                cursor.execute(
                    "SELECT SKILL_NAME FROM VSK_SKILLS WHERE SKILL_ID = :skill_id",
                    skill_id=current[1],
                )
                skill = cursor.fetchone()
                if skill is None:
                    raise CompetencyError("UNKNOWN_SKILL", 422, "skill_id")

                changed_at = datetime.now(UTC)
                cursor.execute(
                    """
                    INSERT INTO VSK_PERSON_COMPETENCY_HISTORY (
                        HISTORY_ID, COMPETENCY_ID, PREVIOUS_LEVEL, NEW_LEVEL,
                        PREVIOUS_EVIDENCE, NEW_EVIDENCE, ACTOR_ID, CHANGED_AT
                    ) VALUES (
                        :history_id, :competency_id, :previous_level, :new_level,
                        :previous_evidence, :new_evidence, :actor_id, :changed_at
                    )
                    """,
                    history_id=str(uuid4()),
                    competency_id=competency_id,
                    previous_level=current[2],
                    new_level=proficiency_level,
                    previous_evidence=current[3],
                    new_evidence=evidence.strip(),
                    actor_id=actor_id,
                    changed_at=changed_at,
                )
                reviewed_at = datetime.combine(review_date, time.min, tzinfo=UTC)
                cursor.execute(
                    """
                    UPDATE VSK_PERSON_COMPETENCIES
                       SET PROFICIENCY_LEVEL = :proficiency_level,
                           EVIDENCE = :evidence,
                           ACTOR_ID = :actor_id,
                           REVIEWED_AT = :reviewed_at
                     WHERE COMPETENCY_ID = :competency_id AND PERSON_ID = :person_id
                    """,
                    proficiency_level=proficiency_level,
                    evidence=evidence.strip(),
                    actor_id=actor_id,
                    reviewed_at=reviewed_at,
                    competency_id=competency_id,
                    person_id=person_id,
                )
                connection.commit()
                return {
                    "competency_id": competency_id,
                    "person_id": person_id,
                    "skill_id": current[1],
                    "skill_name": skill[0],
                    "proficiency_level": proficiency_level,
                    "evidence": evidence.strip(),
                    "origin_type": current[4],
                    "actor_id": actor_id,
                    "review_date": review_date.isoformat(),
                }
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _record(row: tuple[object, ...]) -> dict[str, object]:
        reviewed_at = row[8]
        review_date = reviewed_at.date() if isinstance(reviewed_at, datetime) else reviewed_at
        return {
            "competency_id": row[0],
            "person_id": row[1],
            "skill_id": row[2],
            "skill_name": row[3],
            "proficiency_level": row[4],
            "evidence": row[5],
            "origin_type": row[6],
            "actor_id": row[7],
            "review_date": review_date.isoformat(),
        }


class DemandError(ValueError):
    def __init__(self, code: str, status_code: int, field: str | None = None) -> None:
        self.code = code
        self.status_code = status_code
        self.field = field
        super().__init__(code)


class DemandRepository:
    def __init__(
        self,
        connection_factory: Callable[[], oracledb.Connection] = open_oracle_connection,
    ) -> None:
        self._connection_factory = connection_factory

    def create(
        self,
        project_id: str,
        skill_id: str,
        proficiency_level: int,
        period_start: date,
        load_amount: Decimal,
        load_unit: str,
        actor_id: str,
    ) -> dict[str, object]:
        connection = self._connection_factory()
        try:
            with connection.cursor() as cursor:
                self._validate(
                    cursor,
                    project_id,
                    skill_id,
                    proficiency_level,
                    period_start,
                    load_amount,
                    load_unit,
                )
                demand_id = str(uuid4())
                cursor.execute(
                    """
                    INSERT INTO VSK_PROJECT_DEMANDS (
                        DEMAND_ID, PROJECT_ID, SKILL_ID, PROFICIENCY_LEVEL,
                        PERIOD_START, LOAD_AMOUNT, LOAD_UNIT, ACTOR_ID
                    ) VALUES (
                        :demand_id, :project_id, :skill_id, :proficiency_level,
                        :period_start, :load_amount, :load_unit, :actor_id
                    )
                    """,
                    demand_id=demand_id,
                    project_id=project_id,
                    skill_id=skill_id,
                    proficiency_level=proficiency_level,
                    period_start=period_start,
                    load_amount=load_amount,
                    load_unit=load_unit,
                    actor_id=actor_id,
                )
                connection.commit()
                return self._record(
                    (
                        demand_id,
                        project_id,
                        skill_id,
                        proficiency_level,
                        period_start,
                        load_amount,
                        load_unit,
                        actor_id,
                    )
                )
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def list_for_project(self, project_id: str) -> list[dict[str, object]]:
        connection = self._connection_factory()
        try:
            with connection.cursor() as cursor:
                self._get_project(cursor, project_id)
                cursor.execute(
                    """
                    SELECT DEMAND_ID, PROJECT_ID, SKILL_ID, PROFICIENCY_LEVEL,
                           PERIOD_START, LOAD_AMOUNT, LOAD_UNIT, ACTOR_ID
                      FROM VSK_PROJECT_DEMANDS
                     WHERE PROJECT_ID = :project_id
                     ORDER BY PERIOD_START, DEMAND_ID
                    """,
                    project_id=project_id,
                )
                return [self._record(row) for row in cursor.fetchall()]
        finally:
            connection.close()

    def update(
        self,
        demand_id: str,
        project_id: str,
        skill_id: str,
        proficiency_level: int,
        period_start: date,
        load_amount: Decimal,
        load_unit: str,
        actor_id: str,
    ) -> dict[str, object]:
        connection = self._connection_factory()
        try:
            with connection.cursor() as cursor:
                self._validate(
                    cursor,
                    project_id,
                    skill_id,
                    proficiency_level,
                    period_start,
                    load_amount,
                    load_unit,
                )
                cursor.execute(
                    """
                    UPDATE VSK_PROJECT_DEMANDS
                       SET SKILL_ID = :skill_id,
                           PROFICIENCY_LEVEL = :proficiency_level,
                           PERIOD_START = :period_start,
                           LOAD_AMOUNT = :load_amount,
                           LOAD_UNIT = :load_unit,
                           ACTOR_ID = :actor_id,
                           UPDATED_AT = SYSTIMESTAMP
                     WHERE DEMAND_ID = :demand_id
                       AND PROJECT_ID = :project_id
                    """,
                    demand_id=demand_id,
                    project_id=project_id,
                    skill_id=skill_id,
                    proficiency_level=proficiency_level,
                    period_start=period_start,
                    load_amount=load_amount,
                    load_unit=load_unit,
                    actor_id=actor_id,
                )
                if cursor.rowcount == 0:
                    raise DemandError("DEMAND_NOT_FOUND", 404)
                connection.commit()
                return self._record(
                    (
                        demand_id,
                        project_id,
                        skill_id,
                        proficiency_level,
                        period_start,
                        load_amount,
                        load_unit,
                        actor_id,
                    )
                )
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _validate(
        self,
        cursor: oracledb.Cursor,
        project_id: str,
        skill_id: str,
        proficiency_level: int,
        period_start: date,
        load_amount: Decimal,
        load_unit: str,
    ) -> None:
        if not 1 <= proficiency_level <= 5:
            raise DemandError("INVALID_LEVEL", 422, "proficiency_level")
        if load_amount < 0:
            raise DemandError("INVALID_LOAD", 422, "load_amount")

        horizon_start, horizon_end, project_load_unit = self._get_project(cursor, project_id)
        if load_unit != project_load_unit:
            raise DemandError("INVALID_LOAD_UNIT", 422, "load_unit")
        if period_start.day != 1:
            raise DemandError("INVALID_PERIOD", 422, "period")
        if not self._as_date(horizon_start) <= period_start <= self._as_date(horizon_end):
            raise DemandError("PERIOD_OUTSIDE_HORIZON", 422, "period")

        cursor.execute(
            "SELECT SKILL_ID FROM VSK_SKILLS WHERE SKILL_ID = :skill_id",
            skill_id=skill_id,
        )
        if cursor.fetchone() is None:
            raise DemandError("UNKNOWN_SKILL", 422, "skill_id")

    @staticmethod
    def _get_project(cursor: oracledb.Cursor, project_id: str) -> tuple[object, object, str]:
        cursor.execute(
            """
            SELECT HORIZON_START, HORIZON_END, LOAD_UNIT
              FROM VSK_PROJECTS
             WHERE PROJECT_ID = :project_id
            """,
            project_id=project_id,
        )
        project = cursor.fetchone()
        if project is None:
            raise DemandError("PROJECT_NOT_FOUND", 404, "project_id")
        return project[0], project[1], project[2]

    @classmethod
    def _record(cls, row: tuple[object, ...]) -> dict[str, object]:
        period_start = cls._as_date(row[4])
        return {
            "demand_id": row[0],
            "project_id": row[1],
            "skill_id": row[2],
            "proficiency_level": row[3],
            "period": period_start.strftime("%Y-%m"),
            "load_amount": row[5],
            "load_unit": row[6],
            "actor_id": row[7],
        }

    @staticmethod
    def _as_date(value: date | datetime) -> date:
        return value.date() if isinstance(value, datetime) else value


class ScenarioError(ValueError):
    def __init__(self, code: str, status_code: int) -> None:
        self.code = code
        self.status_code = status_code
        super().__init__(code)


class ScenarioRepository:
    def __init__(
        self,
        connection_factory: Callable[[], oracledb.Connection] = open_oracle_connection,
    ) -> None:
        self._connection_factory = connection_factory

    def create_alternative(
        self,
        base_scenario_id: str,
        name: str,
        deltas: dict[str, object],
        actor_id: str,
    ) -> dict[str, object]:
        try:
            deltas_json = json.dumps(
                deltas,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        except (TypeError, ValueError) as error:
            raise ScenarioError("INVALID_DELTAS", 422) from error

        connection = self._connection_factory()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT SCENARIO_ID, PROJECT_ID, SNAPSHOT_ID
                      FROM VSK_SCENARIOS
                     WHERE SCENARIO_ID = :base_scenario_id
                       AND SCENARIO_TYPE = 'BASE'
                    """,
                    base_scenario_id=base_scenario_id,
                )
                base_scenario = cursor.fetchone()
                if base_scenario is None:
                    raise ScenarioError("BASE_SCENARIO_NOT_FOUND", 404)

                scenario_id = str(uuid4())
                created_at = datetime.now(UTC)
                cursor.execute(
                    """
                    INSERT INTO VSK_SCENARIOS (
                        SCENARIO_ID, PROJECT_ID, SNAPSHOT_ID, BASE_SCENARIO_ID,
                        SCENARIO_TYPE, SCENARIO_NAME, DELTAS_JSON, ACTOR_ID, CREATED_AT
                    ) VALUES (
                        :scenario_id, :project_id, :snapshot_id, :base_scenario_id,
                        'ALTERNATIVE', :scenario_name, :deltas_json, :actor_id, :created_at
                    )
                    """,
                    scenario_id=scenario_id,
                    project_id=base_scenario[1],
                    snapshot_id=base_scenario[2],
                    base_scenario_id=base_scenario[0],
                    scenario_name=name,
                    deltas_json=deltas_json,
                    actor_id=actor_id,
                    created_at=created_at,
                )
                connection.commit()
                return {
                    "scenario_id": scenario_id,
                    "base_scenario_id": base_scenario[0],
                    "project_id": base_scenario[1],
                    "snapshot_id": base_scenario[2],
                    "name": name,
                    "actor_id": actor_id,
                    "created_at": created_at,
                    "deltas": deltas,
                }
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def compare(self, first_scenario_id: str, second_scenario_id: str) -> dict[str, object]:
        if first_scenario_id == second_scenario_id:
            raise ScenarioError("DUPLICATE_SCENARIO", 422)

        connection = self._connection_factory()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT S.SCENARIO_ID, S.PROJECT_ID, S.SNAPSHOT_ID,
                           S.SCENARIO_TYPE, S.DELTAS_JSON, P.SNAPSHOT_JSON
                      FROM VSK_SCENARIOS S
                      JOIN VSK_SCENARIO_SNAPSHOTS P ON P.SNAPSHOT_ID = S.SNAPSHOT_ID
                     WHERE S.SCENARIO_ID IN (:first_scenario_id, :second_scenario_id)
                    """,
                    first_scenario_id=first_scenario_id,
                    second_scenario_id=second_scenario_id,
                )
                rows = cursor.fetchall()

            scenarios_by_id = {row[0]: row for row in rows}
            if first_scenario_id not in scenarios_by_id or second_scenario_id not in scenarios_by_id:
                raise ScenarioError("UNKNOWN_SCENARIO", 404)

            effective_periods: dict[str, dict[str, dict[str, object]]] = {}
            for scenario_id in (first_scenario_id, second_scenario_id):
                row = scenarios_by_id[scenario_id]
                snapshot = self._json_value(row[5])
                deltas = self._json_value(row[4])
                effective = self._merge_json(snapshot, deltas)
                periods = effective.get("periods")
                if not isinstance(periods, dict):
                    raise ScenarioError("INVALID_SCENARIO_SNAPSHOT", 422)
                effective_periods[scenario_id] = periods

            period_ids = sorted(
                {
                    period_id
                    for periods in effective_periods.values()
                    for period_id in periods
                }
            )
            required_periods = {
                period_id
                for periods in effective_periods.values()
                for period_id, assumptions in periods.items()
                if isinstance(assumptions, dict) and assumptions.get("demand")
            }

            scenario_statuses: list[dict[str, object]] = []
            for scenario_id in (first_scenario_id, second_scenario_id):
                missing = []
                periods = effective_periods[scenario_id]
                for period_id in sorted(required_periods):
                    assumptions = periods.get(period_id)
                    availability = (
                        assumptions.get("availability")
                        if isinstance(assumptions, dict)
                        else None
                    )
                    if not availability:
                        missing.append({"period": period_id, "field": "availability"})
                scenario_statuses.append(
                    {
                        "scenario_id": scenario_id,
                        "status": "incomplete" if missing else "complete",
                        "missing": missing,
                    }
                )

            period_comparisons = []
            for period_id in period_ids:
                assumptions_by_scenario = {
                    scenario_id: effective_periods[scenario_id].get(period_id, {})
                    for scenario_id in (first_scenario_id, second_scenario_id)
                }
                fields = {
                    field
                    for assumptions in assumptions_by_scenario.values()
                    if isinstance(assumptions, dict)
                    for field in assumptions
                }
                changed_values = {}
                for field in sorted(fields):
                    values = {
                        scenario_id: (
                            assumptions.get(field)
                            if isinstance(assumptions, dict)
                            else None
                        )
                        for scenario_id, assumptions in assumptions_by_scenario.items()
                    }
                    if values[first_scenario_id] != values[second_scenario_id]:
                        changed_values[field] = values
                period_comparisons.append(
                    {
                        "period": period_id,
                        "assumptions": assumptions_by_scenario,
                        "changed_values": changed_values,
                    }
                )

            return {
                "scenario_ids": [first_scenario_id, second_scenario_id],
                "scenarios": scenario_statuses,
                "periods": period_comparisons,
            }
        finally:
            connection.close()

    @classmethod
    def _merge_json(cls, base: object, delta: object) -> object:
        if isinstance(base, dict) and isinstance(delta, dict):
            merged = deepcopy(base)
            for key, value in delta.items():
                merged[key] = cls._merge_json(merged.get(key), value)
            return merged
        return deepcopy(delta)

    @staticmethod
    def _json_value(value: object) -> object:
        if hasattr(value, "read"):
            value = value.read()
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError as error:
                raise ScenarioError("INVALID_SCENARIO_SNAPSHOT", 422) from error
        if isinstance(value, dict):
            return value
        raise ScenarioError("INVALID_SCENARIO_SNAPSHOT", 422)