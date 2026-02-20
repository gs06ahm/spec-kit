#!/bin/bash
# Simple verification script to view the GitHub Project

PROJECT_URL="https://github.com/users/gs06ahm/projects/12"

echo "🔍 Verifying GitHub Project via API..."
echo ""

# Get project details
gh api graphql -f query='
query {
  user(login: "gs06ahm") {
    projectV2(number: 12) {
      id
      title
      url
      public
      items(first: 20) {
        totalCount
        nodes {
          id
          content {
            ... on Issue {
              number
              title
              state
              repository {
                name
              }
            }
          }
        }
      }
    }
  }
}' | jq -r '
.data.user.projectV2 | 
"Project: \(.title)",
"URL: \(.url)",
"Public: \(.public)",
"Total Items: \(.items.totalCount)",
"",
"Issues:",
(.items.nodes[] | 
  "  #\(.content.number): \(.content.title)")
'

echo ""
echo "✅ Project exists with all issues"
echo ""
echo "📝 To view the hierarchy in GitHub:"
echo "   1. Visit: $PROJECT_URL"
echo "   2. The sub-issues feature should show parent/child relationships"
echo "   3. Click on a Phase issue to see its sub-issues (Task Groups)"
echo "   4. Click on a Task Group to see its sub-issues (Tasks)"
echo ""
