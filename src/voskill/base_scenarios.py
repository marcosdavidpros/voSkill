from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from uuid import uuid4

import oracledb

from .base_scenario_snapshot import (
    as_date,
    build_snapshot,
    normalize_availability,
    optimizer_demand,
    read_optimizer_snapshot,
    serialize_snapshot,
)
from .connection import open_oracle_connection
from .scenario_comparison import ScenarioError


class BaseScenarioRepository:
    def __init__(
        self,
        connection_factory: Callable[[], oracledb.Connection] = open_oracle_connection,
    ) -> None:
        self._connection_factory = connection_factory

    def create_base_scenario(
        self,
        project_id: str,
        scenario_name: str,
        participants: Sequence[Mapping[str, object]],
        actor_id: str,
    ) -> dict[str, object]:
        return self._save(None, project_id, scenario_name, participants, actor_id)

    def update_base_scenario(
        self,
        scenario_id: str,
        scenario_name: str,
        participants: Sequence[Mapping[str, object]],
        actor_id: str,
    ) -> dict[str, object]:
        return self._save(scenario_id, None, scenario_name, participants, actor_id)

    def _save(
        self,
        editing_id: str | None,
        project_id: str | None,
        scenario_name: str,
        participants: Sequence[Mapping[str, object]],
        actor_id: str,
    ) -> dict[str, object]:
        name = scenario_name.strip()
        if not name:
            raise ScenarioError("REQUIRED_SCENARIO_NAME", 422)
        if not participants:
            raise ScenarioError("PARTICIPANTS_REQUIRED", 422)

        connection = self._connection_factory()
        try:
            with connection.cursor() as cursor:
                if editing_id is not None:
                    cursor.execute(
                        """
                        SELECT PROJECT_ID, SCENARIO_TYPE
                          FROM VSK_SCENARIOS
                         WHERE SCENARIO_ID = :scenario_id
                        """,
                        scenario_id=editing_id,
                    )
                    existing = cursor.fetchone()
                    if existing is None:
                        raise ScenarioError("SCENARIO_NOT_FOUND", 404)
                    if str(existing[1]) != "BASE":
                        raise ScenarioError("SCENARIO_NOT_EDITABLE", 422)
                    project_id = str(existing[0])
                    cursor.execute(
                        """
                        SELECT COUNT(*)
                          FROM VSK_SCENARIOS
                         WHERE BASE_SCENARIO_ID = :scenario_id
                        """,
                        scenario_id=editing_id,
                    )
                    alternatives = cursor.fetchone()
                    if alternatives is not None and int(alternatives[0]) > 0:
                        raise ScenarioError("SCENARIO_HAS_ALTERNATIVES", 409)

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
                    raise ScenarioError("PROJECT_NOT_FOUND", 404)
                horizon_start = as_date(project[0])
                horizon_end = as_date(project[1])
                load_unit = str(project[2])

                cursor.execute(
                    """
                    SELECT SCENARIO_ID
                      FROM VSK_SCENARIOS
                     WHERE PROJECT_ID = :project_id
                       AND SCENARIO_NAME = :scenario_name
                    """
                    + ("                       AND SCENARIO_ID <> :editing_id\n" if editing_id else ""),
                    project_id=project_id,
                    scenario_name=name,
                    **({"editing_id": editing_id} if editing_id else {}),
                )
                if cursor.fetchone() is not None:
                    raise ScenarioError("SCENARIO_ALREADY_EXISTS", 409)

                cursor.execute(
                    """
                    SELECT DEMAND_ID, SKILL_ID, PROFICIENCY_LEVEL, PERIOD_START,
                           LOAD_AMOUNT, LOAD_UNIT, TITLE, EPIC_NAME
                      FROM VSK_PROJECT_DEMANDS
                     WHERE PROJECT_ID = :project_id
                     ORDER BY PERIOD_START, DEMAND_ID
                    """,
                    project_id=project_id,
                )
                demand_rows = cursor.fetchall()
                if not demand_rows:
                    raise ScenarioError("PROJECT_HAS_NO_DEMANDS", 422)

                demands = [optimizer_demand(row, load_unit) for row in demand_rows]
                demand_periods = {str(demand["period"]) for demand in demands}
                profiles: list[dict[str, object]] = []
                seen_people: set[str] = set()

                for participant in participants:
                    person_id = str(participant.get("person_id", "")).strip()
                    availability = participant.get("availability")
                    if not person_id or person_id in seen_people or not isinstance(availability, Mapping):
                        raise ScenarioError("INVALID_PARTICIPANT", 422)
                    seen_people.add(person_id)

                    normalized_availability = normalize_availability(
                        availability,
                        horizon_start,
                        horizon_end,
                        demand_periods,
                    )

                    cursor.execute(
                        """
                        SELECT PERSON_ID
                          FROM VSK_PERSONS
                         WHERE PERSON_ID = :person_id
                           AND ACTIVE_FLAG = 'Y'
                        """,
                        person_id=person_id,
                    )
                    if cursor.fetchone() is None:
                        raise ScenarioError("PERSON_NOT_FOUND", 422)

                    cursor.execute(
                        """
                        SELECT SKILL_ID, PROFICIENCY_LEVEL
                          FROM VSK_PERSON_COMPETENCIES
                         WHERE PERSON_ID = :person_id
                        """,
                        person_id=person_id,
                    )
                    competencies = {
                        str(row[0]): int(row[1]) for row in cursor.fetchall()
                    }
                    profiles.append(
                        {
                            "person_id": person_id,
                            "competencies": competencies,
                            "availability": normalized_availability,
                        }
                    )

                snapshot_id = str(uuid4())
                scenario_id = editing_id or str(uuid4())
                snapshot = build_snapshot(snapshot_id, profiles, demands)
                snapshot_json, snapshot_sha256 = serialize_snapshot(snapshot)
                created_at = datetime.now(UTC)
                cursor.execute(
                    """
                    INSERT INTO VSK_SCENARIO_SNAPSHOTS (
                        SNAPSHOT_ID, PROJECT_ID, SNAPSHOT_JSON, SNAPSHOT_SHA256,
                        CREATED_BY, CREATED_AT
                    ) VALUES (
                        :snapshot_id, :project_id, :snapshot_json, :snapshot_sha256,
                        :created_by, :created_at
                    )
                    """,
                    snapshot_id=snapshot_id,
                    project_id=project_id,
                    snapshot_json=snapshot_json,
                    snapshot_sha256=snapshot_sha256,
                    created_by=actor_id,
                    created_at=created_at,
                )
                if editing_id is None:
                    cursor.execute(
                        """
                        INSERT INTO VSK_SCENARIOS (
                            SCENARIO_ID, PROJECT_ID, SNAPSHOT_ID, BASE_SCENARIO_ID,
                            SCENARIO_TYPE, SCENARIO_NAME, DELTAS_JSON, ACTOR_ID, CREATED_AT
                        ) VALUES (
                            :scenario_id, :project_id, :snapshot_id, NULL,
                            'BASE', :scenario_name, '{}', :actor_id, :created_at
                        )
                        """,
                        scenario_id=scenario_id,
                        project_id=project_id,
                        snapshot_id=snapshot_id,
                        scenario_name=name,
                        actor_id=actor_id,
                        created_at=created_at,
                    )
                else:
                    cursor.execute(
                        """
                        UPDATE VSK_SCENARIOS
                           SET SNAPSHOT_ID = :snapshot_id, SCENARIO_NAME = :scenario_name
                         WHERE SCENARIO_ID = :scenario_id
                        """,
                        scenario_id=scenario_id,
                        snapshot_id=snapshot_id,
                        scenario_name=name,
                    )
                connection.commit()
                return {
                    "scenario_id": scenario_id,
                    "snapshot_id": snapshot_id,
                    "project_id": project_id,
                    "scenario_name": name,
                    "scenario_type": "BASE",
                }
        except ScenarioError:
            connection.rollback()
            raise
        except oracledb.Error as error:
            connection.rollback()
            raise ScenarioError("SCENARIO_PERSISTENCE_FAILED", 500) from error
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def list_scenarios(self) -> list[dict[str, object]]:
        connection = self._connection_factory()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT S.SCENARIO_ID, S.SCENARIO_NAME, S.SCENARIO_TYPE,
                           S.PROJECT_ID, P.PROJECT_NAME
                      FROM VSK_SCENARIOS S
                      JOIN VSK_PROJECTS P ON P.PROJECT_ID = S.PROJECT_ID
                     ORDER BY P.PROJECT_NAME, S.CREATED_AT DESC, S.SCENARIO_ID
                    """
                )
                return [
                    {
                        "scenario_id": str(row[0]),
                        "scenario_name": str(row[1]),
                        "scenario_type": str(row[2]),
                        "project_id": str(row[3]),
                        "project_name": str(row[4]),
                    }
                    for row in cursor.fetchall()
                ]
        except oracledb.Error as error:
            raise ScenarioError("SCENARIO_LIST_FAILED", 500) from error
        finally:
            connection.close()

    def get_optimization_snapshot(self, scenario_id: str) -> dict[str, object]:
        return read_optimizer_snapshot(self._connection_factory, scenario_id)