from api_helpers import MemoryCompetencyRepository, _existing_competency
from conftest import _request

from voskill.main import app, get_competency_repository


def test_authorized_competency_correction_updates_value_and_history() -> None:
    repository = MemoryCompetencyRepository()
    repository.rows.append(_existing_competency())
    app.dependency_overrides[get_competency_repository] = lambda: repository

    response = _request(
        "PATCH",
        "/people/P-001/competencies/C-001",
        {
            "proficiency_level": 3,
            "evidence": "Operação do cluster",
            "review_date": "2026-11-08",
        },
        state={"actor_id": "U-001", "authorized_person_ids": ["P-001"]},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["proficiency_level"] == 3
    assert response.json()["actor_id"] == "U-001"
    assert repository.history == [
        {
            "previous_level": 4,
            "new_level": 3,
            "actor_id": "U-001",
            "changed_at": "2026-11-08T00:00:00+00:00",
        }
    ]


def test_person_can_correct_own_competency() -> None:
    repository = MemoryCompetencyRepository()
    repository.rows.append(_existing_competency())
    app.dependency_overrides[get_competency_repository] = lambda: repository

    response = _request(
        "PATCH",
        "/people/P-001/competencies/C-001",
        {
            "proficiency_level": 3,
            "evidence": "Atualização pela própria pessoa",
            "review_date": "2026-11-08",
        },
        state={"actor_id": "P-001"},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["actor_id"] == "P-001"
    assert response.json()["proficiency_level"] == 3
    assert repository.history[0]["actor_id"] == "P-001"


def test_unauthorized_competency_correction_returns_403_without_changes() -> None:
    repository = MemoryCompetencyRepository()
    repository.rows.append(_existing_competency())
    original_rows = [row.copy() for row in repository.rows]
    app.dependency_overrides[get_competency_repository] = lambda: repository

    response = _request(
        "PATCH",
        "/people/P-001/competencies/C-001",
        {
            "proficiency_level": 3,
            "evidence": "Unauthorized change",
            "review_date": "2026-11-08",
        },
        state={"actor_id": "U-999", "authorized_person_ids": []},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 403
    assert repository.rows == original_rows
    assert repository.history == []