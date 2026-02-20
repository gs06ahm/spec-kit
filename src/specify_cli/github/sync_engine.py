"""Sync engine for coordinating GitHub Projects synchronization."""

import hashlib
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
from rich.console import Console

from .graphql_client import GraphQLClient
from .project_creator import ProjectCreator
from .issue_manager import IssueManager
from .config import GitHubProjectsConfig, save_config
from .queries import GET_REPOSITORY_QUERY
from ..parser import parse_tasks_md, build_dependency_graph
from ..parser.models import TasksDocument

console = Console()


class SyncEngine:
    """Orchestrates synchronization between tasks.md and GitHub Projects."""
    
    def __init__(self, client: GraphQLClient):
        """
        Initialize SyncEngine.
        
        Args:
            client: GraphQL client instance
        """
        self.client = client
    
    def sync_tasks_to_project(
        self,
        tasks_file: Path,
        config: GitHubProjectsConfig,
        project_root: Path
    ) -> GitHubProjectsConfig:
        """
        Sync tasks.md to GitHub Project.
        
        Args:
            tasks_file: Path to tasks.md file
            config: Current configuration
            project_root: Project root directory
            
        Returns:
            Updated configuration
        """
        # Parse tasks.md
        console.print(f"\n[bold cyan]Step 1:[/bold cyan] Parsing {tasks_file.name}")
        content = tasks_file.read_text()
        doc = parse_tasks_md(content)
        
        console.print(f"  Found: {doc.task_count} tasks across {len(doc.phases)} phases")
        
        # Build dependency graph
        console.print("\n[bold cyan]Step 2:[/bold cyan] Building dependency graph")
        dep_graph = build_dependency_graph(doc)
        console.print(f"  Found: {len(dep_graph.dependencies)} dependencies")
        
        # Get repository info
        console.print("\n[bold cyan]Step 3:[/bold cyan] Getting repository information")
        repo_info = self._get_repository_info(config.repo_owner, config.repo_name)
        repo_id = repo_info["id"]
        owner_id = repo_info["owner"]["id"] if "owner" in repo_info else repo_info["id"]
        console.print(f"  Repository: {config.repo_owner}/{config.repo_name}")
        
        # Create or get project
        console.print("\n[bold cyan]Step 4:[/bold cyan] Creating GitHub Project")
        creator = ProjectCreator(self.client)
        
        if config.project_id:
            console.print(f"  [yellow]Project already exists:[/yellow] {config.project_url}")
            project_id = config.project_id
            project_number = config.project_number
            project_url = config.project_url
        else:
            project = creator.create_project(
                owner_id=owner_id,
                title=f"Spec-Kit: {doc.title}",
                description=f"Auto-generated from {tasks_file.name}"
            )
            project_id = project["id"]
            project_number = project["number"]
            project_url = project["url"]
            
            # Update config immediately
            config.project_id = project_id
            config.project_number = project_number
            config.project_url = project_url
            save_config(project_root, config)
        
        # Setup custom fields
        console.print("\n[bold cyan]Step 5:[/bold cyan] Setting up custom fields")
        
        # Extract unique phases and user stories
        phase_names = [f"Phase {p.number}: {p.title}" for p in doc.phases]
        user_stories = list(set(
            [g.user_story for p in doc.phases for g in p.groups if g.user_story] +
            [t.user_story for t in doc.all_tasks if t.user_story]
        ))
        
        field_ids = creator.setup_custom_fields(
            project_id=project_id,
            phases=phase_names,
            user_stories=user_stories
        )
        
        # Store field IDs in config
        config.field_ids = field_ids
        save_config(project_root, config)
        
        # Create labels
        console.print("\n[bold cyan]Step 6:[/bold cyan] Creating labels")
        issue_manager = IssueManager(self.client, repo_id)
        issue_manager.create_labels(doc.phases, user_stories)
        
        # Create task issues
        console.print("\n[bold cyan]Step 7:[/bold cyan] Creating issues")
        task_issue_map = issue_manager.create_task_issues(
            doc=doc,
            project_id=project_id,
            field_ids=field_ids
        )
        
        # Create dependencies
        console.print("\n[bold cyan]Step 8:[/bold cyan] Setting up dependencies")
        issue_manager.create_dependencies(dep_graph, task_issue_map)
        
        # Update sync state
        console.print("\n[bold cyan]Step 9:[/bold cyan] Updating sync state")
        content_hash = self._calculate_hash(content)
        config.last_synced_at = datetime.utcnow().isoformat() + "Z"
        config.last_synced_tasks_md_hash = content_hash
        save_config(project_root, config)
        
        console.print(f"\n[bold green]✓ Sync complete![/bold green]")
        console.print(f"\n[cyan]Project URL:[/cyan] {project_url}")
        
        return config
    
    def _get_repository_info(self, owner: str, name: str) -> Dict[str, Any]:
        """Get repository information."""
        variables = {"owner": owner, "name": name}
        result = self.client.execute(GET_REPOSITORY_QUERY, variables)
        return result["repository"]
    
    def _calculate_hash(self, content: str) -> str:
        """Calculate SHA256 hash of content."""
        return hashlib.sha256(content.encode()).hexdigest()
    
    def needs_sync(self, tasks_file: Path, config: GitHubProjectsConfig) -> bool:
        """
        Check if sync is needed.
        
        Args:
            tasks_file: Path to tasks.md file
            config: Current configuration
            
        Returns:
            True if sync is needed
        """
        # No project yet
        if not config.project_id:
            return True
        
        # Never synced
        if not config.last_synced_tasks_md_hash:
            return True
        
        # Check if content changed
        content = tasks_file.read_text()
        current_hash = self._calculate_hash(content)
        
        return current_hash != config.last_synced_tasks_md_hash
