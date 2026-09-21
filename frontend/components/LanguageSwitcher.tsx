"use client";

import { useLocale, useTranslations } from "next-intl";
import { usePathname, useRouter } from "@/i18n/navigation";
import { useState, useEffect, useCallback } from "react";
import { i18nCache } from "@/lib/i18n-cache";
import { getRequiredNamespaces } from "@/i18n/namespaces";

type LocaleCode = "en" | "zh-CN";

const LOCALES: { code: LocaleCode; label: string }[] = [
  { code: "zh-CN", label: "中文" },
  { code: "en", label: "EN" },
];

export function LanguageSwitcher() {
  const locale = useLocale() as LocaleCode;
  const tLanguage = useTranslations("common.language");
  const router = useRouter();
  const pathname = usePathname();
  const [isSwitching, setIsSwitching] = useState(false);

  // Preload the other locale in the background for instant switching
  useEffect(() => {
    const otherLocale: LocaleCode = locale === "en" ? "zh-CN" : "en";
    const namespaces = getRequiredNamespaces(pathname);

    i18nCache.preloadLocale(otherLocale, namespaces).catch(() => {});
  }, [locale, pathname]);

  const switchLocale = useCallback(
    async (newLocale: LocaleCode) => {
      if (isSwitching || newLocale === locale) return;

      setIsSwitching(true);

      try {
        // `replace` keeps the current path and swaps only the locale prefix.
        router.replace(pathname, { locale: newLocale });
      } catch (error) {
        console.error("Language switch failed:", error);
      } finally {
        setTimeout(() => setIsSwitching(false), 250);
      }
    },
    [isSwitching, locale, router, pathname]
  );

  return (
    <div
      data-testid="lang-switcher"
      className="inline-flex items-center p-0.5 rounded-lg bg-gray-100 dark:bg-gray-800/80 border border-gray-200/80 dark:border-gray-700/80 text-xs font-medium select-none shadow-subtle shrink-0 whitespace-nowrap"
      role="radiogroup"
      aria-label={tLanguage("switch")}
    >
      {LOCALES.map(({ code, label }) => {
        const isActive = locale === code;
        return (
          <button
            key={code}
            type="button"
            role="radio"
            aria-checked={isActive}
            disabled={isSwitching}
            onClick={() => switchLocale(code)}
            className={`
              relative inline-flex items-center justify-center min-h-[24px] min-w-[2.25rem] px-2.5 py-1 rounded-md text-xs transition-all duration-200 font-medium whitespace-nowrap shrink-0 leading-none
              ${
                isActive
                  ? "bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-subtle font-semibold"
                  : // 未激活态的 text-gray-500 落在 bg-gray-100 底上只有 4.39:1（低于 AA）。
                    // 这个组件出现在每一个页面顶部，是全站影响面最大的一处不达标。
                    // 改用 text-text-secondary：与该底色 9.45:1，且在深色下自动切到对应的次级色。
                    // 与激活态的区分不靠"颜色更淡"，而靠白底 + font-semibold（视觉层级更稳）。
                    "text-text-secondary hover:text-text-primary hover:bg-black/[0.03] dark:hover:bg-white/[0.03]"
              }
              ${isSwitching ? "opacity-60 cursor-wait" : "cursor-pointer"}
            `}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}
