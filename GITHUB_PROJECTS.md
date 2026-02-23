# GitHub Projects Integration

Specify CLI can automatically synchronize your `tasks.md` spec files with a **GitHub Projects v2** board, creating a three-level issue hierarchy (Phase → Task Group → Task) with custom fields and dependency links.

## Developer How-To (Tested): Initialize from fork + verify GitHub Projects integration

This section is a **tested runbook** using this local fork checkout at `/home/adam/src/spec-kit`.

### 0) Use the forked CLI code explicitly

```bash
$ uv run --project /home/adam/src/spec-kit specify projects --help

Usage: specify projects [OPTIONS] COMMAND [ARGS]...

Manage GitHub Projects integration

╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                          │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ enable   Enable GitHub Projects integration for the current repository.                                              │
│ disable  Disable GitHub Projects integration.                                                                        │
│ status   Show GitHub Projects integration status.                                                                    │
│ sync     Sync tasks.md with GitHub Project (create or update).                                                       │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

[exit 0]
```

### 1) Confirm exposed settings (gh proj)

#### CLI flags

```bash
$ uv run --project /home/adam/src/spec-kit specify projects enable --help

Usage: specify projects enable [OPTIONS]

Enable GitHub Projects integration for the current repository.

╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --token          TEXT  GitHub personal access token                                                                  │
│ --force  -f            Reconfigure even if already enabled                                                           │
│ --help                 Show this message and exit.                                                                   │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

[exit 0]

$ uv run --project /home/adam/src/spec-kit specify projects sync --help

Usage: specify projects sync [OPTIONS] [TASKS_FILE]

Sync tasks.md with GitHub Project (create or update).

╭─ Arguments ──────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│   tasks_file      [TASKS_FILE]  Path to tasks.md file                                                                │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --token            TEXT  GitHub personal access token                                                                │
│ --dry-run  -n            Show what would be done without making changes                                              │
│ --help                   Show this message and exit.                                                                 │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

[exit 0]
```

`init` also exposes GitHub auth support:

```bash
$ uv run --project /home/adam/src/spec-kit specify init --help | sed -n '1,120p'
...
│ --github-token              TEXT  GitHub token to use for API requests (or set GH_TOKEN or GITHUB_TOKEN environment  │
│                                   variable)                                                                          │
...
[exit 0]
```

#### Extension settings file

```bash
$ sed -n '1,120p' /home/adam/src/spec-kit/extensions/github-projects/config-template.yml
# GitHub Projects Integration Configuration
#
# This file configures the spec-kit GitHub Projects extension.
# Copy this file to github-projects-config.yml and edit as needed.
#
# IMPORTANT: If you set github.token here, add this file to .gitignore
# to avoid committing credentials.

github:
  # GitHub personal access token (optional).
  # Required scopes: repo, project
  # Alternatively, set the GH_TOKEN or GITHUB_TOKEN environment variable.
  token: ""

  # Always preview changes without writing to GitHub.
  # Set to true to default every sync to --dry-run.
  dry_run: false

  # Automatically sync tasks.md when the after_tasks hook fires,
  # without prompting the user.
  auto_sync: false
[exit 0]
```

### 2) Initialize a fresh test repo

```bash
$ rm -rf /tmp/spec-kit-ghproj-e2e-final && mkdir -p /tmp/spec-kit-ghproj-e2e-final
[exit 0]

$ uv run --project /home/adam/src/spec-kit specify init /tmp/spec-kit-ghproj-e2e-final/spec-kit-ghproj-test --ai copilot --script sh
...
Initialize Specify Project
├── ● Check required tools (ok)
├── ● Select AI assistant (copilot)
├── ● Select script type (sh)
├── ● Fetch latest release (release v0.1.5 (59,861 bytes))
├── ● Download template (spec-kit-template-copilot-sh-v0.1.5.zip)
├── ● Extract template
├── ● Archive contents (38 entries)
├── ● Extraction summary (3 top-level items)
├── ● Ensure scripts executable (5 updated)
├── ● Constitution setup (copied from template)
├── ● Cleanup
├── ● Initialize git repository (initialized)
└── ● Finalize (project ready)
...
[exit 0]
```

### 3) Enable GitHub Projects integration in the new repo

```bash
$ test -d /tmp/spec-kit-ghproj-e2e-final/spec-kit-ghproj-test/.git && echo .git-directory-present
.git-directory-present
[exit 0]

$ git -C /tmp/spec-kit-ghproj-e2e-final/spec-kit-ghproj-test remote add origin git@github.com:gs06ahm/spec-kit-ghproj-test.git
[exit 0]

$ cd /tmp/spec-kit-ghproj-e2e-final/spec-kit-ghproj-test && uv run --project /home/adam/src/spec-kit specify projects enable --token ghp_dummy_token_for_enable
✓ GitHub Projects integration enabled

Repository: gs06ahm/spec-kit-ghproj-test

Next steps:
  1. Create a feature spec with tasks.md
  2. Run 'specify projects sync' to create/update the GitHub Project
[exit 0]
```

### 4) Verify integration state after init

```bash
$ cd /tmp/spec-kit-ghproj-e2e-final/spec-kit-ghproj-test && uv run --project /home/adam/src/spec-kit specify projects status
             GitHub Projects Status
┌────────────────┬──────────────────────────────┐
│ Enabled        │ Yes                          │
│ Repository     │ gs06ahm/spec-kit-ghproj-test │
│ Project Number │ No project created yet       │
└────────────────┴──────────────────────────────┘

Run 'specify projects sync' to create a project
[exit 0]

$ cd /tmp/spec-kit-ghproj-e2e-final/spec-kit-ghproj-test && python -m json.tool .specify/github-projects.json
{
    "enabled": true,
    "repo_owner": "gs06ahm",
    "repo_name": "spec-kit-ghproj-test",
    "project_number": null,
    "project_id": null,
    "project_url": null,
    "field_ids": null,
    "last_synced_at": null,
    "last_synced_tasks_md_hash": null
}
[exit 0]
```

### 5) Dry-run sync verification

```bash
$ cd /tmp/spec-kit-ghproj-e2e-final/spec-kit-ghproj-test && mkdir -p specs/001-ghproj-integration && printf '%s\n' '# Tasks: GitHub Projects Integration Verification' '' '## Phase 1: Setup' '' '### Task Group: Verification' '' '- [ ] T001 Create baseline task list' '- [ ] T002 [P] Validate dry-run sync output' > specs/001-ghproj-integration/tasks.md
[exit 0]

$ cd /tmp/spec-kit-ghproj-e2e-final/spec-kit-ghproj-test && uv run --project /home/adam/src/spec-kit specify projects sync specs/001-ghproj-integration/tasks.md --dry-run
DRY RUN MODE – no changes will be made

Syncing: specs/001-ghproj-integration/tasks.md
Repository: gs06ahm/spec-kit-ghproj-test

Step 1: Parsing tasks.md
  Found: 2 tasks across 1 phases

Step 2: Building dependency graph
  Found: 1 dependencies

──────────────────────────────────────────
DRY RUN – no changes will be made to GitHub
──────────────────────────────────────────

Project: Would create new project "Spec-Kit: GitHub Projects Integration Verification" for gs06ahm/spec-kit-ghproj-test
...
Dependencies: 1 links would be created
Custom fields: Task ID, Phase, User Story, Priority, Parallel

Dry run complete. Re-run without --dry-run to apply.
[exit 0]
```

### 6) Project UI URL to open

After your **first successful non-dry-run sync**, read `project_url` from `.specify/github-projects.json` and open that value directly in a browser.

- `project_url` is also shown by `specify projects status` once a project is created.
- Typical URL shape is:
  - `https://github.com/orgs/<owner>/projects/<number>` (organization-owned project), or
  - `https://github.com/users/<owner>/projects/<number>` (user-owned project).

In this dry-run-only test, `project_url` stayed `null`, which is expected.

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
