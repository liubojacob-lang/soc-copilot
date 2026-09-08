/**
 * Authentication Store — Zustand + persist (v1.0 migration)
 * Migrated from useSyncExternalStore to Zustand for consistent state management.
 * lib/auth.ts remains the single source of truth for token storage.
 *
 * Key changes from legacy implementation:
 * - useSyncExternalStore → Zustand create() + persist middleware
 * - login/logout/hydrate now use store.setState() directly
 * - Selectors use standard Zustand pattern (s => s.user)
 * - Clearer separation: store state vs lib/auth.js token persistence
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";
import {
  login as authLogin,
  logout as authLogout,
  loadAuthState,
  refreshAccessToken as authRefresh,
  getCurrentUser,
  type User,
} from "@/lib/auth";

export type { User } from "@/lib/auth";

// ── State interface ──
interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

interface AuthActions {
  login: (username: string, password: string) => Promise<void>;
  logoutAction: () => Promise<void>;
  refreshToken: () => Promise<void>;
  fetchUser: () => Promise<void>;
  hydrateFromStorage: () => void;
  clearError: () => void;
}

type AuthStore = AuthState & AuthActions;

// ── Store ──
export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      // -- State --
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      // -- Actions --

      /** Initialize from lib/auth.ts persisted state (call once at app mount) */
      hydrateFromStorage: () => {
        const auth = loadAuthState();
        if (auth?.isAuthenticated && auth.user) {
          set({ user: auth.user, isAuthenticated: true });
        }
      },

      login: async (username: string, password: string) => {
        set({ isLoading: true, error: null });
        try {
          const authState = await authLogin(username, password);
          set({
            user: authState.user,
            isAuthenticated: authState.isAuthenticated,
            isLoading: false,
          });
        } catch (error) {
          const message = error instanceof Error ? error.message : "Login failed";
          set({ user: null, isAuthenticated: false, isLoading: false, error: message });
          throw error;
        }
      },

      logoutAction: async () => {
        authLogout();
        set({ user: null, isAuthenticated: false, isLoading: false, error: null });
        if (typeof window !== "undefined") {
          window.location.href = "/login";
        }
      },

      refreshToken: async () => {
        const { isAuthenticated, logoutAction: doLogout } = get();
        if (!isAuthenticated) return;
        try {
          const authState = await authRefresh();
          if (authState.isAuthenticated) {
            set({ user: authState.user, isAuthenticated: true });
          } else {
            await doLogout();
          }
        } catch {
          await doLogout();
        }
      },

      fetchUser: async () => {
        const { isAuthenticated, logoutAction: doLogout } = get();
        if (!isAuthenticated) return;
        try {
          const user = await getCurrentUser();
          set({ user });
        } catch {
          await doLogout();
        }
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: "auth-storage",
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);

// ── Selectors ──
export const selectUser = (s: AuthState) => s.user;
export const selectIsAuthenticated = (s: AuthState) => s.isAuthenticated;
export const selectIsAdmin = (s: AuthState) => s.user?.role === "admin";
export const selectCanWrite = (s: AuthState) =>
  s.user?.role === "admin" || s.user?.role === "analyst";
export const selectPermissions = (s: AuthState) => s.user?.permissions ?? [];
