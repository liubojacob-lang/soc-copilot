import { hasLocale } from "next-intl";
import { getRequestConfig } from "next-intl/server";
import { notFound } from "next/navigation";

import { routing } from "./routing";

export type Locale = (typeof routing.locales)[number];
export const locales = routing.locales;

/**
 * Loads the message catalog for a locale. `messages/<locale>.json` is the
 * authoritative single-file catalog; per-namespace files under
 * `messages/<locale>/` only serve the client-side preloader
 * (`lib/i18n-cache.ts`).
 */
async function loadAllMessages(locale: Locale) {
  try {
    const messages = await import(`../messages/${locale}.json`);
    return messages.default;
  } catch {
    const fallback = await import("../messages/zh-CN.json");
    return fallback.default;
  }
}

export default getRequestConfig(async ({ requestLocale }) => {
  const requested = await requestLocale;

  if (!hasLocale(routing.locales, requested)) {
    notFound();
  }

  return {
    locale: requested,
    messages: await loadAllMessages(requested),
  };
});
