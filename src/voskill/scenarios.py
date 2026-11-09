import json
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

import oracledb

from .connection import open_oracle_connection
from .scenario_comparison import ScenarioError, compare_scenarios


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
            first_scenario = scenarios_by_id[first_scenario_id]
            second_scenario = scenarios_by_id[second_scenario_id]
            return compare_scenarios(
                first_scenario_id=first_scenario_id,
                first_snapshot=self._json_value(first_scenario[5]),
                first_deltas=self._json_value(first_scenario[4]),
                second_scenario_id=second_scenario_id,
                second_snapshot=self._json_value(second_scenario[5]),
                second_deltas=self._json_value(second_scenario[4]),
            )
        finally:
            connection.close()

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