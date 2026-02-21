"""GitHub Issues manager for creating and linking issues."""

from typing import Dict, List, Any, Optional
from rich.console import Console

from .graphql_client import GraphQLClient, GitHubGraphQLError
from .mutations import (
    CREATE_ISSUE_MUTATION,
    ADD_PROJECT_ITEM_MUTATION,
    UPDATE_FIELD_VALUE_MUTATION,
    CREATE_LABEL_MUTATION,
    ADD_BLOCKED_BY_MUTATION,
)
from ..parser.models import Task, Phase, StoryGroup, TasksDocument, DependencyGraph

console = Console()


class IssueManager:
    """Handles creation of issues, hierarchy, and dependencies."""
    
    def __init__(self, client: GraphQLClient, repo_id: str):
        """
        Initialize IssueManager.
        
        Args:
            client: GraphQL client instance
            repo_id: Repository node ID
        """
        self.client = client
        self.repo_id = repo_id
    
    def create_labels(self, phases: List[Phase], user_stories: List[str]) -> Dict[str, str]:
        """
        Create repository labels for phases and user stories.
        
        Args:
            phases: List of phases
            user_stories: List of user story IDs
            
        Returns:
            Dictionary mapping label names to label IDs (empty for now - IDs not tracked)
        """
        console.print("[cyan]Creating labels...[/cyan]")
        
        labels_created = {}
        
        # Create phase labels
        for phase in phases:
            label_name = f"phase-{phase.number}"
            self._create_label_safe(label_name, "0969DA")  # Blue
            labels_created[label_name] = label_name  # Store name as placeholder
        
        # Create user story labels
        for us in user_stories:
            label_name = f"user-story-{us.lower()}"
            self._create_label_safe(label_name, "BFD4F2")  # Light blue
            labels_created[label_name] = label_name
        
        # Create priority labels
        priority_labels = [
            ("p-critical", "D73A4A"),  # Red
            ("p-high", "FF9800"),      # Orange
            ("p-medium", "FFC107"),    # Yellow
            ("p-low", "4CAF50")        # Green
        ]
        for label, color in priority_labels:
            self._create_label_safe(label, color)
            labels_created[label] = label
        
        # Create parallel label
        self._create_label_safe("parallel", "9C27B0")  # Purple
        labels_created["parallel"] = "parallel"
        
        console.print("[green]✓ Labels created[/green]")
        return labels_created
    
    def _create_label_safe(self, name: str, color: str) -> None:
        """Create a label if it doesn't exist (ignore errors if it does)."""
        try:
            variables = {
                "input": {
                    "repositoryId": self.repo_id,
                    "name": name,
                    "color": color
                }
            }
            self.client.execute(CREATE_LABEL_MUTATION, variables)
        except Exception:
            # Label might already exist, that's fine
            pass
    
    def create_task_issues(
        self,
        doc: TasksDocument,
        project_id: str,
        field_ids: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Create issues for all tasks.
        
        Args:
            doc: Parsed tasks document
            project_id: Project node ID
            field_ids: Field IDs from setup_custom_fields
            
        Returns:
            Dictionary mapping task IDs to issue node IDs
        """
        console.print(f"[cyan]Creating {doc.task_count} task issues...[/cyan]")
        
        task_issue_map = {}
        
        for phase in doc.phases:
            for group in phase.groups:
                for task in group.tasks:
                    # Create issue
                    issue = self._create_task_issue(task, phase, group)
                    task_issue_map[task.id] = issue["id"]
                    
                    # Add to project
                    item = self._add_issue_to_project(project_id, issue["id"])
                    
                    # Set custom field values
                    self._set_field_values(
                        project_id,
                        item["id"],
                        task,
                        phase,
                        group,
                        field_ids
                    )
                    
                    console.print(f"  [green]✓[/green] {task.id}: {task.description[:50]}...")
            
            # Handle direct tasks (if any)
            for task in phase.direct_tasks:
                issue = self._create_task_issue(task, phase, None)
                task_issue_map[task.id] = issue["id"]
                
                item = self._add_issue_to_project(project_id, issue["id"])
                self._set_field_values(
                    project_id,
                    item["id"],
                    task,
                    phase,
                    None,
                    field_ids
                )
                
                console.print(f"  [green]✓[/green] {task.id}: {task.description[:50]}...")
        
        console.print(f"[green]✓ Created {len(task_issue_map)} issues[/green]")
        return task_issue_map
    
    def _get_project_item_id(self, project_id: str, issue_number: int) -> Optional[str]:
        """Get the project item ID for an issue that's already in the project."""
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

        cursor = None
        while True:
            variables = {"projectId": project_id, "cursor": cursor}
            result = self.client.execute(query, variables)
            items_data = result["node"]["items"]
            items = items_data["nodes"]

            for item in items:
                if item.get("content") and item["content"].get("number") == issue_number:
                    return item["id"]

            page_info = items_data.get("pageInfo", {})
            if not page_info.get("hasNextPage"):
                break
            cursor = page_info.get("endCursor")

        return None

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
        
        # Set field values for tasks
        task_set_count = 0
        for task_id, issue in task_issue_map.items():
            # Get the project item ID
            item_id = self._get_project_item_id(project_id, issue["number"])
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
            
            # Get the project item ID
            item_id = self._get_project_item_id(project_id, issue["number"])
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
    
    def _create_task_issue(
        self,
        task: Task,
        phase: Phase,
        group: Optional[StoryGroup]
    ) -> Dict[str, Any]:
        """Create a GitHub issue for a task."""
        # Build title
        title = f"[{task.id}] {task.description}"
        
        # Build body
        body_parts = [
            f"**Phase:** {phase.number} - {phase.title}",
        ]
        
        if group:
            body_parts.append(f"**User Story:** {group.title}")
        
        if task.file_paths:
            body_parts.append(f"**Files:** {', '.join(task.file_paths)}")
        
        if task.is_parallel:
            body_parts.append("**Parallel:** Can run in parallel with other tasks")
        
        body = "\n\n".join(body_parts)
        
        # Build labels
        labels = [f"phase-{phase.number}"]
        if group and group.user_story:
            labels.append(f"user-story-{group.user_story.lower()}")
        if task.user_story:
            labels.append(f"user-story-{task.user_story.lower()}")
        
        # Create issue
        variables = {
            "input": {
                "repositoryId": self.repo_id,
                "title": title,
                "body": body,
                "labelIds": []  # We'll use label names via API, not IDs
            }
        }
        
        result = self.client.execute(CREATE_ISSUE_MUTATION, variables)
        return result["createIssue"]["issue"]
    
    def _add_issue_to_project(
        self,
        project_id: str,
        issue_id: str
    ) -> Dict[str, Any]:
        """Add an issue to a project."""
        variables = {
            "input": {
                "projectId": project_id,
                "contentId": issue_id
            }
        }
        
        result = self.client.execute(ADD_PROJECT_ITEM_MUTATION, variables)
        return result["addProjectV2ItemById"]["item"]
    
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
