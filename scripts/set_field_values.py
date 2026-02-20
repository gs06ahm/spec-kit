#!/usr/bin/env python3
"""Set custom field values on all project items."""
import json
import subprocess
import sys

def run_graphql(query):
    """Run a GraphQL query using gh CLI."""
    result = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={query}"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"Error: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return json.loads(result.stdout)

def run_mutation(query):
    """Run a GraphQL mutation using gh CLI."""
    result = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={query}"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"Error: {result.stderr}", file=sys.stderr)
        return None
    return json.loads(result.stdout)

# Get all project items
items_query = """
query {
  user(login: "gs06ahm") {
    projectV2(number: 12) {
      id
      fields(first: 20) {
        nodes {
          ... on ProjectV2SingleSelectField {
            id
            name
            options {
              id
              name
            }
          }
        }
      }
      items(first: 20) {
        nodes {
          id
          content {
            ... on Issue {
              number
              title
            }
          }
        }
      }
    }
  }
}
"""

print("📋 Getting project items and fields...")
result = run_graphql(items_query)
project = result["data"]["user"]["projectV2"]
project_id = project["id"]

# Build field maps
phase_field = next(f for f in project["fields"]["nodes"] if f.get("name") == "Phase")
task_group_field = next(f for f in project["fields"]["nodes"] if f.get("name") == "Task Group")

phase_options = {opt["name"]: opt["id"] for opt in phase_field["options"]}
task_group_options = {opt["name"]: opt["id"] for opt in task_group_field["options"]}

print(f"✓ Phase field: {phase_field['id']}")
print(f"✓ Task Group field: {task_group_field['id']}")

# Map issue numbers to field values
issue_mappings = {
    # Phase 1
    1: {"phase": "Phase 1: Foundation & Setup", "group": None},  # Duplicate
    3: {"phase": "Phase 1: Foundation & Setup", "group": None},  # Phase 1
    # Task Groups
    2: {"phase": "Phase 1: Foundation & Setup", "group": "Development Environment"},  # Duplicate
    4: {"phase": "Phase 1: Foundation & Setup", "group": "Development Environment"},  # Dev Env
    8: {"phase": "Phase 1: Foundation & Setup", "group": "Core Infrastructure"},  # Core Infra
    # Tasks
    5: {"phase": "Phase 1: Foundation & Setup", "group": "Development Environment"},  # T001
    6: {"phase": "Phase 1: Foundation & Setup", "group": "Development Environment"},  # T002
    7: {"phase": "Phase 1: Foundation & Setup", "group": "Development Environment"},  # T003
    9: {"phase": "Phase 1: Foundation & Setup", "group": "Core Infrastructure"},  # T004
    10: {"phase": "Phase 1: Foundation & Setup", "group": "Core Infrastructure"},  # T005
    
    # Phase 2
    11: {"phase": "Phase 2: Feature Implementation", "group": None},  # Phase 2
    # Task Groups
    12: {"phase": "Phase 2: Feature Implementation", "group": "API Development"},  # API Dev
    16: {"phase": "Phase 2: Feature Implementation", "group": "Integration"},  # Integration
    # Tasks
    13: {"phase": "Phase 2: Feature Implementation", "group": "API Development"},  # T006
    14: {"phase": "Phase 2: Feature Implementation", "group": "API Development"},  # T007
    15: {"phase": "Phase 2: Feature Implementation", "group": "API Development"},  # T008
    17: {"phase": "Phase 2: Feature Implementation", "group": "Integration"},  # T009
}

# Set field values
print("\n📝 Setting field values...")
for item in project["items"]["nodes"]:
    item_id = item["id"]
    issue_num = item["content"]["number"]
    title = item["content"]["title"]
    
    if issue_num not in issue_mappings:
        print(f"⚠️  Skipping #{issue_num} (no mapping)")
        continue
    
    mapping = issue_mappings[issue_num]
    print(f"\n  #{issue_num}: {title}")
    
    # Set Phase
    phase_option_id = phase_options[mapping["phase"]]
    mutation = f"""
    mutation {{
      updateProjectV2ItemFieldValue(input: {{
        projectId: "{project_id}"
        itemId: "{item_id}"
        fieldId: "{phase_field['id']}"
        value: {{singleSelectOptionId: "{phase_option_id}"}}
      }}) {{
        projectV2Item {{
          id
        }}
      }}
    }}
    """
    result = run_mutation(mutation)
    if result:
        print(f"    ✓ Phase: {mapping['phase']}")
    
    # Set Task Group (if applicable)
    if mapping["group"]:
        group_option_id = task_group_options[mapping["group"]]
        mutation = f"""
        mutation {{
          updateProjectV2ItemFieldValue(input: {{
            projectId: "{project_id}"
            itemId: "{item_id}"
            fieldId: "{task_group_field['id']}"
            value: {{singleSelectOptionId: "{group_option_id}"}}
          }}) {{
            projectV2Item {{
              id
            }}
          }}
        }}
        """
        result = run_mutation(mutation)
        if result:
            print(f"    ✓ Task Group: {mapping['group']}")

print("\n✅ All field values set!")
