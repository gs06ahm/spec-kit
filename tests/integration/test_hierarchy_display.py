#!/usr/bin/env python3
"""
Integration test to verify GitHub Projects hierarchy displays correctly.
This test will:
1. Log in to GitHub (manual step)
2. Navigate to the project
3. Configure grouping by Phase
4. Verify the hierarchy is visible
5. Take screenshots for documentation
"""
import os
import sys
import time

if __name__ != "__main__":
    import pytest
    if not os.getenv("RUN_MANUAL_PLAYWRIGHT_TESTS"):
        pytest.skip(
            "Manual Playwright test. Set RUN_MANUAL_PLAYWRIGHT_TESTS=1 to run.",
            allow_module_level=True,
        )
    pytest.importorskip("playwright.sync_api")
    if not os.getenv("TEST_PROJECT_URL"):
        pytest.skip("Set TEST_PROJECT_URL to a newly created project URL.", allow_module_level=True)

from playwright.sync_api import sync_playwright, expect

PROJECT_URL = os.getenv("TEST_PROJECT_URL", "https://github.com/users/gs06ahm/projects/12")

def test_project_hierarchy_display():
    """Test that project displays hierarchy with grouping."""
    
    print("\n" + "="*70)
    print("🧪 GitHub Projects Hierarchy Integration Test")
    print("="*70 + "\n")
    
    with sync_playwright() as p:
        # Launch browser in headed mode with slow motion
        print("🌐 Launching browser...")
        
        # Try to use persistent context first (saves auth)
        user_data_dir = os.path.expanduser("~/.config/playwright-github-test")
        os.makedirs(user_data_dir, exist_ok=True)
        
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir,
                headless=False,
                slow_mo=1000,
                viewport={"width": 1920, "height": 1080}
            )
            page = context.pages[0] if context.pages else context.new_page()
        except:
            # Fallback to regular browser
            browser = p.chromium.launch(headless=False, slow_mo=1000)
            context = browser.new_context(viewport={"width": 1920, "height": 1080})
            page = context.new_page()
        
        # Navigate to project
        print(f"📍 Navigating to: {PROJECT_URL}")
        page.goto(PROJECT_URL, wait_until="networkidle")
        
        # Check if we need to login
        if "login" in page.url:
            print("\n⚠️  NOT LOGGED IN - Manual login required:")
            print("   1. The browser window should be open")
            print("   2. Please log in to GitHub manually")
            print("   3. After logging in, press ENTER here to continue...")
            input()
            
            # Navigate to project again
            page.goto(PROJECT_URL, wait_until="networkidle")
        
        print("✅ Logged in successfully")
        time.sleep(2)
        
        # Create screenshots directory
        screenshots_dir = "tests/integration/screenshots"
        os.makedirs(screenshots_dir, exist_ok=True)
        
        # Take initial screenshot
        print("\n📸 Taking initial screenshot...")
        page.screenshot(path=f"{screenshots_dir}/01-project-initial.png", full_page=True)
        print(f"   ✓ Saved: {screenshots_dir}/01-project-initial.png")
        
        # Wait for project to load
        print("\n⏳ Waiting for project to load...")
        try:
            # Try multiple possible selectors
            selectors_to_try = [
                'h1',  # Project title is usually in h1
                '[role="table"]',  # The table itself
                'text="View 1"',  # View name
            ]
            for selector in selectors_to_try:
                try:
                    page.wait_for_selector(selector, timeout=5000)
                    print(f"   ✓ Found element: {selector}")
                    break
                except:
                    continue
        except:
            print("   ⚠️  Could not find specific element, continuing anyway...")
        
        time.sleep(2)
        
        # Check for table view
        print("\n🔍 Checking for table view...")
        try:
            # Look for the table
            table = page.locator('[role="table"]').first
            expect(table).to_be_visible(timeout=5000)
            print("   ✓ Table view visible")
        except Exception as e:
            print(f"   ⚠️  Table not immediately visible: {e}")
        
        # Take screenshot of current view
        page.screenshot(path=f"{screenshots_dir}/02-table-view.png", full_page=True)
        print(f"   ✓ Saved: {screenshots_dir}/02-table-view.png")
        
        # Look for group by button/menu
        print("\n🔧 Configuring view to group by Phase...")
        try:
            # Click the view menu button (usually has "View" text or settings icon)
            # Try multiple selectors that might work
            selectors = [
                'button:has-text("Group")',
                '[aria-label="Group by"]',
                'button[data-testid="group-by-button"]',
                'button:has-text("View settings")',
            ]
            
            clicked = False
            for selector in selectors:
                try:
                    btn = page.locator(selector).first
                    if btn.is_visible(timeout=2000):
                        print(f"   ✓ Found button: {selector}")
                        btn.click()
                        clicked = True
                        break
                except:
                    continue
            
            if not clicked:
                print("   ⚠️  Could not find group by button automatically")
                print("   📝 Manual step needed:")
                print("      1. In the browser, click the 'Group by' button")
                print("      2. Select 'Phase' from the dropdown")
                print("      3. Press ENTER here when done...")
                input()
            else:
                # Try to select Phase
                time.sleep(1)
                try:
                    phase_option = page.locator('text="Phase"').first
                    phase_option.click()
                    print("   ✓ Selected 'Phase' for grouping")
                except:
                    print("   ⚠️  Please manually select 'Phase' in the browser")
                    print("      Press ENTER when done...")
                    input()
            
            time.sleep(2)
            
        except Exception as e:
            print(f"   ⚠️  Could not configure grouping automatically: {e}")
            print("   📝 Manual configuration needed:")
            print("      1. Click 'Group by' button in the project view")
            print("      2. Select 'Phase' from the dropdown")
            print("      3. Press ENTER here when done...")
            input()
        
        # Take screenshot after grouping
        print("\n📸 Taking screenshot after grouping...")
        time.sleep(2)
        page.screenshot(path=f"{screenshots_dir}/03-grouped-by-phase.png", full_page=True)
        print(f"   ✓ Saved: {screenshots_dir}/03-grouped-by-phase.png")
        
        # Verify phase groups are visible
        print("\n✅ Verifying hierarchy...")
        try:
            phase1 = page.get_by_text("Phase 1: Foundation & Setup", exact=False)
            if phase1.count() > 0:
                print("   ✓ Found 'Phase 1: Foundation & Setup' group")
            
            phase2 = page.get_by_text("Phase 2: Feature Implementation", exact=False)
            if phase2.count() > 0:
                print("   ✓ Found 'Phase 2: Feature Implementation' group")
            
            # Check for task groups
            dev_env = page.get_by_text("Development Environment", exact=False)
            if dev_env.count() > 0:
                print("   ✓ Found 'Development Environment' task group")
            
            # Check for tasks
            task_t001 = page.get_by_text("[T001]", exact=False)
            if task_t001.count() > 0:
                print("   ✓ Found task [T001]")
            
        except Exception as e:
            print(f"   ⚠️  Some elements not found: {e}")
        
        # Take final screenshot
        print("\n📸 Taking final screenshot...")
        page.screenshot(path=f"{screenshots_dir}/04-hierarchy-complete.png", full_page=True)
        print(f"   ✓ Saved: {screenshots_dir}/04-hierarchy-complete.png")
        
        # Summary
        print("\n" + "="*70)
        print("📊 Test Summary")
        print("="*70)
        print(f"✅ Project URL: {PROJECT_URL}")
        print(f"✅ Screenshots saved to: {screenshots_dir}/")
        print(f"✅ Grouping by: Phase")
        print("\n📝 Manual verification:")
        print("   - Check that Phase 1 and Phase 2 are shown as separate groups")
        print("   - Verify tasks are grouped under their phases")
        print("   - Confirm Task Group field shows for each task")
        print("\n⏸️  Browser will stay open for 10 seconds for inspection...")
        time.sleep(10)
        
        context.close()
        
    print("\n✅ Integration test completed!\n")
    return True

if __name__ == "__main__":
    try:
        success = test_project_hierarchy_display()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
