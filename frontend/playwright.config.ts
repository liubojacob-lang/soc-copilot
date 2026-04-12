import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright E2E Test Configuration for SOC Copilot
 *
 * See https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  // Test directory
  testDir: "./e2e",

  // Global setup file
  globalSetup: require.resolve("./e2e/global.setup"),

  // Run tests in parallel
  fullyParallel: true,

  // Fail build on CI if you accidentally left test.only in source code
  forbidOnly: !!process.env.CI,

  // Retry on CI only
  retries: process.env.CI ? 2 : 0,

  // Opt out of parallel tests on CI
  workers: process.env.CI ? 1 : undefined,

  // Reporter configuration
  reporter: [
    ["html", { outputFolder: "playwright-report" }],
    ["json", { outputFolder: "playwright-report", outputFile: "results.json" }],
    ["list"],
  ],

  // Global test settings
  use: {
    // Base URL for tests
    baseURL: process.env.E2E_BASE_URL || "http://localhost:3003",

    // Collect trace on failure
    trace: "on-first-retry",

    // Screenshot on failure
    screenshot: "only-on-failure",

    // Video on failure
    video: "retain-on-failure",

    // Browser context
    contextOptions: {
      // Ignore HTTPS errors for local testing
      ignoreHTTPSErrors: true,
    },
  },

  // Configure projects for major browsers
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "firefox",
      use: { ...devices["Desktop Firefox"] },
    },
    {
      name: "webkit",
      use: { ...devices["Desktop Safari"] },
    },
    // Mobile viewports
    {
      name: "Mobile Chrome",
      use: { ...devices["Pixel 5"] },
    },
    {
      name: "Mobile Safari",
      use: { ...devices["iPhone 12"] },
    },
  ],

  // Run local dev server before tests (only in CI)
  webServer: process.env.CI
    ? {
        command: "npm run dev -- -H localhost -p 3003",
        url: "http://localhost:3003",
        reuseExistingServer: false,
        timeout: 120 * 1000,
      }
    : undefined,
});
