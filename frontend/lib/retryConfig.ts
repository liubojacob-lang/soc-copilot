/**
 * Retry Configuration for API calls
 *
 * Provides retry strategies for different error types and endpoints
 */

export interface RetryStrategy {
  maxRetries: number;
  initialDelay: number; // milliseconds
  maxDelay: number; // milliseconds
  backoffMultiplier: number;
  retryableErrors: (number | string)[];
  shouldRetry?: (error: any, attempt: number) => boolean;
}

export interface RetryOptions {
  maxRetries?: number;
  initialDelay?: number;
  maxDelay?: number;
  backoffMultiplier?: number;
  endpoint?: string;
  onRetry?: (attempt: number, error: any, delay: number) => void;
}

/**
 * Default retry strategies for different scenarios
 */
export const RETRY_STRATEGIES: Record<string, RetryStrategy> = {
  // Network errors - most aggressive retry
  network: {
    maxRetries: 3,
    initialDelay: 1000,
    maxDelay: 10000,
    backoffMultiplier: 2,
    retryableErrors: ["NETWORK_ERROR", "TIMEOUT_ERROR"],
  },

  // Server errors (5xx) - moderate retry
  server: {
    maxRetries: 2,
    initialDelay: 2000,
    maxDelay: 8000,
    backoffMultiplier: 2,
    retryableErrors: [500, 502, 503, 504],
  },

  // Rate limiting (429) - slow exponential backoff
  rateLimit: {
    maxRetries: 3,
    initialDelay: 5000,
    maxDelay: 60000,
    backoffMultiplier: 2,
    retryableErrors: [429],
  },

  // AI/LLM calls - longer timeout, fewer retries
  ai: {
    maxRetries: 2,
    initialDelay: 2000,
    maxDelay: 10000,
    backoffMultiplier: 1.5,
    retryableErrors: [500, 502, 503, 504, "NETWORK_ERROR", "TIMEOUT_ERROR"],
  },

  // Default - conservative retry
  default: {
    maxRetries: 2,
    initialDelay: 1000,
    maxDelay: 5000,
    backoffMultiplier: 2,
    retryableErrors: [408, 429, 500, 502, 503, 504],
  },
};

/**
 * Get retry strategy for endpoint
 */
export function getRetryStrategy(endpoint?: string): RetryStrategy {
  if (!endpoint) return RETRY_STRATEGIES.default;

  // AI endpoints
  if (endpoint.includes("/ai") || endpoint.includes("/llm")) {
    return RETRY_STRATEGIES.ai;
  }

  // Threat Intel endpoints
  if (endpoint.includes("/ti") || endpoint.includes("/threat-intel")) {
    return RETRY_STRATEGIES.server;
  }

  // Playbook endpoints
  if (endpoint.includes("/playbooks") || endpoint.includes("/triggers")) {
    return RETRY_STRATEGIES.default;
  }

  return RETRY_STRATEGIES.default;
}

/**
 * Calculate delay with exponential backoff
 */
export function calculateBackoff(
  attempt: number,
  initialDelay: number,
  maxDelay: number,
  backoffMultiplier: number
): number {
  const delay = initialDelay * Math.pow(backoffMultiplier, attempt);
  return Math.min(delay, maxDelay);
}

/**
 * Check if error is retryable based on strategy
 */
export function isRetryable(error: any, strategy: RetryStrategy): boolean {
  const errorCode = error?.code || error?.status;

  if (typeof errorCode === "number") {
    return strategy.retryableErrors.includes(errorCode);
  }

  if (typeof errorCode === "string") {
    return strategy.retryableErrors.includes(errorCode);
  }

  return false;
}

/**
 * Retry state for UI tracking
 */
export interface RetryState {
  isRetrying: boolean;
  attempt: number;
  maxRetries: number;
  nextRetryIn?: number;
  lastError?: any;
}

/**
 * Format retry message for UI
 */
export function formatRetryMessage(attempt: number, maxRetries: number, delay?: number): string {
  const remaining = maxRetries - attempt;
  if (delay) {
    const seconds = Math.ceil(delay / 1000);
    return `Retrying... (${remaining} attempts left, in ${seconds}s)`;
  }
  return `Retrying... (${remaining} attempts left)`;
}
