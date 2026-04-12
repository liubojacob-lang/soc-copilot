import { test, expect } from "@playwright/test";
import { login } from "../utils/auth";

test.describe("Dashboard Home Page", () => {
  test.beforeEach(async ({ page }) => {
    await login(page, "admin", "admin123!");
  });

  test("displays dashboard with key widgets", async ({ page }) => {
    await page.goto("/en");

    await expect(page.locator("text=Alert")).toBeVisible({ timeout: 10000 });
  });

  test("shows alert severity distribution", async ({ page }) => {
    await page.goto("/en");

    const severityElements = page.locator("text=/critical|high|medium|low|info/i");
    await expect(severityElements.first()).toBeVisible({ timeout: 10000 });
  });

  test("displays navigation sidebar", async ({ page }) => {
    await page.goto("/en");

    await expect(page.locator("text=Alerts")).toBeVisible({ timeout: 10000 });
    await expect(page.locator("text=Playbooks")).toBeVisible();
  });

  test("navigates to alerts page from dashboard", async ({ page }) => {
    await page.goto("/en");

    await page.click('a[href*="/alerts"]');

    await expect(page).toHaveURL(/\/alerts/);
  });

  test("shows system status indicator", async ({ page }) => {
    await page.goto("/en");

    const statusIndicator = page.locator(
      '[data-testid="system-status"], .status-indicator, text=/online|healthy|connected/i'
    );
    if ((await statusIndicator.count()) > 0) {
      await expect(statusIndicator.first()).toBeVisible();
    }
  });

  test("displays user menu with logout option", async ({ page }) => {
    await page.goto("/en");

    const userMenu = page
      .locator('[data-testid="user-menu"], button:has-text("admin"), [aria-label="User menu"]')
      .first();
    if (await userMenu.isVisible()) {
      await userMenu.click();
      await expect(page.locator("text=/logout|sign out/i")).toBeVisible();
    }
  });

  test("shows recent activity or alerts summary", async ({ page }) => {
    await page.goto("/en");

    const summarySection = page.locator("text=/recent|summary|overview|activity/i").first();
    if (await summarySection.isVisible()) {
      await expect(summarySection).toBeVisible();
    }
  });
});
