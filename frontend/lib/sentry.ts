/**
 * Sentry utility functions for error tracking and performance monitoring.
 *
 * Usage:
 * ```typescript
 * import { captureException, captureMessage, setUserInfo } from '@/lib/sentry';
 *
 * // Capture an exception
 * try {
 *   // ... code that might throw
 * } catch (error) {
 *   captureException(error, { context: 'additional info' });
 * }
 *
 * // Capture a message
 * captureMessage('Something happened', 'warning');
 *
 * // Set user info for error context
 * setUserInfo({ id: '123', username: 'john' });
 * ```
 */

import * as Sentry from "@sentry/nextjs";

/**
 * Capture an exception with optional context.
 */
export function captureException(
  error: Error | unknown,
  context?: Record<string, unknown>
): string {
  return Sentry.captureException(error, {
    extra: context,
  });
}

/**
 * Capture a message with a severity level.
 */
export function captureMessage(
  message: string,
  level: "debug" | "info" | "warning" | "error" | "fatal" = "info"
): string {
  return Sentry.captureMessage(message, level);
}

/**
 * Set user information for error context.
 * Call this after user logs in to associate errors with the user.
 */
export function setUserInfo(user: {
  id: string;
  username?: string;
  email?: string;
  role?: string;
}): void {
  Sentry.setUser({
    id: user.id,
    username: user.username,
    email: user.email,
    // Use tags for role to enable filtering in Sentry
  });

  if (user.role) {
    Sentry.setTag("user.role", user.role);
  }
}

/**
 * Clear user information (call on logout).
 */
export function clearUserInfo(): void {
  Sentry.setUser(null);
  Sentry.setTag("user.role", null);
}

/**
 * Add a breadcrumb for debugging.
 * Breadcrumbs show what happened before an error.
 */
export function addBreadcrumb(
  message: string,
  category: string,
  data?: Record<string, unknown>
): void {
  Sentry.addBreadcrumb({
    message,
    category,
    data,
    level: "info",
  });
}

/**
 * Wrap an async function with error tracking.
 * Useful for API calls and other async operations.
 */
export async function withErrorTracking<T>(fn: () => Promise<T>, context?: string): Promise<T> {
  return Sentry.withScope(async (scope) => {
    if (context) {
      scope.setTag("context", context);
    }
    try {
      return await fn();
    } catch (error) {
      Sentry.captureException(error);
      throw error;
    }
  });
}

/**
 * Create an error boundary fallback component helper.
 */
export function createErrorBoundaryError(error: Error, componentStack: string): void {
  captureException(error, { componentStack });
}

// Export Sentry for direct access if needed
export { Sentry };
