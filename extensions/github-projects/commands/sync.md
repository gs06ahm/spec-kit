---
description: "Sync tasks.md to GitHub Projects v2"
---

# Sync tasks.md to GitHub Projects

<!-- Extension: github-projects -->
<!-- Config: .specify/extensions/github-projects/ -->

Synchronize the current `tasks.md` spec with the GitHub Projects v2 board for this
repository. This creates (or updates) a three-level issue hierarchy:
**Phase → Task Group → Task**.

## Prerequisites

1. GitHub Projects integration must be enabled:
   ```bash
   specify projects status
   ```
   If not enabled, run `/speckit.github-projects.enable` first.

2. A valid `tasks.md` must exist under `specs/`.

3. A GitHub token with `repo` and `project` scopes must be available via:
   - `GH_TOKEN` or `GITHUB_TOKEN` environment variable, or
   - `gh auth login` (GitHub CLI).

## User Input

$ARGUMENTS

## Steps

### Step 1: Check configuration

Verify the integration is enabled and a project exists:

```bash
specify projects status
```

If the output shows `Enabled: No`, stop and ask the user to run
`/speckit.github-projects.enable` before continuing.

### Step 2: Locate tasks.md

Find the tasks file to sync. If the user supplied a path in `$ARGUMENTS`, use
that. Otherwise, let `specify projects sync` auto-discover it:

```bash
# Auto-discover (recommended when there is only one tasks.md)
specify projects sync

# Or pass a path explicitly
specify projects sync specs/my-feature/tasks.md
```

### Step 3: Preview with --dry-run (optional)

Before writing to GitHub, show a summary of what would be created:

```bash
specify projects sync --dry-run
```

Confirm with the user that the preview looks correct.

### Step 4: Run the sync

```bash
specify projects sync
```

The command will:
- Parse `tasks.md` and build the dependency graph
- Create (or reuse) the GitHub Project
- Set up custom fields: Task ID, Phase, User Story, Priority, Parallel
- Create Phase / Task Group / Task issues (idempotent – safe to re-run)
- Set field values on every project item
- Link task dependencies

### Step 5: Share the result

After a successful sync, the project URL is printed.
Share it with the user and suggest bookmarking it:

```
✓ Sync complete!
Project URL: https://github.com/orgs/<owner>/projects/<number>
```

## Configuration Reference

Settings are read from `.specify/extensions/github-projects/github-projects-config.yml`
(if it exists) and can be overridden with environment variables:

| Setting | Env override | Description |
|---------|-------------|-------------|
| `github.token` | `GH_TOKEN` | GitHub personal access token |
| `github.dry_run` | — | Default to `--dry-run` mode |
| `github.auto_sync` | — | Auto-sync without prompting |

## Troubleshooting

### "GitHub Projects is not enabled"

Run `/speckit.github-projects.enable` to configure the integration.

### "No tasks.md found in specs/ directory"

Pass the path explicitly:
```bash
specify projects sync path/to/tasks.md
```

### Rate limit errors

Use a GitHub token (`GH_TOKEN=ghp_...`) to raise the limit from 60 to 5 000 req/hr.

## Examples

### Sync with auto-discovery

```
/speckit.github-projects.sync
```

### Preview only

```
/speckit.github-projects.sync --dry-run
```

### Sync a specific file

```
/speckit.github-projects.sync specs/backend-api/tasks.md
```
