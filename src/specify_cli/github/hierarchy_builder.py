"""Builds three-level hierarchy for GitHub Projects using sub-issues."""

from typing import Dict, List, Any, Optional, Set
from rich.console import Console

from .graphql_client import GraphQLClient
from .mutations import CREATE_ISSUE_MUTATION, ADD_PROJECT_ITEM_MUTATION, UPDATE_ISSUE_MUTATION
from .queries import GET_PROJECT_ITEMS_QUERY
from ..parser.models import TasksDocument

console = Console()


class HierarchyBuilder:
    """
    Builds three-level hierarchy: Phase → Task Group → Tasks.
    
    Uses GitHub's sub-issues feature to create parent/child relationships:
    - Phase issues (top level, added to project)
    - Task Group issues (sub-issues of phases, added to project)
    - Task issues (sub-issues of task groups, added to project)
    """
    
    def __init__(self, client: GraphQLClient):
        """
        Initialize HierarchyBuilder.
        
        Args:
            client: GraphQL client instance
        """
        self.client = client
        self._existing_issues_by_title: Dict[str, List[Dict[str, Any]]] = {}
        self._project_issue_ids: Set[str] = set()
    
    def create_hierarchy(
        self,
        doc: TasksDocument,
        repo_id: str,
        project_id: str,
        labels: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Create three-level hierarchy of issues.
        
        Args:
            doc: Parsed tasks document
            repo_id: Repository node ID
            project_id: Project node ID  
            labels: Map of label names to label IDs
            
        Returns:
            Dictionary with:
            - phase_issues: Map of phase number to issue data
            - group_issues: Map of group title to issue data
            - task_issues: Map of task ID to issue data
        """
        console.print("\n[bold cyan]Creating hierarchy:[/bold cyan] Phase → Task Group → Tasks")
        
        phase_issues = {}
        group_issues = {}
        task_issues = {}
        self._existing_issues_by_title = self._load_existing_issues(repo_id)
        # Pre-load project items to avoid duplicate addProjectV2ItemById calls
        self._project_issue_ids = self._load_project_issue_ids(project_id)
        
        # Create Phase issues (top level)
        for phase in doc.phases:
            console.print(f"  📦 Creating Phase {phase.number}: {phase.title}")
            
            # Build phase description
            body_parts = []
            if phase.purpose:
                body_parts.append(f"**Purpose**: {phase.purpose}")
            if phase.goal:
                body_parts.append(f"**Goal**: {phase.goal}")
            if phase.checkpoint:
                body_parts.append(f"**Checkpoint**: {phase.checkpoint}")
            
            # Count tasks in this phase
            phase_tasks = [t for t in doc.all_tasks if t.phase_number == phase.number]
            body_parts.append(f"\n**Tasks**: {len(phase_tasks)} total")
            
            body = "\n\n".join(body_parts)
            
            # Create phase issue
            phase_issue = self._create_issue(
                repo_id=repo_id,
                title=f"Phase {phase.number}: {phase.title}",
                body=body,
                parent_issue_id=None,
                label_ids=[],
                project_ids=[project_id]
            )
            
            phase_issues[phase.number] = phase_issue
            console.print(f"    ✓ Issue #{phase_issue['number']} created")
            
            # Create Task Group issues (children of phase)
            for group in phase.groups:
                console.print(f"    📂 Creating Task Group: {group.title}")
                
                # Count tasks in this group
                group_tasks = [
                    t for t in doc.all_tasks 
                    if t.phase_number == phase.number and t.group_title == group.title
                ]
                
                group_body = f"**Phase**: {phase.number}\n\n**Tasks**: {len(group_tasks)} total"
                if group.user_story:
                    group_body = f"**User Story**: {group.user_story}\n\n" + group_body
                
                # Create group issue as sub-issue of phase
                group_issue = self._create_issue(
                    repo_id=repo_id,
                    title=group.title,
                    body=group_body,
                    parent_issue_id=phase_issue["id"],
                    label_ids=[],
                    project_ids=[project_id]
                )
                
                group_key = f"{phase.number}:{group.title}"
                group_issues[group_key] = group_issue
                console.print(f"      ✓ Issue #{group_issue['number']} created")
                
                # Create Task issues (children of group)
                for task in group_tasks:
                    console.print(f"        📝 Creating Task {task.id}: {task.description[:40]}...")
                    
                    # Build task body
                    task_body = f"**Task ID**: {task.id}\n\n**Description**: {task.description}"
                    if task.is_parallel:
                        task_body += "\n\n**Parallel**: Yes - Can be executed in parallel with other parallel tasks"
                    if task.file_paths:
                        task_body += f"\n\n**Files**:\n" + "\n".join(f"- `{fp}`" for fp in task.file_paths)
                    
                    # Create task issue as sub-issue of group
                    task_issue = self._create_issue(
                        repo_id=repo_id,
                        title=f"[{task.id}] {task.description}",
                        body=task_body,
                        parent_issue_id=group_issue["id"],
                        label_ids=[],
                        project_ids=[project_id]
                    )
                    
                    task_issues[task.id] = task_issue
                    console.print(f"          ✓ Issue #{task_issue['number']} created")

            # Create direct phase tasks (children of phase, no task group)
            for task in phase.direct_tasks:
                console.print(f"    📝 Creating Direct Task {task.id}: {task.description[:40]}...")

                task_body = f"**Task ID**: {task.id}\n\n**Description**: {task.description}"
                if task.is_parallel:
                    task_body += "\n\n**Parallel**: Yes - Can be executed in parallel with other parallel tasks"
                if task.file_paths:
                    task_body += f"\n\n**Files**:\n" + "\n".join(f"- `{fp}`" for fp in task.file_paths)

                task_issue = self._create_issue(
                    repo_id=repo_id,
                    title=f"[{task.id}] {task.description}",
                    body=task_body,
                    parent_issue_id=phase_issue["id"],
                    label_ids=[],
                    project_ids=[project_id]
                )

                task_issues[task.id] = task_issue
                console.print(f"      ✓ Issue #{task_issue['number']} created")
        
        console.print(f"\n[green]✓ Hierarchy created:[/green] {len(phase_issues)} phases, {len(group_issues)} groups, {len(task_issues)} tasks")
        
        return {
            "phase_issues": phase_issues,
            "group_issues": group_issues,
            "task_issues": task_issues
        }
    
    def _create_issue(
        self,
        repo_id: str,
        title: str,
        body: str,
        parent_issue_id: str = None,
        label_ids: List[str] = None,
        project_ids: List[str] = None
    ) -> Dict[str, Any]:
        """
        Create an issue with optional parent (for sub-issues).
        
        Args:
            repo_id: Repository node ID
            title: Issue title
            body: Issue body/description
            parent_issue_id: Optional parent issue ID (for sub-issues)
            label_ids: List of label node IDs
            project_ids: List of project node IDs
            
        Returns:
            Issue data with id, number, url
        """
        existing_issue = self._find_existing_issue(title=title, parent_issue_id=parent_issue_id)
        if existing_issue:
            if body is not None and body != existing_issue.get("body", ""):
                self.client.execute(
                    UPDATE_ISSUE_MUTATION,
                    {"input": {"id": existing_issue["id"], "body": body}}
                )
                existing_issue["body"] = body

            # Only add to project if not already there (idempotency)
            for project_id in project_ids or []:
                if existing_issue["id"] not in self._project_issue_ids:
                    self.client.execute(
                        ADD_PROJECT_ITEM_MUTATION,
                        {"input": {"projectId": project_id, "contentId": existing_issue["id"]}}
                    )
                    self._project_issue_ids.add(existing_issue["id"])

            return existing_issue

        variables = {
            "input": {
                "repositoryId": repo_id,
                "title": title,
                "body": body
            }
        }
        
        if parent_issue_id:
            variables["input"]["parentIssueId"] = parent_issue_id
        
        if label_ids:
            variables["input"]["labelIds"] = label_ids
        
        if project_ids:
            variables["input"]["projectV2Ids"] = project_ids
        
        result = self.client.execute(CREATE_ISSUE_MUTATION, variables)
        issue = result["createIssue"]["issue"]
        cached_issue = {
            "id": issue["id"],
            "number": issue["number"],
            "title": issue["title"],
            "url": issue["url"],
            "body": body,
            "parent": {"id": parent_issue_id} if parent_issue_id else None,
        }
        self._existing_issues_by_title.setdefault(title, []).append(cached_issue)
        # New issues added via projectV2Ids are already in the project
        for project_id in project_ids or []:
            self._project_issue_ids.add(cached_issue["id"])
        return cached_issue

    def _find_existing_issue(self, title: str, parent_issue_id: str = None) -> Optional[Dict[str, Any]]:
        """Find an existing issue by title and parent ID."""
        candidates = self._existing_issues_by_title.get(title, [])
        for issue in candidates:
            issue_parent_id = issue.get("parent", {}).get("id") if issue.get("parent") else None
            if issue_parent_id == parent_issue_id:
                return issue
        return None

    def _load_existing_issues(self, repo_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """Load all existing issues for a repository keyed by title."""
        query = """
        query GetRepositoryIssues($repoId: ID!, $cursor: String) {
          node(id: $repoId) {
            ... on Repository {
              issues(first: 100, after: $cursor, states: [OPEN, CLOSED]) {
                pageInfo {
                  hasNextPage
                  endCursor
                }
                nodes {
                  id
                  number
                  title
                  url
                  body
                  parent {
                    id
                  }
                }
              }
            }
          }
        }
        """
        issues_by_title: Dict[str, List[Dict[str, Any]]] = {}
        cursor = None

        while True:
            result = self.client.execute(query, {"repoId": repo_id, "cursor": cursor})
            issues_data = result.get("node", {}).get("issues", {})
            for issue in issues_data.get("nodes", []):
                issues_by_title.setdefault(issue["title"], []).append(issue)

            page_info = issues_data.get("pageInfo", {})
            if not page_info.get("hasNextPage"):
                break
            cursor = page_info.get("endCursor")

        return issues_by_title

    def _load_project_issue_ids(self, project_id: str) -> Set[str]:
        """
        Load all issue IDs already in the project.

        Returns a set of issue node IDs currently in the project so that
        ``_create_issue`` can skip redundant ``addProjectV2ItemById`` calls.
        """
        issue_ids: Set[str] = set()
        cursor = None

        while True:
            variables = {"projectId": project_id, "cursor": cursor}
            result = self.client.execute(GET_PROJECT_ITEMS_QUERY, variables)
            items_data = result.get("node", {}).get("items", {})
            for item in items_data.get("nodes", []):
                content = item.get("content") or {}
                if content.get("id"):
                    issue_ids.add(content["id"])

            page_info = items_data.get("pageInfo", {})
            if not page_info.get("hasNextPage"):
                break
            cursor = page_info.get("endCursor")

        return issue_ids
