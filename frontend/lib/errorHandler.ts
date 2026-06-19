/**
 * Error Handler - Centralized error processing and user-friendly messaging
 */

import { captureException } from "@sentry/nextjs";
import {
  ERROR_CODES,
  NETWORK_ERROR,
  TIMEOUT_ERROR,
  UNKNOWN_ERROR,
  ENDPOINT_ERRORS,
  type ErrorCodeMapping,
} from "./errorCodes";

export interface AppError {
  code: number | string;
  title: string;
  message: string;
  suggestion?: string;
  actionLabel?: string;
  action?: () => void;
  details?: any;
  requestId?: string;
}

/**
 * Parse HTTP error response and convert to user-friendly error
 */
export function parseHttpError(error: Response | Error | unknown, endpoint?: string): AppError {
  // Handle Response objects (HTTP errors)
  if (error instanceof Response) {
    return handleResponseError(error, endpoint);
  }

  // Handle network/fetch errors
  if (error instanceof TypeError && error.message.includes("fetch")) {
    return {
      code: "NETWORK_ERROR",
      ...NETWORK_ERROR,
      details: error.message,
    };
  }

  // Handle timeout errors
  if (error instanceof Error && error.name === "AbortError") {
    return {
      code: "TIMEOUT_ERROR",
      ...TIMEOUT_ERROR,
      details: error.message,
    };
  }

  // Handle generic errors
  if (error instanceof Error) {
    return {
      code: "GENERIC_ERROR",
      title: "Error",
      message: error.message,
      suggestion: "Please try again or contact support if the problem persists.",
      actionLabel: "Retry",
      details: error.stack,
    };
  }

  // Unknown error type
  return {
    code: "UNKNOWN_ERROR",
    ...UNKNOWN_ERROR,
    details: error,
  };
}

function handleResponseError(response: Response, endpoint?: string): AppError {
  const status = response.status;
  const url = response.url || endpoint || "";

  // Check for endpoint-specific errors
  const endpointErrors = endpoint ? ENDPOINT_ERRORS[endpoint] : null;
  if (endpointErrors && endpointErrors[status]) {
    return {
      code: status,
      ...endpointErrors[status],
      details: { url, status },
    };
  }

  // Use generic error codes
  const errorMapping = ERROR_CODES[status];
  if (errorMapping) {
    return {
      code: status,
      ...errorMapping,
      details: { url, status },
    };
  }

  // Fallback for unknown status codes
  if (status >= 400 && status < 500) {
    return {
      code: status,
      title: "Client Error",
      message: `Request failed with status ${status}.`,
      suggestion: "Please check your request and try again.",
      details: { url, status },
    };
  }

  if (status >= 500) {
    return {
      code: status,
      title: "Server Error",
      message: "The server encountered an error.",
      suggestion: "Please try again later. If the problem persists, contact support.",
      actionLabel: "Retry",
      details: { url, status },
    };
  }

  return {
    code: status,
    ...UNKNOWN_ERROR,
    details: { url, status },
  };
}

/**
 * Extract request ID from headers or response
 */
export function getRequestId(response?: Response): string | undefined {
  if (!response) return undefined;

  // Try common headers
  return (
    response.headers.get("x-request-id") ||
    response.headers.get("x-amzn-requestid") ||
    response.headers.get("x-correlation-id") ||
    undefined
  );
}

/**
 * Report error to monitoring service (Sentry)
 */
export function reportError(error: AppError, context?: Record<string, any>): void {
  // Skip reporting for client errors (4xx) as they are expected
  if (typeof error.code === "number" && error.code >= 400 && error.code < 500) {
    return;
  }

  // Report server errors and unexpected errors to Sentry
  captureException(new Error(error.message), {
    level: "error",
    tags: {
      errorCode: String(error.code),
      endpoint: context?.endpoint,
    },
    extra: {
      errorTitle: error.title,
      errorMessage: error.message,
      suggestion: error.suggestion,
      details: error.details,
      ...context,
    },
  });
}

/**
 * Get user-friendly error display component
 */
export function getErrorDisplay(error: AppError) {
  return {
    title: error.title,
    message: error.message,
    suggestion: error.suggestion,
    actionLabel: error.actionLabel,
    action: error.action,
    requestId: error.requestId,
  };
}

/**
 * Check if error is retryable
 */
export function isRetryableError(error: AppError): boolean {
  if (typeof error.code === "number") {
    // Retry on server errors and rate limiting
    return error.code >= 500 || error.code === 429 || error.code === 408;
  }

  // Retry on network and timeout errors
  return error.code === "NETWORK_ERROR" || error.code === "TIMEOUT_ERROR";
}

/**
 * Check if error is authentication-related
 */
export function isAuthError(error: AppError): boolean {
  if (typeof error.code === "number") {
    return error.code === 401 || error.code === 403;
  }
  return false;
}

/**
 * Format error for logging
 */
export function formatErrorForLogging(error: AppError): string {
  return `[${error.code}] ${error.title}: ${error.message}${error.suggestion ? ` - ${error.suggestion}` : ""}${error.requestId ? ` (Request ID: ${error.requestId})` : ""}`;
}
