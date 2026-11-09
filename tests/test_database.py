import re
from pathlib import Path


def test_repository_tests_are_split_by_domain() -> None:
    test_dir = Path(__file__).parent
    repository_modules = (
        "test_competency_repository.py",
        "test_demand_repository.py",
        "test_suggestion_repository.py",
        "test_scenario_repository.py",
        "test_skill_relation_repository.py",
    )

    for module_name in repository_modules:
        module_source = (test_dir / module_name).read_text(encoding="utf-8")
        assert re.search(r"^def test_", module_source, flags=re.MULTILINE)