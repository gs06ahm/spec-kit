from specify_cli.github.hierarchy_builder import HierarchyBuilder
from specify_cli.github.issue_manager import IssueManager
from specify_cli.parser.models import DependencyGraph
from specify_cli.parser.tasks_parser import parse_tasks_md


class FakeGraphQLClient:
    def __init__(self):
        self.next_issue_number = 1
        self.created_issue_inputs = []
        self.update_issue_inputs = []
        self.repo_issues = []
        self.add_project_item_calls = 0
        self.blocked_by_calls = []

    def execute(self, query, variables=None):
        variables = variables or {}

        if "query GetRepositoryIssues" in query:
            return {
                "node": {
                    "issues": {
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                        "nodes": self.repo_issues,
                    }
                }
            }

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

        if "mutation AddProjectItem" in query:
            self.add_project_item_calls += 1
            return {"addProjectV2ItemById": {"item": {"id": "PROJECT_ITEM_1"}}}

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

        if "query GetProjectItemId" in query:
            cursor = variables.get("cursor")
            if cursor is None:
                return {
                    "node": {
                        "items": {
                            "pageInfo": {"hasNextPage": True, "endCursor": "page-2"},
                            "nodes": [
                                {"id": "ITEM_1", "content": {"number": 10}},
                                {"id": "ITEM_2", "content": {"number": 11}},
                            ],
                        }
                    }
                }
            return {
                "node": {
                    "items": {
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                        "nodes": [
                            {"id": "ITEM_3", "content": {"number": 42}},
                        ],
                    }
                }
            }

        raise AssertionError(f"Unexpected query: {query[:80]}")


def test_parse_decimal_phase_number_and_direct_tasks():
    content = """# Tasks: Parser Coverage

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


def test_hierarchy_builder_is_idempotent_and_keeps_direct_tasks_under_phase():
    content = """# Tasks: Hierarchy Coverage

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


def test_issue_manager_project_item_lookup_paginates():
    client = FakeGraphQLClient()
    manager = IssueManager(client, repo_id="REPO_1")

    item_id = manager._get_project_item_id("PROJECT_1", 42)
    assert item_id == "ITEM_3"


def test_sync_completion_states_updates_issue_states():
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
