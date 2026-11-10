from collections.abc import Mapping, Sequence
from typing import Any


def build_competency_map(
    scenario_id: str,
    project_id: str,
    snapshot: Mapping[str, Any],
    confirmed_by_person: Mapping[str, Sequence[Mapping[str, Any]]],
    inferences: Mapping[tuple[str, str], Mapping[str, Any]],
) -> dict[str, Any]:
    periods = snapshot["periods"]
    skill_ids = sorted(
        {
            str(skill_id)
            for assumptions in periods.values()
            if isinstance(assumptions, Mapping)
            for skill_id in assumptions.get("demand", {})
        }
    )
    person_ids = sorted(
        {
            str(person_id)
            for assumptions in periods.values()
            if isinstance(assumptions, Mapping)
            for person_id in assumptions.get("availability", {})
        }
    )

    skills = []
    for skill_id in skill_ids:
        holders = []
        for person_id in person_ids:
            competency = next(
                (
                    item
                    for item in confirmed_by_person.get(person_id, ())
                    if str(item["skill_id"]) == skill_id
                ),
                None,
            )
            if competency is not None:
                holders.append(
                    {
                        "person_id": person_id,
                        "status": "confirmed",
                        "skill_name": competency["skill_name"],
                        "proficiency_level": competency["proficiency_level"],
                        "evidence": competency["evidence"],
                        "origin_type": competency["origin_type"],
                        "review_date": competency["review_date"],
                    }
                )
                continue

            inference = inferences.get((person_id, skill_id))
            if inference is not None and inference.get("status") == "inferred":
                holders.append(
                    {
                        "person_id": person_id,
                        "status": "inferred",
                        "inferred_level": inference["inferred_level"],
                        "source_skill_id": inference["source_skill_id"],
                        "relation_id": inference["relation_id"],
                        "confidence": inference["confidence"],
                        "review_state": "pending_review",
                    }
                )

        confirmed_count = sum(holder["status"] == "confirmed" for holder in holders)
        status = (
            "confirmed"
            if confirmed_count
            else "inferred"
            if holders
            else "uncovered"
        )
        skills.append(
            {
                "skill_id": skill_id,
                "status": status,
                "confirmed_count": confirmed_count,
                "holders": holders,
            }
        )

    confirmed_count = sum(skill["confirmed_count"] > 0 for skill in skills)
    skill_count = len(skills)
    coverage = confirmed_count / skill_count if skill_count else 0.0
    return {
        "scenario_id": scenario_id,
        "project_id": project_id,
        "coverage": {
            "confirmed_count": confirmed_count,
            "skill_count": skill_count,
            "ratio": coverage,
        },
        "skills": skills,
        "summary": f"{confirmed_count} of {skill_count} demanded skills have confirmed coverage.",
    }