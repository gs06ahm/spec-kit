"""GitHub Projects creator and field setup."""

from typing import Dict, List, Any, Optional
from rich.console import Console

from .graphql_client import GraphQLClient
from .mutations import (
    CREATE_PROJECT_MUTATION,
    CREATE_FIELD_MUTATION,
)
from .queries import GET_REPOSITORY_QUERY, GET_PROJECT_FIELDS_QUERY

console = Console()


class ProjectCreator:
    """Handles creation of GitHub Projects and custom fields."""
    
    def __init__(self, client: GraphQLClient):
        """
        Initialize ProjectCreator.
        
        Args:
            client: GraphQL client instance
        """
        self.client = client
    
    def create_project(
        self,
        owner_id: str,
        title: str,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new GitHub ProjectV2.
        
        Args:
            owner_id: GitHub node ID of the owner (user or org)
            title: Project title
            description: Project description
            
        Returns:
            Project data with id, number, title, url
        """
        console.print(f"[cyan]Creating project:[/cyan] {title}")
        
        variables = {
            "input": {
                "ownerId": owner_id,
                "title": title
            }
        }
        
        # Note: shortDescription is not available in CreateProjectV2Input
        # Description can only be set via UpdateProjectV2 mutation after creation
        
        result = self.client.execute(CREATE_PROJECT_MUTATION, variables)
        project = result["createProjectV2"]["projectV2"]
        
        console.print(f"[green]✓ Project created:[/green] {project['url']}")
        return project
    
    def _get_existing_fields(self, project_id: str) -> Dict[str, Any]:
        """
        Get existing fields for a project.
        
        Returns:
            Dictionary mapping field names to field data (includes id, name, dataType, and options for single-select)
        """
        variables = {"projectId": project_id}
        result = self.client.execute(GET_PROJECT_FIELDS_QUERY, variables)
        fields = result.get("node", {}).get("fields", {}).get("nodes", [])
        
        return {field["name"]: field for field in fields}
    
    def setup_custom_fields(
        self,
        project_id: str,
        phases: List[str],
        user_stories: List[str]
    ) -> Dict[str, str]:
        """
        Create custom fields for the project.
        
        Args:
            project_id: Project node ID
            phases: List of phase names (e.g., ["Phase 1: Setup", "Phase 2: Implementation"])
            user_stories: List of user story IDs (e.g., ["US1", "US2", "US3"])
            
        Returns:
            Dictionary mapping field names to field IDs
        """
        console.print("[cyan]Setting up custom fields...[/cyan]")
        
        # Get existing fields
        existing_fields = self._get_existing_fields(project_id)
        
        field_ids = {}
        
        # 1. Task ID (text field)
        if "Task ID" in existing_fields:
            console.print("  ✓ 'Task ID' field already exists")
            task_id_field = existing_fields["Task ID"]
        else:
            console.print("  Creating 'Task ID' field...")
            task_id_field = self._create_text_field(project_id, "Task ID")
        field_ids["Task ID"] = task_id_field["id"]
        
        # 2. Phase (single-select field)
        if "Phase" in existing_fields:
            console.print(f"  ✓ 'Phase' field already exists")
            phase_field = existing_fields["Phase"]
        else:
            console.print(f"  Creating 'Phase' field with {len(phases)} options...")
            phase_field = self._create_single_select_field(
                project_id,
                "Phase",
                phases
            )
        field_ids["Phase"] = phase_field["id"]
        field_ids["Phase_options"] = {
            opt["name"]: opt["id"] 
            for opt in phase_field.get("options", [])
        }
        
        # 3. User Story (single-select field)
        if "User Story" in existing_fields:
            console.print(f"  ✓ 'User Story' field already exists")
            us_field = existing_fields["User Story"]
        else:
            console.print(f"  Creating 'User Story' field with {len(user_stories)} options...")
            us_field = self._create_single_select_field(
                project_id,
                "User Story",
                user_stories + ["N/A"]
            )
        field_ids["User Story"] = us_field["id"]
        field_ids["UserStory_options"] = {
            opt["name"]: opt["id"]
            for opt in us_field.get("options", [])
        }
        
        # 4. Priority (single-select field)
        if "Priority" in existing_fields:
            console.print("  ✓ 'Priority' field already exists")
            priority_field = existing_fields["Priority"]
        else:
            console.print("  Creating 'Priority' field...")
            priority_field = self._create_single_select_field(
                project_id,
                "Priority",
                ["P1 - Critical", "P2 - High", "P3 - Medium", "P4 - Low", "N/A"]
            )
        field_ids["Priority"] = priority_field["id"]
        field_ids["Priority_options"] = {
            opt["name"]: opt["id"]
            for opt in priority_field.get("options", [])
        }
        
        # 5. Parallel (single-select field)
        if "Parallel" in existing_fields:
            console.print("  ✓ 'Parallel' field already exists")
            parallel_field = existing_fields["Parallel"]
        else:
            console.print("  Creating 'Parallel' field...")
            parallel_field = self._create_single_select_field(
                project_id,
                "Parallel",
                ["Yes", "No"]
            )
        field_ids["Parallel"] = parallel_field["id"]
        field_ids["Parallel_options"] = {
            opt["name"]: opt["id"]
            for opt in parallel_field.get("options", [])
        }
        
        console.print(f"[green]✓ Setup complete - {len([k for k in field_ids if not k.endswith('_options')])} custom fields[/green]")
        return field_ids
    
    def _create_text_field(
        self,
        project_id: str,
        name: str
    ) -> Dict[str, Any]:
        """Create a text field."""
        variables = {
            "input": {
                "projectId": project_id,
                "dataType": "TEXT",
                "name": name
            }
        }
        
        result = self.client.execute(CREATE_FIELD_MUTATION, variables)
        return result["createProjectV2Field"]["projectV2Field"]
    
    def _create_single_select_field(
        self,
        project_id: str,
        name: str,
        options: List[str]
    ) -> Dict[str, Any]:
        """Create a single-select field with options."""
        variables = {
            "input": {
                "projectId": project_id,
                "dataType": "SINGLE_SELECT",
                "name": name,
                "singleSelectOptions": [
                    {
                        "name": opt,
                        "color": self._get_color_for_option(opt),
                        "description": ""  # Description is required but can be empty
                    }
                    for opt in options
                ]
            }
        }
        
        result = self.client.execute(CREATE_FIELD_MUTATION, variables)
        return result["createProjectV2Field"]["projectV2Field"]
    
    def _get_color_for_option(self, option: str) -> str:
        """Get a color for a field option."""
        # Color mapping for better visualization
        color_map = {
            "P1": "RED",
            "P2": "ORANGE", 
            "P3": "YELLOW",
            "P4": "GREEN",
            "Yes": "BLUE",
            "No": "GRAY",
            "N/A": "GRAY",
            "Phase 1": "PINK",
            "Phase 2": "PURPLE",
            "Phase 3": "BLUE",
            "Phase 4": "GREEN",
            "Phase 5": "ORANGE",
        }
        
        # Check for matching prefixes
        for key, color in color_map.items():
            if option.startswith(key):
                return color
        
        # Default colors
        return "GRAY"
    
    def get_repository_id(self, owner: str, repo: str) -> str:
        """
        Get the repository node ID.
        
        Args:
            owner: Repository owner
            repo: Repository name
            
        Returns:
            Repository node ID
        """
        variables = {"owner": owner, "name": repo}
        result = self.client.execute(GET_REPOSITORY_QUERY, variables)
        return result["repository"]["id"]
