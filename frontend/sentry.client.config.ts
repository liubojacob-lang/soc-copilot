/**
 * Sentry client configuration for browser environment.
 *
 * This file configures Sentry for client-side error tracking and performance monitoring.
 * Environment variables required:
 * - NEXT_PUBLIC_SENTRY_DSN: Sentry DSN for your project
 * - NEXT_PUBLIC_SENTRY_ENVIRONMENT: Environment name (development, staging, production)
 */

import * as Sentry from "@sentry/nextjs";

const SENTRY_DSN = process.env.NEXT_PUBLIC_SENTRY_DSN;
const SENTRY_ENVIRONMENT = process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT || "development";
const SENTRY_RELEASE = process.env.NEXT_PUBLIC_SENTRY_RELEASE || "0.9.4";

// Only initialize Sentry if DSN is configured
if (SENTRY_DSN) {
  Sentry.init({
    dsn: SENTRY_DSN,
    environment: SENTRY_ENVIRONMENT,
    release: SENTRY_RELEASE,

    // Performance monitoring
    tracesSampleRate: SENTRY_ENVIRONMENT === "production" ? 0.1 : 1.0,

    // Session replay (optional, useful for debugging)
    replaysSessionSampleRate: SENTRY_ENVIRONMENT === "production" ? 0.1 : 1.0,
    replaysOnErrorSampleRate: 1.0,

    // Ignore common browser errors that are not actionable
    ignoreErrors: [
      // Browser extensions
      "Non-Error promise rejection captured",
      "Network error",
      "NetworkError",
      // Random browser issues
      "ResizeObserver loop limit exceeded",
      "ResizeObserver loop completed with undelivered notifications",
      // Auth related (handled by app)
      "Unauthorized",
      "Invalid token",
      // Cancelled requests
      "cancelled",
      "canceled",
      "AbortError",
    ],

    // Filter out sensitive data
    beforeSend(event, hint) {
      // Don't send events with sensitive data
      const request = event.request;
      if (request) {
        // Remove sensitive headers
        if (request.headers) {
          delete request.headers["authorization"];
          delete request.headers["cookie"];
          delete request.headers["x-api-key"];
        }
        // Remove sensitive URL params
        if (request.url) {
          try {
            const url = new URL(request.url);
            url.searchParams.delete("token");
            url.searchParams.delete("api_key");
            request.url = url.toString();
          } catch {
            // Invalid URL, keep as is
          }
        }
      }
      return event;
    },
  });

  console.log(
    `[Sentry] Client initialized: environment=${SENTRY_ENVIRONMENT}, release=${SENTRY_RELEASE}`
  );
} else {
  console.log("[Sentry] Client not initialized: NEXT_PUBLIC_SENTRY_DSN not set");
}

// Export for use in other files
export { Sentry };
