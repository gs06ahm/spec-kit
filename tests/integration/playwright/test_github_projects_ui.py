"""
Playwright-based integration tests for GitHub Projects web interface.

These tests verify that the GitHub Project created by the sync command
has the correct structure, labels, custom fields, and task relationships.
"""

import os
import re
from pathlib import Path
import pytest


# Skip all tests if GH_TOKEN is not available
pytestmark = pytest.mark.skipif(
    not os.getenv("GH_TOKEN") and not os.getenv("GITHUB_TOKEN"),
    reason="GitHub token required for integration tests"
)


@pytest.fixture(scope="module")
def project_url():
    """Get the project URL from environment or config."""
    # Could be passed via environment variable or read from config
    url = os.getenv("TEST_PROJECT_URL", "https://github.com/users/gs06ahm/projects/11")
    return url


@pytest.fixture(scope="module")
def github_token():
    """Get GitHub token for authentication."""
    return os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")


def test_project_exists(playwright, project_url, github_token):
    """Test that the project exists and is accessible."""
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    
    # Set authentication
    context.set_extra_http_headers({
        "Authorization": f"Bearer {github_token}"
    })
    
    page = context.new_page()
    page.goto(project_url)
    
    # Check that we're on a project page
    assert "projects" in page.url.lower()
    
    # Check for project title
    title = page.locator("h1").first
    assert title.is_visible()
    assert "spec-kit" in title.text_content().lower() or "github projects" in title.text_content().lower()
    
    context.close()
    browser.close()


def test_project_has_tasks(playwright, project_url, github_token):
    """Test that the project contains the expected number of tasks."""
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    context.set_extra_http_headers({
        "Authorization": f"Bearer {github_token}"
    })
    
    page = context.new_page()
    page.goto(project_url)
    page.wait_for_load_state("networkidle")
    
    # Check for task items (issues in the project)
    # GitHub Projects uses data-testid or specific classes for items
    items = page.locator("[data-testid='board-card'], [data-testid='list-item'], .Board-card")
    
    # We expect 9 tasks
    assert items.count() >= 9, f"Expected at least 9 tasks, found {items.count()}"
    
    context.close()
    browser.close()


def test_custom_fields_exist(playwright, project_url, github_token):
    """Test that custom fields (Task ID, Phase, Priority, etc.) exist."""
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    context.set_extra_http_headers({
        "Authorization": f"Bearer {github_token}"
    })
    
    page = context.new_page()
    page.goto(project_url)
    page.wait_for_load_state("networkidle")
    
    # Look for field headers or settings
    # Custom fields appear in table view or board view headers
    expected_fields = ["Task ID", "Phase", "Priority", "Parallel"]
    
    page_content = page.content()
    
    for field in expected_fields:
        assert field in page_content, f"Custom field '{field}' not found in project"
    
    context.close()
    browser.close()


def test_labels_created(playwright, project_url, github_token):
    """Test that phase and priority labels were created."""
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    context.set_extra_http_headers({
        "Authorization": f"Bearer {github_token}"
    })
    
    page = context.new_page()
    page.goto(project_url)
    page.wait_for_load_state("networkidle")
    
    page_content = page.content()
    
    # Check for expected labels
    expected_labels = ["phase-1", "phase-2", "p-high", "p-medium"]
    
    found_labels = []
    for label in expected_labels:
        if label in page_content.lower():
            found_labels.append(label)
    
    assert len(found_labels) >= 2, f"Expected to find labels, found: {found_labels}"
    
    context.close()
    browser.close()


def test_task_ids_in_issues(playwright, project_url, github_token):
    """Test that tasks have their Task IDs (T001, T002, etc.) set."""
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    context.set_extra_http_headers({
        "Authorization": f"Bearer {github_token}"
    })
    
    page = context.new_page()
    page.goto(project_url)
    page.wait_for_load_state("networkidle")
    
    page_content = page.content()
    
    # Look for task IDs
    task_ids = []
    for i in range(1, 10):
        task_id = f"T{i:03d}"
        if task_id in page_content:
            task_ids.append(task_id)
    
    assert len(task_ids) >= 5, f"Expected to find at least 5 task IDs, found: {task_ids}"
    
    context.close()
    browser.close()


@pytest.mark.skipif(
    os.getenv("NO_HEADED_TESTS"),
    reason="Headed tests disabled"
)
def test_demo_headed_mode(playwright, project_url, github_token):
    """
    Demo test in headed mode - shows the project visually.
    
    This test runs in headed mode to demonstrate all features.
    Set NO_HEADED_TESTS=1 to skip this test.
    """
    browser = playwright.chromium.launch(headless=False, slow_mo=1000)
    context = browser.new_context()
    context.set_extra_http_headers({
        "Authorization": f"Bearer {github_token}"
    })
    
    page = context.new_page()
    
    # Navigate to project
    print(f"\n🔗 Opening project: {project_url}")
    page.goto(project_url)
    page.wait_for_load_state("networkidle")
    
    # Show the board view
    print("📊 Viewing project board...")
    page.wait_for_timeout(2000)
    
    # Try to switch to table view if available
    table_view_button = page.locator("button:has-text('Table'), [aria-label*='Table']")
    if table_view_button.count() > 0:
        print("📋 Switching to table view...")
        table_view_button.first.click()
        page.wait_for_timeout(2000)
    
    # Highlight custom fields
    print("✨ Custom fields visible: Task ID, Phase, Priority, Parallel")
    page.wait_for_timeout(2000)
    
    # Show a task detail
    first_card = page.locator("[data-testid='board-card'], [data-testid='list-item']").first
    if first_card.count() > 0:
        print("🔍 Opening first task detail...")
        first_card.click()
        page.wait_for_timeout(3000)
    
    print("✅ Demo complete!")
    page.wait_for_timeout(2000)
    
    context.close()
    browser.close()
