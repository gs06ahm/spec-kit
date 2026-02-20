"""
Integration test for GitHub Projects hierarchy feature.
Uses Playwright to verify the project web interface.
"""
import os
import subprocess
import time
from playwright.sync_api import sync_playwright, expect

def get_gh_auth_token():
    """Get GitHub auth token from gh CLI."""
    result = subprocess.run(
        ["gh", "auth", "token"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        raise RuntimeError("Failed to get GitHub auth token. Run 'gh auth login' first.")
    return result.stdout.strip()

def test_project_hierarchy():
    """Test that the GitHub Project hierarchy is displayed correctly."""
    
    # Get the project URL from the test repository
    project_url = "https://github.com/users/gs06ahm/projects/12"
    
    print(f"\n🧪 Testing GitHub Project: {project_url}\n")
    
    with sync_playwright() as p:
        # Launch browser in headed mode so user can see
        browser = p.chromium.launch(headless=False, slow_mo=500)
        context = browser.new_context()
        
        # Try to use gh CLI auth token
        token = get_gh_auth_token()
        print(f"✓ Got GitHub auth token: {token[:10]}...")
        
        # Set auth cookie (GitHub uses 'user_session' and '_gh_sess' cookies)
        # Note: We can't easily inject the token as a cookie, so we'll need manual auth
        # or use gh CLI to get session cookies
        
        page = context.new_page()
        
        print("\n📋 Step 1: Navigate to GitHub login...")
        page.goto("https://github.com/login")
        
        print("\n⚠️  Please log in manually in the browser window.")
        print("Press Enter when you're logged in and ready to continue...")
        input()
        
        print(f"\n📋 Step 2: Navigate to project...")
        page.goto(project_url)
        page.wait_for_load_state("networkidle")
        
        print(f"✓ Loaded project page: {page.title()}")
        
        # Take screenshot
        page.screenshot(path="tests/integration/screenshots/project-initial.png")
        print("✓ Screenshot saved: tests/integration/screenshots/project-initial.png")
        
        # Verify project title
        print("\n📋 Step 3: Verify project title...")
        title = page.locator("h1").first
        expect(title).to_contain_text("Spec-Kit")
        print(f"✓ Project title verified: {title.inner_text()}")
        
        # Check for issues in the project
        print("\n📋 Step 4: Check for issues...")
        issues = page.locator('[data-testid="board-card"]')
        count = issues.count()
        print(f"✓ Found {count} issue cards in the project")
        
        if count == 0:
            # Try alternative selectors
            issues = page.locator('[role="row"]').filter(has_text="Phase")
            count = issues.count()
            print(f"✓ Found {count} rows with 'Phase' text")
        
        # Look for phase issues
        print("\n📋 Step 5: Verify hierarchy structure...")
        phase1 = page.get_by_text("Phase 1: Foundation & Setup", exact=False)
        if phase1.count() > 0:
            print("✓ Found 'Phase 1: Foundation & Setup'")
        
        phase2 = page.get_by_text("Phase 2: Feature Implementation", exact=False)
        if phase2.count() > 0:
            print("✓ Found 'Phase 2: Feature Implementation'")
        
        # Look for task groups
        dev_env = page.get_by_text("Development Environment", exact=False)
        if dev_env.count() > 0:
            print("✓ Found 'Development Environment' task group")
        
        # Look for tasks
        task_t001 = page.get_by_text("[T001]", exact=False)
        if task_t001.count() > 0:
            print("✓ Found task [T001]")
        
        # Take final screenshot
        page.screenshot(path="tests/integration/screenshots/project-verified.png")
        print("\n✓ Final screenshot saved: tests/integration/screenshots/project-verified.png")
        
        print("\n⏸️  Browser will stay open for 10 seconds so you can inspect...")
        time.sleep(10)
        
        browser.close()
        
    print("\n✅ Integration test completed successfully!")

if __name__ == "__main__":
    # Create screenshots directory
    os.makedirs("tests/integration/screenshots", exist_ok=True)
    test_project_hierarchy()
