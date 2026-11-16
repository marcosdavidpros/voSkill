from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import oracledb

from .scenario_comparison import ScenarioError


def as_date(value: date | datetime) -> date:
    return value.date() if isinstance(value, datetime) else value


def optimizer_demand(row: tuple[object, ...], project_load_unit: str) -> dict[str, object]:
    if row[5] != project_load_unit:
        raise ScenarioError("INVALID_LOAD_UNIT", 422)
    return {
        "demand_id": str(row[0]),
        "skill_id": str(row[1]),
        "proficiency_level": int(row[2]),
        "period": as_date(row[3]).strftime("%Y-%m"),
        "load_amount": float(row[4]),
        "title": row[6],
        "epic": row[7],
    }


def normalize_availability(
    values: Mapping[str, object],
    horizon_start: date,
    horizon_end: date,
    demand_periods: set[str],
) -> dict[str, float]:
    normalized: dict[str, float] = {}
    for period, raw_hours in values.items():
        if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", period):
            raise ScenarioError("INVALID_AVAILABILITY_PERIOD", 422)
        year, month = (int(value) for value in period.split("-"))
        period_start = date(year, month, 1)
        if not horizon_start <= period_start <= horizon_end:
            raise ScenarioError("PERIOD_OUTSIDE_HORIZON", 422)
        hours = Decimal(str(raw_hours))
        if not hours.is_finite() or hours < 0:
            raise ScenarioError("INVALID_AVAILABILITY", 422)
        normalized[period] = float(hours)
    if not demand_periods.issubset(normalized):
        raise ScenarioError("MISSING_AVAILABILITY", 422)
    return normalized


def build_snapshot(
    snapshot_id: str,
    profiles: Sequence[Mapping[str, Any]],
    demands: Sequence[Mapping[str, Any]],
) -> dict[str, object]:
    demands_by_period: dict[str, dict[str, dict[str, object]]] = defaultdict(dict)
    availability_by_period: dict[str, dict[str, dict[str, float]]] = defaultdict(dict)
    for demand in demands:
        demands_by_period[str(demand["period"])][str(demand["skill_id"])] = {
            "level": demand["proficiency_level"],
            "loadAmount": demand["load_amount"],
        }
    for profile in profiles:
        person_id = str(profile["person_id"])
        for period, hours in profile["availability"].items():
            availability_by_period[str(period)][person_id] = {"hours": float(hours)}

    periods = {
        period: {
            "demand": demands_by_period.get(period, {}),
            "availability": availability_by_period.get(period, {}),
        }
        for period in sorted(set(demands_by_period) | set(availability_by_period))
    }
    return {
        "snapshot_id": snapshot_id,
        "profiles": list(profiles),
        "demands": list(demands),
        "periods": periods,
    }


def serialize_snapshot(snapshot: Mapping[str, object]) -> tuple[str, str]:
    content = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return content, digest


def read_optimizer_snapshot(
    connection_factory: Callable[[], oracledb.Connection],
    scenario_id: str,
) -> dict[str, object]:
    connection = connection_factory()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT S.SCENARIO_TYPE, P.SNAPSHOT_JSON
                  FROM VSK_SCENARIOS S
                  JOIN VSK_SCENARIO_SNAPSHOTS P ON P.SNAPSHOT_ID = S.SNAPSHOT_ID
                 WHERE S.SCENARIO_ID = :scenario_id
                """,
                scenario_id=scenario_id,
            )
            row = cursor.fetchone()
            if row is None:
                raise ScenarioError("SCENARIO_NOT_FOUND", 404)
            if row[0] != "BASE":
                raise ScenarioError("BASE_SCENARIO_REQUIRED", 409)
            snapshot = _json_value(row[1])
            if not isinstance(snapshot, dict):
                raise ScenarioError("INVALID_SCENARIO_SNAPSHOT", 422)
            return {
                "snapshot_id": snapshot["snapshot_id"],
                "profiles": snapshot["profiles"],
                "demands": snapshot["demands"],
            }
    finally:
        connection.close()


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