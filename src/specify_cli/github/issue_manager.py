"""GitHub Issues manager for creating and linking issues."""

from typing import Dict, List, Any, Optional
from rich.console import Console

from .graphql_client import GraphQLClient
from .mutations import (
    CREATE_ISSUE_MUTATION,
    ADD_PROJECT_ITEM_MUTATION,
    UPDATE_FIELD_VALUE_MUTATION,
    CREATE_LABEL_MUTATION,
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
    
    def set_field_values(
        self,
        doc: TasksDocument,
        project_id: str,
        task_issue_map: Dict[str, str],
        field_ids: Dict[str, Any]
    ) -> None:
        """
        Set custom field values for all task issues.
        
        Args:
            doc: Parsed tasks document
            project_id: Project node ID
            task_issue_map: Map of task IDs to issue node IDs
            field_ids: Field IDs from setup_custom_fields
        """
        console.print(f"[cyan]Setting field values for {len(task_issue_map)} tasks...[/cyan]")
        
        # First, we need to get the project item IDs for each issue
        # For now, we'll need to add each issue to the project and get the item ID
        task_item_map = {}
        for task_id, issue_id in task_issue_map.items():
            # Issue was already added to project via projectV2Ids in creation
            # We need to query for the item ID - for now, skip field values
            # This will be a future enhancement
            pass
        
        console.print("[yellow]⚠ Field value setting skipped - issues created with projectV2Ids[/yellow]")
        console.print("[yellow]  Custom fields can be set manually in the project UI[/yellow]")
    
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
        task_issue_map: Dict[str, str]
    ) -> None:
        """
        Create issue dependencies based on dependency graph.
        
        Args:
            dep_graph: Dependency graph
            task_issue_map: Mapping from task IDs to issue node IDs
        """
        console.print(f"[cyan]Creating {len(dep_graph.dependencies)} dependencies...[/cyan]")
        
        # Note: GitHub doesn't have a GraphQL API for issue dependencies yet
        # We would need to use the REST API for this
        # For now, we'll document this in the issue descriptions
        
        console.print("[yellow]⚠ Issue dependency linking via REST API not yet implemented[/yellow]")
        console.print("[yellow]  Dependencies are documented in issue descriptions[/yellow]")
