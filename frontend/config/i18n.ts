/**
 * Shared i18n configuration for the application
 * This file should be imported by both next.config.js and i18n/request.ts
 */

export const i18nConfig = {
  // Supported locales
  locales: ["en", "zh"] as const,

  // Default locale to use when no locale is specified
  defaultLocale: "en" as const,

  // Fallback locale to use when a translation key is missing
  fallbackLocale: "en" as const,

  // Locale names for display in UI
  localeNames: {
    en: "English",
    zh: "中文",
  } as const,

  // Locale flags for display in UI
  localeFlags: {
    en: "🇺🇸",
    zh: "🇨🇳",
  } as const,
} as const;

export type Locale = (typeof i18nConfig.locales)[number];
export type LocaleNames = typeof i18nConfig.localeNames;
export type LocaleFlags = typeof i18nConfig.localeFlags;

/**
 * Translation key namespace structure
 * This defines the shape of translation keys for type safety
 */
export type TranslationNamespace =
  | "meta"
  | "common"
  | "nav"
  | "home"
  | "login"
  | "users"
  | "admin"
  | "adminDashboard"
  | "adminSettings"
  | "adminAudit"
  | "alertsPage"
  | "settings"
  | "notificationSettings"
  | "errors"
  | "playbooks"
  | "alerts"
  | "reports"
  | "monitor"
  | "ai"
  | "aiAssistant"
  | "threatIntel"
  | "marketplace"
  | "threatHunting"
  | "ueba"
  | "difyPage"
  | "triggers"
  | "triggersPage"
  | "assets"
  | "correlation"
  | "cloudNative"
  | "actions"
  | "activities"
  | "approvals"
  | "chart"
  | "configModal"
  | "definitions"
  | "difficulty"
  | "history"
  | "infoBox"
  | "manualImport"
  | "mlPowered"
  | "modal"
  | "model"
  | "queue"
  | "quickActions"
  | "resources"
  | "services"
  | "severity"
  | "sidebar"
  | "status"
  | "statuses"
  | "tabs"
  | "welcome"
  | "iocHunt"
  | "settingsApiKeys"
  | "navigation";

/**
 * Helper to check if a string is a valid locale
 */
export function isValidLocale(locale: string): locale is Locale {
  return i18nConfig.locales.includes(locale as Locale);
}

/**
 * Helper to get the default locale
 */
export function getDefaultLocale(): Locale {
  return i18nConfig.defaultLocale;
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
  return i18nConfig.locales;
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
