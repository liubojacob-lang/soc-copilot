import { test, expect } from "@playwright/test";

test.describe("E2E Verification Test", () => {
  test("should load homepage", async ({ page }) => {
    const response = await page.goto("http://localhost:3003/en");
    expect(response?.status()).toBeLessThan(500);

    await page.waitForLoadState("networkidle");
    await page.screenshot({ path: "playwright-report/homepage.png" });

    console.log("✅ Homepage loaded");
  });

  test("should load login page", async ({ page }) => {
    const response = await page.goto("http://localhost:3003/en/login");
    expect(response?.status()).toBeLessThan(500);

    await page.waitForLoadState("domcontentloaded");

    const h1 = page.locator("h1");
    const text = await h1.textContent();
    console.log("Page title:", text);

    expect(text).toContain("SOC");
  });

  test("should have login form", async ({ page }) => {
    await page.goto("http://localhost:3003/en/login");
    await page.waitForLoadState("domcontentloaded");

    const usernameInput = page.locator("#username");
    const passwordInput = page.locator("#password");
    const submitBtn = page.locator('button[type="submit"]');

    expect(await usernameInput.count()).toBeGreaterThan(0);
    expect(await passwordInput.count()).toBeGreaterThan(0);
    expect(await submitBtn.count()).toBeGreaterThan(0);

    console.log("✅ All form elements found");
  });
});
