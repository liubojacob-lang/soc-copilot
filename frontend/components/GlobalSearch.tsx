'use client';

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useLocale } from "next-intl";
import { Search, X, FileText, AlertTriangle, Play, Users, Settings, Link } from "lucide-react";

interface SearchResult {
  type: string;
  title: string;
  url: string;
  icon: React.ReactNode;
}

const NAV_ITEMS: SearchResult[] = [
  { type: "page", title: "Dashboard", url: "/", icon: <FileText className="w-4 h-4" /> },
  { type: "page", title: "Alerts", url: "/alerts", icon: <AlertTriangle className="w-4 h-4" /> },
  { type: "page", title: "Assets", url: "/assets", icon: <FileText className="w-4 h-4" /> },
  { type: "page", title: "Playbooks", url: "/playbooks", icon: <Play className="w-4 h-4" /> },
  { type: "page", title: "Triggers", url: "/triggers", icon: <Link className="w-4 h-4" /> },
  { type: "page", title: "Audit Logs", url: "/audit", icon: <FileText className="w-4 h-4" /> },
  { type: "page", title: "Reports", url: "/reports", icon: <FileText className="w-4 h-4" /> },
  { type: "page", title: "AI Assistant", url: "/ai-assistant", icon: <FileText className="w-4 h-4" /> },
  { type: "page", title: "Admin Users", url: "/admin/users", icon: <Users className="w-4 h-4" /> },
  { type: "page", title: "Settings", url: "/settings", icon: <Settings className="w-4 h-4" /> },
];

export function GlobalSearch() {
  const router = useRouter();
  const locale = useLocale();
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);

  const filteredItems = NAV_ITEMS.filter(item =>
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
    router.push(`/${locale}${url}`);
    setIsOpen(false);
    setQuery("");
  };

  const handleKeyNavigation = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex(i => (i + 1) % filteredItems.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex(i => (i - 1 + filteredItems.length) % filteredItems.length);
    } else if (e.key === "Enter" && filteredItems[selectedIndex]) {
      handleSelect(filteredItems[selectedIndex].url);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh]">
      <div 
        className="absolute inset-0 bg-black/50" 
        onClick={() => setIsOpen(false)}
      />
      <div className="relative w-full max-w-lg bg-white dark:bg-gray-800 rounded-lg shadow-2xl overflow-hidden">
        <div className="flex items-center border-b border-gray-200 dark:border-gray-700 p-3">
          <Search className="w-5 h-5 text-gray-400 mr-2" />
          <input
            type="text"
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyNavigation}
            placeholder="Search pages..."
            className="flex-1 bg-transparent outline-none text-gray-900 dark:text-white placeholder-gray-400"
          />
          <button
            onClick={() => setIsOpen(false)}
            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
          >
            <X className="w-4 h-4 text-gray-400" />
          </button>
        </div>
        
        {filteredItems.length > 0 && (
          <div className="max-h-80 overflow-y-auto py-2">
            {filteredItems.map((item, index) => (
              <button
                key={item.url}
                onClick={() => handleSelect(item.url)}
                className={`w-full flex items-center gap-3 px-4 py-2 text-left ${
                  index === selectedIndex 
                    ? "bg-blue-50 dark:bg-blue-900/30" 
                    : "hover:bg-gray-50 dark:hover:bg-gray-700/50"
                }`}
              >
                <span className="text-gray-400">{item.icon}</span>
                <span className="text-gray-900 dark:text-white">{item.title}</span>
                <span className="ml-auto text-xs text-gray-400 capitalize">{item.type}</span>
              </button>
            ))}
          </div>
        )}

        {filteredItems.length === 0 && query && (
          <div className="p-4 text-center text-gray-500">
            No results found
          </div>
        )}

        <div className="border-t border-gray-200 dark:border-gray-700 px-4 py-2 bg-gray-50 dark:bg-gray-800/50">
          <div className="flex gap-4 text-xs text-gray-400">
            <span><kbd className="px-1 py-0.5 bg-gray-200 dark:bg-gray-700 rounded">↑↓</kbd> Navigate</span>
            <span><kbd className="px-1 py-0.5 bg-gray-200 dark:bg-gray-700 rounded">↵</kbd> Select</span>
            <span><kbd className="px-1 py-0.5 bg-gray-200 dark:bg-gray-700 rounded">Esc</kbd> Close</span>
          </div>
        </div>
      </div>
    </div>
  );
}
