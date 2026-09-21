"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { useRouter } from "@/i18n/navigation";
import { useLocale, useTranslations } from "next-intl";
import { Search, X, FileText, AlertTriangle, Play, Users, Settings, Link } from "lucide-react";
import { isAdmin, loadAuthState } from "@/lib/auth";

interface SearchResult {
  type: string;
  title: string;
  url: string;
  icon: React.ReactNode;
}

export function GlobalSearch() {
  const router = useRouter();
  const locale = useLocale();
  const t = useTranslations("nav");
  const tCommon = useTranslations("common");

  // Use useMemo to create NAV_ITEMS with translations.
  // Admin-only destinations are filtered out for non-admin users — the
  // search must not leak pages the main navigation hides.
  const NAV_ITEMS: SearchResult[] = useMemo(() => {
    const base: SearchResult[] = [
      { type: "page", title: t("home"), url: "/", icon: <FileText className="w-4 h-4" /> },
      {
        type: "page",
        title: t("alerts"),
        url: "/alerts",
        icon: <AlertTriangle className="w-4 h-4" />,
      },
      {
        type: "page",
        title: t("assets") || "Assets",
        url: "/assets",
        icon: <FileText className="w-4 h-4" />,
      },
      { type: "page", title: t("runs"), url: "/playbooks", icon: <Play className="w-4 h-4" /> },
      { type: "page", title: t("triggers"), url: "/triggers", icon: <Link className="w-4 h-4" /> },
      { type: "page", title: t("audit"), url: "/audit", icon: <FileText className="w-4 h-4" /> },
      {
        type: "page",
        title: t("ai"),
        url: "/ai-assistant",
        icon: <FileText className="w-4 h-4" />,
      },
    ];
    if (!isAdmin(loadAuthState()?.user ?? null)) {
      return base;
    }
    return [
      ...base,
      {
        type: "page",
        title: t("users") || "Users",
        url: "/admin/users",
        icon: <Users className="w-4 h-4" />,
      },
      {
        type: "page",
        title: t("settings"),
        url: "/settings",
        icon: <Settings className="w-4 h-4" />,
      },
    ];
  }, [t, tCommon]);
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);

  const filteredItems = NAV_ITEMS.filter((item) =>
    item.title.toLowerCase().includes(query.toLowerCase())
  );

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "k") {
      e.preventDefault();
      setIsOpen(true);
    }
    if (e.key === "Escape") {
      setIsOpen(false);
    }
  }, []);

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  const handleSelect = (url: string) => {
    // The locale-aware router auto-prefixes the current locale; do not prepend /${locale}
    router.push(url);
    setIsOpen(false);
    setQuery("");
  };

  const handleKeyNavigation = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((i) => (i + 1) % (filteredItems.length || 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((i) => (i - 1 + filteredItems.length) % (filteredItems.length || 1));
    } else if (e.key === "Enter" && filteredItems[selectedIndex]) {
      handleSelect(filteredItems[selectedIndex].url);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[14vh] px-4 animate-fade-in">
      <div
        className="fixed inset-0 bg-black/50 dark:bg-black/70 backdrop-blur-sm transition-opacity"
        onClick={() => setIsOpen(false)}
      />
      <div className="relative w-full max-w-xl bg-surface-card border border-border-subtle rounded-2xl shadow-elevated overflow-hidden z-10">
        <div className="flex items-center gap-3 px-4 py-3.5 border-b border-border-subtle">
          <Search className="w-4 h-4 text-text-tertiary shrink-0" />
          <input
            type="text"
            autoFocus
            aria-label="Command search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyNavigation}
            placeholder="Search pages, tools, and actions..."
            className="flex-1 bg-transparent outline-none text-sm text-text-primary placeholder:text-text-tertiary"
          />
          <kbd className="hidden sm:inline-flex items-center px-1.5 py-0.5 text-[10px] font-mono text-text-tertiary bg-surface-hover border border-border-subtle rounded">
            ESC
          </kbd>
          <button
            onClick={() => setIsOpen(false)}
            className="p-1 rounded-md text-text-tertiary hover:text-text-primary hover:bg-surface-hover transition-colors sm:hidden"
            aria-label="Close search"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {filteredItems.length > 0 && (
          <div className="max-h-80 overflow-y-auto p-2 space-y-1 custom-scrollbar">
            <div className="px-2 py-1 text-[11px] font-semibold text-text-tertiary uppercase tracking-wider">
              Navigation
            </div>
            {filteredItems.map((item, index) => (
              <button
                key={item.url}
                onClick={() => handleSelect(item.url)}
                className={`w-full flex items-center gap-3 px-3 py-2 text-left text-xs sm:text-sm rounded-lg transition-colors ${
                  index === selectedIndex
                    ? "bg-accent-600 text-white font-medium"
                    : "text-text-secondary hover:bg-surface-hover hover:text-text-primary"
                }`}
              >
                <span className={index === selectedIndex ? "text-white" : "text-text-tertiary"}>
                  {item.icon}
                </span>
                <span className="truncate">{item.title}</span>
                <span
                  className={`ml-auto text-[11px] font-mono ${
                    index === selectedIndex ? "text-white/80" : "text-text-tertiary"
                  }`}
                >
                  {item.url}
                </span>
              </button>
            ))}
          </div>
        )}

        {filteredItems.length === 0 && query && (
          <div className="py-10 px-4 text-center">
            <p className="text-sm text-text-secondary">
              No matching results for &ldquo;{query}&rdquo;
            </p>
            <p className="text-xs text-text-tertiary mt-1">
              Try searching for alerts, playbooks, or settings
            </p>
          </div>
        )}

        <div className="border-t border-border-subtle px-4 py-2 bg-surface-hover/50 flex items-center justify-between text-[11px] text-text-tertiary">
          <div className="flex items-center gap-3">
            <span>
              <kbd className="px-1.5 py-0.5 font-mono bg-surface-card border border-border-subtle rounded">
                ↑↓
              </kbd>{" "}
              Navigate
            </span>
            <span>
              <kbd className="px-1.5 py-0.5 font-mono bg-surface-card border border-border-subtle rounded">
                ↵
              </kbd>{" "}
              Open
            </span>
          </div>
          <span>SOC Copilot Command</span>
        </div>
      </div>
    </div>
  );
}
