from pathlib import Path

from tests.integration.validate_project_structure import (
    parse_expected_titles,
    validate_hierarchy,
    validate_task_group_fields,
)


def test_parse_expected_titles_from_tasks_file(tmp_path: Path):
    tasks_file = tmp_path / "tasks.md"
    tasks_file.write_text(
        """# Tasks: Validation

## Phase 3.1: Foundation
### Task Group: API
- [ ] T001 Define schema in src/schema.py
- [ ] T002 [P] [US1] Implement endpoint in src/api.py
""",
        encoding="utf-8",
    )

    titles = parse_expected_titles(tasks_file)

    assert "Phase 3.1: Foundation" in titles
    assert "Task Group: API" in titles
    assert "[T001] Define schema in src/schema.py" in titles
    assert "[T002] Implement endpoint in src/api.py" in titles


def test_validate_hierarchy_allows_direct_phase_tasks_and_non_prefixed_groups():
    issues = [
        {"number": 1, "title": "Phase 1: Foundation", "parent": None},
        {"number": 2, "title": "Development Environment", "parent": {"number": 1, "title": "Phase 1: Foundation"}},
        {"number": 3, "title": "[T001] Direct task", "parent": {"number": 1, "title": "Phase 1: Foundation"}},
        {"number": 4, "title": "[T002] Grouped task", "parent": {"number": 2, "title": "Development Environment"}},
    ]

    passed, errors = validate_hierarchy(issues)
    assert passed
    assert errors == []


def test_validate_task_group_fields_detects_group_without_phase_field():
    issues = [
        {"number": 1, "title": "Phase 1: Foundation", "parent": None},
        {"number": 2, "title": "Development Environment", "parent": {"number": 1, "title": "Phase 1: Foundation"}},
        {"number": 3, "title": "[T001] Direct task", "parent": {"number": 1, "title": "Phase 1: Foundation"}},
    ]
    items = [
        {"content": {"number": 2, "title": "Development Environment"}, "fieldValues": {"nodes": []}},
        {"content": {"number": 3, "title": "[T001] Direct task"}, "fieldValues": {"nodes": []}},
    ]

    passed, errors = validate_task_group_fields(items, issues)
    assert not passed
    assert any("missing Phase field" in err for err in errors)
