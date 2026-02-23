"""High-level GitHub API wrapper for Projects operations."""

from typing import Optional, List, Dict, Any
from pathlib import Path

from .graphql_client import GraphQLClient, GitHubGraphQLError, RateLimitError
from .config import GitHubProjectsConfig, load_config, save_config
from .auth import resolve_github_token
from . import queries
from . import mutations


class GitHubProjectsAPI:
    """
    High-level API for GitHub Projects operations.
    
    Simplifies common operations by wrapping the GraphQL client.
    """
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize API wrapper.
        
        Args:
            token: GitHub token (will auto-resolve if not provided)
        """
        self.token = token or resolve_github_token()
        if not self.token:
            raise ValueError("No GitHub token found. Set GH_TOKEN or use gh CLI")
        
        self._client: Optional[GraphQLClient] = None
    
    def __enter__(self):
        self._client = GraphQLClient(self.token).__enter__()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            self._client.__exit__(exc_type, exc_val, exc_tb)
    
    @property
    def client(self) -> GraphQLClient:
        """Get the underlying GraphQL client."""
        if not self._client:
            raise RuntimeError("API must be used as a context manager")
        return self._client
    
    # ===== User & Repository =====
    
    def get_viewer(self) -> Dict[str, Any]:
        """Get the authenticated user's information."""
        data = self.client.execute(queries.get_viewer())
        return data.get("viewer", {})
    
    def get_repository(self, owner: str, name: str) -> Dict[str, Any]:
        """Get repository information."""
        query, variables = queries.get_repository(owner, name)
        data = self.client.execute(query, variables)
        return data.get("repository", {})
    
    # ===== Project Operations =====
    
    def create_project(
        self,
        owner_id: str,
        title: str,
        repository_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new GitHub Project.
        
        Args:
            owner_id: User or organization ID
            title: Project title
            repository_id: Optional repository ID to link
            
        Returns:
            Project data including id, number, title, url
        """
        mutation, variables = mutations.create_project(owner_id, title, repository_id)
        data = self.client.execute(mutation, variables)
        return data.get("createProjectV2", {}).get("projectV2", {})
    
    def update_project(
        self,
        project_id: str,
        title: Optional[str] = None,
        short_description: Optional[str] = None,
        readme: Optional[str] = None,
        public: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Update project details."""
        mutation, variables = mutations.update_project(
            project_id, title, short_description, readme, public
        )
        data = self.client.execute(mutation, variables)
        return data.get("updateProjectV2", {}).get("projectV2", {})
    
    def find_project(self, owner: str, number: int) -> Optional[Dict[str, Any]]:
        """
        Find a project by owner and number.
        
        Args:
            owner: Repository owner
            number: Project number
            
        Returns:
            Project data or None if not found
        """
        query, variables = queries.find_project(owner, number)
        data = self.client.execute(query, variables)
        user_data = data.get("user", {})
        if user_data:
            return user_data.get("projectV2")
        return None
    
    # ===== Custom Fields =====
    
    def create_field(
        self,
        project_id: str,
        name: str,
        data_type: str,
        single_select_options: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Create a custom field on a project.
        
        Args:
            project_id: Project ID
            name: Field name
            data_type: Field type (TEXT, NUMBER, DATE, SINGLE_SELECT, ITERATION)
            single_select_options: Options for SINGLE_SELECT fields
            
        Returns:
            Field data including id, name, dataType
        """
        mutation, variables = mutations.create_field(
            project_id, name, data_type, single_select_options
        )
        data = self.client.execute(mutation, variables)
        return data.get("createProjectV2Field", {}).get("projectV2Field", {})
    
    # ===== Issues =====
    
    def create_issue(
        self,
        repository_id: str,
        title: str,
        body: Optional[str] = None,
        label_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Create an issue.
        
        Args:
            repository_id: Repository ID
            title: Issue title
            body: Issue body
            label_ids: List of label IDs
            
        Returns:
            Issue data including id, number, title, url
        """
        mutation, variables = mutations.create_issue(repository_id, title, body, label_ids)
        data = self.client.execute(mutation, variables)
        return data.get("createIssue", {}).get("issue", {})
    
    def update_issue(
        self,
        issue_id: str,
        state: Optional[str] = None,
        title: Optional[str] = None,
        body: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update an issue."""
        mutation, variables = mutations.update_issue(issue_id, state, title, body)
        data = self.client.execute(mutation, variables)
        return data.get("updateIssue", {}).get("issue", {})
    
    # ===== Project Items =====
    
    def add_project_item(self, project_id: str, content_id: str) -> str:
        """
        Add an item to a project.
        
        Args:
            project_id: Project ID
            content_id: Content ID (issue or PR)
            
        Returns:
            Item ID
        """
        mutation, variables = mutations.add_project_item(project_id, content_id)
        data = self.client.execute(mutation, variables)
        item = data.get("addProjectV2ItemById", {}).get("item", {})
        return item.get("id", "")
    
    def get_project_items(self, project_id: str) -> List[Dict[str, Any]]:
        """
        Get all items in a project (handles pagination).
        
        Args:
            project_id: Project ID
            
        Returns:
            List of project items
        """
        items = []
        cursor = None
        
        while True:
            query, variables = queries.get_project_items(project_id, cursor)
            data = self.client.execute(query, variables)
            
            node = data.get("node", {})
            items_data = node.get("items", {})
            nodes = items_data.get("nodes", [])
            items.extend(nodes)
            
            page_info = items_data.get("pageInfo", {})
            if not page_info.get("hasNextPage"):
                break
            
            cursor = page_info.get("endCursor")
        
        return items
    
    def update_field_value(
        self,
        project_id: str,
        item_id: str,
        field_id: str,
        value: Dict[str, Any],
    ) -> None:
        """
        Update a field value for a project item.
        
        Args:
            project_id: Project ID
            item_id: Item ID
            field_id: Field ID
            value: Field value (structure depends on field type)
        """
        mutation, variables = mutations.update_field_value(
            project_id, item_id, field_id, value
        )
        self.client.execute(mutation, variables)
    
    # ===== Labels =====
    
    def create_label(
        self,
        repository_id: str,
        name: str,
        color: str,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a label.
        
        Args:
            repository_id: Repository ID
            name: Label name
            color: Label color (6-digit hex without #)
            description: Label description
            
        Returns:
            Label data including id, name, color
        """
        mutation, variables = mutations.create_label(repository_id, name, color, description)
        data = self.client.execute(mutation, variables)
        return data.get("createLabel", {}).get("label", {})
    
    # ===== Rate Limiting =====
    
    def get_rate_limit_info(self) -> Dict[str, Any]:
        """Get current rate limit information."""
        return self.client.get_rate_limit_info()


def load_api_for_repo(repo_root: Path, token: Optional[str] = None) -> GitHubProjectsAPI:
    """
    Load GitHub API wrapper configured for a repository.
    
    Args:
        repo_root: Repository root path
        token: Optional GitHub token (will auto-resolve if not provided)
        
    Returns:
        Configured GitHubProjectsAPI instance
        
    Raises:
        ValueError: If GitHub Projects is not enabled or configuration is invalid
    """
    config = load_config(repo_root)
    
    if not config.enabled:
        raise ValueError("GitHub Projects integration is not enabled. Run 'specify projects enable'")
    
    if not config.repo_owner or not config.repo_name:
        raise ValueError("Repository not configured. Run 'specify projects enable'")
    
    return GitHubProjectsAPI(token)
