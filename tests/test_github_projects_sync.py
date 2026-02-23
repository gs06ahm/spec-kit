"""Tests for GitHub Projects sync hardening.

Covers:
- dry-run makes no mutation calls
- idempotent project item behavior (no duplicate addProjectV2ItemById)
- project item lookup map (build_project_item_map) with pagination
- dependency linking
"""

from typing import Any, Dict, List, Optional, Set

import pytest

from specify_cli.github.hierarchy_builder import HierarchyBuilder
from specify_cli.github.issue_manager import IssueManager
from specify_cli.github.sync_engine import SyncEngine
from specify_cli.github.config import GitHubProjectsConfig
from specify_cli.parser.models import DependencyGraph
from specify_cli.parser.tasks_parser import parse_tasks_md


# ---------------------------------------------------------------------------
# Shared fake GraphQL client
# ---------------------------------------------------------------------------

class FakeGraphQLClient:
    """Minimal in-memory GraphQL stub for unit tests."""

    def __init__(self):
        self.next_issue_number = 1
        self.created_issue_inputs: List[Dict] = []
        self.update_issue_inputs: List[Dict] = []
        self.repo_issues: List[Dict] = []
        self.add_project_item_calls: int = 0
        self.blocked_by_calls: List[tuple] = []
        self.mutation_calls: List[str] = []

        # Project items returned by GetProjectItems / GetProjectItemId queries
        # Format: list of {id, content: {number, id}}
        self._project_items: List[Dict] = []

    def _is_mutation(self, query: str) -> bool:
        return query.strip().startswith("mutation")

    def execute(self, query: str, variables: Optional[Dict] = None) -> Dict:
        variables = variables or {}

        if self._is_mutation(query):
            self.mutation_calls.append(query.strip().split()[1].split("(")[0])

        # --- repository issues ---
        if "query GetRepositoryIssues" in query:
            return {
                "node": {
                    "issues": {
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                        "nodes": self.repo_issues,
                    }
                }
            }

        # --- project items (used by both hierarchy builder and issue manager) ---
        if "GetProjectItems" in query or "GetProjectItemId" in query:
            cursor = variables.get("cursor")
            if cursor is None:
                # First page – return first two items if available, with hasNextPage=True
                # when there are more
                first_page = self._project_items[:2]
                rest = self._project_items[2:]
                return {
                    "node": {
                        "items": {
                            "pageInfo": {
                                "hasNextPage": bool(rest),
                                "endCursor": "page-2" if rest else None,
                            },
                            "nodes": [
                                {"id": item["id"], "content": item.get("content", {})}
                                for item in first_page
                            ],
                        }
                    }
                }
            else:
                # Second (last) page
                rest = self._project_items[2:]
                return {
                    "node": {
                        "items": {
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                            "nodes": [
                                {"id": item["id"], "content": item.get("content", {})}
                                for item in rest
                            ],
                        }
                    }
                }

        # --- create issue ---
        if "mutation CreateIssue" in query:
            issue_id = f"ISSUE_{self.next_issue_number}"
            issue_number = self.next_issue_number
            self.next_issue_number += 1
            issue_input = variables["input"]
            self.created_issue_inputs.append(issue_input)
            issue_data = {
                "id": issue_id,
                "number": issue_number,
                "state": "OPEN",
                "title": issue_input["title"],
                "url": f"https://example.test/issues/{issue_number}",
                "body": issue_input.get("body", ""),
                "parent": {"id": issue_input["parentIssueId"]} if issue_input.get("parentIssueId") else None,
            }
            self.repo_issues.append(issue_data)
            return {"createIssue": {"issue": issue_data}}

        # --- add project item ---
        if "mutation AddProjectItem" in query:
            self.add_project_item_calls += 1
            return {"addProjectV2ItemById": {"item": {"id": "PROJECT_ITEM_1"}}}

        # --- dependency ---
        if "mutation AddBlockedBy" in query:
            issue_id = variables["input"]["issueId"]
            blocking_issue_id = variables["input"]["blockingIssueId"]
            self.blocked_by_calls.append((issue_id, blocking_issue_id))
            return {
                "addBlockedBy": {
                    "issue": {"id": issue_id, "number": 2},
                    "blockingIssue": {"id": blocking_issue_id, "number": 1},
                }
            }

        # --- update issue ---
        if "mutation UpdateIssue" in query:
            issue_input = variables["input"]
            issue_id = issue_input["id"]
            self.update_issue_inputs.append(issue_input)
            for issue in self.repo_issues:
                if issue["id"] == issue_id:
                    if "body" in issue_input:
                        issue["body"] = issue_input["body"]
                    if "state" in issue_input:
                        issue["state"] = issue_input["state"]
                    break
            return {"updateIssue": {"issue": {"id": issue_id, "state": issue_input.get("state", "OPEN")}}}

        raise AssertionError(f"Unexpected query in FakeGraphQLClient:\n{query[:120]}")


# ---------------------------------------------------------------------------
# Dry-run tests (requirement 1)
# ---------------------------------------------------------------------------

SIMPLE_TASKS_MD = """\
# Tasks: Dry Run Test

## Phase 1: Setup
### Task Group: Core
- [ ] T001 Initialize repository in src/main.py
- [ ] T002 [P] Write tests in tests/test_main.py
"""


def test_dry_run_makes_no_mutation_calls(tmp_path):
    """--dry-run must not invoke any GraphQL mutations."""
    client = FakeGraphQLClient()
    engine = SyncEngine(client)

    tasks_file = tmp_path / "tasks.md"
    tasks_file.write_text(SIMPLE_TASKS_MD)

    config = GitHubProjectsConfig(
        enabled=True,
        repo_owner="test-owner",
        repo_name="test-repo",
    )

    engine.sync_tasks_to_project(
        tasks_file=tasks_file,
        config=config,
        project_root=tmp_path,
        dry_run=True,
    )

    assert client.mutation_calls == [], (
        f"Expected no mutations but got: {client.mutation_calls}"
    )


def test_dry_run_does_not_write_config(tmp_path):
    """--dry-run must not persist config changes."""
    client = FakeGraphQLClient()
    engine = SyncEngine(client)

    tasks_file = tmp_path / "tasks.md"
    tasks_file.write_text(SIMPLE_TASKS_MD)

    config = GitHubProjectsConfig(
        enabled=True,
        repo_owner="test-owner",
        repo_name="test-repo",
    )

    engine.sync_tasks_to_project(
        tasks_file=tasks_file,
        config=config,
        project_root=tmp_path,
        dry_run=True,
    )

    # Config file must not have been written
    config_file = tmp_path / ".specify" / "github-projects.json"
    assert not config_file.exists()


def test_dry_run_returns_unchanged_config(tmp_path):
    """--dry-run must return the config unchanged (no project_id set)."""
    client = FakeGraphQLClient()
    engine = SyncEngine(client)

    tasks_file = tmp_path / "tasks.md"
    tasks_file.write_text(SIMPLE_TASKS_MD)

    config = GitHubProjectsConfig(
        enabled=True,
        repo_owner="test-owner",
        repo_name="test-repo",
    )

    returned = engine.sync_tasks_to_project(
        tasks_file=tasks_file,
        config=config,
        project_root=tmp_path,
        dry_run=True,
    )

    assert returned.project_id is None
    assert returned.last_synced_at is None


def test_sync_engine_invokes_completion_state_sync(monkeypatch, tmp_path):
    """Full sync flow invokes completion-state sync with parsed tasks."""

    class FakeProjectCreator:
        def __init__(self, client):
            self.client = client

        def setup_custom_fields(self, project_id, phases, user_stories):
            return {}

    class FakeHierarchyBuilder:
        def __init__(self, client):
            self.client = client

        def create_hierarchy(self, doc, repo_id, project_id, labels):
            return {
                "phase_issues": {},
                "group_issues": {},
                "task_issues": {"T001": {"id": "ISSUE_1", "number": 1, "state": "OPEN"}},
            }

    called: Dict[str, Any] = {"sync_completion_states": False}

    class FakeIssueManager:
        def __init__(self, client, repo_id):
            self.client = client
            self.repo_id = repo_id

        def set_field_values_all(self, **kwargs):
            return None

        def sync_completion_states(self, doc, task_issue_map):
            called["sync_completion_states"] = True
            called["is_completed"] = next(t for t in doc.all_tasks if t.id == "T001").is_completed
            called["task_issue_map"] = task_issue_map

        def create_dependencies(self, dep_graph, task_issue_map):
            return None

    monkeypatch.setattr("specify_cli.github.sync_engine.ProjectCreator", FakeProjectCreator)
    monkeypatch.setattr("specify_cli.github.sync_engine.HierarchyBuilder", FakeHierarchyBuilder)
    monkeypatch.setattr("specify_cli.github.sync_engine.IssueManager", FakeIssueManager)

    client = FakeGraphQLClient()
    engine = SyncEngine(client)
    monkeypatch.setattr(
        engine,
        "_get_repository_info",
        lambda owner, name: {"id": "REPO_1", "owner": {"id": "OWNER_1"}},
    )

    tasks_file = tmp_path / "tasks.md"
    tasks_file.write_text(
        """\
# Tasks: Completion Sync

## Phase 1: Setup
- [X] T001 Completed task
"""
    )

    config = GitHubProjectsConfig(
        enabled=True,
        repo_owner="test-owner",
        repo_name="test-repo",
        project_id="PROJECT_1",
        project_number=1,
        project_url="https://example.test/projects/1",
    )

    engine.sync_tasks_to_project(
        tasks_file=tasks_file,
        config=config,
        project_root=tmp_path,
        dry_run=False,
    )

    assert called["sync_completion_states"] is True
    assert called["is_completed"] is True
    assert called["task_issue_map"]["T001"]["id"] == "ISSUE_1"


# ---------------------------------------------------------------------------
# Idempotency tests (requirement 3)
# ---------------------------------------------------------------------------

def test_hierarchy_builder_does_not_duplicate_project_items():
    """
    When an issue already exists in the project, HierarchyBuilder must NOT
    call addProjectV2ItemById again on the second sync.
    """
    content = """\
# Tasks: Idempotency Test

## Phase 1: Setup
### Task Group: Core
- [ ] T001 Do something
"""
    doc = parse_tasks_md(content)
    client = FakeGraphQLClient()
    builder = HierarchyBuilder(client)

    # First sync – creates issues and adds them to the project
    builder.create_hierarchy(doc, "REPO_1", "PROJECT_1", {})
    calls_after_first = client.add_project_item_calls

    # Simulate all issues being in the project now
    # The builder caches created issues; rebuild from scratch to simulate second run
    client2 = FakeGraphQLClient()
    # Pre-populate repo_issues so _load_existing_issues returns them
    client2.repo_issues = list(client.repo_issues)

    # Pre-populate project items with the issue IDs so _load_project_issue_ids
    # knows they are already in the project (uses content.id from GetProjectItems)
    for i, issue in enumerate(client.repo_issues, start=1):
        client2._project_items.append({
            "id": f"ITEM_{i}",
            "content": {"id": issue["id"], "number": issue["number"]},
        })

    builder2 = HierarchyBuilder(client2)
    builder2.create_hierarchy(doc, "REPO_1", "PROJECT_1", {})

    assert client2.add_project_item_calls == 0, (
        "Second sync should not call addProjectV2ItemById for issues already in the project"
    )


def test_hierarchy_builder_is_idempotent_and_keeps_direct_tasks_under_phase():
    """Issues are reused across syncs; counts stay stable."""
    content = """\
# Tasks: Hierarchy Coverage

## Phase 1: Foundation
- [ ] T001 Direct task in root phase
### Task Group: Core
- [ ] T002 Grouped task under core
"""
    doc = parse_tasks_md(content)
    client = FakeGraphQLClient()
    builder = HierarchyBuilder(client)

    result_first = builder.create_hierarchy(doc, "REPO_1", "PROJECT_1", {})
    created_after_first = len(client.created_issue_inputs)

    result_second = builder.create_hierarchy(doc, "REPO_1", "PROJECT_1", {})
    created_after_second = len(client.created_issue_inputs)

    # First run: phase + group + 2 tasks
    assert created_after_first == 4
    # Second run should reuse all existing issues
    assert created_after_second == created_after_first
    assert result_first["task_issues"]["T001"]["id"] == result_second["task_issues"]["T001"]["id"]

    phase_issue_id = result_first["phase_issues"]["1"]["id"]
    direct_task_input = next(i for i in client.created_issue_inputs if i["title"].startswith("[T001]"))
    grouped_task_input = next(i for i in client.created_issue_inputs if i["title"].startswith("[T002]"))

    assert direct_task_input.get("parentIssueId") == phase_issue_id
    assert grouped_task_input.get("parentIssueId") != phase_issue_id


# ---------------------------------------------------------------------------
# Lookup map / pagination tests (requirement 4)
# ---------------------------------------------------------------------------

def test_build_project_item_map_paginates():
    """build_project_item_map must walk all pages and return a complete map."""
    client = FakeGraphQLClient()
    client._project_items = [
        {"id": "ITEM_1", "content": {"number": 10}},
        {"id": "ITEM_2", "content": {"number": 11}},
        {"id": "ITEM_3", "content": {"number": 42}},  # on second page
    ]
    manager = IssueManager(client, repo_id="REPO_1")

    item_map = manager.build_project_item_map("PROJECT_1")

    assert item_map == {10: "ITEM_1", 11: "ITEM_2", 42: "ITEM_3"}


def test_build_project_item_map_empty_project():
    """An empty project returns an empty map."""
    client = FakeGraphQLClient()
    manager = IssueManager(client, repo_id="REPO_1")
    item_map = manager.build_project_item_map("PROJECT_1")
    assert item_map == {}


def test_get_project_item_id_uses_pagination():
    """_get_project_item_id must find items across page boundaries."""
    client = FakeGraphQLClient()
    client._project_items = [
        {"id": "ITEM_1", "content": {"number": 10}},
        {"id": "ITEM_2", "content": {"number": 11}},
        {"id": "ITEM_3", "content": {"number": 42}},
    ]
    manager = IssueManager(client, repo_id="REPO_1")

    item_id = manager._get_project_item_id("PROJECT_1", 42)
    assert item_id == "ITEM_3"


def test_sync_completion_states_updates_issue_states():
    """Completed/incomplete task states are synced to CLOSED/OPEN issues."""
    doc = parse_tasks_md(
        """\
# Tasks: Completion State

## Phase 1: Setup
- [X] T001 Completed task
- [ ] T002 Pending task
"""
    )
    client = FakeGraphQLClient()
    manager = IssueManager(client, repo_id="REPO_1")
    task_issue_map = {
        "T001": {"id": "ISSUE_1", "number": 1, "state": "OPEN"},
        "T002": {"id": "ISSUE_2", "number": 2, "state": "CLOSED"},
    }

    manager.sync_completion_states(doc, task_issue_map)

    assert client.update_issue_inputs == [
        {"id": "ISSUE_1", "state": "CLOSED"},
        {"id": "ISSUE_2", "state": "OPEN"},
    ]
    assert task_issue_map["T001"]["state"] == "CLOSED"
    assert task_issue_map["T002"]["state"] == "OPEN"


def test_sync_completion_states_is_idempotent():
    """No updateIssue call is made when issue state already matches task completion."""
    doc = parse_tasks_md(
        """\
# Tasks: Completion State

## Phase 1: Setup
- [X] T001 Completed task
- [ ] T002 Pending task
"""
    )
    client = FakeGraphQLClient()
    manager = IssueManager(client, repo_id="REPO_1")
    task_issue_map = {
        "T001": {"id": "ISSUE_1", "number": 1, "state": "CLOSED"},
        "T002": {"id": "ISSUE_2", "number": 2, "state": "OPEN"},
    }

    manager.sync_completion_states(doc, task_issue_map)
    manager.sync_completion_states(doc, task_issue_map)

    assert client.update_issue_inputs == []


# ---------------------------------------------------------------------------
# Dependency tests
# ---------------------------------------------------------------------------

def test_issue_manager_creates_dependency_links():
    client = FakeGraphQLClient()
    manager = IssueManager(client, repo_id="REPO_1")
    graph = DependencyGraph()
    graph.add_dependency("T002", "T001")

    manager.create_dependencies(
        graph,
        {
            "T001": {"id": "ISSUE_1"},
            "T002": {"id": "ISSUE_2"},
        },
    )

    assert client.blocked_by_calls == [("ISSUE_2", "ISSUE_1")]


def test_create_dependencies_skips_missing_tasks():
    """Dependencies for tasks not in the map are skipped gracefully."""
    client = FakeGraphQLClient()
    manager = IssueManager(client, repo_id="REPO_1")
    graph = DependencyGraph()
    graph.add_dependency("T002", "T001")

    # T001 is missing from the map
    manager.create_dependencies(graph, {"T002": {"id": "ISSUE_2"}})

    assert client.blocked_by_calls == []


# ---------------------------------------------------------------------------
# Parser regression tests
# ---------------------------------------------------------------------------

def test_parse_decimal_phase_number_and_direct_tasks():
    content = """\
# Tasks: Parser Coverage

## Phase 3.1: Foundation
- [ ] T001 Define baseline requirements in docs/requirements.md
### Task Group: API
- [ ] T002 Build endpoint in src/api.py
"""
    doc = parse_tasks_md(content)

    assert len(doc.phases) == 1
    phase = doc.phases[0]
    assert phase.number == "3.1"
    assert len(phase.direct_tasks) == 1
    assert phase.direct_tasks[0].phase_number == "3.1"
    assert len(phase.groups) == 1
    assert phase.groups[0].tasks[0].phase_number == "3.1"
