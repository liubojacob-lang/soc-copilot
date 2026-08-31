/**
 * Theme Store
 * Manages light/dark/system theme preference with resolvedTheme support
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";

export type Theme = "light" | "dark" | "system";

interface ThemeState {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
  getResolvedTheme: () => "light" | "dark";
}

const STORAGE_KEY = "theme-storage";

function getSystemTheme(): "light" | "dark" {
  if (typeof window === "undefined") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function getResolvedTheme(theme: Theme): "light" | "dark" {
  if (theme === "system") return getSystemTheme();
  return theme;
}

function applyThemeClass(theme: Theme) {
  if (typeof document === "undefined") return;
  const resolved = getResolvedTheme(theme);
  const root = document.documentElement;
  root.classList.remove("light", "dark");
  root.classList.add(resolved);
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      theme: "system",

      setTheme: (theme: Theme) => {
        set({ theme });
        applyThemeClass(theme);
      },

      toggleTheme: () => {
        const current = get().getResolvedTheme();
        const next = current === "light" ? "dark" : "light";
        set({ theme: next });
        applyThemeClass(next);
      },

      getResolvedTheme: () => {
        return getResolvedTheme(get().theme);
      },
    }),
    {
      name: STORAGE_KEY,
      onRehydrateStorage: () => (state) => {
        if (state) {
          applyThemeClass(state.theme);
        }
      },
    }
  )
);

// Listen to system preference changes
if (typeof window !== "undefined") {
  const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
  mediaQuery.addEventListener("change", () => {
    const store = useThemeStore.getState();
    if (store.theme === "system") {
      applyThemeClass("system");
    }
  });
}
