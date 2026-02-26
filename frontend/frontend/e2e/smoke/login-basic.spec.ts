import { test, expect } from '@playwright/test';

test.describe('Basic Login Smoke Test', () => {
  test('should access login page', async ({ page }) => {
    await page.goto('/en/login');
    await page.waitForLoadState('networkidle');
    
    await expect(page.locator('h1')).toContainText('SOC Copilot');
    await expect(page.locator('#username')).toBeVisible();
    await expect(page.locator('#password')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('should show dev mode credentials', async ({ page }) => {
    await page.goto('/en/login');
    await page.waitForLoadState('networkidle');
    
    const devModeText = page.locator('text=admin / admin123');
    await expect(devModeText).toBeVisible();
  });
});
