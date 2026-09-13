/**
 * CSRF Token Management
 *
 * Double-submit pattern: the server sets a hashed csrf_token cookie and the
 * client sends the RAW token in the X-CSRF-Token header; the backend compares
 * sha256(header) against the cookie. The raw token therefore lives in
 * sessionStorage (per-tab), never in the cookie.
 *
 * The raw token arrives in the login response body (data.csrf_token) or can
 * be (re)issued via GET /api/v1/auth/csrf-token.
 */

const CSRF_STORAGE_KEY = "csrf_raw";
const CSRF_HEADER_NAME = "X-CSRF-Token";
const CSRF_PROTECTED_METHODS = new Set(["POST", "PUT", "DELETE", "PATCH"]);

export function getCSRFToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return sessionStorage.getItem(CSRF_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setCSRFToken(token: string): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.setItem(CSRF_STORAGE_KEY, token);
  } catch {
    // sessionStorage unavailable (private mode) — CSRF header will be absent
    // and the backend will reject state-changing requests with a clear 403.
  }
}

export function clearCSRFToken(): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.removeItem(CSRF_STORAGE_KEY);
  } catch {
    /* ignore */
  }
}

/**
 * Fetch a fresh CSRF token pair from the backend and store the raw token.
 */
export async function refreshCSRFToken(): Promise<string | null> {
  try {
    const response = await fetch("/api/v1/auth/csrf-token", {
      credentials: "include",
    });
    if (response.ok) {
      const data = await response.json();
      if (data.csrf_token) {
        setCSRFToken(data.csrf_token);
        return data.csrf_token as string;
      }
    }
  } catch {
    // network error — callers fall back to any stored token
  }
  return getCSRFToken();
}

/**
 * Check if the csrf_token cookie exists in document.cookie.
 * Since csrf_token is not HttpOnly, JavaScript can verify its presence.
 */
export function hasCSRFCookie(): boolean {
  if (typeof document === "undefined") return false;
  return document.cookie.split(";").some((c) => c.trim().startsWith("csrf_token="));
}

/**
 * Ensure a fresh CSRF token pair exists before a state-changing request.
 * If the raw token is missing from sessionStorage OR the csrf_token cookie
 * has expired/missing from document.cookie, proactively fetches a fresh pair.
 */
export async function ensureCSRFToken(): Promise<string | null> {
  const currentToken = getCSRFToken();
  const cookiePresent = hasCSRFCookie();

  if (!currentToken || !cookiePresent) {
    return refreshCSRFToken();
  }
  return currentToken;
}

/**
 * Add the X-CSRF-Token header to fetch options for state-changing methods.
 * Synchronous: uses the stored raw token (call ensureCSRFToken beforehand on
 * flows that may not have one yet, e.g. right after a full page load).
 */
export function addCSRFToken(options: RequestInit): RequestInit {
  const method = (options.method || "GET").toUpperCase();
  if (!CSRF_PROTECTED_METHODS.has(method)) {
    return options;
  }
  const csrfToken = getCSRFToken();
  if (!csrfToken) {
    return options;
  }
  return {
    ...options,
    headers: {
      ...options.headers,
      [CSRF_HEADER_NAME]: csrfToken,
    },
  };
}

/**
 * Fetch wrapper with automatic CSRF protection and self-healing retry
 */
export async function csrfFetch(
  url: string,
  options: RequestInit = {},
  maxRetries = 1
): Promise<Response> {
  const method = (options.method || "GET").toUpperCase();
  if (CSRF_PROTECTED_METHODS.has(method)) {
    await ensureCSRFToken();
  }

  const optionsWithCSRF = addCSRFToken(options);

  const response = await fetch(url, {
    ...optionsWithCSRF,
    credentials: "include", // Include cookies for auth + CSRF validation
  });

  // Self-healing CSRF: retry once if CSRF validation failed
  if (response.status === 403 && CSRF_PROTECTED_METHODS.has(method) && maxRetries > 0) {
    let isCsrfError = false;
    try {
      const cloned = response.clone();
      const errData = await cloned.json();
      if (
        errData?.error === "csrf_validation_failed" ||
        (typeof errData?.detail === "string" && errData.detail.toLowerCase().includes("csrf")) ||
        (typeof errData?.message === "string" && errData.message.toLowerCase().includes("csrf"))
      ) {
        isCsrfError = true;
      }
    } catch {
      // ignore
    }

    if (isCsrfError) {
      const newToken = await refreshCSRFToken();
      if (newToken) {
        const retryHeaders = {
          ...(options.headers as Record<string, string> | undefined),
          [CSRF_HEADER_NAME]: newToken,
        };
        return csrfFetch(
          url,
          {
            ...options,
            headers: retryHeaders,
          },
          maxRetries - 1
        );
      }
    }
  }

  return response;
}

/**
 * Fetch wrapper with JSON and CSRF protection
 */
export async function csrfFetchJSON<T = unknown>(
  url: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await csrfFetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Request failed");
  }

  return response.json();
}
