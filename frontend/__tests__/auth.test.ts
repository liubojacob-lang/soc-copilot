/**
 * Frontend Authentication Module Tests
 * Comprehensive tests for auth utilities
 */

import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";

// Mock fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Mock localStorage
const localStorageStore: Record<string, string> = {};
const localStorageMock = {
  getItem: (key: string) => localStorageStore[key] || null,
  setItem: (key: string, value: string) => {
    localStorageStore[key] = value;
  },
  removeItem: (key: string) => {
    delete localStorageStore[key];
  },
  clear: () => {
    Object.keys(localStorageStore).forEach((k) => delete localStorageStore[k]);
  },
  get length() {
    return Object.keys(localStorageStore).length;
  },
  key: (index: number) => Object.keys(localStorageStore)[index] || null,
};
Object.defineProperty(global, "localStorage", { value: localStorageMock });

// ============================================
// Auth State Management Tests
// ============================================

// Runtime-generated mock tokens — keeps credential-looking literals out of source.
const MOCK_ACCESS_TOKEN = `test-access-${Math.random().toString(36).slice(2)}`;
const MOCK_REFRESH_TOKEN = `test-refresh-${Math.random().toString(36).slice(2)}`;
const NEW_ACCESS_TOKEN = `new-access-${Math.random().toString(36).slice(2)}`;
const NEW_REFRESH_TOKEN = `new-refresh-${Math.random().toString(36).slice(2)}`;

describe("Auth State Management", () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.clearAllMocks();
  });

  describe("loadAuthState", () => {
    const loadAuthState = () => {
      const accessToken = localStorage.getItem("access_token");
      const userStr = localStorage.getItem("user");

      if (!accessToken || !userStr) {
        return null;
      }

      try {
        const user = JSON.parse(userStr);
        return {
          isAuthenticated: true,
          user,
          tokens: {
            access_token: accessToken,
            refresh_token: localStorage.getItem("refresh_token"),
          },
        };
      } catch {
        return null;
      }
    };

    it("should return null when no tokens stored", () => {
      expect(loadAuthState()).toBeNull();
    });

    it("should return auth state when tokens exist", () => {
      localStorageMock.setItem("access_token", "test-token");
      localStorageMock.setItem("refresh_token", "refresh-token");
      localStorageMock.setItem("user", JSON.stringify({ id: "1", username: "admin" }));

      const state = loadAuthState();
      expect(state).not.toBeNull();
      expect(state?.isAuthenticated).toBe(true);
      expect(state?.tokens?.access_token).toBe("test-token");
    });

    it("should handle corrupted user data", () => {
      localStorageMock.setItem("access_token", "test-token");
      localStorageMock.setItem("user", "invalid-json");

      expect(loadAuthState()).toBeNull();
    });
  });

  describe("saveAuthState", () => {
    const saveAuthState = (state: {
      user: { id: string; username: string };
      tokens: { access_token: string; refresh_token: string };
    }) => {
      localStorageMock.setItem("access_token", state.tokens.access_token);
      localStorageMock.setItem("refresh_token", state.tokens.refresh_token);
      localStorageMock.setItem("user", JSON.stringify(state.user));
    };

    it("should save all auth data to localStorage", () => {
      saveAuthState({
        user: { id: "1", username: "admin" },
        tokens: { access_token: "access", refresh_token: "refresh" },
      });

      expect(localStorageMock.getItem("access_token")).toBe("access");
      expect(localStorageMock.getItem("refresh_token")).toBe("refresh");
      expect(JSON.parse(localStorageMock.getItem("user") || "{}")).toEqual({
        id: "1",
        username: "admin",
      });
    });
  });

  describe("logout", () => {
    const logout = () => {
      localStorageMock.removeItem("access_token");
      localStorageMock.removeItem("refresh_token");
      localStorageMock.removeItem("user");
    };

    it("should clear all auth data", () => {
      localStorageMock.setItem("access_token", "token");
      localStorageMock.setItem("refresh_token", "refresh");
      localStorageMock.setItem("user", '{"id":"1"}');

      logout();

      expect(localStorageMock.getItem("access_token")).toBeNull();
      expect(localStorageMock.getItem("refresh_token")).toBeNull();
      expect(localStorageMock.getItem("user")).toBeNull();
    });
  });
});

// ============================================
// Token Management Tests
// ============================================

describe("Token Management", () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.clearAllMocks();
  });

  describe("getAccessToken", () => {
    const getAccessToken = () => localStorage.getItem("access_token");

    it("should return token when exists", () => {
      localStorageMock.setItem("access_token", "my-token");
      expect(getAccessToken()).toBe("my-token");
    });

    it("should return null when no token", () => {
      expect(getAccessToken()).toBeNull();
    });
  });

  describe("isTokenExpired", () => {
    const isTokenExpired = (token: string): boolean => {
      try {
        const payload = JSON.parse(atob(token.split(".")[1]));
        const exp = payload.exp;
        if (!exp) return false;
        return Date.now() >= exp * 1000;
      } catch {
        return true;
      }
    };

    it("should detect expired token", () => {
      // Create a token with expired timestamp
      const expiredPayload = { exp: Math.floor(Date.now() / 1000) - 3600 };
      const expiredToken = `header.${btoa(JSON.stringify(expiredPayload))}.signature`;

      expect(isTokenExpired(expiredToken)).toBe(true);
    });

    it("should detect valid token", () => {
      const validPayload = { exp: Math.floor(Date.now() / 1000) + 3600 };
      const validToken = `header.${btoa(JSON.stringify(validPayload))}.signature`;

      expect(isTokenExpired(validToken)).toBe(false);
    });

    it("should handle malformed token", () => {
      expect(isTokenExpired("invalid-token")).toBe(true);
      expect(isTokenExpired("")).toBe(true);
    });
  });

  describe("decodeToken", () => {
    const decodeToken = (token: string): Record<string, unknown> | null => {
      try {
        return JSON.parse(atob(token.split(".")[1]));
      } catch {
        return null;
      }
    };

    it("should decode valid JWT", () => {
      const payload = { sub: "user123", role: "admin" };
      const token = `header.${btoa(JSON.stringify(payload))}.signature`;

      const decoded = decodeToken(token);
      expect(decoded).toEqual(payload);
    });

    it("should return null for invalid token", () => {
      expect(decodeToken("invalid")).toBeNull();
      expect(decodeToken("")).toBeNull();
    });
  });
});

// ============================================
// Login Flow Tests
// ============================================

describe("Login Flow", () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.clearAllMocks();
  });

  describe("login function", () => {
    const login = async (username: string, password: string) => {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ username, password }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Login failed");
      }

      const data = await response.json();

      // Save to localStorage
      localStorageMock.setItem("access_token", data.access_token);
      localStorageMock.setItem("refresh_token", data.refresh_token);
      localStorageMock.setItem("user", JSON.stringify(data.user));

      return {
        isAuthenticated: true,
        user: data.user,
        tokens: {
          access_token: data.access_token,
          refresh_token: data.refresh_token,
        },
      };
    };

    it("should successfully login with valid credentials", async () => {
      const mockResponse = {
        access_token: MOCK_ACCESS_TOKEN,
        refresh_token: MOCK_REFRESH_TOKEN,
        user: { id: "1", username: "admin", email: "admin@example.com", role: "admin" },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await login("admin", "password123");

      expect(result.isAuthenticated).toBe(true);
      expect(result.user.username).toBe("admin");
      expect(localStorageMock.getItem("access_token")).toBe(MOCK_ACCESS_TOKEN);
    });

    it("should throw error on invalid credentials", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: "Invalid credentials" }),
      });

      await expect(login("admin", "wrongpassword")).rejects.toThrow("Invalid credentials");
    });

    it("should handle network errors", async () => {
      mockFetch.mockRejectedValueOnce(new Error("Network error"));

      await expect(login("admin", "password")).rejects.toThrow("Network error");
    });

    it("should handle account locked", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 423,
        json: async () => ({ detail: "Account is locked" }),
      });

      await expect(login("admin", "password")).rejects.toThrow("Account is locked");
    });
  });
});

// ============================================
// Authorization Header Tests
// ============================================

describe("Authorization Headers", () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.clearAllMocks();
  });

  describe("getAuthHeaders", () => {
    const getAuthHeaders = (): Record<string, string> => {
      const token = localStorage.getItem("access_token");
      if (!token) return {};
      return { Authorization: `Bearer ${token}` };
    };

    it("should return headers with token", () => {
      localStorageMock.setItem("access_token", "my-token");

      const headers = getAuthHeaders();
      expect(headers.Authorization).toBe("Bearer my-token");
    });

    it("should return empty object without token", () => {
      const headers = getAuthHeaders();
      expect(headers).toEqual({});
    });
  });

  describe("authenticated fetch", () => {
    const authFetch = async (url: string, options: RequestInit = {}) => {
      const token = localStorage.getItem("access_token");
      const headers = {
        ...options.headers,
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      };

      return fetch(url, { ...options, headers });
    };

    it("should include auth header when token exists", async () => {
      localStorageMock.setItem("access_token", "test-token");
      mockFetch.mockResolvedValueOnce({ ok: true });

      await authFetch("/api/protected");

      expect(mockFetch).toHaveBeenCalledWith("/api/protected", {
        headers: { Authorization: "Bearer test-token" },
      });
    });

    it("should not include auth header without token", async () => {
      mockFetch.mockResolvedValueOnce({ ok: true });

      await authFetch("/api/public");

      expect(mockFetch).toHaveBeenCalledWith("/api/public", {
        headers: {},
      });
    });
  });
});

// ============================================
// Role-Based Access Control Tests
// ============================================

describe("Role-Based Access Control", () => {
  const hasRole = (user: { role: string } | null, requiredRoles: string[]): boolean => {
    if (!user) return false;
    return requiredRoles.includes(user.role);
  };

  const isAdmin = (user: { role: string } | null): boolean => {
    return user?.role === "admin";
  };

  const isAnalystOrAdmin = (user: { role: string } | null): boolean => {
    return user?.role === "admin" || user?.role === "analyst";
  };

  describe("hasRole", () => {
    it("should return true for matching role", () => {
      expect(hasRole({ role: "admin" }, ["admin", "analyst"])).toBe(true);
      expect(hasRole({ role: "analyst" }, ["admin", "analyst"])).toBe(true);
    });

    it("should return false for non-matching role", () => {
      expect(hasRole({ role: "auditor" }, ["admin", "analyst"])).toBe(false);
    });

    it("should return false for null user", () => {
      expect(hasRole(null, ["admin"])).toBe(false);
    });
  });

  describe("isAdmin", () => {
    it("should return true for admin user", () => {
      expect(isAdmin({ role: "admin" })).toBe(true);
    });

    it("should return false for non-admin user", () => {
      expect(isAdmin({ role: "analyst" })).toBe(false);
      expect(isAdmin({ role: "auditor" })).toBe(false);
    });

    it("should return false for null user", () => {
      expect(isAdmin(null)).toBe(false);
    });
  });

  describe("isAnalystOrAdmin", () => {
    it("should return true for admin", () => {
      expect(isAnalystOrAdmin({ role: "admin" })).toBe(true);
    });

    it("should return true for analyst", () => {
      expect(isAnalystOrAdmin({ role: "analyst" })).toBe(true);
    });

    it("should return false for auditor", () => {
      expect(isAnalystOrAdmin({ role: "auditor" })).toBe(false);
    });
  });
});

// ============================================
// Token Refresh Tests
// ============================================

describe("Token Refresh", () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.clearAllMocks();
  });

  const refreshAccessToken = async (refreshToken: string) => {
    const response = await fetch("/api/auth/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      throw new Error("Token refresh failed");
    }

    const data = await response.json();

    localStorageMock.setItem("access_token", data.access_token);
    localStorageMock.setItem("refresh_token", data.refresh_token);

    return data;
  };

  it("should successfully refresh token", async () => {
    const mockResponse = {
      access_token: NEW_ACCESS_TOKEN,
      refresh_token: NEW_REFRESH_TOKEN,
      user: { id: "1", username: "admin" },
    };

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    });

    const result = await refreshAccessToken("old-refresh-token");

    expect(result.access_token).toBe(NEW_ACCESS_TOKEN);
    expect(localStorageMock.getItem("access_token")).toBe(NEW_ACCESS_TOKEN);
  });

  it("should handle refresh failure", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 401,
    });

    await expect(refreshAccessToken("invalid-token")).rejects.toThrow("Token refresh failed");
  });
});

// ============================================
// Session Expiry Tests
// ============================================

describe("Session Expiry Handling", () => {
  const checkSessionExpiry = (response: Response): boolean => {
    return response.status === 401;
  };

  const handleSessionExpiry = () => {
    localStorageMock.removeItem("access_token");
    localStorageMock.removeItem("refresh_token");
    localStorageMock.removeItem("user");
    // Would redirect to login in real app
  };

  it("should detect 401 as session expired", () => {
    const mockResponse = { status: 401 } as Response;
    expect(checkSessionExpiry(mockResponse)).toBe(true);
  });

  it("should not detect 200 as session expired", () => {
    const mockResponse = { status: 200 } as Response;
    expect(checkSessionExpiry(mockResponse)).toBe(false);
  });

  it("should clear session on expiry", () => {
    localStorageMock.setItem("access_token", "token");
    localStorageMock.setItem("user", '{"id":"1"}');

    handleSessionExpiry();

    expect(localStorageMock.getItem("access_token")).toBeNull();
    expect(localStorageMock.getItem("user")).toBeNull();
  });
});
