/**
 * E2E Tests for Report Generation and Export
 *
 * Tests report creation, generation, and export in various formats.
 */

import { test, expect } from '@playwright/test';
import { login, TEST_USERS } from '../utils/auth';

test.describe('Report Generation - Playbook Reports', () => {
  test.beforeEach(async ({ page }) => {
    const admin = TEST_USERS.admin;
    await login(page, admin.username, admin.password);
  });

  test('should generate report for completed playbook run', async ({ page }) => {
    await page.goto('/playbooks');
    await page.click('button:has-text("History")');

    // Click on completed run
    await page.click('[data-testid="run-item"][data-status="completed"]:first-child');

    // Generate report
    await page.click('button:has-text("Generate Report")');

    // Should show report options
    await expect(page.locator('[data-testid="report-options"]')).toBeVisible();

    // Select PDF format
    await page.selectOption('[data-testid="report-format"]', 'pdf');

    // Generate
    await page.click('button:has-text("Generate")');

    // Should show generating state
    await expect(page.locator('[data-testid="report-generating"]')).toBeVisible();

    // Should complete generation
    await expect(page.locator('[data-testid="report-ready"]')).toBeVisible({
      timeout: 30000,
    });
  });

  test('should download generated report', async ({ page }) => {
    await page.goto('/playbooks');
    await page.click('button:has-text("History")');
    await page.click('[data-testid="run-item"][data-status="completed"]:first-child');

    // If report already exists, download it
    const downloadBtn = page.locator('button:has-text("Download")');
    if (await downloadBtn.isVisible()) {
      const downloadPromise = page.waitForEvent('download');
      await downloadBtn.click();
      const download = await downloadPromise;
      expect(download.suggestedFilename()).toMatch(/\.(pdf|html|json)$/);
    } else {
      // Generate first
      await page.click('button:has-text("Generate Report")');
      await page.selectOption('[data-testid="report-format"]', 'pdf');
      await page.click('button:has-text("Generate")');

      await expect(page.locator('[data-testid="report-ready"]')).toBeVisible({
        timeout: 30000,
      });

      // Then download
      const downloadPromise = page.waitForEvent('download');
      await page.click('button:has-text("Download")');
      const download = await downloadPromise;
      expect(download.suggestedFilename()).toMatch(/\.pdf$/);
    }
  });

  test('should customize report sections', async ({ page }) => {
    await page.goto('/playbooks');
    await page.click('button:has-text("History")');
    await page.click('[data-testid="run-item"][data-status="completed"]:first-child');

    await page.click('button:has-text("Generate Report")');

    // Select sections
    await page.check('input[name="include_summary"]');
    await page.check('input[name="include_timeline"]');
    await page.uncheck('input[name="include_artifacts"]');

    // Generate
    await page.click('button:has-text("Generate")');

    await expect(page.locator('[data-testid="report-ready"]')).toBeVisible({
      timeout: 30000,
    });
  });
});

test.describe('Report Generation - Alert Reports', () => {
  test.beforeEach(async ({ page }) => {
    const admin = TEST_USERS.admin;
    await login(page, admin.username, admin.password);
  });

  test('should generate alert batch report', async ({ page }) => {
    await page.goto('/alerts');

    // Select multiple alerts
    await page.click('[data-testid="select-all-alerts"]');

    // Generate report
    await page.click('button:has-text("Generate Report")');

    // Should show report modal
    await expect(page.locator('[data-testid="alert-report-modal"]')).toBeVisible();

    // Select date range
    await page.click('[data-testid="date-range-picker"]');
    await page.click('button:has-text("Last 7 days")');

    // Generate
    await page.click('button:has-text("Generate")');

    await expect(page.locator('[data-testid="report-generation-success"]')).toBeVisible({
      timeout: 30000,
    });
  });

  test('should schedule recurring report', async ({ page }) => {
    await page.goto('/alerts');
    await page.click('button:has-text("Reports")');
    await page.click('button:has-text("Schedule Report")');

    // Fill schedule
    await page.fill('input[name="report_name"]', 'Weekly Security Report');
    await page.selectOption('[data-testid="frequency"]', 'weekly');
    await page.selectOption('[data-testid="day-of-week"]', 'monday');

    // Add recipients
    await page.click('[data-testid="add-recipient"]');
    await page.fill('[data-testid="recipient-email"]', 'security@example.com');
    await page.click('button:has-text("Add")');

    // Save schedule
    await page.click('button:has-text("Save Schedule")');

    await expect(page.locator('text=/report scheduled/i')).toBeVisible();
  });
});

test.describe('Report Formats', () => {
  test.beforeEach(async ({ page }) => {
    const admin = TEST_USERS.admin;
    await login(page, admin.username, admin.password);
  });

  test('should generate PDF report', async ({ page }) => {
    await page.goto('/playbooks');
    await page.click('button:has-text("History")');
    await page.click('[data-testid="run-item"][data-status="completed"]:first-child');

    await page.click('button:has-text("Generate Report")');
    await page.selectOption('[data-testid="report-format"]', 'pdf');
    await page.click('button:has-text("Generate")');

    await expect(page.locator('[data-testid="report-ready"]')).toBeVisible({
      timeout: 30000,
    });

    const downloadPromise = page.waitForEvent('download');
    await page.click('button:has-text("Download")');
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/\.pdf$/);
  });

  test('should generate HTML report', async ({ page }) => {
    await page.goto('/playbooks');
    await page.click('button:has-text("History")');
    await page.click('[data-testid="run-item"][data-status="completed"]:first-child');

    await page.click('button:has-text("Generate Report")');
    await page.selectOption('[data-testid="report-format"]', 'html');
    await page.click('button:has-text("Generate")');

    await expect(page.locator('[data-testid="report-ready"]')).toBeVisible({
      timeout: 30000,
    });

    const downloadPromise = page.waitForEvent('download');
    await page.click('button:has-text("Download")');
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/\.html$/);
  });

  test('should generate JSON report', async ({ page }) => {
    await page.goto('/playbooks');
    await page.click('button:has-text("History")');
    await page.click('[data-testid="run-item"][data-status="completed"]:first-child');

    await page.click('button:has-text("Generate Report")');
    await page.selectOption('[data-testid="report-format"]', 'json');
    await page.click('button:has-text("Generate")');

    await expect(page.locator('[data-testid="report-ready"]')).toBeVisible({
      timeout: 30000,
    });

    const downloadPromise = page.waitForEvent('download');
    await page.click('button:has-text("Download")');
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/\.json$/);
  });

  test('should generate CSV export for alerts', async ({ page }) => {
    await page.goto('/alerts');

    await page.click('[data-testid="select-all-alerts"]');
    await page.click('button:has-text("Export")');
    await page.click('button:has-text("CSV")');

    const download = await page.waitForEvent('download');
    expect(download.suggestedFilename()).toMatch(/.*\.csv$/);
  });
});

test.describe('Report Templates', () => {
  test.beforeEach(async ({ page }) => {
    const admin = TEST_USERS.admin;
    await login(page, admin.username, admin.password);
  });

  test('should create custom report template', async ({ page }) => {
    await page.goto('/settings');
    await page.click('button:has-text("Report Templates")');
    await page.click('button:has-text("New Template")');

    // Fill template details
    await page.fill('input[name="template_name"]', 'Incident Response Template');
    await page.fill('textarea[name="template_description"]', 'Template for incident response reports');

    // Add sections
    await page.click('button:has-text("Add Section")');
    await page.selectOption('[data-testid="section-type"]', 'executive_summary');
    await page.click('button:has-text("Add")');

    // Save template
    await page.click('button:has-text("Save Template")');

    await expect(page.locator('text=/template created/i')).toBeVisible();
  });

  test('should use custom template for report generation', async ({ page }) => {
    await page.goto('/playbooks');
    await page.click('button:has-text("History")');
    await page.click('[data-testid="run-item"][data-status="completed"]:first-child');

    await page.click('button:has-text("Generate Report")');

    // Select custom template
    await page.selectOption('[data-testid="report-template"]', 'incident_response_template');

    await page.click('button:has-text("Generate")');

    await expect(page.locator('[data-testid="report-ready"]')).toBeVisible({
      timeout: 30000,
    });
  });
});

test.describe('Report History', () => {
  test.beforeEach(async ({ page }) => {
    const admin = TEST_USERS.admin;
    await login(page, admin.username, admin.password);
  });

  test('should display report history', async ({ page }) => {
    await page.goto('/playbooks');
    await page.click('button:has-text("Reports")');

    // Should show report history table
    await expect(page.locator('[data-testid="report-history-table"]')).toBeVisible();

    // Should have columns
    await expect(page.locator('th:has-text("Report Name")')).toBeVisible();
    await expect(page.locator('th:has-text("Created")')).toBeVisible();
    await expect(page.locator('th:has-text("Format")')).toBeVisible();
  });

  test('should filter reports by type', async ({ page }) => {
    await page.goto('/playbooks');
    await page.click('button:has-text("Reports")');

    // Filter by playbook reports
    await page.click('[data-testid="report-type-filter"]');
    await page.click('input[value="playbook"]');
    await page.click('button:has-text("Apply")');

    // Should only show playbook reports
    const reports = page.locator('[data-testid="report-item"][data-type="playbook"]');
    await expect(reports).toHaveCount.greaterThan(0);
  });

  test('should delete old reports', async ({ page }) => {
    await page.goto('/playbooks');
    await page.click('button:has-text("Reports")');

    // Select first report
    await page.check('[data-testid="report-checkbox"]:first-child');

    // Delete
    await page.click('button:has-text("Delete")');
    await page.click('button:has-text("Confirm")');

    await expect(page.locator('text=/report deleted/i')).toBeVisible();
  });
});

test.describe('Report Sharing', () => {
  test.beforeEach(async ({ page }) => {
    const admin = TEST_USERS.admin;
    await login(page, admin.username, admin.password);
  });

  test('should generate shareable report link', async ({ page }) => {
    await page.goto('/playbooks');
    await page.click('button:has-text("History")');
    await page.click('[data-testid="run-item"][data-status="completed"]:first-child');

    await page.click('button:has-text("Generate Report")');
    await page.click('button:has-text("Generate")');

    await expect(page.locator('[data-testid="report-ready"]')).toBeVisible({
      timeout: 30000,
    });

    // Generate share link
    await page.click('button:has-text("Share")');

    // Should show share link
    await expect(page.locator('[data-testid="share-link"]')).toBeVisible();

    // Should copy to clipboard
    await page.click('button:has-text("Copy Link")');
    await expect(page.locator('text=/link copied/i')).toBeVisible();
  });

  test('should set report expiration', async ({ page }) => {
    await page.goto('/playbooks');
    await page.click('button:has-text("History")');
    await page.click('[data-testid="run-item"][data-status="completed"]:first-child');

    await page.click('button:has-text("Share")');

    // Set expiration
    await page.click('[data-testid="expiration-picker"]');
    await page.click('button:has-text("7 days")');

    // Save
    await page.click('button:has-text("Save")');

    await expect(page.locator('text=/link will expire/i')).toBeVisible();
  });
});
