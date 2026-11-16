import json
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any, Protocol
from uuid import uuid4

import oracledb

from .connection import open_oracle_connection
from .optimizer import optimize_snapshot


class OptimizationRunError(ValueError):
    def __init__(self, code: str, status_code: int) -> None:
        self.code = code
        self.status_code = status_code
        super().__init__(code)


class OptimizationRunStore(Protocol):
    def create_run(self, **values: object) -> dict[str, object]: ...

    def get_run(self, run_id: str) -> dict[str, object]: ...


class OptimizationRunRepository:
    def __init__(
        self,
        connection_factory: Callable[[], oracledb.Connection] = open_oracle_connection,
    ) -> None:
        self._connection_factory = connection_factory

    def create_run(
        self,
        run_id: str,
        snapshot_hash: str,
        algorithm_version: str,
        configuration: Mapping[str, object],
        seed: int,
        alternatives_hash: str,
        result: Mapping[str, object],
        actor_id: str,
        created_at: datetime,
    ) -> dict[str, object]:
        configuration_json = _canonical_json(configuration)
        result_json = _canonical_json(result)
        connection = self._connection_factory()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO VSK_OPTIMIZATION_RUNS (
                        RUN_ID, SNAPSHOT_HASH, ALGORITHM_VERSION, CONFIGURATION_JSON,
                        SEED, ALTERNATIVES_HASH, RESULT_JSON, ACTOR_ID, CREATED_AT
                    ) VALUES (
                        :run_id, :snapshot_hash, :algorithm_version, :configuration_json,
                        :seed, :alternatives_hash, :result_json, :actor_id, :created_at
                    )
                    """,
                    run_id=run_id,
                    snapshot_hash=snapshot_hash,
                    algorithm_version=algorithm_version,
                    configuration_json=configuration_json,
                    seed=seed,
                    alternatives_hash=alternatives_hash,
                    result_json=result_json,
                    actor_id=actor_id,
                    created_at=created_at,
                )
                connection.commit()
                return {
                    "run_id": run_id,
                    "snapshot_hash": snapshot_hash,
                    "algorithm_version": algorithm_version,
                    "configuration": dict(configuration),
                    "seed": seed,
                    "alternatives_hash": alternatives_hash,
                    "result": dict(result),
                    "actor_id": actor_id,
                    "created_at": created_at,
                }
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def get_run(self, run_id: str) -> dict[str, object]:
        connection = self._connection_factory()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT RUN_ID, SNAPSHOT_HASH, ALGORITHM_VERSION, CONFIGURATION_JSON,
                           SEED, ALTERNATIVES_HASH, RESULT_JSON, ACTOR_ID, CREATED_AT
                      FROM VSK_OPTIMIZATION_RUNS
                     WHERE RUN_ID = :run_id
                    """,
                    run_id=run_id,
                )
                row = cursor.fetchone()
                if row is None:
                    raise OptimizationRunError("RUN_NOT_FOUND", 404)
                return {
                    "run_id": row[0],
                    "snapshot_hash": row[1],
                    "algorithm_version": row[2],
                    "configuration": _json_value(row[3]),
                    "seed": int(row[4]),
                    "alternatives_hash": row[5],
                    "result": _json_value(row[6]),
                    "actor_id": row[7],
                    "created_at": row[8],
                }
        finally:
            connection.close()
    def get_scenario_snapshot(self, snapshot_id: str) -> dict[str, object]:
        connection = self._connection_factory()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT SNAPSHOT_JSON
                      FROM VSK_SCENARIO_SNAPSHOTS
                     WHERE SNAPSHOT_ID = :snapshot_id
                    """,
                    snapshot_id=snapshot_id,
                )
                row = cursor.fetchone()
                if row is None:
                    raise OptimizationRunError("SNAPSHOT_NOT_FOUND", 404)
                snapshot = _json_value(row[0])
                if not isinstance(snapshot, dict):
                    raise OptimizationRunError("SNAPSHOT_NOT_FOUND", 404)
                return snapshot
        finally:
            connection.close()

    def list_runs(self, actor_id: str, can_audit: bool, limit: int = 50) -> list[dict[str, object]]:
        connection = self._connection_factory()
        try:
            with connection.cursor() as cursor:
                owner_filter = "" if can_audit else " WHERE ACTOR_ID = :actor_id"
                cursor.execute(
                    f"""
                    SELECT RUN_ID, RESULT_JSON, CREATED_AT
                      FROM VSK_OPTIMIZATION_RUNS{owner_filter}
                     ORDER BY CREATED_AT DESC
                     FETCH FIRST {int(limit)} ROWS ONLY
                    """,
                    **({} if can_audit else {"actor_id": actor_id}),
                )
                run_rows = cursor.fetchall()
                cursor.execute(
                    """
                    SELECT S.SNAPSHOT_ID, S.SCENARIO_NAME, P.PROJECT_NAME
                      FROM VSK_SCENARIOS S
                      JOIN VSK_PROJECTS P ON P.PROJECT_ID = S.PROJECT_ID
                     WHERE S.SCENARIO_TYPE = 'BASE'
                    """
                )
                names = {str(row[0]): (str(row[1]), str(row[2])) for row in cursor.fetchall()}

            runs: list[dict[str, object]] = []
            for run_id, result_json, created_at in run_rows:
                result = _json_value(result_json)
                result = result if isinstance(result, dict) else {}
                metadata = result.get("run_metadata")
                metadata = metadata if isinstance(metadata, dict) else {}
                configuration = metadata.get("configuration")
                configuration = configuration if isinstance(configuration, dict) else {}
                snapshot_id = metadata.get("snapshot_id")
                scenario_name, project_name = names.get(str(snapshot_id), (None, None))
                alternatives = result.get("feasible_alternatives")
                rejected = result.get("rejected_alternatives")
                runs.append(
                    {
                        "run_id": run_id,
                        "created_at": created_at,
                        "scenario_name": scenario_name,
                        "project_name": project_name,
                        "status": result.get("status"),
                        "seed": metadata.get("seed"),
                        "population_size": configuration.get("population_size"),
                        "generations": configuration.get("generations"),
                        "rejected_count": len(rejected) if isinstance(rejected, list) else 0,
                        "alternative_ids": [
                            str(alternative["alternative_id"])
                            for alternative in alternatives
                            if isinstance(alternative, dict) and "alternative_id" in alternative
                        ]
                        if isinstance(alternatives, list)
                        else [],
                    }
                )
            return runs
        finally:
            connection.close()


def run_optimization(
    snapshot: Mapping[str, Any],
    seed: int,
    actor_id: str,
    repository: OptimizationRunStore,
    population_size: int = 64,
    generations: int = 40,
) -> dict[str, object]:
    if seed < 0:
        raise OptimizationRunError("INVALID_SEED", 422)

    result = optimize_snapshot(
        snapshot,
        seed=seed,
        population_size=population_size,
        generations=generations,
    )
    configuration = result["run_metadata"]["configuration"]
    snapshot_hash = _canonical_hash(snapshot)
    alternatives_hash = _canonical_hash(
        {
            "feasible_alternatives": result["feasible_alternatives"],
            "rejected_alternatives": result["rejected_alternatives"],
            "conflicting_constraint_ids": result["conflicting_constraint_ids"],
        }
    )
    algorithm_version = str(result["run_metadata"]["algorithm_version"])
    result["run_metadata"].update(
        {
            "snapshot_hash": snapshot_hash,
            "alternatives_hash": alternatives_hash,
        }
    )
    return repository.create_run(
        run_id=str(uuid4()),
        snapshot_hash=snapshot_hash,
        algorithm_version=algorithm_version,
        configuration=configuration,
        seed=seed,
        alternatives_hash=alternatives_hash,
        result=result,
        actor_id=actor_id,
        created_at=datetime.now(UTC),
    )


def _canonical_hash(value: object) -> str:
    return sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _json_value(value: object) -> object:
    if hasattr(value, "read"):
        value = value.read()
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    if isinstance(value, str):
        return json.loads(value)
    if isinstance(value, (dict, list)):
        return value
    raise ValueError("Invalid optimization run JSON")