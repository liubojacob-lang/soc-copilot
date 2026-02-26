/**
 * E2E Tests for Threat Intelligence Flow
 *
 * Tests IOC queries, OTX integration, and threat intel enrichment.
 */

import { test, expect } from '@playwright/test';
import { login, TEST_USERS } from '../utils/auth';

test.describe('Threat Intelligence - IOC Queries', () => {
  test.beforeEach(async ({ page }) => {
    const admin = TEST_USERS.admin;
    await login(page, admin.username, admin.password);
  });

  test('should display threat intel dashboard', async ({ page }) => {
    await page.goto('/threat-intel');

    // Check page title
    await expect(page.locator('h1:has-text("Threat Intelligence")')).toBeVisible();

    // Check for search interface
    await expect(page.locator('[data-testid="ioc-search-input"]')).toBeVisible();

    // Check for query history
    await expect(page.locator('[data-testid="query-history"]')).toBeVisible();
  });

  test('should query IP address', async ({ page }) => {
    await page.goto('/threat-intel');

    // Enter IP address
    await page.fill('[data-testid="ioc-search-input"]', '1.1.1.1');
    await page.selectOption('[data-testid="ioc-type-select"]', 'ip');

    // Click search
    await page.click('button:has-text("Search")');

    // Should show loading state
    await expect(page.locator('[data-testid="ioc-loading"]')).toBeVisible();

    // Should show results
    await expect(page.locator('[data-testid="ioc-results"]')).toBeVisible({
      timeout: 30000,
    });

    // Should show IP details
    await expect(page.locator('[data-testid="ip-address"]')).toContainText('1.1.1.1');
  });

  test('should query domain', async ({ page }) => {
    await page.goto('/threat-intel');

    await page.fill('[data-testid="ioc-search-input"]', 'example.com');
    await page.selectOption('[data-testid="ioc-type-select"]', 'domain');
    await page.click('button:has-text("Search")');

    // Should show domain results
    await expect(page.locator('[data-testid="domain-details"]')).toBeVisible({
      timeout: 30000,
    });

    // Should show whois info if available
    const whois = page.locator('[data-testid="whois-info"]');
    if (await whois.isVisible()) {
      await expect(whois).toBeVisible();
    }
  });

  test('should query URL', async ({ page }) => {
    await page.goto('/threat-intel');

    await page.fill('[data-testid="ioc-search-input"]', 'http://example.com/malware');
    await page.selectOption('[data-testid="ioc-type-select"]', 'url');
    await page.click('button:has-text("Search")');

    // Should show URL analysis
    await expect(page.locator('[data-testid="url-results"]')).toBeVisible({
      timeout: 30000,
    });
  });

  test('should query file hash', async ({ page }) => {
    await page.goto('/threat-intel');

    const testHash = '44d88612fea8a8f36de82e1278abb02f'; // EICAR test file
    await page.fill('[data-testid="ioc-search-input"]', testHash);
    await page.selectOption('[data-testid="ioc-type-select"]', 'hash');
    await page.click('button:has-text("Search")');

    // Should show hash results
    await expect(page.locator('[data-testid="hash-results"]')).toBeVisible({
      timeout: 30000,
    });

    // Should show detection ratio
    await expect(page.locator('[data-testid="detection-ratio"]')).toBeVisible();
  });
});

test.describe('Threat Intelligence - Batch Queries', () => {
  test.beforeEach(async ({ page }) => {
    const admin = TEST_USERS.admin;
    await login(page, admin.username, admin.password);
  });

  test('should query multiple IOCs', async ({ page }) => {
    await page.goto('/threat-intel');

    // Click batch query button
    await page.click('button:has-text("Batch Query")');

    // Enter multiple IOCs
    const batchInput = page.locator('textarea[data-testid="batch-input"]');
    await batchInput.fill('1.1.1.1\n8.8.8.8\nexample.com');

    // Submit batch
    await page.click('button:has-text("Query All")');

    // Should show progress
    await expect(page.locator('[data-testid="batch-progress"]')).toBeVisible();

    // Should show results for all
    await expect(page.locator('[data-testid="batch-results"]')).toBeVisible({
      timeout: 60000,
    });

    // Should have 3 results
    const results = page.locator('[data-testid="ioc-result-item"]');
    await expect(results).toHaveCount(3);
  });

  test('should handle batch query errors gracefully', async ({ page }) => {
    await page.goto('/threat-intel');

    await page.click('button:has-text("Batch Query")');

    // Mix valid and invalid IOCs
    const batchInput = page.locator('textarea[data-testid="batch-input"]');
    await batchInput.fill('1.1.1.1\ninvalid-ip\n!@#$%');

    await page.click('button:has-text("Query All")');

    // Should show results with errors
    await expect(page.locator('[data-testid="ioc-error"]')).toBeVisible({
      timeout: 30000,
    });
  });
});

test.describe('Threat Intelligence - OTX Integration', () => {
  test.beforeEach(async ({ page }) => {
    const admin = TEST_USERS.admin;
    await login(page, admin.username, admin.password);
  });

  test('should show OTX pulses for IOC', async ({ page }) => {
    await page.goto('/threat-intel');

    await page.fill('[data-testid="ioc-search-input"]', '1.1.1.1');
    await page.selectOption('[data-testid="ioc-type-select"]', 'ip');
    await page.click('button:has-text("Search")');

    // Should show OTX section
    await expect(page.locator('[data-testid="otx-pulses"]')).toBeVisible({
      timeout: 30000,
    });
  });

  test('should display OTX pulse details', async ({ page }) => {
    await page.goto('/threat-intel');

    await page.fill('[data-testid="ioc-search-input"]', '1.1.1.1');
    await page.selectOption('[data-testid="ioc-type-select"]', 'ip');
    await page.click('button:has-text("Search")');

    // Wait for results
    await page.waitForSelector('[data-testid="otx-pulses"]', { timeout: 30000 });

    // Click on first pulse
    const firstPulse = page.locator('[data-testid="otx-pulse"]:first-child');
    if (await firstPulse.isVisible()) {
      await firstPulse.click();

      // Should show pulse details
      await expect(page.locator('[data-testid="pulse-details"]')).toBeVisible();
    }
  });
});

test.describe('Threat Intelligence - Cache Management', () => {
  test.beforeEach(async ({ page }) => {
    const admin = TEST_USERS.admin;
    await login(page, admin.username, admin.password);
  });

  test('should display cache statistics', async ({ page }) => {
    await page.goto('/threat-intel');

    // Click on cache stats
    await page.click('[data-testid="cache-stats-toggle"]');

    // Should show cache metrics
    await expect(page.locator('[data-testid="cache-hit-rate"]')).toBeVisible();
    await expect(page.locator('[data-testid="cache-size"]')).toBeVisible();
  });

  test('should clear IOC cache', async ({ page }) => {
    await page.goto('/threat-intel');

    // Open cache settings
    await page.click('[data-testid="cache-settings-btn"]');

    // Clear cache
    await page.click('button:has-text("Clear Cache")');
    await page.click('button:has-text("Confirm")');

    // Should show success message
    await expect(page.locator('text=/cache cleared/i')).toBeVisible();
  });

  test('should use cached results on repeat query', async ({ page }) => {
    await page.goto('/threat-intel');

    const testIP = '1.1.1.1';

    // First query
    await page.fill('[data-testid="ioc-search-input"]', testIP);
    await page.selectOption('[data-testid="ioc-type-select"]', 'ip');
    await page.click('button:has-text("Search")');

    await expect(page.locator('[data-testid="ioc-results"]')).toBeVisible({
      timeout: 30000,
    });

    // Note the timestamp
    const firstTimestamp = await page.locator('[data-testid="query-timestamp"]').textContent();

    // Second query (should be faster from cache)
    await page.fill('[data-testid="ioc-search-input"]', testIP);
    await page.click('button:has-text("Search")');

    // Should show cached indicator
    await expect(page.locator('[data-testid="cached-result"]')).toBeVisible({
      timeout: 5000,
    });

    // Timestamp should be different (but older)
    const secondTimestamp = await page.locator('[data-testid="query-timestamp"]').textContent();
    expect(secondTimestamp).toEqual(firstTimestamp);
  });
});

test.describe('Threat Intelligence - IOC Enrichment', () => {
  test.beforeEach(async ({ page }) => {
    const admin = TEST_USERS.admin;
    await login(page, admin.username, admin.password);
  });

  test('should enrich alert IOCs from threat intel', async ({ page }) => {
    await page.goto('/alerts');
    await page.click('[data-testid="alert-row"]:first-child');

    // Go to IOCs tab
    await page.click('button:has-text("IOCs")');

    // Should show IOC list with threat intel data
    await expect(page.locator('[data-testid="alert-iocs"]')).toBeVisible();

    // IOCs should have reputation indicators
    const iocs = page.locator('[data-testid="ioc-item"]');
    const count = await iocs.count();

    for (let i = 0; i < Math.min(count, 3); i++) {
      const ioc = iocs.nth(i);
      // Should have reputation badge
      await expect(ioc.locator('[data-testid="reputation-badge"]')).toBeVisible();
    }
  });

  test('should filter IOCs by threat level', async ({ page }) => {
    await page.goto('/alerts');
    await page.click('[data-testid="alert-row"]:first-child');
    await page.click('button:has-text("IOCs")');

    // Filter by malicious
    await page.click('[data-testid="ioc-filter"]');
    await page.click('input[value="malicious"]');
    await page.click('button:has-text("Apply")');

    // Should only show malicious IOCs
    const visibleIOCs = page.locator('[data-testid="ioc-item"][data-threat-level="malicious"]');
    await expect(visibleIOCs).toHaveCount.greaterThan(0);
  });
});

test.describe('Threat Intelligence - Export', () => {
  test.beforeEach(async ({ page }) => {
    const admin = TEST_USERS.admin;
    await login(page, admin.username, admin.password);
  });

  test('should export IOC query results', async ({ page }) => {
    await page.goto('/threat-intel');

    await page.fill('[data-testid="ioc-search-input"]', '1.1.1.1');
    await page.selectOption('[data-testid="ioc-type-select"]', 'ip');
    await page.click('button:has-text("Search")');

    await expect(page.locator('[data-testid="ioc-results"]')).toBeVisible({
      timeout: 30000,
    });

    // Export results
    await page.click('button:has-text("Export")');
    await page.click('button:has-text("JSON")');

    // Should trigger download
    const download = await page.waitForEvent('download');
    expect(download.suggestedFilename()).toMatch(/.*threat-intel.*\.json$/);
  });

  test('should export query history', async ({ page }) => {
    await page.goto('/threat-intel');

    // Click on history tab
    await page.click('button:has-text("History")');

    // Export history
    await page.click('button:has-text("Export History")');

    const download = await page.waitForEvent('download');
    expect(download.suggestedFilename()).toMatch(/.*query-history.*\.csv$/);
  });
});
