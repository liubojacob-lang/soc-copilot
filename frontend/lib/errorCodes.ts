/**
 * Error code mappings for user-friendly error messages
 */

export interface ErrorCodeMapping {
  title: string;
  message: string;
  suggestion?: string;
  actionLabel?: string;
  action?: () => void;
}

export const ERROR_CODES: Record<number, ErrorCodeMapping> = {
  // Authentication & Authorization (4xx)
  400: {
    title: "Invalid Request",
    message: "The request was invalid or cannot be served.",
    suggestion: "Please check your input and try again. If the problem persists, contact support.",
  },
  401: {
    title: "Authentication Required",
    message: "You need to sign in to access this resource.",
    suggestion: "Please log in to continue.",
    actionLabel: "Go to Login",
  },
  403: {
    title: "Access Denied",
    message: "You do not have permission to perform this action.",
    suggestion:
      "This action requires elevated privileges. Please contact your administrator if you believe this is an error.",
  },
  404: {
    title: "Not Found",
    message: "The requested resource was not found.",
    suggestion: "The resource may have been moved or deleted. Please check the URL and try again.",
  },
  409: {
    title: "Conflict",
    message: "The request conflicts with the current state of the server.",
    suggestion:
      "Please refresh the page and try again. If you are trying to create a resource, it may already exist.",
  },
  422: {
    title: "Validation Error",
    message: "The request contains invalid data.",
    suggestion: "Please check your input fields and correct any errors.",
  },
  429: {
    title: "Too Many Requests",
    message: "You have sent too many requests in a given amount of time.",
    suggestion: "Please wait a moment and try again later.",
  },

  // Server Errors (5xx)
  500: {
    title: "Server Error",
    message: "Something went wrong on our end.",
    suggestion: "Our team has been notified. Please try again later.",
    actionLabel: "Retry",
  },
  502: {
    title: "Bad Gateway",
    message: "The server received an invalid response from an upstream server.",
    suggestion: "This is usually a temporary issue. Please wait a moment and try again.",
    actionLabel: "Retry",
  },
  503: {
    title: "Service Unavailable",
    message: "The service is temporarily unavailable.",
    suggestion: "We are performing maintenance. Please try again later.",
  },
  504: {
    title: "Gateway Timeout",
    message: "The server did not receive a timely response.",
    suggestion: "The request took too long to process. Please try again.",
    actionLabel: "Retry",
  },
};

export const NETWORK_ERROR: ErrorCodeMapping = {
  title: "Network Error",
  message: "Unable to connect to the server.",
  suggestion: "Please check your internet connection and try again.",
  actionLabel: "Retry",
};

export const TIMEOUT_ERROR: ErrorCodeMapping = {
  title: "Request Timeout",
  message: "The request took too long to complete.",
  suggestion: "The server may be experiencing high load. Please try again later.",
  actionLabel: "Retry",
};

export const UNKNOWN_ERROR: ErrorCodeMapping = {
  title: "Unexpected Error",
  message: "An unexpected error occurred.",
  suggestion: "Please try again. If the problem persists, contact support.",
  actionLabel: "Retry",
};

/**
 * Specialized error messages for specific endpoints
 */
export const ENDPOINT_ERRORS: Record<string, Record<number, ErrorCodeMapping>> = {
  "/api/ai/analyze": {
    500: {
      title: "AI Analysis Failed",
      message: "The AI analysis service encountered an error.",
      suggestion: "This could be due to high demand or a temporary issue. Please try again.",
      actionLabel: "Retry Analysis",
    },
    503: {
      title: "AI Service Unavailable",
      message: "The AI analysis service is currently unavailable.",
      suggestion: "We are working to restore service. Please try again in a few minutes.",
    },
  },
  "/api/playbooks/runs": {
    409: {
      title: "Playbook Already Running",
      message: "This playbook is already running.",
      suggestion: "Please wait for the current run to complete before starting a new one.",
      actionLabel: "View Status",
    },
  },
  "/api/threat-intel/query": {
    500: {
      title: "Threat Intelligence Query Failed",
      message: "Unable to query threat intelligence databases.",
      suggestion:
        "The threat intelligence service may be temporarily unavailable. Please try again later.",
      actionLabel: "Retry",
    },
  },
};
