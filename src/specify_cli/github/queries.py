"""GraphQL queries for GitHub Projects API."""

from typing import Optional

# Query to get the current user's ID
GET_VIEWER_QUERY = """
query GetViewer {
  viewer {
    id
    login
  }
}
"""

# Query to get repository ID
GET_REPOSITORY_QUERY = """
query GetRepository($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    id
    name
    owner {
      id
      login
    }
  }
}
"""

# Query to find a project by number
FIND_PROJECT_QUERY = """
query FindProject($owner: String!, $number: Int!) {
  user(login: $owner) {
    projectV2(number: $number) {
      id
      title
      number
      url
      fields(first: 50) {
        nodes {
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
  }
}
"""

# Query to get project fields by project ID
GET_PROJECT_FIELDS_QUERY = """
query GetProjectFields($projectId: ID!) {
  node(id: $projectId) {
    ... on ProjectV2 {
      fields(first: 50) {
        nodes {
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
  }
}
"""

# Query to get project items with pagination
GET_PROJECT_ITEMS_QUERY = """
query GetProjectItems($projectId: ID!, $cursor: String) {
  node(id: $projectId) {
    ... on ProjectV2 {
      items(first: 100, after: $cursor) {
        pageInfo {
          hasNextPage
          endCursor
        }
        nodes {
          id
          content {
            ... on Issue {
              id
              number
              title
              state
              url
            }
          }
          fieldValues(first: 50) {
            nodes {
              ... on ProjectV2ItemFieldTextValue {
                text
                field {
                  ... on ProjectV2Field {
                    id
                    name
                  }
                }
              }
              ... on ProjectV2ItemFieldSingleSelectValue {
                name
                field {
                  ... on ProjectV2SingleSelectField {
                    id
                    name
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
"""

# Query to get an issue by its ID
GET_ISSUE_QUERY = """
query GetIssue($issueId: ID!) {
  node(id: $issueId) {
    ... on Issue {
      id
      number
      title
      state
      url
    }
  }
}
"""
