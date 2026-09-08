// Base API client with common utilities
import { getAuthHeaders } from "./auth";
import { handleUnauthorized, refreshAccessToken } from "../auth";
import { addCSRFToken, ensureCSRFToken } from "../csrf";

/** Auth endpoints must never trigger the refresh-and-retry flow. */
const AUTH_EXEMPT_FRAGMENTS = ["/api/auth/login", "/api/auth/refresh", "/api/auth/logout"];

const CSRF_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

function isAuthPath(path: string): boolean {
  return AUTH_EXEMPT_FRAGMENTS.some((fragment) => path.includes(fragment));
}

let refreshPromise: Promise<boolean> | null = null;

/**
 * Refresh the session via the refresh_token HttpOnly cookie; concurrent 401
 * handlers share the same in-flight attempt instead of racing the endpoint.
 */
function refreshSession(): Promise<boolean> {
  if (!refreshPromise) {
    const attempt = (async () => {
      try {
        const state = await refreshAccessToken(null);
        return state.isAuthenticated;
      } catch {
        return false;
      }
    })();
    refreshPromise = attempt;
    void attempt.finally(() => {
      if (refreshPromise === attempt) {
        refreshPromise = null;
      }
    });
  }
  return refreshPromise;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = "") {
    this.baseUrl = baseUrl;
  }

  async request<T>(
    path: string,
    options: RequestInit = {},
    timeoutMs: number = 30000,
    isRetry: boolean = false
  ): Promise<T> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
    const method = (options.method || "GET").toUpperCase();

    // Cookie flow: make sure a CSRF raw token exists before state-changing
    // requests (double-submit: raw token in header, hash in cookie).
    if (CSRF_METHODS.has(method) && !isAuthPath(path)) {
      await ensureCSRFToken();
    }

    try {
      const urlWithBust = path.includes("?")
        ? `${this.baseUrl}${path}&_t=${Date.now()}`
        : `${this.baseUrl}${path}?_t=${Date.now()}`;

      const optionsWithCSRF = addCSRFToken(options);
      const response = await fetch(urlWithBust, {
        ...optionsWithCSRF,
        signal: controller.signal,
        keepalive: true,
        credentials: "include",
        headers: {
          ...getAuthHeaders(),
          ...(optionsWithCSRF.headers as Record<string, string> | undefined),
        },
      });

      clearTimeout(timeoutId);

      if (response.status === 401 && !isAuthPath(path) && !isRetry) {
        const refreshed = await refreshSession();
        if (refreshed) {
          // Retry once with the fresh session cookie.
          return this.request<T>(path, options, timeoutMs, true);
        }
        // Session is unrecoverable: clear state and send the user to login.
        handleUnauthorized();
      }

      if (!response.ok) {
        let errorMessage = `Request failed with status ${response.status}`;
        let errorData: unknown = undefined;
        try {
          const text = await response.text();
          if (text) {
            try {
              const parsed = JSON.parse(text);
              errorData = parsed;
              if (typeof parsed === "string") {
                errorMessage = parsed;
              } else if (parsed && typeof parsed === "object") {
                const msg =
                  (parsed as Record<string, any>).detail ||
                  (parsed as Record<string, any>).message ||
                  (parsed as Record<string, any>).error ||
                  (parsed as Record<string, any>).title;
                if (typeof msg === "string" && msg.trim()) {
                  errorMessage = msg;
                } else if (Array.isArray((parsed as Record<string, any>).detail)) {
                  errorMessage = (parsed as Record<string, any>).detail
                    .map((d: any) =>
                      typeof d === "object" ? d.msg || JSON.stringify(d) : String(d)
                    )
                    .join("; ");
                } else {
                  errorMessage = text;
                }
              }
            } catch {
              errorMessage = text;
            }
          }
        } catch {
          // ignore stream read error
        }
        throw new ApiError(response.status, errorMessage, errorData);
      }

      if (response.status === 204) {
        return undefined as unknown as T;
      }

      return response.json();
    } catch (error) {
      clearTimeout(timeoutId);
      if (error instanceof Error && error.name === "AbortError") {
        throw new Error(`Request timeout after ${timeoutMs / 1000}s`);
      }
      throw error;
    }
  }

  async get<T>(path: string, options: RequestInit = {}): Promise<T> {
    return this.request<T>(path, {
      method: "GET",
      ...options,
    });
  }

  async post<T>(path: string, data: unknown = {}, timeoutMs?: number): Promise<T> {
    return this.request<T>(
      path,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
      },
      timeoutMs
    );
  }

  async put<T>(path: string, data: unknown = {}): Promise<T> {
    return this.request<T>(path, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });
  }

  async patch<T>(path: string, data: unknown = {}): Promise<T> {
    return this.request<T>(path, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });
  }

  async delete<T>(path: string): Promise<T> {
    return this.request<T>(path, {
      method: "DELETE",
    });
  }
}

/**
 * Generic API envelope used by import/batch endpoints.
 */
export interface APIResponse<T> {
  success?: boolean;
  status?: string;
  message?: string;
  data: T;
}

export class ApiError extends Error {
  public data?: unknown;

  constructor(
    public status: number,
    message: string,
    data?: unknown
  ) {
    super(message);
    this.name = "ApiError";
    this.data = data;
    Object.setPrototypeOf(this, ApiError.prototype);
  }
}

export const apiClient = new ApiClient("");
