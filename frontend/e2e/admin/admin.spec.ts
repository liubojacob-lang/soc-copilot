/**
 * E2E Tests for Admin Features
 *
 * Tests user management, settings, and admin-only functionality.
 */

import { test, expect } from '@playwright/test';
import { login, logout, TEST_USERS } from '../utils/auth';

test.describe('User Management - View Users', () => {
  test.beforeEach(async ({ page }) => {
    const admin = TEST_USERS.admin;
    await login(page, admin.username, admin.password);
  });

  test('should display user list', async ({ page }) => {
    await page.goto('/admin/users');

    // Check page title
    await expect(page.locator('h1:has-text("Users")')).toBeVisible();

    // Check for user table
    await expect(page.locator('[data-testid="user-table"]')).toBeVisible();

    // Should show columns
    await expect(page.locator('th:has-text("Username")')).toBeVisible();
    await expect(page.locator('th:has-text("Role")')).toBeVisible();
    await expect(page.locator('th:has-text("Status")')).toBeVisible();
  });

  test('should search for users', async ({ page }) => {
    await page.goto('/admin/users');

    // Search for admin user
    await page.fill('[data-testid="user-search"]', 'admin');

    // Should filter results
    await expect(page.locator('[data-testid="user-row"]')).toHaveCount.greaterThan(0);
  });

  test('should filter users by role', async ({ page }) => {
    await page.goto('/admin/users');

    // Filter by analysts
    await page.click('[data-testid="role-filter"]');
    await page.click('input[value="analyst"]');
    await page.click('button:has-text("Apply")');

    // Should only show analysts
    const analysts = page.locator('[data-testid="user-row"][data-role="analyst"]');
    await expect(analysts).toHaveCount.greaterThan(0);
  });
});

test.describe('User Management - Create User', () => {
  test.beforeEach(async ({ page }) => {
    const admin = TEST_USERS.admin;
    await login(page, admin.username, admin.password);
  });

  test('should create new user', async ({ page }) => {
    await page.goto('/admin/users');

    // Click create user button
    await page.click('button:has-text("Add User")');

    // Fill user details
    await page.fill('input[name="username"]', 'test_user_e2e');
    await page.fill('input[name="email"]', 'test_e2e@example.com');
    await page.fill('input[name="password"]', 'TestPassword123!');
    await page.fill('input[name="confirm_password"]', 'TestPassword123!');
    await page.selectOption('[data-testid="role-select"]', 'analyst');

    // Save user
    await page.click('button:has-text("Create")');

    // Should show success message
    await expect(page.locator('text=/user created/i')).toBeVisible();

    // Should show new user in list
    await expect(page.locator('text="test_user_e2e"')).toBeVisible();
  });

  test('should validate user input', async ({ page }) => {
    await page.goto('/admin/users');
    await page.click('button:has-text("Add User")');

    // Try to create without username
    await page.click('button:has-text("Create")');

    // Should show validation error
    await expect(page.locator('text=/username is required/i')).toBeVisible();

    // Fill username but with weak password
    await page.fill('input[name="username"]', 'test_user');
    await page.fill('input[name="password"]', 'weak');

    await page.click('button:has-text("Create")');

    // Should show password strength error
    await expect(page.locator('text=/password must be/i')).toBeVisible();
  });

  test('should check for duplicate username', async ({ page }) => {
    await page.goto('/admin/users');
    await page.click('button:has-text("Add User")');

    // Try to create admin user again
    await page.fill('input[name="username"]', 'admin');
    await page.fill('input[name="email"]', 'admin2@example.com');
    await page.fill('input[name="password"]', 'AdminPass123!');
    await page.fill('input[name="confirm_password"]', 'AdminPass123!');

    await page.click('button:has-text("Create")');

    // Should show duplicate error
    await expect(page.locator('text=/username already exists/i')).toBeVisible();
  });
});

test.describe('User Management - Edit User', () => {
  test.beforeEach(async ({ page }) => {
    const admin = TEST_USERS.admin;
    await login(page, admin.username, admin.password);
  });

  test('should update user role', async ({ page }) => {
    await page.goto('/admin/users');

    // Click on first non-admin user
    await page.click('[data-testid="user-row"]:not([data-role="admin"]):first-child');

    // Edit user
    await page.click('button:has-text("Edit")');

    // Change role
    await page.selectOption('[data-testid="role-select"]', 'auditor');

    // Save changes
    await page.click('button:has-text("Save")');

    await expect(page.locator('text=/user updated/i')).toBeVisible();

    // Role should be updated in table
    await expect(page.locator('[data-testid="user-role"]')).toContainText('auditor');
  });

  test('should reset user password', async ({ page }) => {
    await page.goto('/admin/users');

    await page.click('[data-testid="user-row"]:first-child');
    await page.click('button:has-text("Reset Password")');

    // Generate new password
    await page.click('button:has-text("Generate Password")');

    // Should show generated password
    await expect(page.locator('[data-testid="generated-password"]')).toBeVisible();

    // Confirm reset
    await page.click('button:has-text("Reset")');

    await expect(page.locator('text=/password reset/i')).toBeVisible();
  });

  test('should activate/deactivate user', async ({ page }) => {
    await page.goto('/admin/users');

    await page.click('[data-testid="user-row"]:first-child');
    await page.click('button:has-text("Deactivate")');

    // Confirm
    await page.click('button:has-text("Confirm")');

    await expect(page.locator('text=/user deactivated/i')).toBeVisible();

    // Status should be updated
    await expect(page.locator('[data-testid="user-status"]')).toContainText('inactive');

    // Reactivate
    await page.click('button:has-text("Activate")');
    await expect(page.locator('text=/user activated/i')).toBeVisible();
  });

  test('should delete user', async ({ page }) => {
    await page.goto('/admin/users');

    // Create a user to delete first
    await page.click('button:has-text("Add User")');
    await page.fill('input[name="username"]', 'user_to_delete');
    await page.fill('input[name="email"]', 'delete@example.com');
    await page.fill('input[name="password"]', 'DeleteMe123!');
    await page.fill('input[name="confirm_password"]', 'DeleteMe123!');
    await page.selectOption('[data-testid="role-select"]', 'analyst');
    await page.click('button:has-text("Create")');

    await page.waitForTimeout(1000);

    // Delete the user
    await page.click('[data-testid="user-row"][data-username="user_to_delete"]');
    await page.click('button:has-text("Delete")');

    // Confirm
    await page.click('button:has-text("Confirm")');

    await expect(page.locator('text=/user deleted/i')).toBeVisible();

    // User should not be in list
    await expect(page.locator('text="user_to_delete"')).not.toBeVisible();
  });
});

test.describe('API Key Management', () => {
  test.beforeEach(async ({ page }) => {
    const admin = TEST_USERS.admin;
    await login(page, admin.username, admin.password);
  });

  test('should view API keys', async ({ page }) => {
    await page.goto('/settings');
    await page.click('button:has-text("API Keys")');

    // Should show API key list
    await expect(page.locator('[data-testid="api-key-list"]')).toBeVisible();
  });

  test('should create new API key', async ({ page }) => {
    await page.goto('/settings');
    await page.click('button:has-text("API Keys")');

    await page.click('button:has-text("Create API Key")');

    // Fill key details
    await page.fill('input[name="key_name"]', 'E2E Test Key');
    await page.check('input[value="read"]');
    await page.check('input[value="write"]');

    // Create
    await page.click('button:has-text("Create")');

    // Should show new key (only shown once)
    await expect(page.locator('[data-testid="new-api-key"]')).toBeVisible();

    // Should have copy button
    await expect(page.locator('button:has-text("Copy")')).toBeVisible();
  });

  test('should revoke API key', async ({ page }) => {
    await page.goto('/settings');
    await page.click('button:has-text("API Keys")');

    // Revoke first key
    await page.click('[data-testid="api-key-item"]:first-child');
    await page.click('button:has-text("Revoke")');

    // Confirm
    await page.click('button:has-text("Confirm")');

    await expect(page.locator('text=/key revoked/i')).toBeVisible();
  });
});

test.describe('System Settings', () => {
  test.beforeEach(async ({ page }) => {
    const admin = TEST_USERS.admin;
    await login(page, admin.username, admin.password);
  });

  test('should view system settings', async ({ page }) => {
    await page.goto('/admin/settings');

    // Should show settings sections
    await expect(page.locator('[data-testid="general-settings"]')).toBeVisible();
    await expect(page.locator('[data-testid="security-settings"]')).toBeVisible();
    await expect(page.locator('[data-testid="notification-settings"]')).toBeVisible();
  });

  test('should update general settings', async ({ page }) => {
    await page.goto('/admin/settings');

    // Update session timeout
    await page.fill('input[name="session_timeout"]', '60');

    // Save
    await page.click('button:has-text("Save Settings")');

    await expect(page.locator('text=/settings saved/i')).toBeVisible();
  });

  test('should configure AI provider settings', async ({ page }) => {
    await page.goto('/admin/settings');
    await page.click('button:has-text("AI Configuration")');

    // Should show AI provider options
    await expect(page.locator('[data-testid="ai-provider-select"]')).toBeVisible();

    // Change provider
    await page.selectOption('[data-testid="ai-provider-select"]', 'openai');

    // Add API key
    await page.fill('input[name="provider_api_key"]', 'sk-test-key');
    await page.fill('input[name="provider_model"]', 'gpt-4');

    await page.click('button:has-text("Save")');

    await expect(page.locator('text=/ai configuration saved/i')).toBeVisible();
  });
});

test.describe('Audit Logs', () => {
  test.beforeEach(async ({ page }) => {
    const admin = TEST_USERS.admin;
    await login(page, admin.username, admin.password);
  });

  test('should view audit logs', async ({ page }) => {
    await page.goto('/admin/audit');

    // Should show audit log table
    await expect(page.locator('[data-testid="audit-log-table"]')).toBeVisible();

    // Should have columns
    await expect(page.locator('th:has-text("Timestamp")')).toBeVisible();
    await expect(page.locator('th:has-text("User")')).toBeVisible();
    await expect(page.locator('th:has-text("Action")')).toBeVisible();
  });

  test('should filter audit logs', async ({ page }) => {
    await page.goto('/admin/audit');

    // Filter by action
    await page.click('[data-testid="action-filter"]');
    await page.click('input[value="login"]');
    await page.click('button:has-text("Apply")');

    // Should show only login events
    const loginEvents = page.locator('[data-testid="audit-row"][data-action="login"]');
    await expect(loginEvents).toHaveCount.greaterThan(0);
  });

  test('should export audit logs', async ({ page }) => {
    await page.goto('/admin/audit');

    // Select date range
    await page.click('[data-testid="date-range-picker"]');
    await page.click('button:has-text("Last 30 days")');

    // Export
    await page.click('button:has-text("Export")');
    await page.click('button:has-text("CSV")');

    const download = await page.waitForEvent('download');
    expect(download.suggestedFilename()).toMatch(/.*audit.*\.csv$/);
  });
});

test.describe('System Health', () => {
  test.beforeEach(async ({ page }) => {
    const admin = TEST_USERS.admin;
    await login(page, admin.username, admin.password);
  });

  test('should display system health dashboard', async ({ page }) => {
    await page.goto('/admin/health');

    // Should show health metrics
    await expect(page.locator('[data-testid="health-status"]')).toBeVisible();
    await expect(page.locator('[data-testid="cpu-usage"]')).toBeVisible();
    await expect(page.locator('[data-testid="memory-usage"]')).toBeVisible();
    await expect(page.locator('[data-testid="disk-usage"]')).toBeVisible();
  });

  test('should show database connection status', async ({ page }) => {
    await page.goto('/admin/health');

    // Should show DB status
    await expect(page.locator('[data-testid="db-status"]')).toBeVisible();
    await expect(page.locator('[data-testid="db-connection-pool"]')).toBeVisible();
  });

  test('should show service status', async ({ page }) => {
    await page.goto('/admin/health');

    // Should show AI service status
    await expect(page.locator('[data-testid="ai-service-status"]')).toBeVisible();

    // Should show Redis status
    await expect(page.locator('[data-testid="redis-status"]')).toBeVisible();
  });
});

test.describe('Role-Based Access Control', () => {
  test('analyst should not access admin pages', async ({ page }) => {
    const analyst = TEST_USERS.analyst;
    await login(page, analyst.username, analyst.password);

    // Try to access admin users page
    await page.goto('/admin/users');

    // Should redirect or show error
    await expect(page.locator('text=/unauthorized|access denied/i')).toBeVisible();
  });

  test('auditor should have read-only access', async ({ page }) => {
    const auditor = TEST_USERS.auditor;
    await login(page, auditor.username, auditor.password);

    // Can view alerts
    await page.goto('/alerts');
    await expect(page.locator('[data-testid="alert-table"]')).toBeVisible();

    // Cannot edit alerts (no edit button)
    await expect(page.locator('button:has-text("Edit")')).not.toBeVisible();
  });

  test('admin should have full access', async ({ page }) => {
    const admin = TEST_USERS.admin;
    await login(page, admin.username, admin.password);

    // Can access all admin pages
    await page.goto('/admin/users');
    await expect(page.locator('[data-testid="user-table"]')).toBeVisible();

    await page.goto('/admin/settings');
    await expect(page.locator('[data-testid="general-settings"]')).toBeVisible();

    await page.goto('/admin/audit');
    await expect(page.locator('[data-testid="audit-log-table"]')).toBeVisible();
  });
});
