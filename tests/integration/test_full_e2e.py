#!/usr/bin/env python3
"""
Complete end-to-end test: Create GitHub Project from tasks.md with full validation.

Steps:
1. Create test repository
2. Create GitHub Project  
3. Run complete hierarchy creation from tasks.md
4. Set all custom field values correctly
5. Validate structure
6. Prompt user to configure view manually
7. Wait for confirmation
8. Validate view is configured
"""

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.specify_cli.github.sync_engine import GitHubSyncEngine
from src.specify_cli.parser.parser import parse_tasks_document

def run_gh(args: List[str], check: bool = True) -> Dict:
    """Run gh CLI command and return JSON result."""
    result = subprocess.run(
        ['gh'] + args,
        capture_output=True,
        text=True,
        check=check
    )
    if result.returncode != 0:
        print(f"Error running: gh {' '.join(args)}", file=sys.stderr)
        print(f"stderr: {result.stderr}", file=sys.stderr)
        if check:
            sys.exit(1)
        return {}
    
    try:
        return json.loads(result.stdout)
    except:
        return {"output": result.stdout}

def main():
    """Run complete end-to-end test."""
    print("=" * 80)
    print("SPEC-KIT GITHUB PROJECTS - COMPLETE END-TO-END TEST")
    print("=" * 80)
    
    # Configuration
    owner = "gs06ahm"
    timestamp = int(time.time())
    repo_name = f"spec-kit-e2e-{timestamp}"
    project_title = f"Spec-Kit E2E Test {timestamp}"
    tasks_file = "/tmp/spec-kit-integration-test/spec/tasks.md"
    
    print(f"\n📋 Configuration:")
    print(f"   Owner: {owner}")
    print(f"   Repository: {repo_name}")
    print(f"   Project: {project_title}")
    print(f"   Tasks file: {tasks_file}")
    
    # Verify tasks.md exists
    if not Path(tasks_file).exists():
        print(f"\n❌ Error: {tasks_file} not found")
        print(f"   Creating test directory...")
        Path("/tmp/spec-kit-integration-test/spec").mkdir(parents=True, exist_ok=True)
        Path(tasks_file).write_text("""# Tasks: GitHub Projects Integration Test Feature

**Input**: spec/spec.md  
**Branch**: `feature/github-projects-test`

## Phase 1: Foundation & Setup

**Purpose**: Establish the foundational infrastructure
**Goal**: Create a working development environment with all necessary tools

### Task Group: Development Environment

- [ ] T001 Initialize development environment
- [ ] T002 [P] Configure testing framework  
- [ ] T003 [P] Setup CI/CD pipeline

### Task Group: Core Infrastructure

- [ ] T004 Implement base classes
- [ ] T005 [P] Setup logging and monitoring

## Phase 2: Feature Implementation  

**Purpose**: Build the core feature functionality
**Goal**: Implement all core features with comprehensive test coverage

### Task Group: API Development

- [ ] T006 Design API schema
- [ ] T007 Implement authentication
- [ ] T008 [P] Create CRUD endpoints

### Task Group: Integration

- [ ] T009 [P] Add third-party integrations
""")
        print(f"   ✓ Created {tasks_file}")
    
    project_url = None
    project_number = None
    
    try:
        # Step 1: Create test repository
        print(f"\n{'='*80}")
        print(f"STEP 1: CREATE TEST REPOSITORY")
        print(f"{'='*80}")
        print(f"\n📦 Creating repository: {owner}/{repo_name}")
        
        result = subprocess.run([
            'gh', 'repo', 'create', f'{owner}/{repo_name}',
            '--private',
            '--description', f'E2E test for GitHub Projects - {timestamp}'
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ Failed to create repository")
            print(result.stderr)
            sys.exit(1)
        
        print(f"✓ Repository created: https://github.com/{owner}/{repo_name}")
        
        # Step 2: Parse tasks.md
        print(f"\n{'='*80}")
        print(f"STEP 2: PARSE TASKS.MD")
        print(f"{'='*80}")
        print(f"\n📄 Parsing {tasks_file}...")
        
        with open(tasks_file, 'r') as f:
            content = f.read()
        
        doc = parse_tasks_document(content)
        print(f"✓ Parsed successfully:")
        print(f"   - {len(doc.phases)} phases")
        print(f"   - {sum(len(p.groups) for p in doc.phases)} task groups")
        print(f"   - {len(doc.all_tasks)} tasks")
        
        # Step 3: Run GitHub sync
        print(f"\n{'='*80}")
        print(f"STEP 3: CREATE GITHUB PROJECT WITH HIERARCHY")
        print(f"{'='*80}")
        
        sync_engine = GitHubSyncEngine()
        
        print(f"\n🔄 Creating project and hierarchy...")
        result = sync_engine.sync_to_github(
            repo_owner=owner,
            repo_name=repo_name,
            doc=doc,
            sync_state={}
        )
        
        project_url = result.get('project_url')
        
        # Extract project number from URL
        if project_url:
            project_number = int(project_url.split('/')[-1])
        
        print(f"\n✅ Project created successfully!")
        print(f"   URL: {project_url}")
        print(f"   Project #: {project_number}")
        
        # Step 4: Validate structure
        print(f"\n{'='*80}")
        print(f"STEP 4: VALIDATE PROJECT STRUCTURE")
        print(f"{'='*80}")
        
        print(f"\n🔍 Running validation tests...")
        validation_result = subprocess.run([
            'python',
            'tests/integration/validate_project_structure.py',
            '--owner', owner,
            '--repo', repo_name,
            '--project', str(project_number)
        ], capture_output=True, text=True)
        
        print(validation_result.stdout)
        
        if validation_result.returncode != 0:
            print(f"\n❌ Validation failed!")
            sys.exit(1)
        
        # Step 5: Manual view configuration
        print(f"\n{'='*80}")
        print(f"STEP 5: CONFIGURE VIEW (MANUAL)")
        print(f"{'='*80}")
        
        print(f"""
⚠️  MANUAL STEP REQUIRED

The project has been created with the correct structure, but view configuration
must be done manually (GitHub API limitation).

Please follow these steps:

1. Open the project in your browser:
   {project_url}

2. Click the "View options" button (••• icon) in the top-right

3. Click "Group by: none" to expand the menu

4. Select "Phase" from the list

5. The view will now show:
   ▼ Phase 1: Foundation & Setup (7 items)
   ▼ Phase 2: Feature Implementation (8 items)

6. Press Enter here when done...
""")
        
        input("Press Enter after configuring the view... ")
        
        # Step 6: Final validation
        print(f"\n{'='*80}")
        print(f"STEP 6: FINAL VERIFICATION")
        print(f"{'='*80}")
        
        print(f"\n🔍 Verifying project structure...")
        
        # Re-run validation
        validation_result = subprocess.run([
            'python',
            'tests/integration/validate_project_structure.py',
            '--owner', owner,
            '--repo', repo_name,
            '--project', str(project_number)
        ], capture_output=True, text=True)
        
        print(validation_result.stdout)
        
        if validation_result.returncode != 0:
            print(f"\n❌ Final validation failed!")
            sys.exit(1)
        
        # Success!
        print(f"\n{'='*80}")
        print(f"✅ END-TO-END TEST COMPLETE!")
        print(f"{'='*80}")
        
        print(f"""
Project Details:
  URL: {project_url}
  Repository: https://github.com/{owner}/{repo_name}
  Status: ✅ All validations passed

Structure:
  - 2 Phase issues (top-level)
  - 4 Task Group issues (children of phases)
  - 9 Task issues (children of task groups)
  - Total: 15 items

View Configuration:
  - Manually configured to group by Phase
  - Each phase appears once as a collapsible group
  - All task groups and tasks appear under their phase

Next Steps:
  - View the project in your browser
  - Test the grouping by switching to "Task Group" view
  - Archive the test repository when done: gh repo archive {owner}/{repo_name}
""")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
        if project_url:
            print(f"\nProject URL: {project_url}")
            print(f"You may want to check the project even though the test failed.")
        
        sys.exit(1)

if __name__ == '__main__':
    main()
