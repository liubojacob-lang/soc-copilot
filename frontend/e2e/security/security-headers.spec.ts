import { test, expect } from "@playwright/test";

test.describe("Security Headers", () => {
  test("API responses include security headers", async ({ request }) => {
    const response = await request.get("/api/health");

    expect(response.headers()["x-content-type-options"]).toBe("nosniff");
    expect(response.headers()["x-frame-options"]).toBe("DENY");
    expect(response.headers()["x-xss-protection"]).toBe("1; mode=block");
    expect(response.headers()["referrer-policy"]).toBe("strict-origin-when-cross-origin");
  });

  test("API responses include Content-Security-Policy", async ({ request }) => {
    const response = await request.get("/api/health");

    const csp = response.headers()["content-security-policy"];
    expect(csp).toBeTruthy();
    expect(csp).toContain("default-src 'self'");
    expect(csp).toContain("frame-ancestors 'none'");
    expect(csp).toContain("object-src 'none'");
  });

  test("API responses include Permissions-Policy", async ({ request }) => {
    const response = await request.get("/api/health");

    const permissionsPolicy = response.headers()["permissions-policy"];
    expect(permissionsPolicy).toBeTruthy();
    expect(permissionsPolicy).toContain("camera=()");
    expect(permissionsPolicy).toContain("microphone=()");
    expect(permissionsPolicy).toContain("geolocation=()");
  });

  test("API responses include no-cache headers", async ({ request }) => {
    const response = await request.get("/api/health");

    const cacheControl = response.headers()["cache-control"];
    expect(cacheControl).toBeTruthy();
    expect(cacheControl).toContain("no-store");
  });

  test("HSTS header not set on HTTP (development)", async ({ request }) => {
    const response = await request.get("/api/health");

    const hsts = response.headers()["strict-transport-security"];
    expect(hsts).toBeUndefined();
  });

  test("all API endpoints return security headers", async ({ request }) => {
    const endpoints = ["/api/health", "/api/auth/login", "/api/v1/wazuh/stream/status"];

    for (const endpoint of endpoints) {
      const response = await request.get(endpoint);
      expect(response.headers()["x-content-type-options"]).toBe("nosniff");
      expect(response.headers()["x-frame-options"]).toBe("DENY");
    }
  });

  test("CORS headers are present for API requests", async ({ request }) => {
    const response = await request.get("/api/health", {
      headers: { Origin: "http://localhost:3003" },
    });

    const corsHeader = response.headers()["access-control-allow-origin"];
    expect(corsHeader).toBeTruthy();
  });
});
