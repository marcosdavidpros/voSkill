import pytest

from voskill.alternative_comparison import (
    AlternativeComparisonError,
    compare_alternatives,
)


def test_missing_cost_is_marked_unavailable_without_numeric_value() -> None:
    alternatives = [
        {"alternative_id": "A-001", "objective_metrics": {"coverage": 0.8, "load": 0.7}},
        {"alternative_id": "A-002", "objective_metrics": {"coverage": 0.7, "load": 0.6}},
    ]

    comparison = compare_alternatives(
        alternatives,
        ["A-001", "A-002"],
        objective_names=["coverage", "load", "cost"],
        objective_directions={"coverage": "maximize", "load": "minimize", "cost": "minimize"},
    )

    for alternative in comparison["alternatives"]:
        cost = alternative["objective_metrics"]["cost"]
        assert cost == {"status": "unavailable", "reason": "missing_cost_input"}
        assert "value" not in cost


def test_comparison_displays_exact_metrics_with_units_and_sources() -> None:
    alternatives = [
        {
            "alternative_id": "A-001",
            "objective_metrics": {
                "coverage": 0.80,
                "development": 0.60,
                "load": 0.70,
                "cost": 1200,
            },
        }
    ]
    objective_metadata = {
        "coverage": {"unit": "ratio", "source": "confirmed_profiles"},
        "development": {"unit": "ratio", "source": "development_plan"},
        "load": {"unit": "ratio", "source": "project_demand"},
        "cost": {"unit": "USD", "source": "project_budget"},
    }

    comparison = compare_alternatives(
        alternatives,
        ["A-001"],
        objective_names=["coverage", "development", "load", "cost"],
        objective_directions={
            "coverage": "maximize",
            "development": "maximize",
            "load": "minimize",
            "cost": "minimize",
        },
        objective_metadata=objective_metadata,
    )

    displayed = comparison["alternatives"][0]
    assert displayed["alternative_id"] == "A-001"
    assert displayed["objective_metrics"] == {
        "coverage": {
            "status": "available",
            "value": 0.80,
            "unit": "ratio",
            "source": "confirmed_profiles",
        },
        "development": {
            "status": "available",
            "value": 0.60,
            "unit": "ratio",
            "source": "development_plan",
        },
        "load": {
            "status": "available",
            "value": 0.70,
            "unit": "ratio",
            "source": "project_demand",
        },
        "cost": {
            "status": "available",
            "value": 1200,
            "unit": "USD",
            "source": "project_budget",
        },
    }


def test_comparison_reports_coverage_load_tradeoff_without_aggregate_ranking() -> None:
    alternatives = [
        {"alternative_id": "A-001", "objective_metrics": {"coverage": 0.8, "load": 0.7}},
        {"alternative_id": "A-002", "objective_metrics": {"coverage": 0.7, "load": 0.6}},
    ]

    comparison = compare_alternatives(
        alternatives,
        ["A-001", "A-002"],
        objective_names=["coverage", "load"],
        objective_directions={"coverage": "maximize", "load": "minimize"},
    )

    assert [item["alternative_id"] for item in comparison["alternatives"]] == [
        "A-001",
        "A-002",
    ]
    assert comparison["trade_offs"] == [
        {"alternative_ids": ["A-001", "A-002"], "objectives": ["coverage", "load"]}
    ]
    assert "ranking" not in comparison
    assert "aggregate_score" not in comparison


def test_unknown_alternative_returns_stable_error_without_comparison() -> None:
    alternatives = [
        {"alternative_id": "A-001", "objective_metrics": {"coverage": 0.8}}
    ]

    with pytest.raises(AlternativeComparisonError) as raised:
        compare_alternatives(
            alternatives,
            ["A-001", "A-404"],
            objective_names=["coverage"],
            objective_directions={"coverage": "maximize"},
        )

    assert raised.value.code == "UNKNOWN_ALTERNATIVE"
    assert raised.value.status_code == 404