"use client";

import { useEffect, useCallback, useState } from "react";
import { useTranslations } from "next-intl";
import { X, Keyboard } from "lucide-react";

interface ShortcutItem {
  key: string;
  descriptionKey: string;
  categoryKey: string;
}

const SHORTCUTS: ShortcutItem[] = [
  { key: "r", descriptionKey: "items.refreshPage", categoryKey: "categories.general" },
  { key: "/", descriptionKey: "items.focusSearch", categoryKey: "categories.general" },
  { key: "Escape", descriptionKey: "items.closeDialog", categoryKey: "categories.general" },
  { key: "?", descriptionKey: "items.showHelp", categoryKey: "categories.general" },
  { key: "⌘/Ctrl + K", descriptionKey: "items.openSearch", categoryKey: "categories.general" },
  { key: "⌘/Ctrl + B", descriptionKey: "items.toggleSidebar", categoryKey: "categories.general" },
  { key: "1", descriptionKey: "items.tabAlerts", categoryKey: "categories.home" },
  { key: "2", descriptionKey: "items.tabTimeline", categoryKey: "categories.home" },
  { key: "3", descriptionKey: "items.tabReports", categoryKey: "categories.home" },
  { key: "4", descriptionKey: "items.tabAssets", categoryKey: "categories.home" },
];

export function KeyboardShortcutsHelp() {
  const t = useTranslations("shortcuts");
  const [isOpen, setIsOpen] = useState(false);

  const handleClose = useCallback(() => {
    setIsOpen(false);
  }, []);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "?" && !e.ctrlKey && !e.metaKey) {
        const activeElement = document.activeElement;
        if (activeElement?.tagName !== "INPUT" && activeElement?.tagName !== "TEXTAREA") {
          e.preventDefault();
          setIsOpen((prev) => !prev);
        }
      }
      if (e.key === "Escape" && isOpen) {
        setIsOpen(false);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen]);

  if (!isOpen) return null;

  const groupedShortcuts = SHORTCUTS.reduce(
    (acc, shortcut) => {
      const category = t(shortcut.categoryKey);
      if (!acc[category]) acc[category] = [];
      acc[category].push(shortcut);
      return acc;
    },
    {} as Record<string, ShortcutItem[]>
  );

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={handleClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="shortcuts-title"
    >
      <div
        className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-lg w-full mx-4 overflow-hidden animate-fade-in"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2">
            <Keyboard className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            <h2
              id="shortcuts-title"
              className="text-lg font-semibold text-gray-900 dark:text-white"
            >
              {t("title")}
            </h2>
          </div>
          <button
            onClick={handleClose}
            className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            aria-label={t("close")}
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        <div className="p-4 max-h-[60vh] overflow-y-auto">
          {Object.entries(groupedShortcuts).map(([category, shortcuts]) => (
            <div key={category} className="mb-4 last:mb-0">
              <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
                {category}
              </h3>
              <div className="space-y-2">
                {shortcuts.map((shortcut, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between py-1.5 px-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50"
                  >
                    <span className="text-sm text-gray-700 dark:text-gray-300">
                      {t(shortcut.descriptionKey)}
                    </span>
                    <kbd className="px-2 py-1 text-xs font-mono bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded border border-gray-200 dark:border-gray-600">
                      {shortcut.key}
                    </kbd>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="p-3 bg-gray-50 dark:bg-gray-900/50 border-t border-gray-200 dark:border-gray-700">
          <p className="text-xs text-gray-500 dark:text-gray-400 text-center">
            {t.rich("footer", {
              kbd: (chunks) => (
                <kbd className="px-1.5 py-0.5 text-xs font-mono bg-gray-200 dark:bg-gray-700 rounded">
                  {chunks}
                </kbd>
              ),
            })}
          </p>
        </div>
      </div>
    </div>
  );
}
