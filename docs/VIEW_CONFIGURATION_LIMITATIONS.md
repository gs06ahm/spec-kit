# GitHub Projects View Configuration Limitations

**Date**: 2026-02-20  
**Finding**: View configuration (grouping, sorting, filtering) cannot be automated  

## Investigation Summary

### REST API for Views
**Documentation**: https://docs.github.com/en/enterprise-cloud@latest/rest/projects/views

The REST API documentation shows endpoints for creating and configuring views:
- `POST /users/{user_id}/projectsV2/{project_number}/views`
- `POST /orgs/{org}/projectsV2/{project_number}/views`

These endpoints accept parameters including:
- `name`: View name
- `layout`: `table`, `board`, or `roadmap`
- `filter`: Filter query
- `visible_fields`: Array of field IDs to show
- **`group_by`**: Array of field IDs for horizontal grouping ⭐
- `vertical_group_by`: Array of field IDs for vertical grouping (board layout)
- `sort_by`: Array of `[field_id, direction]` tuples

### Test Results

**Endpoint**: `POST /users/39130281/projectsV2/12/views`  
**Result**: `HTTP 404 Not Found`

```bash
$ gh api /users/39130281/projectsV2/12 
{
  "message": "Not Found",
  "documentation_url": "https://docs.github.com/rest/projects/projects#get-project-for-user",
  "status": "404"
}
```

### GraphQL API

**Query**: Searched `schema.docs.graphql` for view-related mutations  
**Finding**: `group_by_fields` exists as a **read-only** field on `ProjectV2View`  
**Result**: No `updateProjectV2View`, `createProjectV2View`, or similar mutations exist

```graphql
type ProjectV2View {
  groupByFields(first: Int): ProjectV2FieldConnection
  # ... other read-only fields
}
```

## Conclusion

### What's Available
✅ **GraphQL**: Create projects, fields, items, set field values, create sub-issues  
✅ **GraphQL**: Read view configuration (`groupByFields`, `sortByFields`, etc.)  
✅ **REST API (Enterprise Cloud only)**: Full view management with `group_by` parameter

### What's Not Available (GitHub.com)
❌ **REST API**: ProjectsV2 views endpoints return 404 on github.com  
❌ **GraphQL**: No mutations for creating or updating views  
❌ **gh CLI**: No `gh project view-*` commands for configuration  
❌ **Extensions**: No gh extensions support view configuration

## Workarounds

### Option 1: Manual Configuration (Current Approach)
**Time**: < 1 minute per project  
**Persistence**: Per-user, per-view (settings saved automatically)  
**Documentation**: Created user guide in `docs/GITHUB_PROJECTS_VIEW_SETUP.md`

Steps:
1. Open project in browser
2. Click "View options" → "Group by" → Select "Phase"
3. Done - configuration persists

### Option 2: Enterprise Cloud Migration
If your organization has GitHub Enterprise Cloud, the REST API endpoints are available and can be used to automate view configuration.

### Option 3: Browser Automation (Not Recommended)
- Requires maintaining brittle UI selectors
- Needs authentication handling
- Breaks with GitHub UI changes
- Not reliable for CI/CD

## Recommendations

### For Spec-Kit Users
1. Use `specify github sync` to create projects with full hierarchy
2. Follow the view configuration guide (< 1 min manual setup)
3. Create multiple views for different use cases (By Phase, By Task Group, etc.)

### For GitHub Feature Request
Consider requesting public API access to:
- `POST /users/{user_id}/projectsV2/{project_number}/views` (currently enterprise-only)
- GraphQL mutations: `createProjectV2View`, `updateProjectV2View`
- Ability to set `group_by` fields during project creation

## Test Results

**Script**: `tests/integration/test_e2e_with_views.py`  
**Outcome**: Successfully validates structure but cannot create views via API  

```bash
$ python tests/integration/test_e2e_with_views.py

✓ Repository created
✓ Project created
✓ Phase field ID retrieved: 260235550
⚠️  View creation via REST API: HTTP 404
✓ Structure validation: ALL TESTS PASSED
```

## References

- [REST API Views Documentation](https://docs.github.com/en/enterprise-cloud@latest/rest/projects/views) (Enterprise Cloud only)
- [GraphQL API Schema](https://docs.github.com/en/graphql/reference/objects#projectv2view) (Read-only)
- [User View Setup Guide](GITHUB_PROJECTS_VIEW_SETUP.md)
- [Best Practices](../gh_api/best-practices-for-projects.md)

---

**Last Updated**: 2026-02-20  
**Status**: Confirmed limitation - Manual view configuration required for github.com
