from voskill.feasibility import filter_capacity_feasible


def test_all_over_capacity_candidates_return_infeasible_without_recommendations() -> None:
    candidates = [
        {
            "alternative_id": "A-003",
            "assignments": [
                {"person_id": "P-001", "period": "2026-01", "load_amount": 48}
            ],
        }
    ]

    result = filter_capacity_feasible(
        candidates,
        {("P-001", "2026-01"): 40},
    )

    assert result["status"] == "infeasible"
    assert result["feasible_alternatives"] == []
    assert result["conflicting_constraint_ids"] == ["capacity:P-001:2026-01"]
    assert result["rejected_alternatives"] == [
        {
            "alternative_id": "A-003",
            "violations": [
                {
                    "constraint_id": "capacity:P-001:2026-01",
                    "code": "capacity_exceeded",
                    "person_id": "P-001",
                    "period": "2026-01",
                    "assigned_hours": 48,
                    "available_hours": 40,
                }
            ],
        }
    ]


def test_capacity_filter_keeps_feasible_candidates_and_rejects_violations() -> None:
    feasible = {
        "alternative_id": "A-001",
        "assignments": [
            {"person_id": "P-001", "period": "2026-01", "load_amount": 32}
        ],
    }
    overloaded = {
        "alternative_id": "A-003",
        "assignments": [
            {"person_id": "P-001", "period": "2026-01", "load_amount": 48}
        ],
    }
    candidates = [feasible, overloaded]

    result = filter_capacity_feasible(candidates, {("P-001", "2026-01"): 40})

    assert result["status"] == "feasible"
    assert result["feasible_alternatives"] == [feasible]
    assert result["rejected_alternatives"][0]["alternative_id"] == "A-003"
    assert result["rejected_alternatives"][0]["violations"][0]["code"] == "capacity_exceeded"
    assert candidates == [feasible, overloaded]


def test_missing_availability_never_makes_a_candidate_feasible() -> None:
    candidate = {
        "alternative_id": "A-004",
        "assignments": [
            {"person_id": "P-404", "period": "2026-01", "load_amount": 8}
        ],
    }

    result = filter_capacity_feasible([candidate], {})

    assert result["status"] == "infeasible"
    assert result["feasible_alternatives"] == []
    assert result["rejected_alternatives"][0]["violations"][0]["code"] == "availability_missing"


def test_soft_interest_preference_is_reported_separately_and_remains_feasible() -> None:
    candidate = {
        "alternative_id": "A-002",
        "assignments": [
            {"person_id": "P-001", "period": "2026-01", "load_amount": 32}
        ],
        "preference_metrics": {"interest_alignment": 0.35},
    }

    result = filter_capacity_feasible([candidate], {("P-001", "2026-01"): 40})

    assert result["status"] == "feasible"
    assert result["feasible_alternatives"] == [candidate]
    assert result["rejected_alternatives"] == []
    assert result["soft_preference_metrics"] == [
        {"alternative_id": "A-002", "metrics": {"interest_alignment": 0.35}}
    ]