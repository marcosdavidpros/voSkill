import logging

from api_helpers import MemoryCompetencyRepository, _existing_competency
from conftest import _request

from voskill.main import app, get_competency_repository


def test_unauthorized_profile_read_is_forbidden_and_audited_without_profile_data(caplog) -> None:
    repository = MemoryCompetencyRepository()
    repository.rows.append(_existing_competency())
    app.dependency_overrides[get_competency_repository] = lambda: repository

    try:
        with caplog.at_level(logging.WARNING, logger="voskill.audit"):
            response = _request(
                "GET",
                "/people/P-001/competencies",
                state={"actor_id": "U-999", "authorized_person_ids": []},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": {"code": "FORBIDDEN"}}
    assert "Kubernetes" not in response.text
    assert "Migração do cluster" not in response.text

    audit_events = [record for record in caplog.records if record.name == "voskill.audit"]
    assert len(audit_events) == 1
    event = audit_events[0]
    assert event.actor_id == "U-999"
    assert event.resource_id == "P-001"
    assert event.action == "view_person_competencies"
    assert event.outcome == "denied"
    assert not hasattr(event, "skill_name")
    assert not hasattr(event, "evidence")
    assert "Kubernetes" not in caplog.text
    assert "Migração do cluster" not in caplog.text