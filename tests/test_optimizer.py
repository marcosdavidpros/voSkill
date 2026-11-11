from voskill.optimizer import optimize_snapshot


def _snapshot(available_hours: tuple[int, int] = (40, 50), load_amount: int = 40) -> dict:
    return {
        "snapshot_id": "S-001",
        "profiles": [
            {
                "person_id": "P-001",
                "competencies": {"SKILL-1": 4},
                "availability": {"2026-01": available_hours[0]},
            },
            {
                "person_id": "P-002",
                "competencies": {"SKILL-1": 2},
                "availability": {"2026-01": available_hours[1]},
            },
        ],
        "demands": [
            {
                "demand_id": "D-001",
                "skill_id": "SKILL-1",
                "proficiency_level": 3,
                "period": "2026-01",
                "load_amount": load_amount,
            }
        ],
    }


def _dominates(first: dict, second: dict) -> bool:
    first_metrics = first["objective_metrics"]
    second_metrics = second["objective_metrics"]
    names = ("skill_gap_hours", "peak_utilization")
    no_worse = all(first_metrics[name] <= second_metrics[name] for name in names)
    strictly_better = any(first_metrics[name] < second_metrics[name] for name in names)
    return no_worse and strictly_better


def test_nsga2_returns_traceable_feasible_non_dominated_alternatives() -> None:
    result = optimize_snapshot(_snapshot(), seed=42, population_size=20, generations=12)

    assert result["status"] == "feasible"
    alternatives = result["feasible_alternatives"]
    assert len(alternatives) >= 2
    assert result["run_metadata"]["snapshot_id"] == "S-001"
    assert result["run_metadata"]["seed"] == 42
    assert result["run_metadata"]["algorithm"] == "NSGA-II"
    assert result["constraint_evaluation"]["checked_hard_constraints"] == [
        "availability_missing",
        "capacity_exceeded",
    ]
    assert result["constraint_evaluation"]["rejected_alternatives"] == []
    assert result["constraint_evaluation"]["soft_preference_metrics"] == []

    for alternative in alternatives:
        assert alternative["status"] == "feasible"
        assert alternative["allocation"]
        assert "development_actions" in alternative
        assert set(alternative["objective_metrics"]) == {
            "skill_gap_hours",
            "peak_utilization",
        }

    assert not any(
        _dominates(first, second)
        for index, first in enumerate(alternatives)
        for other_index, second in enumerate(alternatives)
        if index != other_index
    )


def test_optimizer_reports_infeasible_when_every_assignment_exceeds_capacity() -> None:
    result = optimize_snapshot(
        _snapshot(available_hours=(30, 35), load_amount=40),
        seed=42,
        population_size=20,
        generations=12,
    )

    assert result["status"] == "infeasible"
    assert result["feasible_alternatives"] == []
    assert result["conflicting_constraint_ids"]
    assert all(
        violation["code"] == "capacity_exceeded"
        for candidate in result["rejected_alternatives"]
        for violation in candidate["violations"]
    )


def test_optimizer_never_returns_candidate_that_exceeds_availability() -> None:
    result = optimize_snapshot(
        _snapshot(available_hours=(40, 40), load_amount=48),
        seed=42,
        population_size=20,
        generations=12,
    )

    assert result["status"] == "infeasible"
    assert result["feasible_alternatives"] == []
    assert any(
        violation["code"] == "capacity_exceeded"
        for candidate in result["rejected_alternatives"]
        for violation in candidate["violations"]
    )