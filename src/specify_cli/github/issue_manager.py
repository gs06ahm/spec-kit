"""GitHub Issues manager for creating and linking issues."""

from typing import Dict, List, Any, Optional
from rich.console import Console

from .graphql_client import GraphQLClient, GitHubGraphQLError
from .mutations import (
    ADD_PROJECT_ITEM_MUTATION,
    UPDATE_FIELD_VALUE_MUTATION,
    ADD_BLOCKED_BY_MUTATION,
    UPDATE_ISSUE_MUTATION,
)
from ..parser.models import Task, Phase, StoryGroup, TasksDocument, DependencyGraph

console = Console()


class IssueManager:
    """Handles field value assignment and dependency linking for issues."""
    
    def __init__(self, client: GraphQLClient, repo_id: str):
        """
        Initialize IssueManager.
        
        Args:
            client: GraphQL client instance
            repo_id: Repository node ID
        """
        self.client = client
        self.repo_id = repo_id

    def build_project_item_map(self, project_id: str) -> Dict[int, str]:
        """
        Fetch all project items once and return a mapping of issue number → item ID.

        This avoids the O(n²) per-issue pagination of ``_get_project_item_id``
        by fetching all pages a single time and building a lookup table.

        Args:
            project_id: Project node ID

        Returns:
            Dict mapping issue number (int) to project item ID (str)
        """
        query = '''
        query GetProjectItemId($projectId: ID!, $cursor: String) {
          node(id: $projectId) {
            ... on ProjectV2 {
              items(first: 100, after: $cursor) {
                pageInfo {
                  hasNextPage
                  endCursor
                }
                nodes {
                  id
                  content {
                    ... on Issue {
                      number
                    }
                  }
                }
              }
            }
          }
        }
        '''
        item_map: Dict[int, str] = {}
        cursor = None

        while True:
            variables = {"projectId": project_id, "cursor": cursor}
            result = self.client.execute(query, variables)
            items_data = result["node"]["items"]

            for item in items_data["nodes"]:
                content = item.get("content") or {}
                number = content.get("number")
                if number is not None:
                    item_map[number] = item["id"]

            page_info = items_data.get("pageInfo", {})
            if not page_info.get("hasNextPage"):
                break
            cursor = page_info.get("endCursor")

        return item_map

    def _get_project_item_id(self, project_id: str, issue_number: int) -> Optional[str]:
        """
        Get the project item ID for an issue that's already in the project.

        Prefer ``build_project_item_map`` when you need to look up many issues
        because it fetches all pages only once.
        """
        item_map = self.build_project_item_map(project_id)
        return item_map.get(issue_number)

    def set_field_values_all(
        self,
        doc: TasksDocument,
        project_id: str,
        task_issue_map: Dict[str, Dict],
        group_issue_map: Dict[str, Dict],
        field_ids: Dict[str, Any]
    ) -> None:
        """
        Set custom field values for all task and group issues.
        
        Args:
            doc: Parsed tasks document
            project_id: Project node ID
            task_issue_map: Map of task IDs to issue dictionaries  
            group_issue_map: Map of group keys to issue dictionaries
            field_ids: Field IDs from setup_custom_fields
        """
        total_items = len(task_issue_map) + len(group_issue_map)
        console.print(f"[cyan]Setting field values for {total_items} items ({len(task_issue_map)} tasks, {len(group_issue_map)} groups)...[/cyan]")

        # Build lookup map once for all issues (avoids O(n²) pagination)
        item_map = self.build_project_item_map(project_id)
        
        # Set field values for tasks
        task_set_count = 0
        for task_id, issue in task_issue_map.items():
            item_id = item_map.get(issue["number"])
            if not item_id:
                console.print(f"[yellow]  ⚠ Could not find project item for task {task_id}[/yellow]")
                continue
            
            # Find the task, phase, and group
            task = None
            for t in doc.all_tasks:
                if t.id == task_id:
                    task = t
                    break
            
            if not task:
                continue
            
            # Find the phase
            phase = None
            for p in doc.phases:
                if p.number == task.phase_number:
                    phase = p
                    break
            
            if not phase:
                continue
            
            # Find the group
            group = None
            if task.group_title:
                for g in phase.groups:
                    if g.title == task.group_title:
                        group = g
                        break
            
            # Set field values
            self._set_field_values(
                project_id, item_id, task, phase, group, field_ids
            )
            task_set_count += 1
        
        # Set field values for task groups
        group_set_count = 0
        for group_key, issue in group_issue_map.items():
            # Parse group_key: "phase_number:group_title"
            parts = group_key.split(":", 1)
            if len(parts) != 2:
                continue
            phase_number = parts[0]
            group_title = parts[1]
            
            item_id = item_map.get(issue["number"])
            if not item_id:
                console.print(f"[yellow]  ⚠ Could not find project item for group {group_title}[/yellow]")
                continue
            
            # Find the phase
            phase = None
            for p in doc.phases:
                if p.number == phase_number:
                    phase = p
                    break
            
            if not phase:
                continue
            
            # Find the group
            group = None
            for g in phase.groups:
                if g.title == group_title:
                    group = g
                    break
            
            if not group:
                continue
            
            # Set field values for group
            self._set_group_field_values(
                project_id, item_id, phase, group, field_ids
            )
            group_set_count += 1
        
        console.print(f"[green]✓ Set field values for {task_set_count} tasks and {group_set_count} groups[/green]")
    
    def _set_group_field_values(
        self,
        project_id: str,
        item_id: str,
        phase: Phase,
        group: StoryGroup,
        field_ids: Dict[str, Any]
    ) -> None:
        """Set custom field values for a task group project item."""
        # Set Phase field - this allows the group to appear in the correct Phase group
        phase_name = f"Phase {phase.number}: {phase.title}"
        if phase_name in field_ids.get("Phase_options", {}):
            self._set_single_select_field(
                project_id,
                item_id,
                field_ids["Phase"],
                field_ids["Phase_options"][phase_name]
            )
    
    def _set_field_values(
        self,
        project_id: str,
        item_id: str,
        task: Task,
        phase: Phase,
        group: Optional[StoryGroup],
        field_ids: Dict[str, Any]
    ) -> None:
        """Set custom field values for a project item."""
        # Set Task ID (text field)
        self._set_text_field(
            project_id,
            item_id,
            field_ids["Task ID"],
            task.id
        )
        
        # Set Phase (single-select field)
        phase_name = f"Phase {phase.number}: {phase.title}"
        if phase_name in field_ids.get("Phase_options", {}):
            self._set_single_select_field(
                project_id,
                item_id,
                field_ids["Phase"],
                field_ids["Phase_options"][phase_name]
            )
        
        # Set User Story (single-select field)
        us_value = "N/A"
        if group and group.user_story:
            us_value = group.user_story
        elif task.user_story:
            us_value = task.user_story
        
        if us_value in field_ids.get("UserStory_options", {}):
            self._set_single_select_field(
                project_id,
                item_id,
                field_ids["User Story"],
                field_ids["UserStory_options"][us_value]
            )
        
        # Set Parallel (single-select field)
        parallel_value = "Yes" if task.is_parallel else "No"
        if parallel_value in field_ids.get("Parallel_options", {}):
            self._set_single_select_field(
                project_id,
                item_id,
                field_ids["Parallel"],
                field_ids["Parallel_options"][parallel_value]
            )
        
        # Set Priority (default to N/A for now)
        if "N/A" in field_ids.get("Priority_options", {}):
            self._set_single_select_field(
                project_id,
                item_id,
                field_ids["Priority"],
                field_ids["Priority_options"]["N/A"]
            )
    
    def _set_text_field(
        self,
        project_id: str,
        item_id: str,
        field_id: str,
        value: str
    ) -> None:
        """Set a text field value."""
        variables = {
            "input": {
                "projectId": project_id,
                "itemId": item_id,
                "fieldId": field_id,
                "value": {
                    "text": value
                }
            }
        }
        
        self.client.execute(UPDATE_FIELD_VALUE_MUTATION, variables)
    
    def _set_single_select_field(
        self,
        project_id: str,
        item_id: str,
        field_id: str,
        option_id: str
    ) -> None:
        """Set a single-select field value."""
        variables = {
            "input": {
                "projectId": project_id,
                "itemId": item_id,
                "fieldId": field_id,
                "value": {
                    "singleSelectOptionId": option_id
                }
            }
        }
        
        self.client.execute(UPDATE_FIELD_VALUE_MUTATION, variables)
    
    def create_dependencies(
        self,
        dep_graph: DependencyGraph,
        task_issue_map: Dict[str, Dict[str, Any]]
    ) -> None:
        """
        Create issue dependencies based on dependency graph.
        
        Args:
            dep_graph: Dependency graph
            task_issue_map: Mapping from task IDs to issue dictionaries
        """
        total_links = sum(len(blockers) for blockers in dep_graph.dependencies.values())
        console.print(f"[cyan]Creating {total_links} dependencies...[/cyan]")

        created_links = 0
        skipped_links = 0

        for task_id, blockers in dep_graph.dependencies.items():
            dependent_issue = task_issue_map.get(task_id)
            if not dependent_issue:
                skipped_links += len(blockers)
                continue

            dependent_issue_id = dependent_issue["id"]

            for blocker_task_id in blockers:
                blocker_issue = task_issue_map.get(blocker_task_id)
                if not blocker_issue:
                    skipped_links += 1
                    continue

                variables = {
                    "input": {
                        "issueId": dependent_issue_id,
                        "blockingIssueId": blocker_issue["id"],
                    }
                }

                try:
                    self.client.execute(ADD_BLOCKED_BY_MUTATION, variables)
                    created_links += 1
                except GitHubGraphQLError as exc:
                    message = str(exc).lower()
                    if "already" in message and "block" in message:
                        skipped_links += 1
                        continue
                    raise

        console.print(
            f"[green]✓ Dependencies linked:[/green] {created_links} created"
            + (f", {skipped_links} skipped" if skipped_links else "")
        )

    def sync_completion_states(
        self,
        doc: TasksDocument,
        task_issue_map: Dict[str, Dict[str, Any]],
    ) -> None:
        """Sync task completion state to GitHub issue state."""
        updated = 0
        skipped = 0

        for task in doc.all_tasks:
            issue = task_issue_map.get(task.id)
            if not issue:
                skipped += 1
                continue

            desired_state = "CLOSED" if task.is_completed else "OPEN"
            current_state = (issue.get("state") or "OPEN").upper()
            if current_state == desired_state:
                continue

            self.client.execute(
                UPDATE_ISSUE_MUTATION,
                {"input": {"id": issue["id"], "state": desired_state}},
            )
            issue["state"] = desired_state
            updated += 1

        console.print(
            f"[green]✓ Synced task completion states:[/green] {updated} updated"
            + (f", {skipped} skipped" if skipped else "")
        )
