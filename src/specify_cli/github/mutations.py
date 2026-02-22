"""GraphQL mutations for GitHub Projects API."""

from typing import Optional, List, Dict, Any


# Create a new ProjectV2
CREATE_PROJECT_MUTATION = """
mutation CreateProject($input: CreateProjectV2Input!) {
  createProjectV2(input: $input) {
    projectV2 {
      id
      number
      title
      url
    }
  }
}
"""

# Update project details
UPDATE_PROJECT_MUTATION = """
mutation UpdateProject($input: UpdateProjectV2Input!) {
  updateProjectV2(input: $input) {
    projectV2 {
      id
      title
      shortDescription
      readme
    }
  }
}
"""

# Create a custom field
CREATE_FIELD_MUTATION = """
mutation CreateField($input: CreateProjectV2FieldInput!) {
  createProjectV2Field(input: $input) {
    projectV2Field {
      ... on ProjectV2Field {
        id
        name
        dataType
      }
      ... on ProjectV2SingleSelectField {
        id
        name
        dataType
        options {
          id
          name
          color
        }
      }
    }
  }
}
"""

# Create an issue
CREATE_ISSUE_MUTATION = """
mutation CreateIssue($input: CreateIssueInput!) {
  createIssue(input: $input) {
    issue {
      id
      number
      title
      url
    }
  }
}
"""

# Add item to project
ADD_PROJECT_ITEM_MUTATION = """
mutation AddProjectItem($input: AddProjectV2ItemByIdInput!) {
  addProjectV2ItemById(input: $input) {
    item {
      id
    }
  }
}
"""

# Set field value
UPDATE_FIELD_VALUE_MUTATION = """
mutation UpdateFieldValue($input: UpdateProjectV2ItemFieldValueInput!) {
  updateProjectV2ItemFieldValue(input: $input) {
    projectV2Item {
      id
    }
  }
}
"""

# Update issue state (close/reopen)
UPDATE_ISSUE_MUTATION = """
mutation UpdateIssue($input: UpdateIssueInput!) {
  updateIssue(input: $input) {
    issue {
      id
      state
    }
  }
}
"""

# Create label
CREATE_LABEL_MUTATION = """
mutation CreateLabel($input: CreateLabelInput!) {
  createLabel(input: $input) {
    label {
      id
      name
      color
    }
  }
}
"""

# Add issue dependency (blocked by)
ADD_BLOCKED_BY_MUTATION = """
mutation AddBlockedBy($input: AddBlockedByInput!) {
  addBlockedBy(input: $input) {
    issue {
      id
      number
    }
    blockingIssue {
      id
      number
    }
  }
}
"""
