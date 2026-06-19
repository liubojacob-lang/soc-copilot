/**
 * Enhanced Retry Handler
 *
 * Provides intelligent retry logic with configurable strategies,
 * exponential backoff, and retry state tracking.
 */

import { isRetryableError, type AppError } from "./errorHandler";
import {
  getRetryStrategy,
  calculateBackoff,
  isRetryable as checkIsRetryable,
  formatRetryMessage,
  type RetryOptions,
  type RetryState,
} from "./retryConfig";

/**
 * Internal retry state for tracking active retries
 */
const activeRetries = new Map<string, RetryState>();

/**
 * Generate unique key for retry tracking
 */
function getRetryKey(input: RequestInfo | URL, init?: RequestInit): string {
  const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
  const method = init?.method || "GET";
  return `${method}:${url}`;
}

/**
 * Update retry state
 */
function updateRetryState(key: string, state: RetryState): void {
  activeRetries.set(key, state);

  // Dispatch event for UI updates
  if (typeof window !== "undefined") {
    window.dispatchEvent(
      new CustomEvent("api-retry", {
        detail: { key, state },
      })
    );
  }
}

/**
 * Clear retry state
 */
function clearRetryState(key: string): void {
  activeRetries.delete(key);

  if (typeof window !== "undefined") {
    window.dispatchEvent(
      new CustomEvent("api-retry-complete", {
        detail: { key },
      })
    );
  }
}

/**
 * Get current retry state
 */
export function getRetryState(key: string): RetryState | undefined {
  return activeRetries.get(key);
}

/**
 * Enhanced fetch with intelligent retry
 *
 * Features:
 * - Configurable retry strategies per endpoint
 * - Exponential backoff with jitter
 * - Retry state tracking for UI
 * - Retry callbacks for logging
 *
 * @example
 * ```typescript
 * const response = await fetchWithRetryEnhanced('/api/alerts', {
 *   maxRetries: 3,
 *   onRetry: (attempt, error, delay) => {
 *     console.log(`Retry ${attempt}: ${error.message}, waiting ${delay}ms`);
 *   }
 * });
 * ```
 */
export async function fetchWithRetryEnhanced(
  input: RequestInfo | URL,
  init?: RequestInit & RetryOptions,
  fetchFn: typeof fetch = fetch
): Promise<Response> {
  const key = getRetryKey(input, init);
  const strategy = getRetryStrategy(init?.endpoint);

  // Allow override via init options
  const maxRetries = init?.maxRetries ?? strategy.maxRetries;
  const initialDelay = init?.initialDelay ?? strategy.initialDelay;
  const maxDelay = init?.maxDelay ?? strategy.maxDelay;
  const backoffMultiplier = init?.backoffMultiplier ?? strategy.backoffMultiplier;

  let lastError: AppError | undefined;
  let attempt = 0;

  for (attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      // First attempt is immediate
      if (attempt > 0) {
        // Calculate delay with exponential backoff
        const delay = calculateBackoff(attempt - 1, initialDelay, maxDelay, backoffMultiplier);

        // Update retry state
        updateRetryState(key, {
          isRetrying: true,
          attempt,
          maxRetries,
          nextRetryIn: delay,
          lastError: lastError as AppError,
        });

        // Wait before retry
        await new Promise((resolve) => setTimeout(resolve, delay));

        // Retry attempt logged via onRetry callback
      }

      // Call onRetry callback if provided
      if (init?.onRetry && attempt > 0 && lastError) {
        const delay = calculateBackoff(attempt - 1, initialDelay, maxDelay, backoffMultiplier);
        init.onRetry(attempt, lastError, delay);
      }

      // Attempt fetch
      const response = await fetchFn(input, init);

      if (!response.ok) {
        // Parse error
        const error = await parseErrorResponse(response);

        // Check if retryable
        if (!checkIsRetryable(error, strategy) || attempt === maxRetries) {
          throw error;
        }

        lastError = error;
        continue;
      }

      // Success - clear retry state
      if (attempt > 0) {
        clearRetryState(key);
      }

      return response;
    } catch (error) {
      lastError = error as AppError;

      // Check if error is retryable
      if (!isRetryableError(lastError) || attempt === maxRetries) {
        clearRetryState(key);
        throw lastError;
      }

      // Continue to next attempt
    }
  }

  // Should not reach here, but just in case
  clearRetryState(key);
  throw lastError!;
}

/**
 * Parse error response
 */
async function parseErrorResponse(response: Response): Promise<AppError> {
  try {
    const body = await response.json().catch(() => null);

    return {
      code: response.status,
      title: body?.title || "Request Failed",
      message: body?.message || body?.detail || `HTTP ${response.status}`,
      suggestion: body?.suggestion,
      details: {
        status: response.status,
        url: response.url,
        body,
      },
    };
  } catch {
    return {
      code: response.status,
      title: "Request Failed",
      message: `HTTP ${response.status}`,
      details: { status: response.status, url: response.url },
    };
  }
}

/**
 * React hook for retry state tracking
 *
 * @example
 * ```typescript
 * function MyComponent() {
 *   const { retryState } = useRetryState('/api/alerts');
 *
 *   return (
 *     <div>
 *       {retryState?.isRetrying && (
 *         <div>{formatRetryMessage(retryState.attempt, retryState.maxRetries, retryState.nextRetryIn)}</div>
 *       )}
 *     </div>
 *   );
 * }
 * ```
 */
export function useRetryState(input: RequestInfo | URL) {
  const [retryState, setRetryState] = React.useState<RetryState | undefined>(undefined);

  React.useEffect(() => {
    const key = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;

    // Initial check
    setRetryState(getRetryState(key));

    // Listen for retry events
    const handleRetry = (event: CustomEvent) => {
      if (event.detail.key === key) {
        setRetryState(event.detail.state);
      }
    };

    const handleRetryComplete = (event: CustomEvent) => {
      if (event.detail.key === key) {
        setRetryState(undefined);
      }
    };

    window.addEventListener("api-retry", handleRetry as EventListener);
    window.addEventListener("api-retry-complete", handleRetryComplete as EventListener);

    return () => {
      window.removeEventListener("api-retry", handleRetry as EventListener);
      window.removeEventListener("api-retry-complete", handleRetryComplete as EventListener);
    };
  }, [input]);

  return { retryState };
}

// Import React
import React from "react";
