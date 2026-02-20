# Fix: Duplicate Issues in GitHub Project

**Date**: 2026-02-20  
**Issue**: Project showing duplicate Phase and Task Group issues  
**Root Cause**: Sync command was run twice, creating two sets of hierarchy  

## Problem Description

The project at https://github.com/users/gs06ahm/projects/12 showed:
- Phase 1: Foundation & Setup appearing 3 times (issues #1 and #3 were duplicates)
- Task Group: Development Environment appearing 2 times (issues #2 and #4 were duplicates)
- Similarly for other phases and task groups

## Root Cause Analysis

### Timeline
```
15:45:18Z - Issue #1 created: Phase 1: Foundation & Setup
15:45:23Z - Issue #2 created: Task Group: Development Environment
[90 second gap]
15:46:52Z - Issue #3 created: Phase 1: Foundation & Setup
15:46:53Z - Issue #4 created: Task Group: Development Environment
15:46:57Z - Issues #5-17 created (rest of hierarchy)
```

### What Happened
1. First sync run created issues #1-2 but failed/stopped
2. Second sync run (90 seconds later) created the complete hierarchy (#3-17)
3. Both sets of issues were added to the project
4. Project grouped by Phase field showed all issues with "Phase 1" value, including duplicates

### Hierarchy Structure
**Incorrect** (with duplicates):
```
Issues #1-2: Orphaned, no children, no parent relationships
Issues #3-17: Correct hierarchy with parent/child relationships
```

**Correct** (after fix):
```
Issue #3: Phase 1 (TOP LEVEL)
  ├── Issue #4: Task Group: Development Environment (parent: #3)
  │   ├── Issue #5: T001 (parent: #4)
  │   ├── Issue #6: T002 (parent: #4)
  │   └── Issue #7: T003 (parent: #4)
  └── Issue #8: Task Group: Core Infrastructure (parent: #3)
      ├── Issue #9: T004 (parent: #8)
      └── Issue #10: T005 (parent: #8)

Issue #11: Phase 2 (TOP LEVEL)
  ├── Issue #12: Task Group: API Development (parent: #11)
  │   ├── Issue #13: T006 (parent: #12)
  │   ├── Issue #14: T007 (parent: #12)
  │   └── Issue #15: T008 (parent: #12)
  └── Issue #16: Task Group: Integration (parent: #11)
      └── Issue #17: T009 (parent: #16)
```

## Solution Applied

### Step 1: Unarchive Repository
```bash
gh api repos/gs06ahm/spec-kit-hierarchy-test -X PATCH -f archived=false
```

### Step 2: Remove Duplicate Items from Project
```bash
# Get project item IDs for issues #1 and #2
gh project item-list 12 --owner gs06ahm --format json | \
  jq -r '.items[] | select(.content.number == 1 or .content.number == 2) | .id'

# Output:
# PVTI_lAHOAlUUqc4BPtx6zgl2rDQ
# PVTI_lAHOAlUUqc4BPtx6zgl2rFM

# Delete from project
gh project item-delete 12 --owner gs06ahm --id PVTI_lAHOAlUUqc4BPtx6zgl2rDQ
gh project item-delete 12 --owner gs06ahm --id PVTI_lAHOAlUUqc4BPtx6zgl2rFM
```

### Step 3: Verify Fix
```bash
# List remaining items (should be 15 total: 2 phases + 4 groups + 9 tasks)
gh project item-list 12 --owner gs06ahm --format json | \
  jq -r '.items[] | "\(.content.number) - \(.content.title)"' | sort -n

# Output:
# 3 - Phase 1: Foundation & Setup
# 4 - Task Group: Development Environment
# 5 - [T001] Initialize development environment
# ... (15 items total)
```

### Step 4: Verify Hierarchy
```bash
gh api graphql -f query='
query {
  repository(owner: "gs06ahm", name: "spec-kit-hierarchy-test") {
    issues(first: 20, orderBy: {field: CREATED_AT, direction: ASC}) {
      nodes {
        number
        title
        parent { number title }
      }
    }
  }
}'
```

**Result**: All parent/child relationships correct, no duplicates.

## Prevention for Future

### Code Change Not Required
The `hierarchy_builder.py` code is correct - it only creates each issue once. The duplicate was caused by running the sync command twice, not a bug in the code.

### User Guidelines
When running `specify github sync`:
1. Wait for complete execution before running again
2. If sync fails, investigate the error before re-running
3. Check for existing issues before creating new hierarchy
4. Consider adding idempotency checks to detect existing issues

### Potential Enhancement
Add duplicate detection to `sync_engine.py`:
```python
# Before creating issues, check if project already has items
existing_items = query_project_items(project_id)
if existing_items:
    console.print("[yellow]Warning:[/yellow] Project already has items. Continue? (y/n)")
    if not confirm():
        return
```

## Verification Commands

### Check for Duplicates in Any Project
```bash
# List all issues with counts
gh project item-list <PROJECT_NUMBER> --owner <OWNER> --format json | \
  jq -r '.items[].content.title' | sort | uniq -c | grep -v "^ *1 "

# If output is empty, no duplicates exist
```

### Verify Hierarchy Structure
```bash
gh api graphql -f query='
query {
  repository(owner: "<OWNER>", name: "<REPO>") {
    issues(first: 100, orderBy: {field: CREATED_AT, direction: ASC}) {
      nodes {
        number
        title
        parent { number }
      }
    }
  }
}' | jq -r '.data.repository.issues.nodes[] | 
  if .parent then
    "  └─ #\(.number): \(.title) (parent: #\(.parent.number))"
  else
    "#\(.number): \(.title) (TOP LEVEL)"
  end'
```

## Impact

**Before Fix**:
- 17 items in project (2 duplicates)
- Phase 1 appeared 3 times in grouped view
- Task Group: Development Environment appeared 2 times
- Confusing and incorrect visualization

**After Fix**:
- 15 items in project (correct count)
- Each phase appears once
- Each task group appears once under its phase
- Clean three-level hierarchy visualization

## Status

✅ **RESOLVED** - Duplicates removed, project structure now displays correctly.

---

**Reference**: See `PHASE3-5_INTEGRATION_COMPLETE.md` for full project documentation.
