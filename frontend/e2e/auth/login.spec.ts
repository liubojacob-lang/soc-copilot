/**
 * E2E Tests for Authentication Flow
 * 
 * Tests login, logout, and session management.
 */

import { test, expect } from '@playwright/test';
import { login, logout, isLoggedIn, TEST_USERS } from '../utils/auth';

test.describe('Authentication', () => {
  test.describe.configure({ mode: 'serial' });
  
  test.beforeEach(async ({ page }) => {
    // Start from a fresh state
    await page.goto('/');
  });

  test('should display login page for unauthenticated users', async ({ page }) => {
    await page.goto('/dashboard');
    
    // Should redirect to login
    await page.waitForURL('**/login', { timeout: 10000 });
    
    // Check login form elements
    await expect(page.locator('input[name="username"]')).toBeVisible();
    await expect(page.locator('input[name="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('should login successfully with valid credentials', async ({ page }) => {
    const admin = TEST_USERS.admin;
    
    await login(page, admin.username, admin.password);
    
    // Should be on dashboard
    await expect(page).toHaveURL(/.*dashboard.*/);
    
    // Should show user menu
    await expect(page.locator('[data-testid="user-menu"]')).toBeVisible();
    
    // Should show navigation
    await expect(page.locator('nav')).toBeVisible();
  });

  test('should show error for invalid credentials', async ({ page }) => {
    await page.goto('/login');
    
    await page.fill('input[name="username"]', 'invalid_user');
    await page.fill('input[name="password"]', 'wrong_password');
    await page.click('button[type="submit"]');
    
    // Should show error message
    await expect(page.locator('[data-testid="error-message"]')).toBeVisible();
    
    // Should still be on login page
    await expect(page).toHaveURL(/.*login.*/);
  });

  test('should logout successfully', async ({ page }) => {
    // Login first
    const admin = TEST_USERS.admin;
    await login(page, admin.username, admin.password);
    
    // Verify logged in
    expect(await isLoggedIn(page)).toBe(true);
    
    // Logout
    await logout(page);
    
    // Should redirect to login
    await page.waitForURL('**/login', { timeout: 10000 });
    
    // Verify logged out
    expect(await isLoggedIn(page)).toBe(false);
  });

  test('should persist session across page reloads', async ({ page }) => {
    // Login
    const admin = TEST_USERS.admin;
    await login(page, admin.username, admin.password);
    
    // Reload page
    await page.reload();
    
    // Should still be logged in
    expect(await isLoggedIn(page)).toBe(true);
  });

  test('should redirect to original URL after login', async ({ page }) => {
    // Try to access protected page
    await page.goto('/playbooks');
    
    // Should redirect to login
    await page.waitForURL('**/login', { timeout: 10000 });
    
    // Login
    const admin = TEST_USERS.admin;
    await page.fill('input[name="username"]', admin.username);
    await page.fill('input[name="password"]', admin.password);
    await page.click('button[type="submit"]');
    
    // Should redirect back to playbooks
    await page.waitForURL('**/playbooks', { timeout: 10000 });
  });

  test('should validate required fields', async ({ page }) => {
    await page.goto('/login');
    
    // Submit without filling fields
    await page.click('button[type="submit"]');
    
    // Should show validation errors
    await expect(page.locator('input[name="username"]:invalid')).toBeVisible();
    await expect(page.locator('input[name="password"]:invalid')).toBeVisible();
  });

  test('should disable submit button while logging in', async ({ page }) => {
    await page.goto('/login');
    
    const admin = TEST_USERS.admin;
    await page.fill('input[name="username"]', admin.username);
    await page.fill('input[name="password"]', admin.password);
    
    const submitButton = page.locator('button[type="submit"]');
    
    // Click and check if button is disabled during request
    await submitButton.click();
    
    // Button should show loading state
    await expect(submitButton).toBeDisabled();
  });
});

test.describe('Role-based Access Control', () => {
  test('admin should have access to all pages', async ({ page }) => {
    const admin = TEST_USERS.admin;
    await login(page, admin.username, admin.password);
    
    // Check admin-only pages
    const adminPages = ['/settings', '/users', '/api-keys'];
    
    for (const adminPage of adminPages) {
      await page.goto(adminPage);
      await expect(page).not.toHaveURL(/.*login.*/);
    }
  });

  test('analyst should not have access to admin pages', async ({ page }) => {
    const analyst = TEST_USERS.analyst;
    await login(page, analyst.username, analyst.password);
    
    // Try to access admin page
    await page.goto('/settings');
    
    // Should show access denied or redirect
    await expect(
      page.locator('text=/access denied|unauthorized/i')
    ).toBeVisible();
  });

  test('auditor should have read-only access', async ({ page }) => {
    const auditor = TEST_USERS.auditor;
    await login(page, auditor.username, auditor.password);
    
    // Navigate to audit logs
    await page.goto('/audit-logs');
    await expect(page).toHaveURL(/.*audit-logs.*/);
    
    // Should not see create/edit buttons
    await expect(page.locator('button:has-text("Create")')).not.toBeVisible();
    await expect(page.locator('button:has-text("Edit")')).not.toBeVisible();
  });
});
