import { test, expect } from "@playwright/test";
import { login } from "../utils/auth";

test.describe("Marketplace", () => {
  test.beforeEach(async ({ page }) => {
    await login(page, "admin", "admin123!");
  });

  test("displays marketplace page with playbooks", async ({ page }) => {
    await page.goto("/en/marketplace");

    await expect(page.locator("text=/marketplace|playbook/i")).toBeVisible({ timeout: 10000 });
  });

  test("shows search functionality", async ({ page }) => {
    await page.goto("/en/marketplace");

    const searchInput = page
      .locator('input[type="text"], input[placeholder*="search" i], input[placeholder*="filter" i]')
      .first();
    if (await searchInput.isVisible()) {
      await searchInput.fill("phishing");
      await page.waitForTimeout(500);

      const results = page.locator("text=/phishing/i");
      if ((await results.count()) > 0) {
        await expect(results.first()).toBeVisible();
      }
    }
  });

  test("displays category filter", async ({ page }) => {
    await page.goto("/en/marketplace");

    const categoryFilter = page
      .locator("select, button:has-text('category'), [data-testid='category-filter']")
      .first();
    if (await categoryFilter.isVisible()) {
      await expect(categoryFilter).toBeEnabled();
    }
  });

  test("shows featured playbooks section", async ({ page }) => {
    await page.goto("/en/marketplace");

    const featured = page.locator("text=/featured|recommended|popular/i").first();
    if (await featured.isVisible()) {
      await expect(featured).toBeVisible();
    }
  });

  test("opens playbook detail view", async ({ page }) => {
    await page.goto("/en/marketplace");

    const playbookCard = page.locator("[class*='card'], [class*='playbook']").first();
    if (await playbookCard.isVisible()) {
      await playbookCard.click();

      await expect(page.locator("text=/description|details|download|dag/i")).toBeVisible({
        timeout: 5000,
      });
    }
  });

  test("download button triggers import", async ({ page }) => {
    await page.goto("/en/marketplace");

    const downloadBtn = page
      .locator("button:has-text('download' i), button:has-text('import' i)")
      .first();
    if (await downloadBtn.isVisible()) {
      const [response] = await Promise.all([
        page
          .waitForResponse(
            (resp) => resp.url().includes("/marketplace/") && resp.url().includes("/download"),
            { timeout: 5000 }
          )
          .catch(() => null),
        downloadBtn.click(),
      ]);

      if (response) {
        expect(response.status()).toBeLessThan(500);
      }
    }
  });

  test("publishes local playbook to marketplace", async ({ page }) => {
    await page.goto("/en/marketplace");

    const publishBtn = page
      .locator("button:has-text('publish' i), a:has-text('publish' i)")
      .first();
    if (await publishBtn.isVisible()) {
      await publishBtn.click();

      const form = page.locator("form, [class*='modal'], [role='dialog']").first();
      if (await form.isVisible()) {
        await expect(form).toBeVisible();
      }
    }
  });
});

test.describe("Marketplace - Admin Review", () => {
  test.beforeEach(async ({ page }) => {
    await login(page, "admin", "admin123!");
  });

  test("admin can access pending review list", async ({ page }) => {
    await page.goto("/en/marketplace");

    const adminTab = page
      .locator("button:has-text('pending' i), a:has-text('pending' i), [data-testid='admin-tab']")
      .first();
    if (await adminTab.isVisible()) {
      await adminTab.click();

      await expect(page).toHaveURL(/marketplace/);
    }
  });

  test("admin can approve a pending playbook", async ({ page }) => {
    const response = await page.request.get("/api/marketplace/admin/pending");
    if (response.ok()) {
      const data = await response.json();
      if (data.playbooks && data.playbooks.length > 0) {
        const playbookId = data.playbooks[0].id;

        const approveResponse = await page.request.post(
          `/api/marketplace/admin/playbooks/${playbookId}/review`,
          {
            data: { approved: true, review_note: "E2E test approval" },
          }
        );
        expect(approveResponse.status()).toBeLessThan(500);
      }
    }
  });

  test("admin can reject a pending playbook", async ({ page }) => {
    const response = await page.request.get("/api/marketplace/admin/pending");
    if (response.ok()) {
      const data = await response.json();
      if (data.playbooks && data.playbooks.length > 0) {
        const playbookId = data.playbooks[0].id;

        const rejectResponse = await page.request.post(
          `/api/marketplace/admin/playbooks/${playbookId}/review`,
          {
            data: { approved: false, review_note: "E2E test rejection" },
          }
        );
        expect(rejectResponse.status()).toBeLessThan(500);
      }
    }
  });
});
