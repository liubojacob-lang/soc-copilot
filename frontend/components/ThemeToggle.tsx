"use client";

import { useEffect, useState } from "react";
import { Sun, Moon, Monitor } from "lucide-react";
import { useTranslations } from "next-intl";
import { useThemeStore, type Theme } from "@/stores/themeStore";

interface ThemeOption {
  value: Theme;
  labelKey: "light" | "dark" | "system";
  icon: React.ComponentType<{ className?: string; strokeWidth?: number }>;
}

const THEME_OPTIONS: ThemeOption[] = [
  { value: "light", labelKey: "light", icon: Sun },
  { value: "dark", labelKey: "dark", icon: Moon },
  { value: "system", labelKey: "system", icon: Monitor },
];

export function ThemeToggle() {
  const theme = useThemeStore((state) => state.theme);
  const setTheme = useThemeStore((state) => state.setTheme);
  const tTheme = useTranslations("common.theme");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Prevent hydration mismatch: render neutral placeholder container with exact matching size
  if (!mounted) {
    return (
      <div
        className="inline-flex items-center p-0.5 rounded-lg bg-gray-100 dark:bg-gray-800/80 border border-gray-200/80 dark:border-gray-700/80 h-7 w-[5.5rem] opacity-50 shrink-0"
        aria-hidden="true"
      />
    );
  }

  return (
    <div
      className="inline-flex items-center p-0.5 rounded-lg bg-gray-100 dark:bg-gray-800/80 border border-gray-200/80 dark:border-gray-700/80 text-xs font-medium select-none shadow-subtle shrink-0 whitespace-nowrap"
      role="radiogroup"
      aria-label={tTheme("toggle")}
    >
      {THEME_OPTIONS.map(({ value, labelKey, icon: Icon }) => {
        const isActive = theme === value;
        const label = tTheme(labelKey);

        return (
          <button
            key={value}
            type="button"
            role="radio"
            aria-checked={isActive}
            onClick={() => setTheme(value)}
            title={label}
            aria-label={label}
            className={`
              relative inline-flex items-center justify-center p-1.5 rounded-md text-xs transition-all duration-200 shrink-0 leading-none
              ${
                isActive
                  ? "bg-white dark:bg-gray-700 text-accent-600 dark:text-accent-400 shadow-subtle font-semibold"
                  : "text-gray-400 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-black/[0.03] dark:hover:bg-white/[0.03]"
              }
            `}
          >
            <Icon className="w-3.5 h-3.5" strokeWidth={isActive ? 2 : 1.75} />
          </button>
        );
      })}
    </div>
  );
}
