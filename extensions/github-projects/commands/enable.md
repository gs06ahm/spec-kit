---
description: "Enable GitHub Projects integration for this repository"
---

# Enable GitHub Projects Integration

<!-- Extension: github-projects -->
<!-- Config: .specify/extensions/github-projects/ -->

Configure the current repository so that `specify projects sync` can push
`tasks.md` specs to a **GitHub Projects v2** board.

## Prerequisites

1. You must be inside a git repository with a GitHub `origin` remote.
2. A GitHub token with `repo` and `project` scopes.

## User Input

$ARGUMENTS

## Steps

### Step 1: Obtain a GitHub token

If the user doesn't already have a token, guide them to create one:

- **GitHub CLI** (easiest):
  ```bash
  gh auth login
  ```
- **Personal access token** (classic): Settings → Developer settings → Personal
  access tokens → Generate new token.  
  Required scopes: `repo`, `project`.

Set the token in the shell:
```bash
export GH_TOKEN=ghp_your_token_here
```

### Step 2: Enable the integration

```bash
specify projects enable
```

If the integration was already enabled and the user wants to reconfigure:
```bash
specify projects enable --force
```

The command will:
- Detect `repo_owner` and `repo_name` from the `origin` remote
- Write `.specify/github-projects.json`

### Step 3: Verify

```bash
specify projects status
```

Expected output:
```
GitHub Projects Status
 Enabled       Yes
 Repository    <owner>/<repo>
 Project Number  No project created yet
```

### Step 4: Configure the extension (optional)

If a `github-projects-config.yml` is present, update it with any overrides:

```bash
cat .specify/extensions/github-projects/github-projects-config.yml
```

The most common override is setting a token so it doesn't need to be in the
environment every time:

```yaml
github:
  token: "ghp_your_token_here"  # keep this file out of version control
```

### Step 5: Run the first sync

```bash
specify projects sync
```

Or use the agent command:
```
/speckit.github-projects.sync
```

## Configuration Reference

| Setting | Env override | Description |
|---------|-------------|-------------|
| `github.token` | `GH_TOKEN` | GitHub personal access token |
| `github.dry_run` | — | Default to dry-run mode |
| `github.auto_sync` | — | Auto-sync without prompting |

## Troubleshooting

### "Not a git repository"

Run this command from the root of your git repository.

### "Could not parse GitHub repository from remote URL"

Ensure the `origin` remote points to a GitHub URL:
```bash
git remote get-url origin
# Should look like:
#   https://github.com/owner/repo.git
#   git@github.com:owner/repo.git
```

### "No GitHub token found"

Provide a token via `--token`, `GH_TOKEN`, or `gh auth login`.
