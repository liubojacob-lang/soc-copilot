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
 * Ensure a raw CSRF token exists before a state-changing request.
 */
export async function ensureCSRFToken(): Promise<string | null> {
  return getCSRFToken() ?? refreshCSRFToken();
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
 * Fetch wrapper with automatic CSRF protection
 */
export async function csrfFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const optionsWithCSRF = addCSRFToken(options);

  return fetch(url, {
    ...optionsWithCSRF,
    credentials: "include", // Include cookies for auth + CSRF validation
  });
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
