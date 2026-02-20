# GitHub Projects Integration - Complete Implementation

**Status**: ✅ **Production Ready**  
**Last Updated**: 2026-02-20

## Overview

Spec-Kit now supports full GitHub Projects integration with three-level hierarchy:
**Phase → Task Group → Tasks**

## Features

### Implemented ✅

1. **Three-Level Hierarchy**
   - Phase issues (top level, no parent)
   - Task Group issues (children of phases)
   - Task issues (children of task groups)
   - Implemented using GitHub's native sub-issues feature

2. **Custom Fields**
   - Phase: Single-select field with phase options
   - Task Group: Single-select field with group options
   - Enables visual grouping in project table views
   - Automatically set during sync

3. **Project Creation**
   - Creates project via GraphQL API
   - Sets up all required custom fields
   - Adds all issues to project automatically

4. **Validation**
   - Comprehensive API-based validation
   - Checks for duplicates
   - Validates hierarchy structure
   - Ensures correct field values
   - Detects Phase issues appearing in their own group

### Manual Step Required ⚠️

**View Configuration** (< 1 minute, one-time per project):
- Grouping by Phase or Task Group field must be configured manually
- GitHub's REST API for views is Enterprise Cloud only
- No GraphQL mutations exist for view configuration
- See: `docs/GITHUB_PROJECTS_VIEW_SETUP.md`

## Usage

### Create a Project

```bash
# 1. Ensure tasks.md has hierarchy structure
cat spec/tasks.md
# Phase 1: Foundation & Setup
#   Task Group: Development Environment
#     - T001: Task description
#     - T002: Task description

# 2. Run sync
specify github sync

# Output:
# ✓ Created project: https://github.com/users/USERNAME/projects/42
# ✓ Created 15 issues with hierarchy
# ✓ Set custom field values
# ✓ Added all issues to project
#
# Next steps:
# - Open project URL and configure view grouping
# - See docs/GITHUB_PROJECTS_VIEW_SETUP.md for instructions

# 3. Configure view (manual, 30 seconds)
# - Open project URL in browser
# - Click "View options" → "Group by" → "Phase"
```

### Validate Structure

```bash
python tests/integration/validate_project_structure.py \
  --owner USERNAME \
  --repo REPO_NAME \
  --project PROJECT_NUMBER
```

## Architecture

### Hierarchy Implementation

**Sub-Issues** (semantic relationships):
```python
# Phase issues created with no parentIssueId
phase_issue = create_issue(
    title="Phase 1: Foundation & Setup",
    parent_issue_id=None,
    project_ids=[project_id]
)

# Task Group issues created as children of phases
group_issue = create_issue(
    title="Task Group: Development Environment",
    parent_issue_id=phase_issue["id"],
    project_ids=[project_id]
)

# Task issues created as children of groups
task_issue = create_issue(
    title="[T001] Initialize development environment",
    parent_issue_id=group_issue["id"],
    project_ids=[project_id]
)
```

**Custom Fields** (visual grouping):
```python
# Phase field set on Task Groups and Tasks only
set_field_value(
    item_id=group_item_id,
    field_id=phase_field_id,
    value="Phase 1: Foundation & Setup"
)

# Task Group field set on Task Groups and Tasks
set_field_value(
    item_id=group_item_id,
    field_id=task_group_field_id,
    value="Development Environment"
)

# Phase issues themselves do NOT have Phase field set
# (prevents them appearing in their own group)
```

### Visual Display

When grouped by Phase in project view:
```
▼ Phase 1: Foundation & Setup (7 items)
  - Task Group: Development Environment
  - [T001] Initialize development environment
  - [T002] Configure testing framework
  - [T003] Setup CI/CD pipeline
  - Task Group: Core Infrastructure
  - [T004] Implement base classes
  - [T005] Setup logging and monitoring

▼ Phase 2: Feature Implementation (8 items)
  - Task Group: API Development
  - [T006] Design API schema
  - [T007] Implement authentication
  - [T008] Create CRUD endpoints
  - Task Group: Integration
  - [T009] Add third-party integrations
```

**Note**: Phase issues themselves (#3, #11) don't appear in the table because they don't have the Phase field set. This is intentional to avoid them appearing in their own group.

## Files

### Implementation
- `src/specify_cli/github/hierarchy_builder.py` - Three-level hierarchy creation
- `src/specify_cli/github/sync_engine.py` - Orchestrates the sync workflow
- `src/specify_cli/github/issue_manager.py` - Field value management
- `src/specify_cli/github/project_creator.py` - Project and field creation

### Tests
- `tests/integration/validate_project_structure.py` - Comprehensive API validation
- `tests/integration/test_e2e_with_views.py` - End-to-end test with view creation attempt

### Documentation
- `GITHUB_PROJECTS.md` - This file (overview)
- `docs/GITHUB_PROJECTS_VIEW_SETUP.md` - User guide for view configuration
- `docs/VIEW_CONFIGURATION_LIMITATIONS.md` - Technical investigation of API limitations
- `TEST_RESULTS.md` - Validation test results
- `PHASE3-5_INTEGRATION_COMPLETE.md` - Implementation summary
- `PHASE4_HIERARCHY_COMPLETE.md` - Phase 4 technical details
- `PHASE5_CUSTOM_FIELDS_COMPLETE.md` - Phase 5 technical details
- `DUPLICATE_ISSUES_FIX.md` - Fix documentation for duplicate issues bug

## Testing

### Validation Tests

Run comprehensive structure validation:
```bash
cd /home/adam/src/spec-kit
python tests/integration/validate_project_structure.py
```

**Tests Performed**:
1. ✓ No duplicate items in project
2. ✓ Correct parent/child hierarchy (Phase → Task Group → Tasks)
3. ✓ Phase issues don't have Phase field set
4. ✓ Task Groups have correct Phase and Task Group fields
5. ✓ All expected items present, no unexpected items

### End-to-End Test

```bash
python tests/integration/test_e2e_with_views.py
```

**Performs**:
- Creates test repository
- Creates project
- Attempts view configuration via REST API (documents limitation)
- Runs validation
- Cleans up

## Best Practices

Following recommendations from `gh_api/best-practices-for-projects.md`:

✅ **Use sub-issues for hierarchies** (Lines 11-20)
- Implemented with `parentIssueId` field
- Creates semantic relationships queryable via GraphQL

✅ **Customize views with grouping by custom fields** (Lines 37-62)
- Created Phase and Task Group custom fields
- Enables visual grouping in table views

✅ **Use single-select fields for metadata** (Lines 64-78)
- Both Phase and Task Group use single-select format
- Allows efficient filtering and grouping

## Known Limitations

1. **View Configuration Requires Manual Setup**
   - REST API for views is Enterprise Cloud only
   - No GraphQL mutations for view configuration
   - Takes < 1 minute to configure manually
   - Configuration persists per user

2. **Phase Issues Don't Appear in Table**
   - Phase issues don't have Phase field set
   - Intentional: prevents appearing in own group
   - Visible in hierarchy on individual issue pages

## Troubleshooting

### "Phase 1" appearing multiple times
**Cause**: Sync was run twice, creating duplicate issues  
**Fix**: Remove duplicates from project, close duplicate issues  
**Prevention**: Validation test now catches this

### Phase issue appearing in its own group
**Cause**: Phase issue has Phase field set incorrectly  
**Fix**: Clear Phase field from Phase issues  
**Prevention**: Validation test checks for this

### Hierarchy not visible in table
**Expected**: Sub-issues don't show as nested rows in table view  
**Solution**: Use "Sub-issues progress" column or Board view with "Show hierarchy"

## Future Enhancements

- [ ] Auto-detect and handle duplicate issues during sync
- [ ] Support for Enterprise Cloud REST API view configuration
- [ ] Optional browser automation for view setup (if user enables)
- [ ] Multi-phase project support
- [ ] Milestone integration

## References

- [GitHub Projects Best Practices](gh_api/best-practices-for-projects.md)
- [GitHub GraphQL API Schema](gh_api/schema.docs.graphql)
- [GitHub REST API Objects](gh_api/objects.md)
- [Sub-Issues Documentation](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/about-issues#sub-issues)
- [Enterprise Cloud Views API](https://docs.github.com/en/enterprise-cloud@latest/rest/projects/views)

---

**Questions?** See `docs/GITHUB_PROJECTS_VIEW_SETUP.md` or open an issue.
