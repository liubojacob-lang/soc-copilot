/**
 * Keyboard shortcuts hook for global keyboard navigation
 *
 * Usage:
 * useKeyboardShortcuts({
 *   'r': () => handleRefresh(),
 *   'n': () => handleNew(),
 *   '/': () => handleSearch(),
 *   'Escape': () => handleClose(),
 * }, { enabled: !isModalOpen });
 */

import { useEffect, useCallback } from "react";

export interface KeyboardShortcut {
  key: string;
  handler: () => void;
  description?: string;
}

interface UseKeyboardShortcutsOptions {
  enabled?: boolean;
  preventDefault?: string[];
}

export function useKeyboardShortcuts(
  shortcuts: Record<string, () => void>,
  options: UseKeyboardShortcutsOptions = {}
) {
  const { enabled = true, preventDefault = [] } = options;

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (!enabled) return;

      // Don't trigger shortcuts when typing in input fields
      const target = event.target as HTMLElement;
      const isInput =
        target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable;

      // Allow some shortcuts even in input fields
      const allowedInInput = ["Escape", "Meta+Enter", "Ctrl+Enter"];
      const shouldAllow = allowedInInput.some((s) => {
        const [key, mod] = s.split("+");
        if (mod === "Meta" && !event.metaKey) return false;
        if (mod === "Ctrl" && !event.ctrlKey) return false;
        return event.key === key;
      });

      if (isInput && !shouldAllow) return;

      // Check for shortcut
      const key = event.key;
      const modifier = event.metaKey || event.ctrlKey ? "Meta+" : "";
      const shortcutKey = modifier + key;

      if (shortcuts[shortcutKey] || shortcuts[key]) {
        if (preventDefault.includes(shortcutKey) || preventDefault.includes(key)) {
          event.preventDefault();
        }
        (shortcuts[shortcutKey] || shortcuts[key])();
      }
    },
    [shortcuts, enabled, preventDefault]
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);
}

/**
 * Common keyboard shortcuts for the application
 */
export const COMMON_SHORTCUTS = {
  r: "Refresh",
  n: "New/Create",
  e: "Edit",
  d: "Delete",
  "/": "Search",
  Escape: "Close/Cancel",
  "Meta+k": "Command palette",
  "Ctrl+k": "Command palette",
};

/**
 * Get keyboard shortcut display string
 */
export function getShortcutDisplay(key: string): string {
  const isMac = typeof navigator !== "undefined" && /Mac/.test(navigator.platform);
  const mod = isMac ? "⌘" : "Ctrl";

  return key
    .replace("Meta+", mod + "+")
    .replace("Ctrl+", mod + "+")
    .replace("Escape", "Esc");
}
