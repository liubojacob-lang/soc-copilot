/**
 * Global API client with authentication handling.
 *
 * Features:
 * - Automatic token injection
 * - CSRF protection for state-changing requests
 * - 401 response handling (redirect to login)
 * - Error normalization
 * - Request retry support with exponential backoff
 */

import { ApiError } from "./types";

// Browser requests use same-origin relative paths ("/api/...") and are proxied
// to the backend by next.config.js rewrites() — this avoids embedding a
// container-internal host (e.g. http://backend:8000) into the client bundle,
// which browsers cannot resolve. Server-side rendering needs the internal URL,
// resolved at request time (not build-inlined into the public bundle).
const INTERNAL_API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_BASE = typeof window !== "undefined" ? "" : INTERNAL_API_URL;

// Retry configuration
const RETRY_CONFIG = {
  maxRetries: 3,
  baseDelay: 1000, // 1 second
  maxDelay: 10000, // 10 seconds
  retryableStatuses: [408, 429, 500, 502, 503, 504],
  retryableErrors: ["ECONNRESET", "ENOTFOUND", "ETIMEDOUT", "NETWORK_ERROR"],
};

// Sleep utility for retry delays
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// Calculate delay with exponential backoff + jitter
function calculateRetryDelay(attempt: number): number {
  const exponentialDelay = RETRY_CONFIG.baseDelay * Math.pow(2, attempt);
  const jitter = Math.random() * 0.5 * exponentialDelay; // 0-50% jitter
  const delay = Math.min(exponentialDelay + jitter, RETRY_CONFIG.maxDelay);
  return delay;
}

// Check if error is retryable
function isRetryableError(error: any): boolean {
  // Check status code
  if (error?.status && RETRY_CONFIG.retryableStatuses.includes(error.status)) {
    return true;
  }
  // Check error code
  if (error?.code) {
    if (RETRY_CONFIG.retryableErrors.includes(error.code)) {
      return true;
    }
    // Network errors (fetch failed)
    if (error.code === "NETWORK_ERROR" || error.message?.includes("fetch")) {
      return true;
    }
  }
  // TypeError from fetch failure
  if (error instanceof TypeError && error.message.includes("fetch")) {
    return true;
  }
  return false;
}

// Token management
let authToken: string | null = null;

export function setAuthToken(token: string | null) {
  authToken = token;
  if (typeof window !== "undefined") {
    if (token) {
      localStorage.setItem("auth_token", token);
    } else {
      localStorage.removeItem("auth_token");
    }
  }
}

export function getAuthToken(): string | null {
  if (authToken) return authToken;
  if (typeof window !== "undefined") {
    authToken = localStorage.getItem("auth_token");
  }
  return authToken;
}

export function clearAuthToken() {
  setAuthToken(null);
}

// Check if we're on a login page
function isLoginPage(): boolean {
  if (typeof window === "undefined") return false;
  return window.location.pathname === "/login";
}

// Redirect to login page
function redirectToLogin() {
  if (typeof window === "undefined") return;
  if (isLoginPage()) return;

  // Clear token
  clearAuthToken();

  // Store current URL for redirect after login
  const currentPath = window.location.pathname + window.location.search;
  const loginUrl = `/login?redirect=${encodeURIComponent(currentPath)}`;

  window.location.href = loginUrl;
}

// Handle API error
function handleApiError(response: Response, data: any): ApiError {
  const error: ApiError = {
    status: response.status,
    message: data?.message || data?.detail || "An error occurred",
    code: data?.error || "UNKNOWN_ERROR",
    traceId: data?.trace_id || response.headers.get("x-trace-id") || undefined,
    details: data?.detail || undefined,
  };

  // Handle 401 Unauthorized
  if (response.status === 401) {
    console.warn("[API] 401 Unauthorized, redirecting to login");
    redirectToLogin();
    error.code = "UNAUTHORIZED";
    error.message = "Session expired. Please login again.";
  }

  // Handle 403 Forbidden
  if (response.status === 403) {
    error.code = "FORBIDDEN";
    error.message = data?.detail || "You do not have permission to perform this action.";
  }

  // Handle 500 Internal Server Error
  if (response.status >= 500) {
    error.code = "SERVER_ERROR";
    error.message = "A server error occurred. Please try again later.";
  }

  return error;
}

// Build headers with CSRF token for mutating requests
function buildHeaders(
  customHeaders?: Record<string, string>,
  method: string = "GET"
): Record<string, string> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...customHeaders,
  };

  const token = getAuthToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  // Add CSRF token for state-changing methods
  if (["POST", "PUT", "PATCH", "DELETE"].includes(method.toUpperCase())) {
    const csrfToken = getCSRFToken();
    if (csrfToken) {
      headers["X-CSRF-Token"] = csrfToken;
    }
  }

  return headers;
}

// CSRF token extraction from cookie
function getCSRFToken(): string | null {
  if (typeof document === "undefined") return null;
  const value = `; ${document.cookie}`;
  const parts = value.split("; csrf_token=");
  if (parts.length === 2) {
    return parts.pop()?.split(";")?.shift() || null;
  }
  return null;
}

// Retry wrapper for fetch operations
async function fetchWithRetry<T>(
  operation: () => Promise<T>,
  options: { maxRetries?: number; skipRetry?: boolean } = {}
): Promise<T> {
  const maxRetries = options.maxRetries ?? RETRY_CONFIG.maxRetries;
  let lastError: any;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await operation();
    } catch (error: any) {
      lastError = error;

      // Don't retry if explicitly skipped
      if (options.skipRetry) {
        throw error;
      }

      // Don't retry on last attempt
      if (attempt === maxRetries) {
        break;
      }

      // Check if error is retryable
      if (!isRetryableError(error)) {
        throw error;
      }

      // Calculate and wait for retry delay
      const delay = calculateRetryDelay(attempt);
      console.warn(
        `[API] Retry attempt ${attempt + 1}/${maxRetries} after ${Math.round(delay)}ms`,
        {
          error: error.code || error.status,
          message: error.message,
        }
      );

      await sleep(delay);
    }
  }

  throw lastError;
}

// API client
export const apiClient = {
  async get<T>(
    path: string,
    params?: Record<string, string>,
    options?: { maxRetries?: number }
  ): Promise<T> {
    return fetchWithRetry(async () => {
      const url = new URL(`${API_BASE}${path}`);
      if (params) {
        Object.entries(params).forEach(([key, value]) => {
          url.searchParams.append(key, value);
        });
      }

      const response = await fetch(url.toString(), {
        method: "GET",
        headers: buildHeaders(undefined, "GET"),
        credentials: "include",
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw handleApiError(response, data);
      }

      return data as T;
    }, options);
  },

  async post<T>(
    path: string,
    body?: unknown,
    options?: { maxRetries?: number; skipRetry?: boolean }
  ): Promise<T> {
    return fetchWithRetry(async () => {
      const response = await fetch(`${API_BASE}${path}`, {
        method: "POST",
        headers: buildHeaders(undefined, "POST"),
        credentials: "include",
        body: body ? JSON.stringify(body) : undefined,
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw handleApiError(response, data);
      }

      return data as T;
    }, options);
  },

  async put<T>(
    path: string,
    body: unknown,
    options?: { maxRetries?: number; skipRetry?: boolean }
  ): Promise<T> {
    return fetchWithRetry(async () => {
      const response = await fetch(`${API_BASE}${path}`, {
        method: "PUT",
        headers: buildHeaders(undefined, "PUT"),
        credentials: "include",
        body: JSON.stringify(body),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw handleApiError(response, data);
      }

      return data as T;
    }, options);
  },

  async patch<T>(
    path: string,
    body: unknown,
    options?: { maxRetries?: number; skipRetry?: boolean }
  ): Promise<T> {
    return fetchWithRetry(async () => {
      const response = await fetch(`${API_BASE}${path}`, {
        method: "PATCH",
        headers: buildHeaders(undefined, "PATCH"),
        credentials: "include",
        body: JSON.stringify(body),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw handleApiError(response, data);
      }

      return data as T;
    }, options);
  },

  async delete<T>(
    path: string,
    options?: { maxRetries?: number; skipRetry?: boolean }
  ): Promise<T> {
    return fetchWithRetry(async () => {
      const response = await fetch(`${API_BASE}${path}`, {
        method: "DELETE",
        headers: buildHeaders(undefined, "DELETE"),
        credentials: "include",
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw handleApiError(response, data);
      }

      return data as T;
    }, options);
  },
};

// Export for convenience
export default apiClient;

// Export retry utilities for custom use cases
export { fetchWithRetry, calculateRetryDelay, isRetryableError, RETRY_CONFIG };
