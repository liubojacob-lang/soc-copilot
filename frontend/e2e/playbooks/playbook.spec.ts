/**
 * E2E Tests for Playbook Execution Flow
 * 
 * Tests playbook creation, execution, and monitoring.
 */

import { test, expect } from '@playwright/test';
import { login, TEST_USERS } from '../utils/auth';

test.describe('Playbook Management', () => {
  test.beforeEach(async ({ page }) => {
    // Login as admin for full access
    const admin = TEST_USERS.admin;
    await login(page, admin.username, admin.password);
  });

  test('should display playbook list page', async ({ page }) => {
    await page.goto('/playbooks');
    
    // Check page title
    await expect(page.locator('h1:has-text("Playbooks")')).toBeVisible();
    
    // Check for playbook table or list
    await expect(page.locator('[data-testid="playbook-list"]')).toBeVisible();
    
    // Check for create button
    await expect(page.locator('button:has-text("Create")')).toBeVisible();
  });

  test('should create a new playbook', async ({ page }) => {
    await page.goto('/playbooks');
    
    // Click create button
    await page.click('button:has-text("Create")');
    
    // Fill in playbook details
    await page.fill('input[name="name"]', 'E2E Test Playbook');
    await page.fill('textarea[name="description"]', 'Created by E2E tests');
    
    // Add a step (assuming there's a step builder)
    await page.click('button:has-text("Add Step")');
    
    // Select step type
    await page.click('[data-testid="step-type-otx-lookup"]');
    
    // Save playbook
    await page.click('button:has-text("Save")');
    
    // Should show success message
    await expect(page.locator('text=/playbook created/i')).toBeVisible();
    
    // Should redirect to playbook detail
    await expect(page).toHaveURL(/.*playbooks\/.+/);
  });

  test('should execute a playbook', async ({ page }) => {
    // Navigate to existing playbook
    await page.goto('/playbooks');
    
    // Click on first playbook
    await page.click('[data-testid="playbook-item"]:first-child');
    
    // Wait for playbook detail
    await page.waitForSelector('[data-testid="playbook-detail"]');
    
    // Click run button
    await page.click('button:has-text("Run")');
    
    // Should show run configuration modal
    await page.waitForSelector('[data-testid="run-config-modal"]');
    
    // Confirm run
    await page.click('button:has-text("Start")');
    
    // Should redirect to run detail
    await page.waitForURL(/.*runs\/.+/);
    
    // Should show running status
    await expect(page.locator('[data-testid="run-status"]')).toContainText(/running|pending/i);
  });

  test('should display playbook run history', async ({ page }) => {
    await page.goto('/playbooks');
    
    // Click on history tab
    await page.click('button:has-text("History")');
    
    // Should show run history table
    await expect(page.locator('[data-testid="run-history-table"]')).toBeVisible();
    
    // Should have columns for status, time, duration
    await expect(page.locator('th:has-text("Status")')).toBeVisible();
    await expect(page.locator('th:has-text("Started")')).toBeVisible();
    await expect(page.locator('th:has-text("Duration")')).toBeVisible();
  });

  test('should show playbook run details', async ({ page }) => {
    await page.goto('/playbooks');
    
    // Click on history tab
    await page.click('button:has-text("History")');
    
    // Click on first run
    await page.click('[data-testid="run-item"]:first-child');
    
    // Should show run detail page
    await expect(page.locator('[data-testid="run-detail"]')).toBeVisible();
    
    // Should show step execution timeline
    await expect(page.locator('[data-testid="step-timeline"]')).toBeVisible();
    
    // Should show output
    await expect(page.locator('[data-testid="run-output"]')).toBeVisible();
  });

  test('should cancel a running playbook', async ({ page }) => {
    // Start a playbook run first
    await page.goto('/playbooks');
    await page.click('[data-testid="playbook-item"]:first-child');
    await page.click('button:has-text("Run")');
    await page.click('button:has-text("Start")');
    
    // Wait for run to start
    await page.waitForURL(/.*runs\/.+/);
    
    // Click cancel button
    await page.click('button:has-text("Cancel")');
    
    // Confirm cancellation
    await page.click('button:has-text("Confirm")');
    
    // Should show cancelled status
    await expect(page.locator('[data-testid="run-status"]')).toContainText(/cancelled/i);
  });

  test('should edit playbook definition', async ({ page }) => {
    await page.goto('/playbooks');
    
    // Click on first playbook
    await page.click('[data-testid="playbook-item"]:first-child');
    
    // Click edit button
    await page.click('button:has-text("Edit")');
    
    // Modify description
    const descriptionField = page.locator('textarea[name="description"]');
    await descriptionField.fill('Updated by E2E test');
    
    // Save changes
    await page.click('button:has-text("Save")');
    
    // Should show success message
    await expect(page.locator('text=/playbook updated/i')).toBeVisible();
  });

  test('should delete a playbook', async ({ page }) => {
    // Create a playbook to delete
    await page.goto('/playbooks');
    await page.click('button:has-text("Create")');
    await page.fill('input[name="name"]', 'Playbook to Delete');
    await page.click('button:has-text("Save")');
    
    // Wait for creation
    await page.waitForURL(/.*playbooks\/.+/);
    
    // Delete the playbook
    await page.click('button:has-text("Delete")');
    
    // Confirm deletion
    await page.click('button:has-text("Confirm")');
    
    // Should redirect to list
    await page.waitForURL(/.*playbooks$/);
    
    // Should not show deleted playbook
    await expect(page.locator('text="Playbook to Delete"')).not.toBeVisible();
  });

  test('should validate playbook input', async ({ page }) => {
    await page.goto('/playbooks');
    await page.click('button:has-text("Create")');
    
    // Try to save without name
    await page.click('button:has-text("Save")');
    
    // Should show validation error
    await expect(page.locator('text=/name is required/i')).toBeVisible();
    
    // Fill name but with invalid characters
    await page.fill('input[name="name"]', 'Invalid@Name!');
    await page.click('button:has-text("Save")');
    
    // Should show validation error for invalid characters
    await expect(page.locator('text=/invalid characters/i')).toBeVisible();
  });
});

test.describe('Playbook DAG Visualization', () => {
  test.beforeEach(async ({ page }) => {
    const admin = TEST_USERS.admin;
    await login(page, admin.username, admin.password);
  });

  test('should display DAG visualization', async ({ page }) => {
    await page.goto('/playbooks');
    await page.click('[data-testid="playbook-item"]:first-child');
    
    // Click on DAG view tab
    await page.click('button:has-text("DAG View")');
    
    // Should show DAG canvas
    await expect(page.locator('[data-testid="dag-canvas"]')).toBeVisible();
    
    // Should show nodes
    await expect(page.locator('[data-testid="dag-node"]')).toHaveCount.greaterThan(0);
  });

  test('should highlight execution path in DAG', async ({ page }) => {
    // Navigate to a completed run
    await page.goto('/playbooks');
    await page.click('button:has-text("History")');
    await page.click('[data-testid="run-item"][data-status="completed"]:first-child');
    
    // Should show DAG with highlighted path
    await expect(page.locator('[data-testid="dag-node"][data-status="completed"]')).toHaveCount.greaterThan(0);
  });

  test('should allow zooming and panning in DAG', async ({ page }) => {
    await page.goto('/playbooks');
    await page.click('[data-testid="playbook-item"]:first-child');
    await page.click('button:has-text("DAG View")');
    
    // Zoom in
    await page.click('button[aria-label="Zoom in"]');
    
    // Zoom out
    await page.click('button[aria-label="Zoom out"]');
    
    // Reset zoom
    await page.click('button[aria-label="Reset zoom"]');
    
    // Should have zoom controls visible
    await expect(page.locator('[data-testid="zoom-controls"]')).toBeVisible();
  });
});

test.describe('Playbook Approval Workflow', () => {
  test.beforeEach(async ({ page }) => {
    const admin = TEST_USERS.admin;
    await login(page, admin.username, admin.password);
  });

  test('should request approval for playbook', async ({ page }) => {
    await page.goto('/playbooks');
    await page.click('[data-testid="playbook-item"]:first-child');
    
    // Click request approval
    await page.click('button:has-text("Request Approval")');
    
    // Fill approval request
    await page.fill('textarea[name="justification"]', 'E2E test approval request');
    await page.click('button:has-text("Submit")');
    
    // Should show pending status
    await expect(page.locator('[data-testid="approval-status"]')).toContainText(/pending/i);
  });

  test('should approve playbook', async ({ page }) => {
    // Navigate to pending approvals
    await page.goto('/approvals');
    
    // Click on first pending approval
    await page.click('[data-testid="approval-item"][data-status="pending"]:first-child');
    
    // Approve
    await page.fill('textarea[name="comment"]', 'Approved by E2E test');
    await page.click('button:has-text("Approve")');
    
    // Should show approved status
    await expect(page.locator('[data-testid="approval-status"]')).toContainText(/approved/i);
  });

  test('should reject playbook', async ({ page }) => {
    await page.goto('/approvals');
    await page.click('[data-testid="approval-item"][data-status="pending"]:first-child');
    
    // Reject
    await page.fill('textarea[name="comment"]', 'Rejected by E2E test');
    await page.click('button:has-text("Reject")');
    
    // Should show rejected status
    await expect(page.locator('[data-testid="approval-status"]')).toContainText(/rejected/i);
  });
});
