/**
 * Authentication Store
 * Manages user authentication state using Zustand
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { authApi } from '@/lib/api';

interface User {
  id: string;
  username: string;
  email: string;
  role: 'admin' | 'analyst' | 'auditor';
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
          const response = await authApi.login({ username, password });

          set({
            user: response.user,
            token: response.access_token,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });

          // Handle forced password change
          if (response.must_change_password) {
            // Redirect to password change page
            if (typeof window !== 'undefined') {
              window.location.href = '/change-password';
            }
          }
        } catch (error) {
          const message = error instanceof Error ? error.message : 'Login failed';
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
          await authApi.logout();
        } catch (error) {
          // Continue with logout even if API call fails
          console.error('Logout error:', error);
        } finally {
          set({
            user: null,
            token: null,
            isAuthenticated: false,
            isLoading: false,
            error: null,
          });

          // Redirect to login
          if (typeof window !== 'undefined') {
            window.location.href = '/login';
          }
        }
      },

      // Refresh token action
      refreshToken: async () => {
        try {
          const response = await authApi.refreshToken();

          set({
            user: response.user,
            token: response.access_token,
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
        const { isAuthenticated } = get();

        if (!isAuthenticated) {
          return;
        }

        try {
          const user = await authApi.getCurrentUser();
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
      name: 'auth-storage',
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
export const selectIsAdmin = (state: AuthState) => state.user?.role === 'admin';
export const selectCanWrite = (state: AuthState) =>
  state.user?.role === 'admin' || state.user?.role === 'analyst';
export const selectPermissions = (state: AuthState) => state.user?.permissions || [];
