# GitHub Projects View Configuration Guide

After running `specify github sync`, your GitHub Project will be created with all issues, custom fields, and hierarchy relationships. However, **view configuration must be done manually** due to GitHub API limitations.

## Why Manual Configuration?

GitHub's API does not currently expose:
- ProjectV2View update mutations (GraphQL)
- View configuration REST endpoints
- CLI commands for view settings

The `groupByFields` property on views is read-only in the API. This affects all users and tools, not just Spec-Kit.

## Quick Setup Guide

### 1. Open Your Project

After running `specify github sync`, you'll receive a project URL:
```
Project created: https://github.com/users/YOUR_USERNAME/projects/NUMBER
```

Open this URL in your browser.

### 2. Configure Grouping by Phase

1. Click the **"View options"** button (three dots icon) in the top-right of the table
2. Click **"Group by: none"** to expand the grouping menu
3. Select **"Phase"** from the list
4. The view will now show phases as collapsible groups

**Result**: Your project will display like this:
```
▼ Phase 1: Foundation & Setup (10)
  ├─ Phase 1: Foundation & Setup (#1)
  ├─ Task Group: Development Environment (#2)
  ├─ T001: Initialize Project Repository (#10)
  └─ ...

▼ Phase 2: Implementation & Testing (7)
  ├─ Phase 2: Implementation & Testing (#4)
  └─ ...
```

### 3. Alternative: Group by Task Group

For a more granular view:

1. Follow the same steps as above
2. Select **"Task Group"** instead of Phase
3. The view will show all task groups as top-level groups

### 4. Enable Hierarchy View (Optional)

To see sub-issue relationships in detail:

1. Click **"View options"**
2. Toggle **"Show hierarchy"** to ON
3. This works best with Board view for visual parent/child display

**Note**: Hierarchy view is currently in Beta.

## View Persistence

Your view configuration is saved automatically and persists for:
- Your user account
- The specific view you configured
- All future visits to the project

Other users will need to configure their own views.

## Multiple Views

You can create multiple views with different configurations:

1. Click the **"+"** button next to your current view tab
2. Select **"New table view"**
3. Configure grouping and fields independently
4. Name your views (e.g., "By Phase", "By Task Group", "All Tasks")

## Recommended View Configurations

### "Overview" View
- **Layout**: Table
- **Group by**: Phase
- **Fields**: Title, Status, Task Group, Sub-issues progress
- **Use case**: High-level project status

### "Task Details" View
- **Layout**: Table
- **Group by**: Task Group
- **Fields**: Title, Assignees, Status, Priority, Phase
- **Use case**: Daily work management

### "Hierarchy" View
- **Layout**: Board
- **Group by**: Status
- **Show hierarchy**: ON
- **Use case**: Visual parent/child relationships

## Automation Script (Future)

We are investigating potential solutions:
- Browser automation for initial setup
- GitHub Actions to configure views on project creation
- Feature request to GitHub for API support

For now, manual configuration takes < 1 minute and only needs to be done once per project.

## Troubleshooting

### "Phase" or "Task Group" not showing in grouping menu

**Cause**: Custom fields may not have been created properly.

**Solution**:
```bash
# Verify fields exist
gh api graphql -f query='
query($project: Int!) {
  user(login: "YOUR_USERNAME") {
    projectV2(number: $project) {
      fields(first: 20) {
        nodes {
          ... on ProjectV2SingleSelectField {
            name
            options { name }
          }
        }
      }
    }
  }
}' -F project=12
```

If fields are missing, re-run `specify github sync`.

### Grouping shows empty groups

**Cause**: Field values may not be set on all issues.

**Solution**: Check that Phase and Task Group values are set:
```bash
gh api graphql -f query='
query($project: Int!) {
  user(login: "YOUR_USERNAME") {
    projectV2(number: $project) {
      items(first: 100) {
        nodes {
          content {
            ... on Issue { number, title }
          }
          fieldValues(first: 20) {
            nodes {
              ... on ProjectV2ItemFieldSingleSelectValue {
                field { ... on ProjectV2SingleSelectField { name } }
                name
              }
            }
          }
        }
      }
    }
  }
}' -F project=12
```

### Sub-issues not showing in table

**Expected behavior**: Sub-issues are NOT displayed hierarchically in table view. They appear:
- As individual rows in the table
- In the "Sub-issues progress" column (e.g., "0 of 3 (0%)")
- On individual issue detail pages when you click an issue

For visual hierarchy, use Board view with "Show hierarchy" enabled.

## References

- GitHub Docs: [Customizing views in your project](https://docs.github.com/en/issues/planning-and-tracking-with-projects/customizing-views-in-your-project)
- GitHub Docs: [About sub-issues](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/about-issues#sub-issues)
- Spec-Kit: [Best Practices](../gh_api/best-practices-for-projects.md)

---

**Questions?** Open an issue at [github.com/YourOrg/spec-kit](https://github.com)
