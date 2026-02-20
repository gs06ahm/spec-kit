#!/usr/bin/env python3
"""Add Task Group custom field to project."""
import json
import subprocess
import sys

def run_graphql(query, variables=None):
    """Run a GraphQL query using gh CLI."""
    cmd = ["gh", "api", "graphql", "-f", f"query={query}"]
    if variables:
        for key, value in variables.items():
            if isinstance(value, (dict, list)):
                cmd.extend(["-F", f"{key}={json.dumps(value)}"])
            else:
                cmd.extend(["-f", f"{key}={value}"])
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return json.loads(result.stdout)

# Get project ID
project_query = """
query {
  user(login: "gs06ahm") {
    projectV2(number: 12) {
      id
    }
  }
}
"""

result = run_graphql(project_query)
project_id = result["data"]["user"]["projectV2"]["id"]
print(f"✓ Project ID: {project_id}")

# Create Task Group field
create_field_mutation = """
mutation CreateField($projectId: ID!, $dataType: ProjectV2CustomFieldType!, $name: String!, $options: [ProjectV2SingleSelectFieldOptionInput!]) {
  createProjectV2Field(input: {
    projectId: $projectId
    dataType: $dataType
    name: $name
    singleSelectOptions: $options
  }) {
    projectV2Field {
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
}
"""

# Task groups from the test data
task_groups = [
    {"name": "Development Environment", "color": "BLUE"},
    {"name": "Core Infrastructure", "color": "GREEN"},
    {"name": "API Development", "color": "YELLOW"},
    {"name": "Integration", "color": "ORANGE"}
]

variables = {
    "projectId": project_id,
    "dataType": "SINGLE_SELECT",
    "name": "Task Group",
    "options": task_groups
}

print("\n📋 Creating Task Group field...")
result = run_graphql(create_field_mutation, variables)
field = result["data"]["createProjectV2Field"]["projectV2Field"]
print(f"✓ Created field: {field['name']} (ID: {field['id']})")
print(f"  Options:")
for option in field["options"]:
    print(f"    - {option['name']} (ID: {option['id']})")

print("\n✅ Task Group field created successfully!")
