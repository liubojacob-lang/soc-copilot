"use client";

import { useEffect, useState } from "react";
import { Sun, Moon } from "lucide-react";
import { useThemeStore } from "@/stores/themeStore";

export function ThemeToggle() {
  const theme = useThemeStore((state) => state.theme);
  const getResolvedTheme = useThemeStore((state) => state.getResolvedTheme);
  const toggleTheme = useThemeStore((state) => state.toggleTheme);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Prevent hydration mismatch: render a neutral placeholder until mounted
  if (!mounted) {
    return (
      <button
        className="p-2 text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors opacity-50 shrink-0"
        aria-label="Loading theme toggle"
        disabled
      >
        <Sun className="w-5 h-5" strokeWidth={1.5} />
      </button>
    );
  }

  const resolvedTheme = getResolvedTheme();

  return (
    <button
      onClick={toggleTheme}
      className="p-2 text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors shrink-0"
      title={resolvedTheme === "light" ? "Switch to dark mode" : "Switch to light mode"}
      aria-label={resolvedTheme === "light" ? "Switch to dark mode" : "Switch to light mode"}
    >
      {resolvedTheme === "light" ? (
        <Moon className="w-5 h-5" strokeWidth={1.5} />
      ) : (
        <Sun className="w-5 h-5" strokeWidth={1.5} />
      )}
    </button>
  );
}
