/**
 * Theme Store
 * Manages light/dark mode theme preference
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";

type Theme = "light" | "dark" | "system";

interface ThemeState {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  getEffectiveTheme: () => "light" | "dark";
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      theme: "system",

      setTheme: (theme: Theme) => {
        set({ theme });

        // Apply theme to document
        if (typeof document !== "undefined") {
          const effectiveTheme = getEffectiveTheme(theme);
          document.documentElement.classList.remove("light", "dark");
          document.documentElement.classList.add(effectiveTheme);
        }
      },

      getEffectiveTheme: () => {
        const { theme } = get();

        if (theme === "system") {
          // Check system preference
          if (typeof window !== "undefined" && window.matchMedia) {
            return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
          }
          return "light";
        }

        return theme;
      },
    }),
    {
      name: "theme-storage",
    }
  )
);

// Helper function to get effective theme
function getEffectiveTheme(theme: Theme): "light" | "dark" {
  if (theme === "system") {
    if (typeof window !== "undefined" && window.matchMedia) {
      return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    }
    return "light";
  }
  return theme;
}

// Initialize theme on app load
if (typeof document !== "undefined") {
  const storedTheme = localStorage.getItem("theme-storage");
  if (storedTheme) {
    const theme = JSON.parse(storedTheme).state.theme;
    const effectiveTheme = getEffectiveTheme(theme);
    document.documentElement.classList.remove("light", "dark");
    document.documentElement.classList.add(effectiveTheme);
  }
}
