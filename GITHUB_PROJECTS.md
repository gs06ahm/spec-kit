# GitHub Projects Integration

Specify CLI can automatically synchronize your `tasks.md` spec files with a **GitHub Projects v2** board, creating a three-level issue hierarchy (Phase → Task Group → Task) with custom fields and dependency links.

## Installation as a Spec-Kit Extension

The GitHub Projects integration ships as a first-party **spec-kit extension**.
Install it with:

```bash
specify extension add extensions/github-projects
```

Once installed, your AI agent (Claude, Copilot, Gemini, etc.) gains two new
slash commands:

| Command | What it does |
|---------|-------------|
| `/speckit.github-projects.enable` | Enable and configure the integration |
| `/speckit.github-projects.sync` | Sync `tasks.md` → GitHub Projects v2 |

The extension also registers an `after_tasks` hook that prompts your AI agent
to sync whenever `/speckit.tasks` generates a new `tasks.md`.

To view the extension in the catalog:
```bash
specify extension search github-projects
```

---

## Quick Start

### 1. Enable the integration

```bash
specify projects enable
```

This detects your `origin` remote and stores `repo_owner` / `repo_name` in `.specify/github-projects.json`.

A GitHub token is required. Provide it via:

| Method | Example |
|--------|---------|
| `--token` flag | `specify projects enable --token ghp_xxx` |
| `GH_TOKEN` env var | `export GH_TOKEN=ghp_xxx` |
| `GITHUB_TOKEN` env var | `export GITHUB_TOKEN=ghp_xxx` |
| GitHub CLI | `gh auth login` |

If the integration is already enabled and you want to reconfigure, pass `--force`:

```bash
specify projects enable --force
```

### 2. Preview a sync (dry run)

`--dry-run` parses `tasks.md`, builds the full plan, and prints a summary table.
**No writes are made** – no GraphQL mutations, no config file changes.

```bash
specify projects sync --dry-run
# or
specify projects sync specs/my-feature/tasks.md --dry-run
```

### 3. Run the sync

```bash
specify projects sync
```

This will:

1. Parse `tasks.md`
2. Build the dependency graph
3. Fetch repository info
4. Create (or reuse) the GitHub Project
5. Set up custom fields (Task ID, Phase, User Story, Priority, Parallel)
6. Create the issue hierarchy (Phase → Task Group → Task) – idempotent
7. Set custom field values on each project item
8. Link issue dependencies

### 4. Check status

```bash
specify projects status
```

### 5. Disable the integration

```bash
specify projects disable
```

---

## Commands Reference

```
specify projects enable   [--token TOKEN] [--force]
specify projects disable
specify projects status
specify projects sync     [TASKS_FILE] [--token TOKEN] [--dry-run]
```

---

## How It Works

### Issue Hierarchy

For a `tasks.md` with this structure:

```markdown
## Phase 1: Foundation
### Task Group: Setup
- [ ] T001 Initialize project
- [ ] T002 [P] Write tests
```

The sync creates:

- 📦 **Phase 1: Foundation** (top-level issue, added to project)
  - 📂 **Setup** (sub-issue of phase)
    - 📝 **[T001] Initialize project** (sub-issue of group)
    - 📝 **[T002] Write tests** (parallel, sub-issue of group)

### Custom Fields

| Field | Type | Description |
|-------|------|-------------|
| Task ID | Text | e.g. `T001` |
| Phase | Single Select | e.g. `Phase 1: Foundation` |
| User Story | Single Select | e.g. `US1` |
| Priority | Single Select | P1–P4 or N/A |
| Parallel | Single Select | Yes / No |

### Idempotent Syncs

Re-running `specify projects sync` is safe:

- **Existing issues** are matched by title + parent and reused (body updated if changed).
- **Project items** – if an issue is already in the project board, `addProjectV2ItemById` is **not** called again.
- **Dependencies** – duplicate `addBlockedBy` errors are caught and silently skipped.

### Dry Run Guarantee

`--dry-run` never calls any GraphQL **mutation**. It only:

- Reads and parses `tasks.md`
- Builds the dependency graph
- Prints the plan

No network writes, no config changes.

---

## Configuration File

`.specify/github-projects.json`:

```json
{
  "enabled": true,
  "repo_owner": "my-org",
  "repo_name": "my-repo",
  "project_number": 42,
  "project_id": "PVT_...",
  "project_url": "https://github.com/orgs/my-org/projects/42",
  "field_ids": { ... },
  "last_synced_at": "2026-02-21T12:00:00Z",
  "last_synced_tasks_md_hash": "sha256..."
}
```

This file should be committed to version control so all contributors share the same project configuration.

---

## Token Permissions

Your GitHub token needs the following scopes:

| Scope | Reason |
|-------|--------|
| `repo` | Read repository metadata, create issues |
| `project` | Create and update Projects v2 |

---

## Troubleshooting

**"GitHub Projects is not enabled"**  
Run `specify projects enable` first.

**"No tasks.md found in specs/ directory"**  
Either pass the file path explicitly (`specify projects sync path/to/tasks.md`) or ensure you have a `specs/*/tasks.md` file.

**Rate limit errors**  
Large repositories with many tasks may hit GitHub's GraphQL rate limit (5,000 requests/hour for authenticated users). The client automatically adds delays when the remaining budget is low. Consider running the sync during off-peak hours.
