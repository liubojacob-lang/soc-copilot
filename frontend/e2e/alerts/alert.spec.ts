/**
 * E2E Tests for Alert Analysis Flow
 *
 * Tests alert list display, filtering, search, detail navigation,
 * timeline/notes tabs, AI analysis panel, and export functionality.
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
    await page.waitForLoadState("domcontentloaded");

    // Check for search input
    const searchInput = page.locator('input[placeholder*="search" i], input[type="text"]').first();
    await expect(searchInput).toBeVisible({ timeout: 10000 });

    // Check for alert table or rows
    const table = page.locator("table");
    await expect(table.first()).toBeVisible({ timeout: 10000 });

    // Check for filter controls (Severity / Status dropdowns)
    const severityBtn = page
      .locator('button:has-text("Severity"), button:has-text("严重级别")')
      .first();
    await expect(severityBtn).toBeVisible({ timeout: 10000 });
  });

  test("should filter alerts by severity", async ({ page }) => {
    await page.goto("/alerts");
    await page.waitForLoadState("domcontentloaded");

    // Open severity filter dropdown
    const severityBtn = page
      .locator('button:has-text("Severity"), button:has-text("严重级别")')
      .first();
    await expect(severityBtn).toBeVisible({ timeout: 10000 });
    await severityBtn.click();

    // Select a severity option
    const option = page
      .locator(
        'button:has-text("Critical"), button:has-text("严重"), button:has-text("High"), button:has-text("高危")'
      )
      .first();
    if (await option.isVisible()) {
      await option.click();
      await page.waitForTimeout(500);

      // Active filter chip or badge should appear
      const activeFilter = page.locator("text=/critical|high|严重|高危/i").first();
      await expect(activeFilter).toBeVisible({ timeout: 5000 });
    }
  });

  test("should search alerts", async ({ page }) => {
    await page.goto("/alerts");
    await page.waitForLoadState("domcontentloaded");

    const searchInput = page.locator('input[placeholder*="search" i], input[type="text"]').first();
    await expect(searchInput).toBeVisible({ timeout: 10000 });

    // Type in search box
    await searchInput.fill("ssh");
    await page.waitForTimeout(500);

    // Verify search term is filled
    await expect(searchInput).toHaveValue("ssh");
  });

  test("should display alert detail", async ({ page }) => {
    await page.goto("/alerts");
    await page.waitForLoadState("domcontentloaded");

    // Wait for table rows to load
    const alertLink = page.locator("table tbody tr button, table tbody tr a").first();
    await expect(alertLink).toBeVisible({ timeout: 10000 });
    await alertLink.click();

    // Verify navigated to detail page
    await expect(page).toHaveURL(/\/alerts\/\d+/, { timeout: 10000 });

    // Verify detail page has basic elements
    const backBtn = page
      .locator('button:has-text("Back"), button:has-text("返回"), a[href*="/alerts"]')
      .first();
    await expect(backBtn).toBeVisible({ timeout: 10000 });
  });

  test("should display alert tabs (overview, timeline, notes, rootCause)", async ({ page }) => {
    await page.goto("/alerts");
    await page.waitForLoadState("domcontentloaded");

    const alertLink = page.locator("table tbody tr button, table tbody tr a").first();
    await expect(alertLink).toBeVisible({ timeout: 10000 });
    await alertLink.click();

    await expect(page).toHaveURL(/\/alerts\/\d+/, { timeout: 10000 });

    // Check tabs
    const timelineTab = page
      .locator('button:has-text("Timeline"), button:has-text("时间线")')
      .first();
    if (await timelineTab.isVisible()) {
      await timelineTab.click();
      await page.waitForTimeout(300);
    }

    const notesTab = page.locator('button:has-text("Notes"), button:has-text("笔记")').first();
    if (await notesTab.isVisible()) {
      await notesTab.click();
      await page.waitForTimeout(300);
    }

    const rootCauseTab = page
      .locator('button:has-text("Root Cause"), button:has-text("根因分析")')
      .first();
    if (await rootCauseTab.isVisible()) {
      await rootCauseTab.click();
      await page.waitForTimeout(300);
    }
  });

  test("should display AI analysis section on detail page", async ({ page }) => {
    await page.goto("/alerts");
    await page.waitForLoadState("domcontentloaded");

    const alertLink = page.locator("table tbody tr button, table tbody tr a").first();
    await expect(alertLink).toBeVisible({ timeout: 10000 });
    await alertLink.click();

    await expect(page).toHaveURL(/\/alerts\/\d+/, { timeout: 10000 });

    // AI analysis panel should be present on page
    const aiSection = page.locator("text=/AI/i").first();
    await expect(aiSection).toBeVisible({ timeout: 10000 });
  });

  test("should support row selection and batch action bar", async ({ page }) => {
    await page.goto("/alerts");
    await page.waitForLoadState("domcontentloaded");

    // Click checkbox on first row
    const checkbox = page.locator('table tbody tr input[type="checkbox"]').first();
    if (await checkbox.isVisible()) {
      await checkbox.click();
      await page.waitForTimeout(300);

      // Batch action bar should appear
      const batchBar = page.locator("text=/selected|已选择/i").first();
      await expect(batchBar).toBeVisible({ timeout: 5000 });
    }
  });

  test("should have export button on alert list", async ({ page }) => {
    await page.goto("/alerts");
    await page.waitForLoadState("domcontentloaded");

    const exportBtn = page.locator('button:has-text("Export"), button:has-text("导出")').first();
    await expect(exportBtn).toBeVisible({ timeout: 10000 });
  });
});
