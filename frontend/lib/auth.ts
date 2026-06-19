// Authentication utilities for frontend
// P3-10: Enhanced with HttpOnly Cookie support and localStorage fallback

// import { ReadonlyRequestCookies } from "next/server"; // Not needed in client-side code

// Use Next.js API proxy to avoid CORS issues
// Note: Next.js rewrites /api/:path* to http://localhost:8000/api/:path*
// So we don't include /api prefix in the path
const API_BASE = "";

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
  if (strategy === "cookie") {
    // Check if access token cookie exists
    return !!getCookie(COOKIE_ACCESS_TOKEN_NAME);
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
}

/**
 * Login with username and password
 * P3-10: Enhanced with Cookie support
 */
export async function login(username: string, password: string): Promise<AuthState> {
  const response = await fetch(`/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include", // P3-10: Include cookies
    body: JSON.stringify({ username, password }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Login failed");
  }

  const data = await response.json();

  // P3-10: Detect storage strategy
  const strategy = detectStorageStrategy();

  const authState: AuthState = {
    isAuthenticated: true,
    user: data.user,
    tokens: {
      access_token: data.access_token,
      refresh_token: data.refresh_token,
    },
    storageStrategy: strategy,
  };

  // P3-10: Always save to localStorage as backup
  // Even when using HttpOnly cookies, we need localStorage for client-side auth checks
  // because HttpOnly cookies cannot be read by JavaScript
  saveAuthState(authState);

  return authState;
}

/**
 * Refresh access token
 * P3-10: Enhanced with Cookie support
 */
export async function refreshAccessToken(refreshToken: string): Promise<AuthState> {
  const response = await fetch(`/api/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include", // P3-10: Include cookies
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!response.ok) {
    // Clear tokens on failure
    logout();
    return { isAuthenticated: false, user: null, tokens: null, storageStrategy: "localStorage" };
  }

  const data = await response.json();
  const strategy = detectStorageStrategy();

  const authState: AuthState = {
    isAuthenticated: true,
    user: data.user,
    tokens: {
      access_token: data.access_token,
      refresh_token: data.refresh_token,
    },
    storageStrategy: strategy,
  };

  // Save to localStorage if using hybrid/localStorage strategy
  if (strategy !== "cookie") {
    saveAuthState(authState);
  }

  return authState;
}

/**
 * Logout (client-side only - discard tokens)
 * P3-10: Enhanced to clear both cookies and localStorage
 */
export function logout(): void {
  if (typeof window !== "undefined") {
    // Clear localStorage (for hybrid/localStorage mode)
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem(USER_KEY);

    // P3-10: Note: HttpOnly cookies are cleared by the backend
    // Call backend logout endpoint to clear HttpOnly cookies
    fetch("/api/auth/logout", {
      method: "POST",
      credentials: "include",
    }).catch(() => {
      // Ignore errors during logout
    });
  }
}

/**
 * Save auth state to localStorage
 * P3-10: ALWAYS save to localStorage as backup for client-side auth checks.
 * Even when using HttpOnly cookies, we need localStorage because:
 * 1. HttpOnly cookies cannot be read by JavaScript
 * 2. Client-side routing needs immediate auth state for protected routes
 * 3. The tokens in localStorage serve as a backup reference (actual API calls use cookies)
 */
export function saveAuthState(authState: AuthState): void {
  if (typeof window !== "undefined") {
    // Always save to localStorage regardless of storage strategy
    // This is critical because HttpOnly cookies cannot be read by JavaScript
    if (authState.tokens) {
      localStorage.setItem(ACCESS_TOKEN_KEY, authState.tokens.access_token);
      localStorage.setItem(REFRESH_TOKEN_KEY, authState.tokens.refresh_token);
    }
    if (authState.user) {
      localStorage.setItem(USER_KEY, JSON.stringify(authState.user));
    }
  }
}

/**
 * Load auth state from localStorage or Cookies
 * P3-10: Enhanced with Cookie support
 */
export function loadAuthState(): AuthState | null {
  if (typeof window === "undefined") return null;

  const strategy = detectStorageStrategy();

  // P3-10: Try localStorage first (primary source for client-side auth)
  // Even when using HttpOnly cookies, we need localStorage for immediate auth checks
  // because HttpOnly cookies cannot be read by JavaScript
  const accessToken = localStorage.getItem(ACCESS_TOKEN_KEY);
  const userStr = localStorage.getItem(USER_KEY);

  if (accessToken && userStr) {
    try {
      const user = JSON.parse(userStr);
      return {
        isAuthenticated: true,
        user,
        tokens: {
          access_token: accessToken,
          refresh_token: localStorage.getItem(REFRESH_TOKEN_KEY) || "",
        },
        storageStrategy: strategy,
      };
    } catch {
      return null;
    }
  }

  // P3-10: If no localStorage, try to detect cookies
  // Note: HttpOnly cookies cannot be accessed by JS, so this only works for non-HttpOnly cookies
  if (strategy === "cookie" || strategy === "hybrid") {
    const cookieToken = getCookie(COOKIE_ACCESS_TOKEN_NAME);
    if (cookieToken) {
      // Verify user from server (cookies don't contain user info)
      // For now, return a minimal auth state
      return {
        isAuthenticated: true,
        user: null, // Will be loaded separately
        tokens: {
          access_token: cookieToken,
          refresh_token: getCookie(COOKIE_REFRESH_TOKEN_NAME) || "",
        },
        storageStrategy: strategy,
      };
    }
  }

  return null;
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
function handleUnauthorized(): void {
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

/**
 * Fetch wrapper that automatically adds auth token and handles refresh
 * P3-10: Enhanced with Cookie support and CSRF protection
 */
export async function authFetch(
  url: string,
  options: RequestInit = {},
  maxRetries = 1
): Promise<Response> {
  let accessToken = getAccessToken();
  let refreshToken = getRefreshToken();

  // If no tokens, try without auth (for public endpoints)
  if (!accessToken) {
    return fetch(url, {
      ...options,
      credentials: "include", // P3-10: Include cookies
    });
  }

  const makeRequest = async (token: string): Promise<Response> => {
    return fetch(url, {
      ...options,
      credentials: "include", // P3-10: Include cookies
      headers: {
        ...options.headers,
        // P3-10: Only add Authorization header if not using cookies
        ...(getCookie(COOKIE_ACCESS_TOKEN_NAME) ? {} : { Authorization: `Bearer ${token}` }),
      },
    });
  };

  let response = await makeRequest(accessToken);

  // If access token expired, try to refresh
  if (response.status === 401 && refreshToken && maxRetries > 0) {
    const authState = await refreshAccessToken(refreshToken);
    if (authState.isAuthenticated && authState.tokens) {
      saveAuthState(authState);
      return authFetch(url, options, maxRetries - 1);
    }
    // Refresh failed, handle unauthorized
    handleUnauthorized();
  } else if (response.status === 401) {
    // No refresh token or max retries exceeded
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
  // Use url as-is since it already includes /api prefix
  const fullUrl = url.startsWith("http") ? url : url;

  // P3-10: Import CSRF protection
  const { csrfFetch } = await import("./csrf");

  const response = await csrfFetch(fullUrl, {
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
    usingHttpOnlyCookies: usingCookies && getCookie(COOKIE_ACCESS_TOKEN_NAME),
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
