#!/usr/bin/env python3
"""
Manual test script for GitHub Projects integration.

This script guides you through testing the sync functionality with a real GitHub repository.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from rich.console import Console
from rich.prompt import Prompt, Confirm

console = Console()


def main():
    console.print("\n[bold cyan]GitHub Projects Integration - Manual Test[/bold cyan]\n")
    
    console.print("This test will:")
    console.print("  1. Create a test project")
    console.print("  2. Enable GitHub Projects")
    console.print("  3. Run the sync command")
    console.print("  4. Verify the created project\n")
    
    # Check prerequisites
    console.print("[bold]Prerequisites:[/bold]")
    console.print("  ✓ specify CLI installed")
    console.print("  ✓ GitHub token with 'repo' and 'project' scopes")
    console.print("  ✓ GitHub repository to test with\n")
    
    if not Confirm.ask("Do you have these prerequisites?"):
        console.print("[yellow]Please set up prerequisites first.[/yellow]")
        return
    
    # Get GitHub details
    console.print("\n[bold]GitHub Configuration:[/bold]")
    gh_token = Prompt.ask("GitHub Token (or press Enter to use $GITHUB_TOKEN)")
    if not gh_token:
        gh_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if not gh_token:
            console.print("[red]No token found in environment variables[/red]")
            return
    
    repo_owner = Prompt.ask("Repository Owner (e.g., 'username')")
    repo_name = Prompt.ask("Repository Name (e.g., 'my-test-repo')")
    
    # Create test directory
    test_dir = Path("/tmp/gh-projects-test")
    console.print(f"\n[bold]Creating test project:[/bold] {test_dir}")
    
    if test_dir.exists():
        if not Confirm.ask(f"{test_dir} exists. Remove it?"):
            return
        os.system(f"rm -rf {test_dir}")
    
    # Initialize test project
    test_dir.mkdir(parents=True)
    os.chdir(test_dir)
    
    console.print("  Initializing git...")
    os.system("git init -q")
    os.system("git config user.email 'test@example.com'")
    os.system("git config user.name 'Test User'")
    os.system(f"git remote add origin https://github.com/{repo_owner}/{repo_name}.git")
    
    console.print("  Creating tasks.md...")
    specs_dir = test_dir / "specs" / "001-test-feature"
    specs_dir.mkdir(parents=True)
    
    tasks_md = specs_dir / "tasks.md"
    tasks_md.write_text("""# Tasks: GitHub Projects Integration Test

## Phase 1: Setup

### User Story 1: Project Initialization
As a developer, I want to set up the project structure.

#### Tasks
- [ ] T001: Create directory structure (`src/`)
- [ ] T002: Initialize package configuration (`package.json`)
- [ ] T003: Set up development environment (`.env`)

## Phase 2: Implementation

### User Story 2: Core Features
As a user, I want core functionality implemented.

#### Tasks
- [ ] T004: Implement main module (`src/main.py`)
- [ ] T005: Add validation logic (`src/validator.py`)
- [ ] T006: Create API endpoints (`src/api.py`)

### User Story 3: Testing
As a developer, I want comprehensive test coverage.

#### Tasks
- [ ] T007: Write unit tests (`tests/unit/`)
- [ ] T008: Write integration tests (`tests/integration/`)
- [ ] T009: Set up CI/CD pipeline (`.github/workflows/ci.yml`)
""")
    
    # Set environment variable
    os.environ["GITHUB_TOKEN"] = gh_token
    
    # Enable GitHub Projects
    console.print("\n[bold]Enabling GitHub Projects...[/bold]")
    result = os.system("specify projects enable")
    if result != 0:
        console.print("[red]Failed to enable projects[/red]")
        return
    
    # Run sync
    console.print("\n[bold]Running sync...[/bold]")
    result = os.system("specify projects sync specs/001-test-feature/tasks.md")
    if result != 0:
        console.print("[red]Sync failed[/red]")
        return
    
    # Show status
    console.print("\n[bold]Project Status:[/bold]")
    os.system("specify projects status")
    
    # Read config to get project URL
    import json
    config_file = test_dir / ".specify" / "github-projects.json"
    if config_file.exists():
        config = json.loads(config_file.read_text())
        project_url = config.get("project_url")
        
        if project_url:
            console.print(f"\n[bold green]✓ Success![/bold green]")
            console.print(f"\n[cyan]Project URL:[/cyan] {project_url}")
            console.print("\n[bold]Next Steps:[/bold]")
            console.print("  1. Open the project URL in your browser")
            console.print("  2. Verify the custom fields are created")
            console.print("  3. Check that all 9 issues are present")
            console.print("  4. Verify labels (phase-1, phase-2, user-story-*)")
            console.print("  5. Check custom field values for each issue\n")
        else:
            console.print("[yellow]Project created but URL not found in config[/yellow]")
    else:
        console.print("[yellow]Config file not found[/yellow]")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}")
        import traceback
        traceback.print_exc()
