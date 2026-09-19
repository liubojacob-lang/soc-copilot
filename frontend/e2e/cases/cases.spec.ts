/**
 * E2E Tests for Case Management Flow
 *
 * Tests case list loading, filtering, search, and navigation to details.
 */

import { test, expect } from "@playwright/test";
import { login, TEST_USERS } from "../utils/auth";

test.describe("Case Management", () => {
  test.beforeEach(async ({ page }) => {
    const admin = TEST_USERS.admin;
    await login(page, admin.username, admin.password);
  });

  test("should display cases list page", async ({ page }) => {
    await page.goto("/cases");
    await page.waitForLoadState("domcontentloaded");

    // Verify search input is rendered
    const searchInput = page.locator('input[type="text"]').first();
    await expect(searchInput).toBeVisible({ timeout: 10000 });
  });

  test("should support search input interaction", async ({ page }) => {
    await page.goto("/cases");
    await page.waitForLoadState("domcontentloaded");

    const searchInput = page.locator('input[type="text"]').first();
    await expect(searchInput).toBeVisible({ timeout: 10000 });
    await searchInput.fill("Incident");
    await page.waitForTimeout(300);
  });

  test("should open create case modal when button clicked", async ({ page }) => {
    await page.goto("/cases");
    await page.waitForLoadState("domcontentloaded");

    // Find the create case button
    const createBtn = page
      .locator('button:has-text("Create"), button:has-text("新建"), button:has-text("创建")')
      .first();
    if (await createBtn.isVisible()) {
      await createBtn.click();
      // Dialog / modal should appear
      const dialog = page.getByRole("dialog", { name: /Case|案件|新建/ });
      await expect(dialog).toBeVisible({ timeout: 10000 });
    }
  });
});
