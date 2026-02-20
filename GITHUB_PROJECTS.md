# GitHub Projects Integration for Spec-Kit

> **Status**: Phase 1 Complete (Configuration & CLI) | Phase 2+ In Progress

## Overview

Spec-Kit now supports optional integration with GitHub Projects to automatically create and sync project boards from your `tasks.md` files. This integration provides a visual project management interface that stays in sync with your specification-driven development workflow.

## Features

### ✅ Phase 1 Complete (v0.2.0)

- **Configuration Management**: Store GitHub Projects settings in `.specify/github-projects.json`
- **CLI Commands**: Full command group for managing integration
  - `specify projects enable` - Enable integration and configure repository
  - `specify projects disable` - Disable integration
  - `specify projects status` - View current configuration
  - `specify projects sync` - Sync tasks.md with GitHub Project
- **Tasks.md Parser**: Comprehensive parser for Spec-Kit tasks.md format
  - Extract phases, user stories, tasks
  - Parse metadata (completion, priorities, parallel markers)
  - Extract file paths from descriptions
- **Dependency Graph**: Automatic dependency inference following Spec-Kit conventions
  - Sequential task dependencies
  - Parallel task grouping
  - Cross-phase boundaries
- **Authentication**: Multiple token resolution methods
  - Command-line flag (`--token`)
  - Environment variables (`GH_TOKEN`, `GITHUB_TOKEN`)
  - GitHub CLI (`gh auth token`)

### 🚧 Phase 2+ In Progress

- **GitHub GraphQL API Client**: Not yet implemented
- **Project Creator**: Orchestration for creating GitHub Projects
- **Project Updater**: Bidirectional sync between tasks.md and Projects
- **Custom Fields**: Priority, Phase, User Story, Task ID, Status
- **Three-Level Hierarchy**: Phase → Story Group → Task (using sub-issues)
- **Dependency Visualization**: Using GitHub's native issue dependencies

## Installation

GitHub Projects integration is included in Spec-Kit v0.2.0+. No additional installation required.

## Quick Start

### 1. Enable GitHub Projects

From your Spec-Kit project root:

```bash
specify projects enable
```

This will:
- Detect your GitHub repository from git remote
- Prompt for confirmation
- Store configuration in `.specify/github-projects.json`

### 2. Check Status

```bash
specify projects status
```

Expected output:
```
╭────────────── GitHub Projects Status ──────────────╮
│ Enabled      Yes                                   │
│ Repository   owner/repo-name                       │
│ Project      No project created yet                │
╰────────────────────────────────────────────────────╯

Run 'specify projects sync' to create a project
```

### 3. Sync Your Tasks (Coming Soon)

```bash
# Auto-detect tasks.md in specs/ directory
specify projects sync

# Or specify explicitly
specify projects sync specs/001-feature/tasks.md
```

## Architecture

### Module Structure

```
src/specify_cli/
├── github/
│   ├── __init__.py          # Module exports
│   ├── auth.py              # Token resolution and validation
│   ├── config.py            # Configuration management
│   ├── graphql_client.py    # [TODO] GraphQL API client
│   ├── queries.py           # [TODO] GraphQL queries
│   ├── mutations.py         # [TODO] GraphQL mutations
│   ├── project_creator.py   # [TODO] Project creation orchestration
│   └── project_updater.py   # [TODO] Project sync logic
└── parser/
    ├── __init__.py          # Module exports
    ├── models.py            # Data models (Task, Phase, etc.)
    ├── tasks_parser.py      # Tasks.md parser
    └── dependency_graph.py  # Dependency inference
```

### Data Models

#### Task
```python
@dataclass
class Task:
    id: str                      # e.g., "T001"
    description: str
    is_completed: bool           # [X] vs [ ]
    is_parallel: bool            # [P] marker
    user_story: Optional[str]    # e.g., "US1"
    file_paths: list[str]        # Extracted paths
    phase_number: int
    group_title: Optional[str]
```

#### Phase
```python
@dataclass
class Phase:
    number: int
    title: str
    purpose: Optional[str]
    goal: Optional[str]
    checkpoint: Optional[str]
    priority: Optional[str]      # e.g., "P1"
    user_story: Optional[str]    # e.g., "US1"
    is_mvp: bool                 # 🎯 marker
    groups: list[StoryGroup]
    direct_tasks: list[Task]
```

#### DependencyGraph
```python
@dataclass
class DependencyGraph:
    dependencies: dict[str, list[str]]  # task_id → blockers
    
    def add_dependency(task_id, depends_on)
    def get_blockers(task_id) -> list[str]
```

### Dependency Inference Rules

The dependency graph follows Spec-Kit conventions:

1. **Within a Phase**:
   - Sequential tasks: Each depends on previous non-parallel task
   - Parallel tasks `[P]`: All depend on last sequential "anchor" task
   - Parallel tasks do NOT block each other

2. **Across Phases**:
   - First task of Phase N depends on last task of Phase N-1

Example:
```
- [ ] T001 Setup project                    # No dependencies
- [ ] T002 Install dependencies              # Depends on: T001
- [ ] T003 [P] Configure linting             # Depends on: T002
- [ ] T004 [P] Configure testing             # Depends on: T002 (not T003)
- [ ] T005 Run initial tests                 # Depends on: T002 (last sequential)
```

## Configuration File

Location: `.specify/github-projects.json`

```json
{
  "enabled": true,
  "repo_owner": "username",
  "repo_name": "project",
  "project_number": 42,
  "project_id": "PVT_kwDOABCD...",
  "project_url": "https://github.com/users/username/projects/42",
  "field_ids": {
    "Priority": "PVTF_lADOABCD...",
    "Phase": "PVTF_lADOABCD...",
    "User Story": "PVTF_lADOABCD...",
    "Task ID": "PVTF_lADOABCD..."
  },
  "last_synced_at": "2026-02-19T13:00:00Z",
  "last_synced_tasks_md_hash": "abc123..."
}
```

## Planned GitHub Project Structure

### Custom Fields

| Field Name | Type | Values | Purpose |
|------------|------|--------|---------|
| Task ID | Text | T001, T002, ... | Unique identifier for sync |
| Phase | Single Select | Phase 1: Setup, Phase 2: Foundation, ... | Phase grouping |
| User Story | Single Select | US1, US2, US3, N/A | Story mapping |
| Priority | Single Select | P1 - Critical, P2 - High, P3 - Medium | Priority levels |
| Status | Status | Todo, In Progress, Done | Completion tracking |
| Parallel | Single Select | Yes, No | Parallelizable indicator |

### Three-Level Hierarchy

Using GitHub's sub-issues feature:

```
📦 Phase 1: Setup (Shared Infrastructure)          [Phase Issue]
  └─ 📦 Project Initialization                     [Story Group]
      ├─ ☑️ [T001] Create directory structure     [Task]
      ├─ ☑️ [T002] Initialize project             [Task]
      └─ ⬜ [T003] Configure tools                [Task]
```

### Dependency Visualization

GitHub Projects will show:
- **Blocks**: T002 blocks T003, T004
- **Blocked by**: T005 is blocked by T002

This creates a clear visual dependency chain in the project board.

## CLI Command Reference

### `specify projects enable`

Enable GitHub Projects integration for the current repository.

**Options:**
- `--token TEXT` - GitHub personal access token

**Example:**
```bash
specify projects enable
specify projects enable --token ghp_xxx...
```

### `specify projects disable`

Disable GitHub Projects integration without deleting the configuration.

**Example:**
```bash
specify projects disable
```

### `specify projects status`

Show current GitHub Projects integration status and configuration.

**Example:**
```bash
specify projects status
```

### `specify projects sync`

Sync tasks.md with GitHub Project (create or update).

**Arguments:**
- `TASKS_FILE` (optional) - Path to tasks.md file

**Options:**
- `--token TEXT` - GitHub personal access token
- `--dry-run, -n` - Show what would be done without making changes

**Examples:**
```bash
# Auto-detect tasks.md
specify projects sync

# Specify file explicitly
specify projects sync specs/001-feature/tasks.md

# Dry run
specify projects sync --dry-run
```

## Authentication

### Token Requirements

GitHub Projects requires a Personal Access Token with the following scopes:
- `repo` - Full control of private repositories
- `project` - Full control of projects

### Creating a Token

1. Go to GitHub Settings → Developer settings → Personal access tokens → Fine-grained tokens
2. Click "Generate new token"
3. Give it a descriptive name (e.g., "Spec-Kit GitHub Projects")
4. Select repository access (specific repositories or all)
5. Select permissions:
   - Repository: Read and Write access to Contents, Issues
   - Organization: Read and Write access to Projects
6. Generate token and save it securely

### Providing the Token

**Method 1: Environment variable** (Recommended)
```bash
export GH_TOKEN="ghp_xxx..."
specify projects enable
```

**Method 2: Command-line flag**
```bash
specify projects enable --token ghp_xxx...
```

**Method 3: GitHub CLI** (Automatic)
```bash
gh auth login
specify projects enable  # Uses gh CLI token
```

## Troubleshooting

### "Not a git repository"

GitHub Projects integration requires a git repository with a GitHub remote.

```bash
git init
git remote add origin https://github.com/username/repo.git
```

### "No GitHub token found"

Provide a token using one of the methods above.

### "Could not parse GitHub repository"

Ensure your git remote URL is a valid GitHub URL:

```bash
git remote -v
# Should show: origin  https://github.com/username/repo.git (fetch)
```

### "Multiple tasks.md files found"

Specify which tasks.md to sync:

```bash
specify projects sync specs/001-feature/tasks.md
```

## Development Status

| Phase | Status | Description |
|-------|--------|-------------|
| 1 | ✅ Complete | Configuration & CLI commands |
| 2 | 🚧 In Progress | GitHub GraphQL API client |
| 3 | 🚧 In Progress | Project creator orchestration |
| 4 | ⏳ Planned | Project updater & sync |
| 5 | ⏳ Planned | Integration with task commands |
| 6 | ⏳ Planned | Documentation & examples |
| 7 | ⏳ Planned | Testing & validation |

## Roadmap

### v0.2.0 (Current)
- ✅ CLI commands and configuration
- ✅ Tasks.md parser
- ✅ Dependency graph builder

### v0.3.0 (Next)
- ⏳ GitHub GraphQL API integration
- ⏳ Project creation from tasks.md
- ⏳ Custom fields setup
- ⏳ Issue hierarchy creation

### v0.4.0 (Future)
- ⏳ Bidirectional sync
- ⏳ Automatic sync on task updates
- ⏳ Conflict detection and resolution

### v0.5.0 (Future)
- ⏳ Support for organization projects
- ⏳ Template projects
- ⏳ Advanced dependency visualization

## Contributing

Contributions are welcome! See the implementation plan in `.copilot/session-state/.../plan.md` for details on pending work.

### Running Tests

```bash
# Unit tests (when implemented)
pytest tests/github/
pytest tests/parser/

# Manual parser test
python -c "
from pathlib import Path
from specify_cli.parser import parse_tasks_md, build_dependency_graph

content = Path('specs/001-feature/tasks.md').read_text()
doc = parse_tasks_md(content)
print(f'Phases: {len(doc.phases)}, Tasks: {doc.task_count}')
"
```

## License

MIT License - See LICENSE file for details.

## Related Documentation

- [Spec-Driven Development](spec-driven.md)
- [Spec Kit README](README.md)
- [Templates](templates/)
- [Implementation Plan](.copilot/session-state/.../plan.md)
