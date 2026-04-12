/**
 * Authentication Store
 * Manages user authentication state using Zustand
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";

interface User {
  id: string;
  username: string;
  email: string;
  role: "admin" | "analyst" | "auditor";
  is_active: boolean;
  permissions?: string[];
}

interface AuthState {
  // State
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  // Actions
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<void>;
  fetchUser: () => Promise<void>;
  clearError: () => void;
}

// Helper to get auth headers
function getAuthHeaders(token?: string): Record<string, string> {
  const accessToken = token || localStorage.getItem("access_token");
  if (!accessToken) return {};
  return { Authorization: `Bearer ${accessToken}` };
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // Initial state
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      // Login action
      login: async (username: string, password: string) => {
        set({ isLoading: true, error: null });

        try {
          const response = await fetch("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password }),
          });

          if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Login failed");
          }

          const data = await response.json();

          set({
            user: data.user,
            token: data.access_token,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });

          // Store token in localStorage
          localStorage.setItem("access_token", data.access_token);
          if (data.refresh_token) {
            localStorage.setItem("refresh_token", data.refresh_token);
          }

          // Handle forced password change
          if (data.must_change_password) {
            // Redirect to password change page
            if (typeof window !== "undefined") {
              window.location.href = "/change-password";
            }
          }
        } catch (error) {
          const message = error instanceof Error ? error.message : "Login failed";
          set({
            user: null,
            token: null,
            isAuthenticated: false,
            isLoading: false,
            error: message,
          });
          throw error;
        }
      },

      // Logout action
      logout: async () => {
        set({ isLoading: true });

        try {
          const { token } = get();
          await fetch("/api/auth/logout", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              ...getAuthHeaders(token || undefined),
            },
          });
        } catch (error) {
          // Continue with logout even if API call fails
          console.error("Logout error:", error);
        } finally {
          // Clear tokens from localStorage
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");

          set({
            user: null,
            token: null,
            isAuthenticated: false,
            isLoading: false,
            error: null,
          });

          // Redirect to login
          if (typeof window !== "undefined") {
            window.location.href = "/login";
          }
        }
      },

      // Refresh token action
      refreshToken: async () => {
        try {
          const refreshToken = localStorage.getItem("refresh_token");
          if (!refreshToken) {
            throw new Error("No refresh token");
          }

          const response = await fetch("/api/auth/refresh", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ refresh_token: refreshToken }),
          });

          if (!response.ok) {
            throw new Error("Token refresh failed");
          }

          const data = await response.json();

          localStorage.setItem("access_token", data.access_token);
          if (data.refresh_token) {
            localStorage.setItem("refresh_token", data.refresh_token);
          }

          set({
            user: data.user,
            token: data.access_token,
            isAuthenticated: true,
          });
        } catch (error) {
          // Refresh failed, logout
          await get().logout();
          throw error;
        }
      },

      // Fetch current user
      fetchUser: async () => {
        const { isAuthenticated, token } = get();

        if (!isAuthenticated) {
          return;
        }

        try {
          const response = await fetch("/api/auth/me", {
            headers: getAuthHeaders(token || undefined),
          });

          if (!response.ok) {
            throw new Error("Failed to fetch user");
          }

          const user = await response.json();
          set({ user });
        } catch (error) {
          // Failed to fetch user, might be token expired
          await get().logout();
        }
      },

      // Clear error
      clearError: () => {
        set({ error: null });
      },
    }),
    {
      name: "auth-storage",
      // Only persist essential data
      partialize: (state) => ({
        token: state.token,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);

// Selectors for common use cases
export const selectUser = (state: AuthState) => state.user;
export const selectIsAuthenticated = (state: AuthState) => state.isAuthenticated;
export const selectIsAdmin = (state: AuthState) => state.user?.role === "admin";
export const selectCanWrite = (state: AuthState) =>
  state.user?.role === "admin" || state.user?.role === "analyst";
export const selectPermissions = (state: AuthState) => state.user?.permissions || [];
