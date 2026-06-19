/**
 * Error handling utilities for user-friendly error messages.
 *
 * This module provides functions to convert technical API errors into
 * user-friendly messages that can be displayed in the UI.
 */

/**
 * Error message mappings for common HTTP status codes.
 */
const HTTP_ERROR_MESSAGES: Record<number, string> = {
  400: "Invalid request. Please check your input and try again.",
  401: "Your session has expired. Please log in again.",
  403: "You do not have permission to perform this action.",
  404: "The requested resource was not found.",
  409: "This resource already exists or there is a conflict.",
  422: "The data you provided is invalid. Please check and try again.",
  429: "Too many requests. Please wait a moment and try again.",
  500: "A server error occurred. Please try again later.",
  502: "The server is temporarily unavailable. Please try again.",
  503: "The service is currently unavailable. Please try again later.",
  504: "The request timed out. Please try again.",
};

/**
 * Error message mappings for common error patterns.
 */
const ERROR_PATTERNS: Array<{ pattern: RegExp; message: string }> = [
  {
    pattern: /network|ECONNREFUSED|ENOTFOUND|fetch failed/i,
    message: "Network error. Please check your internet connection.",
  },
  { pattern: /timeout|ETIMEDOUT/i, message: "The request timed out. Please try again." },
  {
    pattern: /unauthorized|invalid token|token expired/i,
    message: "Your session has expired. Please log in again.",
  },
  {
    pattern: /forbidden|not authorized|permission denied/i,
    message: "You do not have permission to perform this action.",
  },
  { pattern: /not found|does not exist/i, message: "The requested resource was not found." },
  { pattern: /already exists|duplicate|unique constraint/i, message: "This item already exists." },
  {
    pattern: /invalid.*input|validation failed|invalid format/i,
    message: "The data you provided is invalid. Please check and try again.",
  },
  {
    pattern: /rate limit|too many requests/i,
    message: "Too many requests. Please wait a moment and try again.",
  },
  {
    pattern: /server error|internal error/i,
    message: "A server error occurred. Please try again later.",
  },
  {
    pattern: /connection refused|service unavailable/i,
    message: "The service is temporarily unavailable. Please try again later.",
  },
];

/**
 * Convert an error to a user-friendly message.
 *
 * @param error - The error to convert
 * @param fallbackMessage - Optional fallback message if no specific message is found
 * @returns A user-friendly error message
 */
export function getErrorMessage(
  error: unknown,
  fallbackMessage: string = "An unexpected error occurred. Please try again."
): string {
  // Handle null/undefined
  if (!error) {
    return fallbackMessage;
  }

  // Handle string errors
  if (typeof error === "string") {
    return matchErrorPattern(error) || error;
  }

  // Handle Error objects
  if (error instanceof Error) {
    // Check for API error with status code
    const apiError = error as ApiError;
    if (apiError.status) {
      const httpMessage = HTTP_ERROR_MESSAGES[apiError.status];
      if (httpMessage) {
        return httpMessage;
      }
    }

    // Check error message patterns
    const patternMessage = matchErrorPattern(error.message);
    if (patternMessage) {
      return patternMessage;
    }

    // Return the error message if it's user-friendly enough
    if (error.message && !isTechnicalError(error.message)) {
      return error.message;
    }
  }

  // Handle API error responses
  if (typeof error === "object" && error !== null) {
    const errorObj = error as Record<string, unknown>;

    // Check for detail field (common in API responses)
    if (typeof errorObj.detail === "string") {
      const patternMessage = matchErrorPattern(errorObj.detail);
      return patternMessage || errorObj.detail;
    }

    // Check for message field
    if (typeof errorObj.message === "string") {
      const patternMessage = matchErrorPattern(errorObj.message);
      return patternMessage || errorObj.message;
    }

    // Check for error field
    if (typeof errorObj.error === "string") {
      const patternMessage = matchErrorPattern(errorObj.error);
      return patternMessage || errorObj.error;
    }
  }

  return fallbackMessage;
}

/**
 * Match an error message against known patterns.
 */
function matchErrorPattern(message: string): string | null {
  for (const { pattern, message: patternMessage } of ERROR_PATTERNS) {
    if (pattern.test(message)) {
      return patternMessage;
    }
  }
  return null;
}

/**
 * Check if an error message is too technical to show users.
 */
function isTechnicalError(message: string): boolean {
  const technicalPatterns = [
    /Error:/,
    /at \w+\.\w+/,
    /at \w+ \(/,
    /\.\.\.\d+ more/,
    /stack trace/i,
    /exception/i,
    /TypeError:/,
    /ReferenceError:/,
    /SyntaxError:/,
  ];

  return technicalPatterns.some((pattern) => pattern.test(message));
}

/**
 * API Error class with status code.
 */
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/**
 * Check if an error is an authentication error.
 */
export function isAuthError(error: unknown): boolean {
  if (error instanceof ApiError) {
    return error.status === 401;
  }

  if (error instanceof Error) {
    return /unauthorized|invalid token|token expired|session expired/i.test(error.message);
  }

  return false;
}

/**
 * Check if an error is a network error.
 */
export function isNetworkError(error: unknown): boolean {
  if (error instanceof Error) {
    return /network|ECONNREFUSED|ENOTFOUND|fetch failed|connection refused/i.test(error.message);
  }
  return false;
}

/**
 * Check if an error is a timeout error.
 */
export function isTimeoutError(error: unknown): boolean {
  if (error instanceof Error) {
    return /timeout|ETIMEDOUT|aborterror/i.test(error.message);
  }
  return false;
}

/**
 * Log an error with context for debugging.
 * This will also send the error to Sentry if configured.
 */
export function logError(error: unknown, context?: string): void {
  const message = getErrorMessage(error);
  const timestamp = new Date().toISOString();

  // Console log for development
  console.error(`[${timestamp}]${context ? ` [${context}]` : ""} ${message}`, error);

  // Send to Sentry if available
  if (typeof window !== "undefined") {
    import("@/lib/sentry")
      .then(({ captureException }) => {
        captureException(error, { context });
      })
      .catch(() => {
        // Ignore Sentry errors
      });
  }
}

/**
 * Create a standardized error handler for API calls.
 */
export function createErrorHandler(context: string) {
  return (error: unknown): string => {
    logError(error, context);
    return getErrorMessage(error);
  };
}
