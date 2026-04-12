/**
 * E2E Tests for Alert Analysis Flow
 *
 * Tests alert viewing, analysis, and AI-powered insights.
 */

import { test, expect } from "@playwright/test";
import { login, TEST_USERS } from "../utils/auth";

test.describe("Alert Management", () => {
  test.beforeEach(async ({ page }) => {
    const admin = TEST_USERS.admin;
    await login(page, admin.username, admin.password);
  });

  test("should display alert list", async ({ page }) => {
    await page.goto("/alerts");

    // Check page title
    await expect(page.locator('h1:has-text("Alerts")')).toBeVisible();

    // Check for alert table
    await expect(page.locator('[data-testid="alert-table"]')).toBeVisible();

    // Check for filter controls
    await expect(page.locator('[data-testid="alert-filters"]')).toBeVisible();
  });

  test("should filter alerts by severity", async ({ page }) => {
    await page.goto("/alerts");

    // Open severity filter
    await page.click('[data-testid="severity-filter"]');

    // Select critical
    await page.click('input[value="critical"]');

    // Apply filter
    await page.click('button:has-text("Apply")');

    // URL should contain severity filter
    await expect(page).toHaveURL(/.*severity=critical.*/);

    // All visible alerts should be critical
    const alerts = page.locator('[data-testid="alert-row"]');
    const count = await alerts.count();

    for (let i = 0; i < Math.min(count, 5); i++) {
      await expect(alerts.nth(i)).toHaveAttribute("data-severity", "critical");
    }
  });

  test("should search alerts", async ({ page }) => {
    await page.goto("/alerts");

    // Type in search box
    await page.fill('[data-testid="alert-search"]', "phishing");

    // Wait for URL to update (debounce is handled by the component)
    await expect(page).toHaveURL(/.*search=phishing.*/, { timeout: 5000 });
  });

  test("should display alert detail", async ({ page }) => {
    await page.goto("/alerts");

    // Click on first alert
    await page.click('[data-testid="alert-row"]:first-child');

    // Should show alert detail panel
    await expect(page.locator('[data-testid="alert-detail"]')).toBeVisible();

    // Should show key information
    await expect(page.locator('[data-testid="alert-title"]')).toBeVisible();
    await expect(page.locator('[data-testid="alert-severity"]')).toBeVisible();
    await expect(page.locator('[data-testid="alert-timestamp"]')).toBeVisible();
  });

  test("should change alert status", async ({ page }) => {
    await page.goto("/alerts");
    await page.click('[data-testid="alert-row"]:first-child');

    // Open status dropdown
    await page.click('[data-testid="status-dropdown"]');

    // Select "In Progress"
    await page.click('button:has-text("In Progress")');

    // Should show success toast
    await expect(page.locator("text=/status updated/i")).toBeVisible();

    // Status should be updated
    await expect(page.locator('[data-testid="alert-status"]')).toContainText(/in progress/i);
  });

  test("should assign alert to user", async ({ page }) => {
    await page.goto("/alerts");
    await page.click('[data-testid="alert-row"]:first-child');

    // Click assign button
    await page.click('button:has-text("Assign")');

    // Select user from dropdown
    await page.click('[data-testid="assignee-dropdown"]');
    await page.click('[data-testid="assignee-option"]:first-child');

    // Confirm assignment
    await page.click('button:has-text("Confirm")');

    // Should show assigned user
    await expect(page.locator('[data-testid="assigned-user"]')).toBeVisible();
  });

  test("should add comment to alert", async ({ page }) => {
    await page.goto("/alerts");
    await page.click('[data-testid="alert-row"]:first-child');

    // Navigate to comments tab
    await page.click('button:has-text("Comments")');

    // Add comment
    await page.fill('textarea[name="comment"]', "E2E test comment");
    await page.click('button:has-text("Add Comment")');

    // Should show new comment
    await expect(page.locator('text="E2E test comment"')).toBeVisible();
  });
});

test.describe("AI Alert Analysis", () => {
  test.beforeEach(async ({ page }) => {
    const admin = TEST_USERS.admin;
    await login(page, admin.username, admin.password);
  });

  test("should trigger AI analysis", async ({ page }) => {
    await page.goto("/alerts");
    await page.click('[data-testid="alert-row"]:first-child');

    // Click AI analyze button
    await page.click('button:has-text("AI Analyze")');

    // Should show loading state
    await expect(page.locator('[data-testid="ai-analysis-loading"]')).toBeVisible();

    // Wait for analysis to complete (with timeout)
    await expect(page.locator('[data-testid="ai-analysis-result"]')).toBeVisible({
      timeout: 60000, // 60 seconds for AI response
    });
  });

  test("should display AI analysis results", async ({ page }) => {
    // Navigate to alert with existing analysis
    await page.goto("/alerts");
    await page.click('[data-testid="alert-row"][data-has-analysis="true"]:first-child');

    // Click on AI Analysis tab
    await page.click('button:has-text("AI Analysis")');

    // Should show analysis sections
    await expect(page.locator('[data-testid="analysis-summary"]')).toBeVisible();
    await expect(page.locator('[data-testid="analysis-iocs"]')).toBeVisible();
    await expect(page.locator('[data-testid="analysis-recommendations"]')).toBeVisible();
  });

  test("should extract IOCs from AI analysis", async ({ page }) => {
    await page.goto("/alerts");
    await page.click('[data-testid="alert-row"][data-has-analysis="true"]:first-child');
    await page.click('button:has-text("AI Analysis")');

    // Should show IOC list
    const iocSection = page.locator('[data-testid="analysis-iocs"]');
    await expect(iocSection).toBeVisible();

    // IOC items should be clickable
    const firstIoc = iocSection.locator('[data-testid="ioc-item"]:first-child');
    if (await firstIoc.isVisible()) {
      await firstIoc.click();

      // Should show IOC detail or enrichment
      await expect(page.locator('[data-testid="ioc-detail"]')).toBeVisible();
    }
  });

  test("should show AI analysis error gracefully", async ({ page }) => {
    // Mock AI service failure
    await page.route("**/api/ai/analyze", (route) => {
      route.fulfill({
        status: 500,
        body: JSON.stringify({ detail: "AI service unavailable" }),
      });
    });

    await page.goto("/alerts");
    await page.click('[data-testid="alert-row"]:first-child');
    await page.click('button:has-text("AI Analyze")');

    // Should show error message
    await expect(page.locator("text=/analysis failed|unavailable/i")).toBeVisible({
      timeout: 30000,
    });
  });
});

test.describe("Alert Timeline", () => {
  test.beforeEach(async ({ page }) => {
    const admin = TEST_USERS.admin;
    await login(page, admin.username, admin.password);
  });

  test("should display alert timeline", async ({ page }) => {
    await page.goto("/alerts");
    await page.click('[data-testid="alert-row"]:first-child');

    // Click on Timeline tab
    await page.click('button:has-text("Timeline")');

    // Should show timeline
    await expect(page.locator('[data-testid="alert-timeline"]')).toBeVisible();

    // Should show timeline events
    const timelineEventCount = await page.locator('[data-testid="timeline-event"]').count();
    await expect(timelineEventCount).toBeGreaterThan(0);
  });

  test("should show related events in timeline", async ({ page }) => {
    await page.goto("/alerts");
    await page.click('[data-testid="alert-row"]:first-child');
    await page.click('button:has-text("Timeline")');

    // Expand related events
    await page.click('button:has-text("Show Related")');

    // Should show related events
    await expect(page.locator('[data-testid="related-events"]')).toBeVisible();
  });
});

test.describe("Alert Export", () => {
  test.beforeEach(async ({ page }) => {
    const admin = TEST_USERS.admin;
    await login(page, admin.username, admin.password);
  });

  test("should export alerts to CSV", async ({ page }) => {
    await page.goto("/alerts");

    // Select some alerts
    await page.click('[data-testid="alert-checkbox"]:first-child');
    await page.click('[data-testid="alert-checkbox"]:nth-child(2)');

    // Click export
    await page.click('button:has-text("Export")');
    await page.click('button:has-text("CSV")');

    // Should trigger download
    const download = await page.waitForEvent("download");
    expect(download.suggestedFilename()).toMatch(/.*\.csv$/);
  });

  test("should export alerts to JSON", async ({ page }) => {
    await page.goto("/alerts");

    await page.click('[data-testid="alert-checkbox"]:first-child');
    await page.click('button:has-text("Export")');
    await page.click('button:has-text("JSON")');

    const download = await page.waitForEvent("download");
    expect(download.suggestedFilename()).toMatch(/.*\.json$/);
  });
});

test.describe("Alert Bulk Actions", () => {
  test.beforeEach(async ({ page }) => {
    const admin = TEST_USERS.admin;
    await login(page, admin.username, admin.password);
  });

  test("should bulk update status", async ({ page }) => {
    await page.goto("/alerts");

    // Select multiple alerts
    await page.click('[data-testid="alert-checkbox"]:first-child');
    await page.click('[data-testid="alert-checkbox"]:nth-child(2)');
    await page.click('[data-testid="alert-checkbox"]:nth-child(3)');

    // Open bulk actions
    await page.click('button:has-text("Bulk Actions")');
    await page.click('button:has-text("Mark as Resolved")');

    // Confirm
    await page.click('button:has-text("Confirm")');

    // Should show success message
    await expect(page.locator("text=/alerts updated/i")).toBeVisible();
  });

  test("should bulk assign alerts", async ({ page }) => {
    await page.goto("/alerts");

    // Select multiple alerts
    await page.click('[data-testid="select-all-alerts"]');

    // Open bulk actions
    await page.click('button:has-text("Bulk Actions")');
    await page.click('button:has-text("Assign")');

    // Select assignee
    await page.click('[data-testid="assignee-dropdown"]');
    await page.click('[data-testid="assignee-option"]:first-child');

    // Confirm
    await page.click('button:has-text("Confirm")');

    // Should show success message
    await expect(page.locator("text=/alerts assigned/i")).toBeVisible();
  });
});
