import pytest

from voskill.scenario_comparison import ScenarioError, compare_scenarios


def test_compare_scenarios_merges_deltas_and_reports_changes_and_missing_data() -> None:
    snapshot = {
        "periods": {
            "2026-01": {
                "demand": {"SKILL-1": {"level": 3, "loadAmount": 40}},
                "availability": {"P-001": {"hours": 40}},
            }
        }
    }
    first_deltas: dict[str, object] = {}
    second_deltas = {
        "periods": {
            "2026-01": {
                "demand": {"SKILL-1": {"loadAmount": 50}},
                "availability": None,
            }
        }
    }

    comparison = compare_scenarios(
        first_scenario_id="S-001",
        first_snapshot=snapshot,
        first_deltas=first_deltas,
        second_scenario_id="S-002",
        second_snapshot=snapshot,
        second_deltas=second_deltas,
    )

    assert comparison["scenario_ids"] == ["S-001", "S-002"]
    scenarios = {item["scenario_id"]: item for item in comparison["scenarios"]}
    assert scenarios["S-001"] == {"scenario_id": "S-001", "status": "complete", "missing": []}
    assert scenarios["S-002"] == {
        "scenario_id": "S-002",
        "status": "incomplete",
        "missing": [{"period": "2026-01", "field": "availability"}],
    }
    period = comparison["periods"][0]
    assert period["changed_values"]["demand"] == {
        "S-001": {"SKILL-1": {"level": 3, "loadAmount": 40}},
        "S-002": {"SKILL-1": {"level": 3, "loadAmount": 50}},
    }
    assert period["assumptions"]["S-001"]["availability"] == {"P-001": {"hours": 40}}
    assert period["assumptions"]["S-002"]["availability"] is None


def test_compare_scenarios_rejects_snapshot_without_periods() -> None:
    with pytest.raises(ScenarioError) as raised:
        compare_scenarios(
            first_scenario_id="S-001",
            first_snapshot={},
            first_deltas={},
            second_scenario_id="S-002",
            second_snapshot={"periods": {}},
            second_deltas={},
        )

    assert raised.value.code == "INVALID_SCENARIO_SNAPSHOT"
    assert raised.value.status_code == 422