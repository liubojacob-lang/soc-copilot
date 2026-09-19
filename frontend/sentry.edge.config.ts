/**
 * Sentry edge configuration for edge runtime.
 *
 * This file configures Sentry for edge runtime (middleware, edge functions).
 * Environment variables required:
 * - SENTRY_DSN: Sentry DSN for your project
 * - SENTRY_ENVIRONMENT: Environment name (development, staging, production)
 */

import * as Sentry from "@sentry/nextjs";

const SENTRY_DSN = process.env.SENTRY_DSN || process.env.NEXT_PUBLIC_SENTRY_DSN;
const SENTRY_ENVIRONMENT =
  process.env.SENTRY_ENVIRONMENT || process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT || "development";
const SENTRY_RELEASE =
  process.env.SENTRY_RELEASE || process.env.NEXT_PUBLIC_SENTRY_RELEASE || "0.9.4";

// Only initialize Sentry if DSN is configured
if (SENTRY_DSN) {
  Sentry.init({
    dsn: SENTRY_DSN,
    environment: SENTRY_ENVIRONMENT,
    release: SENTRY_RELEASE,

    // Performance monitoring
    tracesSampleRate: SENTRY_ENVIRONMENT === "production" ? 0.1 : 1.0,

    // Ignore common errors
    ignoreErrors: ["ECONNREFUSED", "ECONNRESET", "ETIMEDOUT", "Unauthorized", "Invalid token"],
  });
}

// Export for use in other files
export { Sentry };
