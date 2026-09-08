import { defineRouting } from "next-intl/routing";

/**
 * Single source of truth for i18n routing.
 *
 * - `zh-CN` is the default locale; every URL carries an explicit prefix
 *   (`localePrefix: "always"`, e.g. `/zh-CN/alerts`, `/en/alerts`).
 * - `/` is redirected by `middleware.ts` based on the `NEXT_LOCALE` cookie
 *   or the `Accept-Language` header.
 */
export const routing = defineRouting({
  locales: ["zh-CN", "en"],
  defaultLocale: "zh-CN",
  localePrefix: "always",
  localeDetection: true,
});

export type Locale = (typeof routing.locales)[number];

export const locales = routing.locales;
export const defaultLocale = routing.defaultLocale;
