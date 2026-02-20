#!/usr/bin/env python3
"""
Validate GitHub Project structure matches tasks.md exactly.
Tests that:
1. No duplicate issues
2. Correct parent/child hierarchy
3. Phase issues don't have Phase field set (to avoid appearing in their own group)
4. All expected issues exist
5. No unexpected issues exist

Usage:
    python validate_project_structure.py [--owner OWNER] [--repo REPO] [--project NUMBER]
"""

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from typing import Dict, List, Set, Optional

def run_gh_graphql(query: str) -> dict:
    """Run a GraphQL query using gh CLI."""
    result = subprocess.run(
        ['gh', 'api', 'graphql', '-f', f'query={query}'],
        capture_output=True,
        text=True,
        check=True
    )
    return json.loads(result.stdout)

def get_project_items(owner: str, project_number: int) -> List[dict]:
    """Get all items in a project."""
    query = f'''
    query {{
      user(login: "{owner}") {{
        projectV2(number: {project_number}) {{
          items(first: 100) {{
            nodes {{
              id
              content {{
                ... on Issue {{
                  number
                  title
                }}
              }}
              fieldValues(first: 20) {{
                nodes {{
                  ... on ProjectV2ItemFieldSingleSelectValue {{
                    field {{
                      ... on ProjectV2SingleSelectField {{
                        name
                      }}
                    }}
                    name
                  }}
                }}
              }}
            }}
          }}
        }}
      }}
    }}
    '''
    data = run_gh_graphql(query)
    return data['data']['user']['projectV2']['items']['nodes']

def get_issue_hierarchy(owner: str, repo: str) -> List[dict]:
    """Get all issues with their parent relationships."""
    query = f'''
    query {{
      repository(owner: "{owner}", name: "{repo}") {{
        issues(first: 100, orderBy: {{field: CREATED_AT, direction: ASC}}, states: OPEN) {{
          nodes {{
            number
            title
            parent {{
              number
              title
            }}
          }}
        }}
      }}
    }}
    '''
    data = run_gh_graphql(query)
    return data['data']['repository']['issues']['nodes']

def validate_no_duplicates(items: List[dict]) -> tuple[bool, List[str]]:
    """Ensure no duplicate titles in project."""
    errors = []
    title_counts = defaultdict(int)
    
    for item in items:
        title = item['content']['title']
        title_counts[title] += 1
    
    duplicates = {title: count for title, count in title_counts.items() if count > 1}
    if duplicates:
        for title, count in duplicates.items():
            errors.append(f"DUPLICATE: '{title}' appears {count} times in project")
        return False, errors
    
    return True, []

def validate_hierarchy(issues: List[dict]) -> tuple[bool, List[str]]:
    """Validate parent/child relationships are correct."""
    errors = []
    
    # Build hierarchy map
    issues_by_number = {issue['number']: issue for issue in issues}
    phases = []
    task_groups = []
    tasks = []
    
    for issue in issues:
        title = issue['title']
        parent = issue.get('parent')
        
        if title.startswith('Phase '):
            if parent:
                errors.append(f"ERROR: Phase issue #{issue['number']} '{title}' has a parent #{parent['number']}")
            phases.append(issue)
        elif title.startswith('Task Group:'):
            if not parent:
                errors.append(f"ERROR: Task Group #{issue['number']} '{title}' has no parent")
            elif not issues_by_number.get(parent['number'], {}).get('title', '').startswith('Phase '):
                errors.append(f"ERROR: Task Group #{issue['number']} '{title}' parent #{parent['number']} is not a Phase")
            task_groups.append(issue)
        elif title.startswith('[T') or title.startswith('[M'):
            if not parent:
                errors.append(f"ERROR: Task #{issue['number']} '{title}' has no parent")
            elif not issues_by_number.get(parent['number'], {}).get('title', '').startswith('Task Group:'):
                errors.append(f"ERROR: Task #{issue['number']} '{title}' parent #{parent['number']} is not a Task Group")
            tasks.append(issue)
    
    return len(errors) == 0, errors

def validate_phase_fields(items: List[dict]) -> tuple[bool, List[str]]:
    """Ensure Phase issues don't have Phase field set (to avoid appearing in own group)."""
    errors = []
    
    for item in items:
        title = item['content']['title']
        number = item['content']['number']
        
        # Check if this is a Phase issue
        if title.startswith('Phase '):
            # Get Phase field value
            phase_value = None
            for field_value in item.get('fieldValues', {}).get('nodes', []):
                if field_value.get('field', {}).get('name') == 'Phase':
                    phase_value = field_value.get('name')
                    break
            
            if phase_value:
                errors.append(
                    f"ERROR: Phase issue #{number} '{title}' has Phase field set to '{phase_value}'. "
                    f"This causes it to appear in its own group. Phase issues should NOT have Phase field set."
                )
    
    return len(errors) == 0, errors

def validate_task_group_fields(items: List[dict]) -> tuple[bool, List[str]]:
    """Ensure Task Group issues have Phase field set."""
    errors = []
    
    for item in items:
        title = item['content']['title']
        number = item['content']['number']
        
        if title.startswith('Task Group:'):
            # Get field values
            fields = {}
            for field_value in item.get('fieldValues', {}).get('nodes', []):
                field_name = field_value.get('field', {}).get('name')
                if field_name:
                    fields[field_name] = field_value.get('name')
            
            # Task groups should have Phase field set so they appear in correct group
            if 'Phase' not in fields:
                errors.append(f"ERROR: Task Group #{number} '{title}' missing Phase field")
    
    return len(errors) == 0, errors

def validate_expected_structure(items: List[dict], issues: List[dict]) -> tuple[bool, List[str]]:
    """Validate expected counts and structure."""
    errors = []
    
    # Count by type
    phase_count = sum(1 for i in issues if i['title'].startswith('Phase '))
    group_count = sum(1 for i in issues if i['title'].startswith('Task Group:'))
    task_count = sum(1 for i in issues if i['title'].startswith('[T') or i['title'].startswith('[M'))
    
    total = phase_count + group_count + task_count
    
    # Verify counts
    if len(items) != total:
        errors.append(f"ERROR: Project has {len(items)} items but should have {total} (phases:{phase_count}, groups:{group_count}, tasks:{task_count})")
    
    # Verify expected items from tasks.md
    expected_items = {
        'Phase 1: Foundation & Setup',
        'Phase 2: Feature Implementation',
        'Task Group: Development Environment',
        'Task Group: Core Infrastructure',
        'Task Group: API Development',
        'Task Group: Integration',
        '[T001] Initialize development environment',
        '[T002] Configure testing framework',
        '[T003] Setup CI/CD pipeline',
        '[T004] Implement base classes',
        '[T005] Setup logging and monitoring',
        '[T006] Design API schema',
        '[T007] Implement authentication',
        '[T008] Create CRUD endpoints',
        '[T009] Add third-party integrations',
    }
    
    actual_items = {item['content']['title'] for item in items}
    
    missing = expected_items - actual_items
    extra = actual_items - expected_items
    
    if missing:
        for title in sorted(missing):
            errors.append(f"ERROR: Missing expected item: '{title}'")
    
    if extra:
        for title in sorted(extra):
            errors.append(f"ERROR: Unexpected item in project: '{title}'")
    
    return len(errors) == 0, errors

def main():
    """Run all validation tests."""
    parser = argparse.ArgumentParser(description='Validate GitHub Project structure')
    parser.add_argument('--owner', default='gs06ahm', help='GitHub username or org')
    parser.add_argument('--repo', default='spec-kit-hierarchy-test', help='Repository name')
    parser.add_argument('--project', type=int, default=12, help='Project number')
    
    args = parser.parse_args()
    owner = args.owner
    repo = args.repo
    project_number = args.project
    
    print(f"Validating project structure for {owner}/projects/{project_number}")
    print("=" * 70)
    
    # Get data
    print("Fetching project items...")
    items = get_project_items(owner, project_number)
    print(f"Found {len(items)} items in project")
    
    print("Fetching issue hierarchy...")
    issues = get_issue_hierarchy(owner, repo)
    print(f"Found {len(issues)} issues in repository")
    print()
    
    all_passed = True
    
    # Test 1: No duplicates
    print("Test 1: Checking for duplicate items...")
    passed, errors = validate_no_duplicates(items)
    if passed:
        print("  ✓ PASSED: No duplicate items")
    else:
        print("  ✗ FAILED:")
        for error in errors:
            print(f"    {error}")
        all_passed = False
    print()
    
    # Test 2: Hierarchy structure
    print("Test 2: Validating parent/child hierarchy...")
    passed, errors = validate_hierarchy(issues)
    if passed:
        print("  ✓ PASSED: Hierarchy structure is correct")
    else:
        print("  ✗ FAILED:")
        for error in errors:
            print(f"    {error}")
        all_passed = False
    print()
    
    # Test 3: Phase field values
    print("Test 3: Validating Phase field values...")
    passed, errors = validate_phase_fields(items)
    if passed:
        print("  ✓ PASSED: Phase issues don't have Phase field set")
    else:
        print("  ✗ FAILED:")
        for error in errors:
            print(f"    {error}")
        all_passed = False
    print()
    
    # Test 4: Task Group fields
    print("Test 4: Validating Task Group field values...")
    passed, errors = validate_task_group_fields(items)
    if passed:
        print("  ✓ PASSED: Task Groups have correct fields")
    else:
        print("  ✗ FAILED:")
        for error in errors:
            print(f"    {error}")
        all_passed = False
    print()
    
    # Test 5: Expected structure
    print("Test 5: Validating expected items from tasks.md...")
    passed, errors = validate_expected_structure(items, issues)
    if passed:
        print("  ✓ PASSED: All expected items present, no extras")
    else:
        print("  ✗ FAILED:")
        for error in errors:
            print(f"    {error}")
        all_passed = False
    print()
    
    # Summary
    print("=" * 70)
    if all_passed:
        print("✓ ALL TESTS PASSED")
        return 0
    else:
        print("✗ SOME TESTS FAILED")
        return 1

if __name__ == '__main__':
    sys.exit(main())
