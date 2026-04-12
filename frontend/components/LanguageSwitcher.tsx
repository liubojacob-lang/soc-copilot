"use client";

import { useLocale } from "next-intl";
import { useRouter, usePathname } from "@/i18n/routing";
import { Check, ChevronDown, Loader2 } from "lucide-react";
import { useState, useEffect, useRef, useCallback } from "react";
import { i18nCache } from "@/lib/i18n-cache";
import { getRequiredNamespaces } from "@/i18n/namespaces";

type LocaleCode = "en" | "zh";

const locales: { code: LocaleCode; label: string; flag: string }[] = [
  { code: "en", label: "English", flag: "EN" },
  { code: "zh", label: "中文", flag: "中" },
];

export function LanguageSwitcher() {
  const locale = useLocale() as LocaleCode;
  const router = useRouter();
  const pathname = usePathname();
  const [isOpen, setIsOpen] = useState(false);
  const [isSwitching, setIsSwitching] = useState(false);
  const [preloadStatus, setPreloadStatus] = useState<Record<string, boolean>>({});
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const otherLocale = locale === "en" ? "zh" : "en";
    const namespaces = getRequiredNamespaces(pathname);

    i18nCache.preloadLocale(otherLocale, namespaces).then(() => {
      setPreloadStatus((prev) => ({ ...prev, [otherLocale]: true }));
    });
  }, [locale, pathname]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        setIsOpen(false);
      }
    };

    window.addEventListener("keydown", handleKeyPress);
    return () => window.removeEventListener("keydown", handleKeyPress);
  }, [isOpen]);

  const switchLocale = useCallback(
    async (newLocale: LocaleCode) => {
      if (isSwitching || newLocale === locale) return;

      setIsSwitching(true);

      try {
        document.cookie = `NEXT_LOCALE=${newLocale};path=/;max-age=${60 * 60 * 24 * 365};SameSite=lax`;

        const namespaces = getRequiredNamespaces(pathname);
        await i18nCache.switchLocale(newLocale);

        router.push(pathname, { locale: newLocale });
        setIsOpen(false);
      } catch (error) {
        console.error("Language switch failed:", error);
      } finally {
        setTimeout(() => setIsSwitching(false), 300);
      }
    },
    [isSwitching, locale, router, pathname]
  );

  const currentLocale = locales.find((l) => l.code === locale);

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={isSwitching}
        className={`
          flex items-center gap-1 px-2 py-1.5 text-xs rounded transition-all duration-200
          ${
            isOpen
              ? "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300 font-medium"
              : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
          }
          ${isSwitching ? "opacity-50 cursor-wait" : ""}
        `}
        aria-label="Switch language"
        aria-expanded={isOpen}
        aria-haspopup="listbox"
      >
        {isSwitching ? (
          <Loader2 className="w-3 h-3 animate-spin" />
        ) : (
          <span className="font-medium">{currentLocale?.flag}</span>
        )}
        <ChevronDown
          className={`w-3 h-3 transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`}
        />
      </button>

      {isOpen && (
        <>
          <div className="fixed inset-0 z-40 lg:hidden" onClick={() => setIsOpen(false)} />

          <div
            className="absolute right-0 mt-1 w-32 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-50 py-1"
            role="listbox"
            aria-label="Language options"
          >
            {locales.map(({ code, label, flag }) => {
              const isActive = locale === code;
              const isPreloaded = preloadStatus[code];

              return (
                <button
                  key={code}
                  onClick={() => switchLocale(code)}
                  disabled={isSwitching || isActive}
                  className={`
                    w-full flex items-center gap-2 px-3 py-2 text-xs transition-colors
                    ${
                      isActive
                        ? "bg-blue-50 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300"
                        : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                    }
                    ${isSwitching ? "opacity-50 cursor-not-allowed" : ""}
                  `}
                  role="option"
                  aria-selected={isActive}
                >
                  <span className="w-4 text-center font-medium">{flag}</span>
                  <span className="flex-1 text-left">{label}</span>
                  {isActive && <Check className="w-3 h-3" />}
                  {isPreloaded && !isActive && (
                    <span className="w-2 h-2 rounded-full bg-green-400" title="Preloaded" />
                  )}
                </button>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
