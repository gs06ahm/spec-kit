#!/bin/bash
set -e

echo "================================================================================"
echo "SPEC-KIT GITHUB PROJECTS - COMPLETE END-TO-END TEST"
echo "================================================================================"

# Configuration
OWNER="gs06ahm"
TIMESTAMP=$(date +%s)
REPO_NAME="spec-kit-e2e-${TIMESTAMP}"
PROJECT_TITLE="Spec-Kit E2E Test ${TIMESTAMP}"
TEST_DIR="/tmp/spec-kit-e2e-${TIMESTAMP}"

echo ""
echo "📋 Configuration:"
echo "   Owner: $OWNER"
echo "   Repository: $REPO_NAME"
echo "   Project: $PROJECT_TITLE"
echo "   Test directory: $TEST_DIR"

# Create test directory and tasks.md
mkdir -p "$TEST_DIR/spec"
cat > "$TEST_DIR/spec/tasks.md" << 'TASKS'
# Tasks: GitHub Projects E2E Test

**Input**: spec/spec.md  
**Branch**: `feature/e2e-test`

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
TASKS

echo ""
echo "================================================================================"
echo "STEP 1: CREATE TEST REPOSITORY"
echo "================================================================================"
echo ""
echo "📦 Creating repository: $OWNER/$REPO_NAME"

gh repo create "$OWNER/$REPO_NAME" \
    --private \
    --description "E2E test for GitHub Projects - $TIMESTAMP"

echo "✓ Repository created: https://github.com/$OWNER/$REPO_NAME"

# Clone and setup
echo ""
echo "📥 Cloning repository..."
cd /tmp
git clone "git@github.com:$OWNER/$REPO_NAME.git" "$TEST_DIR-repo" 2>&1 | grep -v "warning: You appear to have cloned an empty" || true
cd "$TEST_DIR-repo"

# Copy tasks.md
cp "$TEST_DIR/spec/tasks.md" .
mkdir -p spec
mv tasks.md spec/

# Commit
git add spec/tasks.md
git config user.email "test@example.com"
git config user.name "E2E Test"
git commit -m "Add tasks.md for E2E test"
git push -u origin main 2>&1 | tail -3

echo "✓ Pushed tasks.md to repository"

echo ""
echo "================================================================================"
echo "STEP 2: RUN SPECIFY GITHUB SYNC"
echo "================================================================================"
echo ""

# Run specify sync
cd "$TEST_DIR-repo"
source /home/adam/src/spec-kit/.venv/bin/activate

echo "🔧 Enabling GitHub Projects integration..."
echo ""
specify projects enable

echo ""
echo "🔄 Running: specify projects sync spec/tasks.md"
echo "   (from directory: $(pwd))"
echo ""

# Capture output and extract project URL
SYNC_OUTPUT=$(specify projects sync spec/tasks.md 2>&1 | tee /dev/tty)
PROJECT_URL=$(echo "$SYNC_OUTPUT" | grep -oP 'https://github.com/users/[^/]+/projects/\d+' | head -1)
PROJECT_NUMBER=$(echo "$PROJECT_URL" | grep -oP '\d+$')

if [ -z "$PROJECT_URL" ]; then
    echo ""
    echo "❌ Error: Could not extract project URL from output"
    exit 1
fi

echo ""
echo "✅ Project created successfully!"
echo "   URL: $PROJECT_URL"
echo "   Project #: $PROJECT_NUMBER"

echo ""
echo "================================================================================"
echo "STEP 3: VALIDATE PROJECT STRUCTURE"
echo "================================================================================"
echo ""

echo "🔍 Running validation tests..."

# Copy validation script to test repo
cp /home/adam/src/spec-kit/tests/integration/validate_project_structure.py .

python validate_project_structure.py \
    --owner "$OWNER" \
    --repo "$REPO_NAME" \
    --project "$PROJECT_NUMBER"

VALIDATION_RESULT=$?
if [ $VALIDATION_RESULT -ne 0 ]; then
    echo ""
    echo "❌ Validation failed!"
    exit 1
fi

echo ""
echo "================================================================================"
echo "STEP 4: CONFIGURE VIEW (MANUAL)"
echo "================================================================================"
echo ""

cat << INSTRUCTIONS

⚠️  MANUAL STEP REQUIRED

The project has been created with the correct structure, but view configuration
must be done manually (GitHub API limitation).

Please follow these steps:

1. Open the project in your browser:
   $PROJECT_URL

2. Click the "View options" button (••• icon) in the top-right

3. Click "Group by: none" to expand the menu

4. Select "Phase" from the list

5. The view will now show:
   ▼ Phase 1: Foundation & Setup (7 items)
   ▼ Phase 2: Feature Implementation (8 items)

6. Press Enter here when done...

INSTRUCTIONS

read -p "Press Enter after configuring the view... "

echo ""
echo "================================================================================"
echo "STEP 5: FINAL VERIFICATION"
echo "================================================================================"
echo ""

echo "🔍 Verifying project structure..."
python validate_project_structure.py \
    --owner "$OWNER" \
    --repo "$REPO_NAME" \
    --project "$PROJECT_NUMBER"

VALIDATION_RESULT=$?
if [ $VALIDATION_RESULT -ne 0 ]; then
    echo ""
    echo "❌ Final validation failed!"
    exit 1
fi

echo ""
echo "================================================================================"
echo "✅ END-TO-END TEST COMPLETE!"
echo "================================================================================"
echo ""

cat << SUMMARY

Project Details:
  URL: $PROJECT_URL
  Repository: https://github.com/$OWNER/$REPO_NAME
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
  - View the project in your browser: $PROJECT_URL
  - Test the grouping by switching to "Task Group" view
  - Archive test repository: gh repo archive $OWNER/$REPO_NAME

Cleanup:
  - Test directory: $TEST_DIR
  - Repository clone: $TEST_DIR-repo

SUMMARY

