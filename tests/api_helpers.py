from voskill.database import CompetencyError, DemandError, ScenarioError


class MemoryDemandRepository:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def create(self, **values: object) -> dict:
        record = {
            "demand_id": "D-001",
            **values,
            "period": values["period_start"].strftime("%Y-%m"),
        }
        del record["period_start"]
        self.rows.append(record)
        return record

    def list_for_project(self, project_id: str) -> list[dict]:
        return [row for row in self.rows if row["project_id"] == project_id]

    def update(self, demand_id: str, project_id: str, **values: object) -> dict:
        for row in self.rows:
            if row["demand_id"] == demand_id and row["project_id"] == project_id:
                row.update(values)
                row["period"] = values["period_start"].strftime("%Y-%m")
                del row["period_start"]
                return row
        raise DemandError("DEMAND_NOT_FOUND", 404)

class MemoryCompetencyRepository:
    def __init__(self) -> None:
        self.rows: list[dict] = []
        self.history: list[dict] = []

    def create(self, **values: object) -> dict:
        if not 1 <= values["proficiency_level"] <= 5:
            raise CompetencyError("INVALID_LEVEL", 422, "proficiency_level")
        if not values["evidence"].strip():
            raise CompetencyError("REQUIRED_EVIDENCE", 422, "evidence")
        record = {
            "competency_id": "C-001",
            "skill_name": "Kubernetes",
            "origin_type": "MANUAL",
            **values,
        }
        self.rows.append(record)
        return record

    def list_for_person(self, person_id: str) -> list[dict]:
        return [row for row in self.rows if row["person_id"] == person_id]

    def correct(self, **values: object) -> dict:
        row = next(
            row
            for row in self.rows
            if row["competency_id"] == values["competency_id"]
            and row["person_id"] == values["person_id"]
        )
        self.history.append(
            {
                "previous_level": row["proficiency_level"],
                "new_level": values["proficiency_level"],
                "actor_id": values["actor_id"],
                "changed_at": "2026-11-08T00:00:00+00:00",
            }
        )
        row.update(
            proficiency_level=values["proficiency_level"],
            evidence=values["evidence"],
            actor_id=values["actor_id"],
            review_date=values["review_date"].isoformat(),
        )
        return row

def _existing_competency() -> dict:
    return {
        "competency_id": "C-001",
        "person_id": "P-001",
        "skill_id": "SKILL-1",
        "skill_name": "Kubernetes",
        "proficiency_level": 4,
        "evidence": "Migração do cluster",
        "origin_type": "MANUAL",
        "actor_id": "U-001",
        "review_date": "2026-11-08",
    }

class MemoryScenarioRepository:
    def __init__(self) -> None:
        self.base_snapshot = b'{"demands":[]}'
        self.created_alternatives: list[dict] = []

    def create_alternative(
        self,
        base_scenario_id: str,
        name: str,
        deltas: dict,
        actor_id: str,
    ) -> dict:
        if base_scenario_id != "B-001":
            raise ScenarioError("BASE_SCENARIO_NOT_FOUND", 404)
        alternative = {
            "scenario_id": "A-001",
            "base_scenario_id": base_scenario_id,
            "project_id": "P-001",
            "snapshot_id": "S-001",
            "name": name,
            "actor_id": actor_id,
            "created_at": "2026-11-08T12:00:00+00:00",
            "deltas": deltas,
        }
        self.created_alternatives.append(alternative)
        return alternative

    def compare(self, first_scenario_id: str, second_scenario_id: str) -> dict:
        return {
            "scenario_ids": [first_scenario_id, second_scenario_id],
            "scenarios": [
                {"scenario_id": first_scenario_id, "status": "complete", "missing": []},
                {
                    "scenario_id": second_scenario_id,
                    "status": "incomplete",
                    "missing": [{"period": "2026-02", "field": "availability"}],
                },
            ],
            "periods": [
                {
                    "period": "2026-01",
                    "assumptions": {first_scenario_id: {}, second_scenario_id: {}},
                    "changed_values": {},
                }
            ],
        }

class MemorySkillRelationRepository:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def create(self, **values: object) -> dict:
        relation = {"relation_id": "R-001", "active": True, **values}
        self.rows.append(relation)
        return relation

class MemorySkillInferenceRepository:
    def __init__(self, result: dict) -> None:
        self.result = result
        self.confirmed_competencies = {"SKILL-1": 4}
        self.calls: list[tuple[str, str]] = []

    def infer_for_person(self, person_id: str, target_skill_id: str) -> dict:
        self.calls.append((person_id, target_skill_id))
        return {**self.result, "person_id": person_id, "target_skill_id": target_skill_id}
