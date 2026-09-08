/**
 * E2E Test Authentication Utilities
 *
 * Session strategy: the backend rate-limits logins (5/min per IP), so the
 * UI login is performed at most once per username per worker process and
 * the resulting session cookies are replayed into every later test context.
 * Login submission retries on 429 instead of failing the suite.
 */

import { Cookie, Page } from "@playwright/test";

export interface TestUser {
  username: string;
  password: string;
  role?: "admin" | "analyst" | "auditor";
}

/**
 * Default test users from environment or defaults
 */
export const TEST_USERS: Record<string, TestUser> = {
  admin: {
    username: process.env.E2E_ADMIN_USERNAME || "admin",
    password: process.env.E2E_ADMIN_PASSWORD || "admin123",
    role: "admin",
  },
  analyst: {
    username: process.env.E2E_ANALYST_USERNAME || "analyst",
    password: process.env.E2E_ANALYST_PASSWORD || "analyst123",
    role: "analyst",
  },
  auditor: {
    username: process.env.E2E_AUDITOR_USERNAME || "auditor",
    password: process.env.E2E_AUDITOR_PASSWORD || "auditor123",
    role: "auditor",
  },
};

/** Per-username session cookies captured from the first successful UI login. */
const sessionCache = new Map<string, Cookie[]>();

/**
 * Get locale for E2E tests
 */
function getLocale(): string {
  return process.env.E2E_LOCALE || "en";
}

async function submitLoginForm(page: Page, username: string, password: string): Promise<void> {
  const locale = getLocale();
  await page.goto(`/${locale}/login`);
  await page.waitForSelector("#username", { timeout: 15000 });

  // 429 (login rate limit) surfaces as a failed submit; retry with a wait
  for (let attempt = 1; attempt <= 3; attempt++) {
    await page.fill("#username", username);
    await page.fill("#password", password);
    await page.click('button[type="submit"]');

    try {
      await page.waitForURL((url) => !url.pathname.includes("/login"), {
        timeout: 15000,
      });
      return;
    } catch {
      if (attempt === 3) throw new Error("Login did not complete after 3 attempts");
      // Stay on /login — likely rate limited; back off before retrying
      await page.waitForTimeout(20000);
      await page.goto(`/${locale}/login`);
    }
  }
}

/**
 * Perform login via the UI (once per username), then replay session cookies.
 */
export async function login(page: Page, username: string, password: string): Promise<void> {
  const locale = getLocale();
  const cached = sessionCache.get(username);

  if (cached) {
    await page.context().addCookies(cached);
    // The replayed cookie may have expired server-side; detect and re-login.
    const probe = await page.request.get(`/api/v1/auth/me`);
    if (probe.status() === 200) {
      return;
    }
    sessionCache.delete(username);
  }

  await submitLoginForm(page, username, password);
  sessionCache.set(username, await page.context().cookies());
  await page.waitForTimeout(500);
}

/**
 * Perform logout via the UI
 */
export async function logout(page: Page): Promise<void> {
  const locale = getLocale();

  await page.evaluate(() => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user");
  });
  await page.context().clearCookies();

  await page.goto(`/${locale}/login`);
  await page.waitForSelector("#username", { timeout: 15000 });
}

/**
 * Check if user is logged in
 */
export async function isLoggedIn(page: Page): Promise<boolean> {
  try {
    const hasToken = await page.evaluate(() => {
      return !!document.cookie.includes("access_token");
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
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ username, password }),
  });

  if (!response.ok) {
    throw new Error(`Login failed: ${response.status} ${response.statusText}`);
  }

  const data = await response.json();
  return data.access_token;
}
