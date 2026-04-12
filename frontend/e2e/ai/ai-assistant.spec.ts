/**
 * E2E Tests for AI Assistant Flow
 *
 * Tests AI-powered chat, alert analysis, and playbook recommendations.
 */

import { test, expect } from "@playwright/test";
import { login, TEST_USERS } from "../utils/auth";

test.describe("AI Assistant - Basic Chat", () => {
  test.beforeEach(async ({ page }) => {
    const admin = TEST_USERS.admin;
    await login(page, admin.username, admin.password);
  });

  test("should display AI assistant panel", async ({ page }) => {
    await page.goto("/dashboard");

    // Open AI assistant
    await page.click('[data-testid="ai-assistant-toggle"]');

    // Should show chat interface
    await expect(page.locator('[data-testid="ai-chat-panel"]')).toBeVisible();
    await expect(page.locator('[data-testid="chat-input"]')).toBeVisible();
    await expect(page.locator('[data-testid="send-message-btn"]')).toBeVisible();
  });

  test("should send message and receive response", async ({ page }) => {
    await page.goto("/dashboard");
    await page.click('[data-testid="ai-assistant-toggle"]');

    // Type a message
    const testMessage = "What are the recent security alerts?";
    await page.fill('[data-testid="chat-input"]', testMessage);
    await page.click('[data-testid="send-message-btn"]');

    // Should show user message
    await expect(page.locator(`text="${testMessage}"`)).toBeVisible();

    // Should show typing indicator
    await expect(page.locator('[data-testid="ai-typing-indicator"]')).toBeVisible();

    // Should receive AI response (with timeout)
    await expect(page.locator('[data-testid="ai-message"]')).toBeVisible({
      timeout: 60000,
    });
  });

  test("should display conversation history", async ({ page }) => {
    await page.goto("/dashboard");
    await page.click('[data-testid="ai-assistant-toggle"]');

    // Send multiple messages
    await page.fill('[data-testid="chat-input"]', "Hello");
    await page.click('[data-testid="send-message-btn"]');

    // Wait for response to appear
    await expect(page.locator('[data-testid="ai-message"]').first()).toBeVisible({
      timeout: 10000,
    });

    await page.fill('[data-testid="chat-input"]', "Show me alerts");
    await page.click('[data-testid="send-message-btn"]');

    // Wait for second response
    await expect(page.locator('[data-testid="ai-message"]').nth(1)).toBeVisible({ timeout: 10000 });

    // Should show conversation history
    const messages = page.locator('[data-testid="ai-message"], [data-testid="user-message"]');
    const messageCount = await messages.count();
    await expect(messageCount).toBeGreaterThan(2);
  });

  test("should clear conversation", async ({ page }) => {
    await page.goto("/dashboard");
    await page.click('[data-testid="ai-assistant-toggle"]');

    // Send a message
    await page.fill('[data-testid="chat-input"]', "Test message");
    await page.click('[data-testid="send-message-btn"]');

    // Wait for response
    await expect(page.locator('[data-testid="ai-message"]').first()).toBeVisible({
      timeout: 10000,
    });

    // Clear conversation
    await page.click('[data-testid="clear-chat-btn"]');

    // Confirm clear
    await page.click('button:has-text("Confirm")');

    // Should not show previous messages
    await expect(page.locator('[data-testid="ai-message"]')).toHaveCount(0);
  });
});

test.describe("AI Assistant - Alert Analysis", () => {
  test.beforeEach(async ({ page }) => {
    const admin = TEST_USERS.admin;
    await login(page, admin.username, admin.password);
  });

  test("should analyze alert from context", async ({ page }) => {
    await page.goto("/alerts");
    await page.click('[data-testid="alert-row"]:first-child');

    // Open AI assistant
    await page.click('[data-testid="ai-assistant-toggle"]');

    // Should show alert context in AI
    await expect(page.locator('[data-testid="alert-context"]')).toBeVisible();

    // Ask AI to analyze
    await page.fill('[data-testid="chat-input"]', "Analyze this alert");
    await page.click('[data-testid="send-message-btn"]');

    // Should provide analysis
    await expect(page.locator('[data-testid="ai-analysis"]')).toBeVisible({
      timeout: 60000,
    });
  });

  test("should extract IOCs from alert", async ({ page }) => {
    await page.goto("/alerts");
    await page.click('[data-testid="alert-row"]:first-child');
    await page.click('[data-testid="ai-assistant-toggle"]');

    await page.fill('[data-testid="chat-input"]', "Extract all IOCs from this alert");
    await page.click('[data-testid="send-message-btn"]');

    // Should show IOC list in response
    await expect(page.locator('[data-testid="ioc-extraction"]')).toBeVisible({
      timeout: 60000,
    });

    // IOCs should be clickable
    const iocs = page.locator('[data-testid="ioc-item"]');
    const count = await iocs.count();
    if (count > 0) {
      await expect(iocs.first()).toBeVisible();
    }
  });

  test("should suggest playbooks for alert", async ({ page }) => {
    await page.goto("/alerts");
    await page.click('[data-testid="alert-row"]:first-child');
    await page.click('[data-testid="ai-assistant-toggle"]');

    await page.fill('[data-testid="chat-input"]', "What playbooks should I run?");
    await page.click('[data-testid="send-message-btn"]');

    // Should show playbook recommendations
    await expect(page.locator('[data-testid="playbook-recommendations"]')).toBeVisible({
      timeout: 60000,
    });
  });
});

test.describe("AI Assistant - Quick Actions", () => {
  test.beforeEach(async ({ page }) => {
    const admin = TEST_USERS.admin;
    await login(page, admin.username, admin.password);
  });

  test("should use quick action prompts", async ({ page }) => {
    await page.goto("/dashboard");
    await page.click('[data-testid="ai-assistant-toggle"]');

    // Should show quick actions
    await expect(page.locator('[data-testid="quick-actions"]')).toBeVisible();

    // Click a quick action
    await page.click('[data-testid="quick-action-summary"]:first-child');

    // Should auto-fill and send prompt
    await expect(page.locator('[data-testid="ai-message"]')).toBeVisible({
      timeout: 60000,
    });
  });

  test("should search alerts via AI", async ({ page }) => {
    await page.goto("/dashboard");
    await page.click('[data-testid="ai-assistant-toggle"]');

    await page.fill('[data-testid="chat-input"]', "Show me phishing alerts from last 24 hours");
    await page.click('[data-testid="send-message-btn"]');

    // Should show search results
    await expect(page.locator('[data-testid="alert-search-results"]')).toBeVisible({
      timeout: 60000,
    });
  });
});

test.describe("AI Assistant - Error Handling", () => {
  test.beforeEach(async ({ page }) => {
    const admin = TEST_USERS.admin;
    await login(page, admin.username, admin.password);
  });

  test("should handle service unavailability gracefully", async ({ page }) => {
    // Mock AI service failure
    await page.route("**/api/ai/chat", (route) => {
      route.fulfill({
        status: 503,
        body: JSON.stringify({ detail: "AI service unavailable" }),
      });
    });

    await page.goto("/dashboard");
    await page.click('[data-testid="ai-assistant-toggle"]');

    await page.fill('[data-testid="chat-input"]', "Test message");
    await page.click('[data-testid="send-message-btn"]');

    // Should show error message
    await expect(page.locator("text=/unavailable|try again/i")).toBeVisible({
      timeout: 10000,
    });
  });

  test("should handle timeout gracefully", async ({ page }) => {
    // Mock timeout
    await page.route("**/api/ai/chat", (route) => {
      // Delay response
      setTimeout(() => {
        route.fulfill({
          status: 200,
          body: JSON.stringify({ response: "Delayed response" }),
        });
      }, 70000);
    });

    await page.goto("/dashboard");
    await page.click('[data-testid="ai-assistant-toggle"]');

    await page.fill('[data-testid="chat-input"]', "Test message");
    await page.click('[data-testid="send-message-btn"]');

    // Should show timeout message
    await expect(page.locator("text=/timeout|took too long/i")).toBeVisible({
      timeout: 70000,
    });
  });

  test("should show retry option on error", async ({ page }) => {
    await page.route("**/api/ai/chat", (route) => {
      route.fulfill({
        status: 500,
        body: JSON.stringify({ detail: "Internal server error" }),
      });
    });

    await page.goto("/dashboard");
    await page.click('[data-testid="ai-assistant-toggle"]');

    await page.fill('[data-testid="chat-input"]', "Test message");
    await page.click('[data-testid="send-message-btn"]');

    // Should show retry button
    await expect(page.locator('[data-testid="retry-btn"]')).toBeVisible({
      timeout: 10000,
    });
  });
});

test.describe("AI Assistant - Streaming Response", () => {
  test.beforeEach(async ({ page }) => {
    const admin = TEST_USERS.admin;
    await login(page, admin.username, admin.password);
  });

  test("should stream AI response in real-time", async ({ page }) => {
    await page.goto("/dashboard");
    await page.click('[data-testid="ai-assistant-toggle"]');

    await page.fill('[data-testid="chat-input"]', "Tell me about recent alerts");
    await page.click('[data-testid="send-message-btn"]');

    // Should show streaming indicator
    await expect(page.locator('[data-testid="streaming-indicator"]')).toBeVisible();

    // Wait for response to appear
    await expect(page.locator('[data-testid="ai-message"]').first()).toBeVisible({
      timeout: 10000,
    });
    const initialContent = await page.locator('[data-testid="ai-message"]').first().textContent();
    expect(initialContent?.length).toBeGreaterThan(0);

    // Wait for response to complete (streaming indicator disappears)
    await expect(page.locator('[data-testid="streaming-indicator"]')).not.toBeVisible({
      timeout: 15000,
    });
    const finalContent = await page.locator('[data-testid="ai-message"]').first().textContent();
    expect(finalContent?.length).toBeGreaterThanOrEqual(initialContent?.length || 0);
  });
});
