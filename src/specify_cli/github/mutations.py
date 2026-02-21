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


def create_project(
    owner_id: str,
    title: str,
    repository_id: Optional[str] = None,
) -> tuple[str, dict]:
    """
    Create mutation to create a new ProjectV2.
    
    Args:
        owner_id: User or organization ID
        title: Project title
        repository_id: Optional repository ID to link
        
    Returns:
        Tuple of (mutation, variables)
    """
    input_data: Dict[str, Any] = {
        "ownerId": owner_id,
        "title": title,
    }
    
    if repository_id:
        input_data["repositoryId"] = repository_id
    
    return CREATE_PROJECT_MUTATION, {"input": input_data}


def update_project(
    project_id: str,
    title: Optional[str] = None,
    short_description: Optional[str] = None,
    readme: Optional[str] = None,
    public: Optional[bool] = None,
) -> tuple[str, dict]:
    """
    Create mutation to update project details.
    
    Args:
        project_id: Project ID
        title: New title (optional)
        short_description: New description (optional)
        readme: New README content (optional)
        public: Make project public (optional)
        
    Returns:
        Tuple of (mutation, variables)
    """
    input_data: Dict[str, Any] = {"projectId": project_id}
    
    if title is not None:
        input_data["title"] = title
    if short_description is not None:
        input_data["shortDescription"] = short_description
    if readme is not None:
        input_data["readme"] = readme
    if public is not None:
        input_data["public"] = public
    
    return UPDATE_PROJECT_MUTATION, {"input": input_data}


def create_field(
    project_id: str,
    name: str,
    data_type: str,
    single_select_options: Optional[List[Dict[str, str]]] = None,
) -> tuple[str, dict]:
    """
    Create mutation to create a custom field.
    
    Args:
        project_id: Project ID
        name: Field name
        data_type: Field data type (TEXT, NUMBER, DATE, SINGLE_SELECT, ITERATION)
        single_select_options: Options for SINGLE_SELECT fields
                               List of dicts with 'name', 'description', 'color'
        
    Returns:
        Tuple of (mutation, variables)
    """
    input_data: Dict[str, Any] = {
        "projectId": project_id,
        "name": name,
        "dataType": data_type,
    }
    
    if single_select_options:
        input_data["singleSelectOptions"] = single_select_options
    
    return CREATE_FIELD_MUTATION, {"input": input_data}


def create_issue(
    repository_id: str,
    title: str,
    body: Optional[str] = None,
    label_ids: Optional[List[str]] = None,
) -> tuple[str, dict]:
    """
    Create mutation to create an issue.
    
    Args:
        repository_id: Repository ID
        title: Issue title
        body: Issue body (optional)
        label_ids: List of label IDs (optional)
        
    Returns:
        Tuple of (mutation, variables)
    """
    input_data: Dict[str, Any] = {
        "repositoryId": repository_id,
        "title": title,
    }
    
    if body is not None:
        input_data["body"] = body
    if label_ids:
        input_data["labelIds"] = label_ids
    
    return CREATE_ISSUE_MUTATION, {"input": input_data}


def add_project_item(project_id: str, content_id: str) -> tuple[str, dict]:
    """
    Create mutation to add an item to a project.
    
    Args:
        project_id: Project ID
        content_id: Content ID (issue or pull request)
        
    Returns:
        Tuple of (mutation, variables)
    """
    input_data = {
        "projectId": project_id,
        "contentId": content_id,
    }
    
    return ADD_PROJECT_ITEM_MUTATION, {"input": input_data}


def update_field_value(
    project_id: str,
    item_id: str,
    field_id: str,
    value: Dict[str, Any],
) -> tuple[str, dict]:
    """
    Create mutation to update a field value.
    
    Args:
        project_id: Project ID
        item_id: Item ID
        field_id: Field ID
        value: Field value (structure depends on field type)
               - TEXT: {"text": "value"}
               - NUMBER: {"number": 42}
               - DATE: {"date": "2024-01-01"}
               - SINGLE_SELECT: {"singleSelectOptionId": "option_id"}
               - ITERATION: {"iterationId": "iteration_id"}
        
    Returns:
        Tuple of (mutation, variables)
    """
    input_data = {
        "projectId": project_id,
        "itemId": item_id,
        "fieldId": field_id,
        "value": value,
    }
    
    return UPDATE_FIELD_VALUE_MUTATION, {"input": input_data}


def update_issue(
    issue_id: str,
    state: Optional[str] = None,
    title: Optional[str] = None,
    body: Optional[str] = None,
) -> tuple[str, dict]:
    """
    Create mutation to update an issue.
    
    Args:
        issue_id: Issue ID
        state: New state (OPEN or CLOSED)
        title: New title (optional)
        body: New body (optional)
        
    Returns:
        Tuple of (mutation, variables)
    """
    input_data: Dict[str, Any] = {"id": issue_id}
    
    if state is not None:
        input_data["state"] = state
    if title is not None:
        input_data["title"] = title
    if body is not None:
        input_data["body"] = body
    
    return UPDATE_ISSUE_MUTATION, {"input": input_data}


def create_label(
    repository_id: str,
    name: str,
    color: str,
    description: Optional[str] = None,
) -> tuple[str, dict]:
    """
    Create mutation to create a label.
    
    Args:
        repository_id: Repository ID
        name: Label name
        color: Label color (6-digit hex without #)
        description: Label description (optional)
        
    Returns:
        Tuple of (mutation, variables)
    """
    input_data: Dict[str, Any] = {
        "repositoryId": repository_id,
        "name": name,
        "color": color,
    }
    
    if description is not None:
        input_data["description"] = description
    
    return CREATE_LABEL_MUTATION, {"input": input_data}
