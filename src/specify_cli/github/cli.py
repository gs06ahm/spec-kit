"""GitHub Projects CLI subcommands for Specify CLI."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

console = Console()

projects_app = typer.Typer(
    name="projects",
    help="Manage GitHub Projects integration",
    add_completion=False,
)


@projects_app.command("enable")
def projects_enable(
    github_token: Optional[str] = typer.Option(None, "--token", help="GitHub personal access token"),
    force: bool = typer.Option(False, "--force", "-f", help="Reconfigure even if already enabled"),
):
    """Enable GitHub Projects integration for the current repository."""
    from .auth import resolve_github_token
    from .config import load_config, save_config, GitHubProjectsConfig

    project_root = Path.cwd()

    # Check if we're in a git repository
    if not (project_root / ".git").exists():
        console.print("[red]Error:[/red] Not a git repository")
        console.print("GitHub Projects integration requires a git repository")
        raise typer.Exit(1)

    # Resolve GitHub token
    token = resolve_github_token(github_token)
    if not token:
        console.print("[red]Error:[/red] No GitHub token found")
        console.print("\nPlease provide a token via:")
        console.print("  • --token flag")
        console.print("  • GH_TOKEN or GITHUB_TOKEN environment variable")
        console.print("  • gh auth login (GitHub CLI)")
        raise typer.Exit(1)

    # Get repository info from git
    try:
        import subprocess
        import re
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True,
        )
        remote_url = result.stdout.strip()
        if not remote_url:
            console.print("[red]Error:[/red] No git remote 'origin' found")
            raise typer.Exit(1)

        # Parse owner/repo from URL
        # Supports: git@github.com:owner/repo.git or https://github.com/owner/repo.git
        match = re.search(r'github\.com[:/]([^/]+)/([^/\.]+)', remote_url)
        if not match:
            console.print(f"[red]Error:[/red] Could not parse GitHub repository from: {remote_url}")
            raise typer.Exit(1)

        repo_owner = match.group(1)
        repo_name = match.group(2)

    except (subprocess.CalledProcessError, Exception) as e:
        console.print(f"[red]Error:[/red] Failed to get repository info: {e}")
        raise typer.Exit(1)

    # Load existing config
    config = load_config(project_root)

    if config.enabled and not force:
        console.print("[yellow]GitHub Projects is already enabled[/yellow]")
        console.print(f"\nRepository: {config.repo_owner}/{config.repo_name}")
        if config.project_url:
            console.print(f"Project URL: {config.project_url}")
        console.print("\nUse --force to reconfigure.")
        raise typer.Exit(0)

    # Enable and save config
    config.enabled = True
    config.repo_owner = repo_owner
    config.repo_name = repo_name
    save_config(project_root, config)

    console.print("[green]✓[/green] GitHub Projects integration enabled")
    console.print(f"\nRepository: {repo_owner}/{repo_name}")
    console.print("\nNext steps:")
    console.print("  1. Create a feature spec with tasks.md")
    console.print("  2. Run 'specify projects sync' to create/update the GitHub Project")


@projects_app.command("disable")
def projects_disable():
    """Disable GitHub Projects integration."""
    from .config import load_config, save_config

    project_root = Path.cwd()
    config = load_config(project_root)

    if not config.enabled:
        console.print("[yellow]GitHub Projects is not enabled[/yellow]")
        raise typer.Exit(0)

    config.enabled = False
    save_config(project_root, config)

    console.print("[green]✓[/green] GitHub Projects integration disabled")
    console.print("\nConfiguration has been saved. To re-enable:")
    console.print("  specify projects enable")


@projects_app.command("status")
def projects_status():
    """Show GitHub Projects integration status."""
    from .config import load_config

    project_root = Path.cwd()
    config = load_config(project_root)

    table = Table(title="GitHub Projects Status", show_header=False)
    table.add_column("Setting", style="cyan")
    table.add_column("Value")

    table.add_row("Enabled", "[green]Yes[/green]" if config.enabled else "[red]No[/red]")

    if config.enabled:
        table.add_row("Repository", f"{config.repo_owner}/{config.repo_name}" if config.repo_owner else "[dim]Not set[/dim]")
        table.add_row("Project Number", str(config.project_number) if config.project_number else "[dim]No project created yet[/dim]")

        if config.project_url:
            table.add_row("Project URL", config.project_url)

        if config.last_synced_at:
            table.add_row("Last Synced", config.last_synced_at)

    console.print(table)

    if not config.enabled:
        console.print("\n[dim]Run 'specify projects enable' to get started[/dim]")
    elif not config.project_number:
        console.print("\n[dim]Run 'specify projects sync' to create a project[/dim]")


@projects_app.command("sync")
def projects_sync(
    tasks_file: Optional[Path] = typer.Argument(None, help="Path to tasks.md file"),
    github_token: Optional[str] = typer.Option(None, "--token", help="GitHub personal access token"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would be done without making changes"),
):
    """Sync tasks.md with GitHub Project (create or update)."""
    from .auth import resolve_github_token
    from .config import load_config

    project_root = Path.cwd()
    config = load_config(project_root)

    if not config.enabled:
        console.print("[red]Error:[/red] GitHub Projects is not enabled")
        console.print("Run 'specify projects enable' first")
        raise typer.Exit(1)

    # Resolve token (not required for dry-run preview)
    token = resolve_github_token(github_token)
    if not token and not dry_run:
        console.print("[red]Error:[/red] No GitHub token found")
        raise typer.Exit(1)

    # Find tasks.md if not specified
    if not tasks_file:
        specs_dir = project_root / "specs"
        if specs_dir.exists():
            tasks_files = list(specs_dir.glob("*/tasks.md"))
            if len(tasks_files) == 0:
                console.print("[red]Error:[/red] No tasks.md found in specs/ directory")
                raise typer.Exit(1)
            elif len(tasks_files) == 1:
                tasks_file = tasks_files[0]
            else:
                console.print("[yellow]Multiple tasks.md files found:[/yellow]")
                for i, f in enumerate(tasks_files, 1):
                    console.print(f"  {i}. {f.relative_to(project_root)}")
                console.print("\nPlease specify which one to sync:")
                console.print("  specify projects sync <path-to-tasks.md>")
                raise typer.Exit(1)
        else:
            console.print("[red]Error:[/red] No specs/ directory found")
            raise typer.Exit(1)

    # Resolve to absolute path if relative
    if not tasks_file.is_absolute():
        tasks_file = project_root / tasks_file

    if not tasks_file.exists():
        console.print(f"[red]Error:[/red] File not found: {tasks_file}")
        raise typer.Exit(1)

    if dry_run:
        console.print("[yellow]DRY RUN MODE[/yellow] – no changes will be made\n")

    console.print(f"Syncing: {tasks_file.relative_to(project_root)}")
    console.print(f"Repository: {config.repo_owner}/{config.repo_name}\n")

    from .graphql_client import GraphQLClient
    from .sync_engine import SyncEngine

    try:
        if dry_run:
            # Dry run: use a dummy token since no API calls will be made
            _token = token or "dry-run-placeholder"
            with GraphQLClient(_token) as gql_client:
                engine = SyncEngine(gql_client)
                engine.sync_tasks_to_project(
                    tasks_file=tasks_file,
                    config=config,
                    project_root=project_root,
                    dry_run=True,
                )
        else:
            with GraphQLClient(token) as gql_client:
                engine = SyncEngine(gql_client)
                engine.sync_tasks_to_project(
                    tasks_file=tasks_file,
                    config=config,
                    project_root=project_root,
                    dry_run=False,
                )
                console.print(f"\n[bold green]✓ Sync completed successfully![/bold green]")

    except Exception as e:
        console.print(f"\n[red]Error during sync:[/red] {str(e)}")
        import traceback
        traceback.print_exc()
        raise typer.Exit(1)
