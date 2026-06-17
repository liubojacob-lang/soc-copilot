/**
 * Authentication Store
 * Reactive layer on top of lib/auth.ts.
 * lib/auth.ts is the single source of truth for token storage.
 *
 * NOTE: usePermission hook is the only consumer of this store.
 * If zustand is added later, this can be converted to a Zustand store.
 */

import { useSyncExternalStore } from "react";
import {
  login as authLogin,
  logout as authLogout,
  loadAuthState,
  saveAuthState,
  refreshAccessToken as authRefresh,
  getCurrentUser,
  type User,
  type AuthState,
} from "@/lib/auth";

export type { User } from "@/lib/auth";

interface StoreState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

type Listener = () => void;

let state: StoreState = {
  user: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,
};

const listeners = new Set<Listener>();

function setState(patch: Partial<StoreState>) {
  state = { ...state, ...patch };
  listeners.forEach((l) => l());
}

function subscribe(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function getSnapshot(): StoreState {
  return state;
}

/** Initialize from lib/auth.ts persisted state (call once at app mount) */
export function hydrateAuthStore(): void {
  const auth = loadAuthState();
  if (auth?.isAuthenticated && auth.user) {
    setState({ user: auth.user, isAuthenticated: true });
  }
}

export async function login(username: string, password: string): Promise<void> {
  setState({ isLoading: true, error: null });
  try {
    const authState: AuthState = await authLogin(username, password);
    setState({
      user: authState.user,
      isAuthenticated: authState.isAuthenticated,
      isLoading: false,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Login failed";
    setState({ user: null, isAuthenticated: false, isLoading: false, error: message });
    throw error;
  }
}

export async function logoutAction(): Promise<void> {
  authLogout();
  setState({ user: null, isAuthenticated: false, isLoading: false, error: null });
  if (typeof window !== "undefined") {
    window.location.href = "/login";
  }
}

export async function refreshToken(): Promise<void> {
  if (!state.isAuthenticated) return;
  try {
    const storedRefresh = localStorage.getItem("refresh_token");
    if (!storedRefresh) throw new Error("No refresh token");
    const authState = await authRefresh(storedRefresh);
    if (authState.isAuthenticated) {
      saveAuthState(authState);
      setState({ user: authState.user, isAuthenticated: true });
    } else {
      await logoutAction();
    }
  } catch {
    await logoutAction();
  }
}

export async function fetchUser(): Promise<void> {
  if (!state.isAuthenticated) return;
  try {
    const user = await getCurrentUser();
    setState({ user });
  } catch {
    await logoutAction();
  }
}

export function clearError(): void {
  setState({ error: null });
}

/**
 * useAuthStore hook — React useSyncExternalStore compatible.
 * Replaces the previous Zustand-based implementation.
 */
export function useAuthStore(): StoreState {
  return useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
}

export const selectUser = (s: StoreState) => s.user;
export const selectIsAuthenticated = (s: StoreState) => s.isAuthenticated;
export const selectIsAdmin = (s: StoreState) => s.user?.role === "admin";
export const selectCanWrite = (s: StoreState) =>
  s.user?.role === "admin" || s.user?.role === "analyst";
export const selectPermissions = (s: StoreState) => s.user?.permissions ?? [];
