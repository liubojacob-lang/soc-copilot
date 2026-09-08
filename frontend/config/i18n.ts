/**
 * Shared i18n configuration for the application.
 *
 * The routing itself (locales/default/prefix) is owned by `i18n/routing.ts`;
 * this file only carries display metadata consumed by UI helpers.
 */

import { routing, type Locale } from "@/i18n/routing";

export const i18nConfig = {
  locales: routing.locales,

  defaultLocale: routing.defaultLocale,

  // Fallback locale to use when a translation key is missing
  fallbackLocale: "en" as const,

  // Locale names for display in UI
  localeNames: {
    "zh-CN": "中文",
    en: "English",
  } as const,

  // Locale flags for display in UI
  localeFlags: {
    "zh-CN": "🇨🇳",
    en: "🇺🇸",
  } as const,
} as const;

export type LocaleNames = typeof i18nConfig.localeNames;
export type LocaleFlags = typeof i18nConfig.localeFlags;

/**
 * Helper to check if a string is a valid locale
 */
export function isValidLocale(locale: string): locale is Locale {
  return routing.locales.includes(locale as Locale);
}

/**
 * Helper to get the default locale
 */
export function getDefaultLocale(): Locale {
  return routing.defaultLocale;
}

/**
 * Helper to get the fallback locale
 */
export function getFallbackLocale(): Locale {
  return i18nConfig.fallbackLocale;
}

/**
 * Helper to get all available locales
 */
export function getLocales(): readonly Locale[] {
  return routing.locales;
}

/**
 * Helper to get locale display name
 */
export function getLocaleName(locale: Locale): string {
  return i18nConfig.localeNames[locale];
}

/**
 * Helper to get locale flag
 */
export function getLocaleFlag(locale: Locale): string {
  return i18nConfig.localeFlags[locale];
}
