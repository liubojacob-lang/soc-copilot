/**
 * E2E Test Authentication Utilities
 *
 * Provides helper functions for authentication in E2E tests.
 */

import { Page } from '@playwright/test';

export interface TestUser {
  username: string;
  password: string;
  role?: 'admin' | 'analyst' | 'auditor';
}

/**
 * Default test users from environment or defaults
 */
export const TEST_USERS: Record<string, TestUser> = {
  admin: {
    username: process.env.E2E_ADMIN_USERNAME || 'admin',
    password: process.env.E2E_ADMIN_PASSWORD || 'admin123',
    role: 'admin',
  },
  analyst: {
    username: process.env.E2E_ANALYST_USERNAME || 'analyst',
    password: process.env.E2E_ANALYST_PASSWORD || 'analyst123',
    role: 'analyst',
  },
  auditor: {
    username: process.env.E2E_AUDITOR_USERNAME || 'auditor',
    password: process.env.E2E_AUDITOR_PASSWORD || 'auditor123',
    role: 'auditor',
  },
};

/**
 * Get locale for E2E tests
 */
function getLocale(): string {
  return process.env.E2E_LOCALE || 'en';
}

/**
 * Perform login via the UI
 */
export async function login(
  page: Page,
  username: string,
  password: string
): Promise<void> {
  const locale = getLocale();

  // Navigate to login page with locale
  await page.goto(`/${locale}/login`);

  // Wait for page to load
  await page.waitForLoadState('networkidle');

  // Fill in credentials using id selector
  await page.fill('#username', username);
  await page.fill('#password', password);

  // Submit form
  await page.click('button[type="submit"]');

  // Wait for navigation - should redirect to home or dashboard
  // The app redirects to /{locale} after login
  await page.waitForURL(`**/${locale}/**`, { timeout: 10000 });

  // Wait a bit for any additional loading
  await page.waitForTimeout(1000);
}

/**
 * Perform logout via the UI
 */
export async function logout(page: Page): Promise<void> {
  const locale = getLocale();

  // Navigate to a page that has logout functionality
  // Since we don't have a logout button in the current UI, call API directly
  await page.evaluate(() => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
  });

  // Also clear cookies
  const context = page.context();
  await context.clearCookies();

  // Navigate to login page
  await page.goto(`/${locale}/login`);
  await page.waitForLoadState('networkidle');
}

/**
 * Check if user is logged in
 */
export async function isLoggedIn(page: Page): Promise<boolean> {
  try {
    // Check if we have auth tokens
    const hasToken = await page.evaluate(() => {
      return !!(
        localStorage.getItem('access_token') ||
        localStorage.getItem('refresh_token') ||
        document.cookie.includes('access_token')
      );
    });
    return hasToken;
  } catch {
    return false;
  }
}

/**
 * Get authentication token via API (for API testing)
 */
export async function getAuthToken(
  username: string,
  password: string,
  baseUrl: string
): Promise<string> {
  const response = await fetch(`${baseUrl}/api/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ username, password }),
  });

  if (!response.ok) {
    throw new Error(`Login failed: ${response.status} ${response.statusText}`);
  }

  const data = await response.json();
  return data.access_token;
}
