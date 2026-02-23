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
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Optional

PHASE_PATTERN = re.compile(r'^##\s+Phase\s+(\d+(?:\.\d+)*):\s+(.+)$')
GROUP_PATTERN = re.compile(r'^###\s+(.+)$')
TASK_PATTERN = re.compile(r'^-\s+\[[ Xx]\]\s+(T\d{3,4})\s*(?:\[P\])?\s*(?:\[US\d+\])?\s*(.+)$')

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
    phase_numbers, group_numbers, task_numbers = classify_issues(issues)
    
    for issue in issues:
        number = issue['number']
        title = issue['title']
        parent = issue.get('parent')
        parent_number = parent['number'] if parent else None
        
        if number in phase_numbers:
            if parent:
                errors.append(f"ERROR: Phase issue #{number} '{title}' has a parent #{parent['number']}")
        elif number in group_numbers:
            if not parent:
                errors.append(f"ERROR: Task Group #{number} '{title}' has no parent")
            elif parent_number not in phase_numbers:
                errors.append(f"ERROR: Task Group #{number} '{title}' parent #{parent['number']} is not a Phase")
        elif number in task_numbers:
            if not parent:
                errors.append(f"ERROR: Task #{number} '{title}' has no parent")
            elif parent_number not in group_numbers and parent_number not in phase_numbers:
                parent_title = issues_by_number.get(parent_number, {}).get('title', 'Unknown')
                errors.append(
                    f"ERROR: Task #{number} '{title}' parent #{parent_number} ('{parent_title}') is not a Task Group or Phase"
                )
    
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

def validate_task_group_fields(items: List[dict], issues: List[dict]) -> tuple[bool, List[str]]:
    """Ensure Task Group issues have Phase field set."""
    errors = []
    _, group_numbers, _ = classify_issues(issues)
    
    for item in items:
        title = item['content']['title']
        number = item['content']['number']
        
        if number in group_numbers:
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


def classify_issues(issues: List[dict]) -> tuple[Set[int], Set[int], Set[int]]:
    """Classify issues into phase, group, and task buckets by hierarchy/title."""
    phase_numbers = {issue['number'] for issue in issues if issue['title'].startswith('Phase ')}
    task_numbers = {
        issue['number'] for issue in issues if issue['title'].startswith('[T') or issue['title'].startswith('[M')
    }

    group_numbers: Set[int] = set()
    for issue in issues:
        number = issue['number']
        if number in phase_numbers or number in task_numbers:
            continue
        parent = issue.get('parent')
        if parent and parent['number'] in phase_numbers:
            group_numbers.add(number)

    return phase_numbers, group_numbers, task_numbers

def find_tasks_file(explicit_path: Optional[str]) -> Optional[Path]:
    """Find tasks.md file from explicit path or common defaults."""
    if explicit_path:
        candidate = Path(explicit_path)
        return candidate if candidate.exists() else None

    defaults = [Path("spec/tasks.md")]
    defaults.extend(sorted(Path("specs").glob("*/tasks.md")) if Path("specs").exists() else [])
    for candidate in defaults:
        if candidate.exists():
            return candidate
    return None


def parse_expected_titles(tasks_file: Path) -> Set[str]:
    """Extract expected phase/group/task issue titles from tasks.md."""
    expected_titles: Set[str] = set()
    for raw_line in tasks_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue

        phase_match = PHASE_PATTERN.match(line)
        if phase_match:
            expected_titles.add(f"Phase {phase_match.group(1)}: {phase_match.group(2).strip()}")
            continue

        group_match = GROUP_PATTERN.match(line)
        if group_match:
            expected_titles.add(group_match.group(1).strip())
            continue

        task_match = TASK_PATTERN.match(line)
        if task_match:
            expected_titles.add(f"[{task_match.group(1)}] {task_match.group(2).strip()}")

    return expected_titles


def validate_expected_structure(items: List[dict], issues: List[dict], expected_items: Set[str]) -> tuple[bool, List[str]]:
    """Validate expected counts and structure."""
    errors = []
    
    # Count by type
    phase_numbers, group_numbers, task_numbers = classify_issues(issues)
    phase_count = len(phase_numbers)
    group_count = len(group_numbers)
    task_count = len(task_numbers)
    
    total = phase_count + group_count + task_count
    
    # Verify counts
    if len(items) != total:
        errors.append(f"ERROR: Project has {len(items)} items but should have {total} (phases:{phase_count}, groups:{group_count}, tasks:{task_count})")
    
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
    parser.add_argument('--tasks-file', default=None, help='Path to tasks.md used to generate expected items')
    
    args = parser.parse_args()
    owner = args.owner
    repo = args.repo
    project_number = args.project
    tasks_file = find_tasks_file(args.tasks_file)

    expected_items: Set[str] = set()
    if tasks_file:
        expected_items = parse_expected_titles(tasks_file)
        print(f"Using expected items from {tasks_file} ({len(expected_items)} titles)")
    else:
        print("WARNING: No tasks.md found; expected item validation will be skipped")
    print()
    
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
    passed, errors = validate_task_group_fields(items, issues)
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
    if expected_items:
        passed, errors = validate_expected_structure(items, issues, expected_items)
    else:
        passed, errors = True, []
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
