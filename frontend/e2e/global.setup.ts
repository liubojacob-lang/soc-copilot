/**
 * E2E Test Global Setup
 *
 * Runs once before all tests to set up the test environment.
 */

import { chromium, FullConfig } from "@playwright/test";

async function globalSetup(config: FullConfig) {
  console.log("🚀 Starting E2E test setup...");

  const baseURL = config.projects?.[0]?.use?.baseURL || "http://localhost:3003";
  console.log(`📡 Base URL: ${baseURL}`);

  // Verify backend is running
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    console.log("🔍 Checking backend health...");
    const response = await page.goto(`${baseURL.replace(":3003", ":8000")}/api/health`);

    if (response && response.ok()) {
      console.log("✅ Backend is healthy");
    } else {
      console.warn("⚠️ Backend health check failed, but continuing...");
    }
  } catch (error) {
    console.warn("⚠️ Could not connect to backend:", error);
  } finally {
    await browser.close();
  }

  console.log("✅ E2E test setup complete");
}

export default globalSetup;
