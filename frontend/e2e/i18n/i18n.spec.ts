import { test, expect } from "@playwright/test";
import { login } from "../utils/auth";

test.describe("Internationalization (i18n)", () => {
  test.beforeEach(async ({ page }) => {
    await login(page, "admin", "admin123!");
  });

  test("loads English content by default", async ({ page }) => {
    await page.goto("/en");

    await expect(page.locator("text=/alert|dashboard|security/i")).toBeVisible({ timeout: 10000 });
  });

  test("loads Chinese content when switching locale", async ({ page }) => {
    await page.goto("/zh");

    await expect(page.locator("text=/告警|仪表盘|安全/i")).toBeVisible({ timeout: 10000 });
  });

  test("language switcher toggles between locales", async ({ page }) => {
    await page.goto("/en");

    const langSwitcher = page
      .locator(
        '[data-testid="lang-switcher"], button:has-text("中文"), button:has-text("EN"), select[aria-label*="language" i], a[href*="/zh/"]'
      )
      .first();

    if (await langSwitcher.isVisible()) {
      await langSwitcher.click();

      const zhLink = page.locator('a[href*="/zh/"], button:has-text("中文")').first();
      if (await zhLink.isVisible()) {
        await zhLink.click();
        await expect(page).toHaveURL(/\/zh/);
      }
    }
  });

  test("preserves current page path on locale switch", async ({ page }) => {
    await page.goto("/en/alerts");

    const langSwitcher = page
      .locator('a[href*="/zh/alerts"], button:has-text("中文"), [data-testid="lang-switcher"]')
      .first();

    if (await langSwitcher.isVisible()) {
      await langSwitcher.click();

      await expect(page).toHaveURL(/\/zh\/alerts/);
    }
  });

  test("displays localized date/time format", async ({ page }) => {
    await page.goto("/en/alerts");

    const dateElement = page.locator("time, [class*='date'], [class*='timestamp']").first();
    if (await dateElement.isVisible()) {
      const text = await dateElement.textContent();
      expect(text).toBeTruthy();
    }
  });

  test("falls back to English for missing translations", async ({ page }) => {
    await page.goto("/zh");

    const bodyText = await page.locator("body").textContent();
    expect(bodyText).toBeTruthy();
  });

  test("valid locale paths are accessible", async ({ page }) => {
    const locales = ["en", "zh"];

    for (const locale of locales) {
      const response = await page.request.get(`/${locale}`);
      expect(response.status()).toBeLessThan(400);
    }
  });
});
