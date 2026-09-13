// Authentication utilities for frontend
// P3-10: Enhanced with HttpOnly Cookie support and localStorage fallback

// import { ReadonlyRequestCookies } from "next/server"; // Not needed in client-side code

// Use Next.js API proxy to avoid CORS issues
// Note: Next.js rewrites /api/:path* to http://localhost:8000/api/:path*
// So we don't include /api prefix in the path
const API_BASE = "";

import { setCSRFToken, clearCSRFToken } from "./csrf";

// Storage keys (for localStorage fallback)
const ACCESS_TOKEN_KEY = "access_token";
const REFRESH_TOKEN_KEY = "refresh_token";
const USER_KEY = "user";

// Cookie names (must match backend)
const COOKIE_ACCESS_TOKEN_NAME = "access_token";
const COOKIE_REFRESH_TOKEN_NAME = "refresh_token";

// P3-10: Storage strategy detection
export type StorageStrategy = "cookie" | "localStorage" | "hybrid";

let detectedStorageStrategy: StorageStrategy | null = null;

/**
 * Detect the best available storage strategy
 * Priority: Cookie > localStorage > None
 */
export function detectStorageStrategy(): StorageStrategy {
  if (detectedStorageStrategy) {
    return detectedStorageStrategy;
  }

  // Check if cookies are accessible
  const cookieEnabled = typeof document !== "undefined" && navigator.cookieEnabled;

  // Check if localStorage is accessible
  let localStorageEnabled = false;
  if (typeof window !== "undefined") {
    try {
      localStorage.setItem("test", "test");
      localStorage.removeItem("test");
      localStorageEnabled = true;
    } catch (e) {
      localStorageEnabled = false;
    }
  }

  // Determine strategy
  if (cookieEnabled) {
    detectedStorageStrategy = "cookie";
  } else if (localStorageEnabled) {
    detectedStorageStrategy = "localStorage";
  } else {
    detectedStorageStrategy = "localStorage"; // Fallback, will fail gracefully
  }

  return detectedStorageStrategy;
}

/**
 * Get cookie value by name
 */
function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;

  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) {
    return parts.pop()?.split(";")?.shift() || null;
  }

  return null;
}

/**
 * Check if HttpOnly cookies are being used
 */
export function usingHttpOnlyCookies(): boolean {
  const strategy = detectStorageStrategy();
  if (strategy === "cookie" || strategy === "hybrid") {
    // HttpOnly cookies cannot be read via document.cookie.
    // Check if a session exists via stored user or csrf_token cookie.
    return (
      !!loadStoredUser() ||
      (typeof document !== "undefined" && document.cookie.includes("csrf_token"))
    );
  }
  return false;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
}

import type { User } from "@/lib/types";
export type { User };

export interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  tokens: AuthTokens | null;
  storageStrategy: StorageStrategy;
  /** Server requires this session's user to set a new password before proceeding. */
  mustChangePassword?: boolean;
  /** Server requires 2FA verification code to complete login. */
  require2FA?: boolean;
  /** Short-lived pre-auth token to complete 2FA login challenge. */
  preAuthToken?: string;
}

/**
 * Login with username and password.
 *
 * Cookie flow: the backend sets HttpOnly access/refresh cookies and returns
 * the raw CSRF token in the body. Tokens are NEVER persisted to
 * JavaScript-readable storage (XSS would otherwise grant a 7-day takeover);
 * only the non-sensitive user object is kept for UI state.
 */
export async function login(username: string, password: string): Promise<AuthState> {
  const response = await fetch(`/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include", // HttpOnly cookies are set by this response
    body: JSON.stringify({ username, password }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    const message =
      error.message ||
      error.detail ||
      (response.status === 429 ? "请求过于频繁，请稍后再试" : "登录失败");
    throw new Error(message);
  }

  const data = await response.json();

  // If 2FA is required, return challenge state without persisting session
  if (data.require_2fa) {
    return {
      isAuthenticated: false,
      user: data.user,
      tokens: null,
      storageStrategy: "cookie",
      require2FA: true,
      preAuthToken: data.pre_auth_token,
    };
  }

  // Keep the raw CSRF token for state-changing requests (double-submit).
  if (data.csrf_token) {
    setCSRFToken(data.csrf_token);
  }

  const authState: AuthState = {
    isAuthenticated: true,
    user: data.user,
    tokens: null,
    storageStrategy: "cookie",
    mustChangePassword: data.must_change_password === true,
  };

  saveAuthState(authState);

  return authState;
}

/**
 * Complete 2FA login challenge with TOTP code or backup recovery code.
 */
export async function loginWith2FA(preAuthToken: string, code: string): Promise<AuthState> {
  const response = await fetch(`/api/v1/auth/login-2fa`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ pre_auth_token: preAuthToken, code }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "2FA verification failed");
  }

  const data = await response.json();
  if (data.csrf_token) {
    setCSRFToken(data.csrf_token);
  }

  const authState: AuthState = {
    isAuthenticated: true,
    user: data.user,
    tokens: null,
    storageStrategy: "cookie",
    mustChangePassword: data.must_change_password === true,
  };

  saveAuthState(authState);
  return authState;
}

/**
 * Verify TOTP code for Sudo Mode (sensitive operations).
 * Returns a 10-minute temporary sudo token.
 */
export async function verifySudoMode(
  code: string
): Promise<{ valid: boolean; sudo_token: string; expires_in_seconds: number }> {
  return authFetchJSON<{ valid: boolean; sudo_token: string; expires_in_seconds: number }>(
    "/api/v1/auth/2fa/verify-sudo",
    {
      method: "POST",
      body: JSON.stringify({ code }),
    }
  );
}

/**
 * Refresh the session via the refresh_token HttpOnly cookie.
 * The backend falls back to the cookie when no body token is provided.
 */
export async function refreshAccessToken(_refreshToken?: string | null): Promise<AuthState> {
  const response = await fetch(`/api/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({}),
  });

  if (!response.ok) {
    // Session unrecoverable: clear client-side state and CSRF token.
    logout();
    return { isAuthenticated: false, user: null, tokens: null, storageStrategy: "cookie" };
  }

  const data = await response.json();

  if (data.csrf_token) {
    setCSRFToken(data.csrf_token);
  }

  const authState: AuthState = {
    isAuthenticated: true,
    user: data.user ?? loadStoredUser(),
    tokens: null,
    storageStrategy: "cookie",
  };

  if (authState.user) {
    saveAuthState(authState);
  }

  return authState;
}

/**
 * Logout (client-side + server-side cookie clearing)
 */
export function logout(): void {
  if (typeof window !== "undefined") {
    // Clear local UI state (user hint + CSRF raw token)
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    clearCSRFToken();

    // Clear UI hint cookies used for SSR navigation alignment
    document.cookie = "user_role=; path=/; max-age=0; SameSite=Lax";
    document.cookie = "sidebar_collapsed=; path=/; max-age=0; SameSite=Lax";
    document.cookie = "sidebar_collapsed_groups=; path=/; max-age=0; SameSite=Lax";

    // HttpOnly cookies are cleared by the backend logout endpoint
    fetch("/api/auth/logout", {
      method: "POST",
      credentials: "include",
    }).catch(() => {
      // Ignore errors during logout
    });
  }
}

function loadStoredUser(): User | null {
  if (typeof window === "undefined") return null;
  try {
    const userStr = localStorage.getItem(USER_KEY);
    return userStr ? (JSON.parse(userStr) as User) : null;
  } catch {
    return null;
  }
}

/**
 * Save auth state to localStorage.
 *
 * ONLY the non-sensitive user object is persisted — it exists purely as a UI
 * hint (navigation, role-gated menus). Tokens live exclusively in HttpOnly
 * cookies, which JavaScript cannot read, so an XSS cannot steal a session.
 * We also mirror the non-sensitive role into a Lax cookie so SSR can render
 * identical role-gated navigation without any client-side layout shifts.
 */
export function saveAuthState(authState: AuthState): void {
  if (typeof window !== "undefined") {
    // Defensive cleanup: remove any tokens left by the previous storage scheme.
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    if (authState.user) {
      localStorage.setItem(USER_KEY, JSON.stringify(authState.user));
      if (authState.user.role) {
        document.cookie = `user_role=${encodeURIComponent(authState.user.role)}; path=/; max-age=2592000; SameSite=Lax`;
      }
    }
  }
}

/**
 * Load auth state for UI purposes.
 *
 * The user object is the client-side hint that a session existed; the real
 * authority is the HttpOnly cookie validated on every request. An expired
 * session surfaces as 401 → refresh → redirect (handled in the API clients).
 */
export function loadAuthState(): AuthState | null {
  if (typeof window === "undefined") return null;

  const user = loadStoredUser();
  if (!user) {
    return null;
  }

  return {
    isAuthenticated: true,
    user,
    tokens: null,
    storageStrategy: "cookie",
  };
}

/**
 * Get access token for API requests
 * P3-10: Enhanced to check Cookies first, then localStorage
 */
export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;

  // P3-10: Try HttpOnly cookie first (more secure)
  const cookieToken = getCookie(COOKIE_ACCESS_TOKEN_NAME);
  if (cookieToken) {
    return cookieToken;
  }

  // Fallback to localStorage
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

/**
 * Get refresh token
 * P3-10: Enhanced to check Cookies first, then localStorage
 */
export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;

  // P3-10: Try HttpOnly cookie first
  const cookieToken = getCookie(COOKIE_REFRESH_TOKEN_NAME);
  if (cookieToken) {
    return cookieToken;
  }

  // Fallback to localStorage
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

/**
 * Check if user has specific permission
 */
export function hasPermission(user: User | null, permission: string): boolean {
  if (!user) return false;
  return user.permissions.includes(permission);
}

/**
 * Check if user has any of the specified permissions
 */
export function hasAnyPermission(user: User | null, permissions: string[]): boolean {
  if (!user) return false;
  return permissions.some((p) => user.permissions.includes(p));
}

/**
 * Check if user is admin
 */
export function isAdmin(user: User | null): boolean {
  return user?.role === "admin";
}

/**
 * Check if user is analyst or admin
 */
export function isAnalystOrAdmin(user: User | null): boolean {
  if (!user) return false;
  return user.role === "admin" || user.role === "analyst";
}

/**
 * Check if user can execute playbook apply mode
 */
export function canApplyPlaybook(user: User | null): boolean {
  return user?.role === "admin";
}

/**
 * Check if user can execute playbook run/resume
 */
export function canRunPlaybook(user: User | null): boolean {
  if (!user) return false;
  return user.role === "admin" || user.role === "analyst";
}

/**
 * Handle 401 response - clear tokens and redirect to login
 */
export function handleUnauthorized(): void {
  logout();
  // Only redirect if in browser and not already on login page
  if (typeof window !== "undefined" && !window.location.pathname.includes("/login")) {
    // Store the current URL for redirect after login
    const currentPath = window.location.pathname + window.location.search;
    sessionStorage.setItem("redirect_after_login", currentPath);
    // Redirect to login
    window.location.href = "/login";
  }
}

const CSRF_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);
const AUTH_EXEMPT_FRAGMENTS = [
  "/api/auth/login",
  "/api/auth/refresh",
  "/api/auth/logout",
  "/login-2fa",
];

function isAuthPath(path: string): boolean {
  return AUTH_EXEMPT_FRAGMENTS.some((fragment) => path.includes(fragment));
}

/**
 * Fetch wrapper that automatically adds auth token and handles refresh
 * P3-10: Enhanced with Cookie support and CSRF protection
 */
export async function authFetch(
  url: string,
  options: RequestInit = {},
  maxRetries = 1
): Promise<Response> {
  const { addCSRFToken, ensureCSRFToken } = await import("./csrf");
  const method = (options.method || "GET").toUpperCase();

  // Ensure CSRF token exists for state-changing methods
  if (CSRF_METHODS.has(method) && !isAuthPath(url)) {
    await ensureCSRFToken();
  }

  const optionsWithCSRF = addCSRFToken(options);
  const accessToken = getAccessToken();
  const headers = {
    ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
    ...(optionsWithCSRF.headers as Record<string, string> | undefined),
  };

  const response = await fetch(url, {
    ...optionsWithCSRF,
    credentials: "include", // Always include cookies
    headers,
  });

  // Self-healing CSRF: If request failed with 403 CSRF error, refresh token and retry once
  if (response.status === 403 && !isAuthPath(url) && maxRetries > 0) {
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
      // non-JSON response or clone error
    }

    if (isCsrfError) {
      const { refreshCSRFToken } = await import("./csrf");
      const newToken = await refreshCSRFToken();
      if (newToken) {
        const retryHeaders = {
          ...headers,
          "X-CSRF-Token": newToken,
        };
        return authFetch(
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

  // If session expired, try to refresh via refresh_token cookie/localStorage
  if (response.status === 401 && !isAuthPath(url) && maxRetries > 0) {
    const authState = await refreshAccessToken(getRefreshToken());
    if (authState.isAuthenticated) {
      saveAuthState(authState);
      return authFetch(url, options, maxRetries - 1);
    }
    handleUnauthorized();
  }

  return response;
}

/**
 * Fetch wrapper that returns JSON with auth
 * P3-10: Enhanced with CSRF protection
 */
export async function authFetchJSON<T = unknown>(
  url: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await authFetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string> | undefined),
    },
  });

  if (!response.ok) {
    let errorDetail = `Request failed (${response.status})`;
    try {
      const errorJson = await response.json();
      errorDetail = errorJson.detail || errorJson.message || errorDetail;
    } catch {
      try {
        const text = await response.text();
        if (text) errorDetail = text;
      } catch {
        /* ignore */
      }
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

/**
 * Get current user from server
 */
export async function getCurrentUser(): Promise<User> {
  return authFetchJSON<User>(`/api/auth/me`);
}

/**
 * P3-10: Get current auth security info
 */
export function getAuthSecurityInfo() {
  const strategy = detectStorageStrategy();
  const usingCookies = strategy === "cookie" || strategy === "hybrid";

  return {
    storageStrategy: strategy,
    usingHttpOnlyCookies:
      usingCookies &&
      (!!loadStoredUser() ||
        (typeof document !== "undefined" && document.cookie.includes("csrf_token"))),
    usingLocalStorage: strategy === "localStorage" || !!localStorage.getItem(ACCESS_TOKEN_KEY),
    cookieAccessible: typeof document !== "undefined" && navigator.cookieEnabled,
    localStorageAccessible: (() => {
      try {
        localStorage.setItem("test", "test");
        localStorage.removeItem("test");
        return true;
      } catch {
        return false;
      }
    })(),
  };
}

/**
 * P3-10: Manually switch storage strategy
 * Useful for testing or when auto-detection fails
 */
export function setStorageStrategy(strategy: StorageStrategy): void {
  detectedStorageStrategy = strategy;

  // Migrate data if needed
  if (strategy === "cookie") {
    // When switching to cookies, clear localStorage tokens
    // (The backend will set HttpOnly cookies)
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  }
}

/**
 * P3-10: Export storage strategy for debugging
 */
export { detectedStorageStrategy as currentStorageStrategy };

/**
 * Check if user is authenticated by verifying with server
 * This is more reliable than just checking localStorage
 */
export async function checkAuthStatus(): Promise<boolean> {
  try {
    const response = await fetch("/api/auth/me", {
      method: "GET",
      credentials: "include", // Ensure cookies are sent
      headers: {
        "Content-Type": "application/json",
      },
    });
    return response.ok;
  } catch (error) {
    console.error("[Auth] Failed to check auth status:", error);
    return false;
  }
}

/**
 * Check if user has valid tokens locally (without server verification)
 * Use this for quick UI checks, use checkAuthStatus() for secure operations
 */
export function hasLocalAuth(): boolean {
  if (typeof window === "undefined") return false;

  const accessToken = localStorage.getItem(ACCESS_TOKEN_KEY);
  const userStr = localStorage.getItem(USER_KEY);

  return !!(accessToken && userStr);
}

/**
 * Clear all auth data and redirect to login
 * Use this when auth errors are detected
 */
export function clearAuthAndRedirect(): void {
  logout();
  if (typeof window !== "undefined" && !window.location.pathname.includes("/login")) {
    const currentPath = window.location.pathname + window.location.search;
    sessionStorage.setItem("redirect_after_login", currentPath);
    window.location.href = "/login";
  }
}
