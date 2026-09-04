"use client";

import { useEffect } from "react";
import { useLocale } from "next-intl";
import { applyThemeClass, useThemeStore } from "@/stores/themeStore";

/**
 * Locale switches re-render the <html> element, which wipes the theme class
 * applied earlier by the inline theme-init script (React removes attributes
 * that are not in its vdom). Re-apply the class whenever the locale changes;
 * the mount run also re-asserts it right after hydration.
 */
export function ThemeClassSync() {
  const locale = useLocale();

  useEffect(() => {
    applyThemeClass(useThemeStore.getState().theme);
  }, [locale]);

  return null;
}
