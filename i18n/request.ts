import { getRequestConfig } from 'next-intl/server';
import { i18nConfig, isValidLocale, getDefaultLocale } from '../frontend/config/i18n';

// Re-export for backward compatibility
export const locales = i18nConfig.locales;
export type Locale = (typeof i18nConfig.locales)[number];
export const defaultLocale = i18nConfig.defaultLocale;

export default getRequestConfig(async ({ requestLocale }) => {
  let locale = await requestLocale;

  // Validate that the incoming `locale` parameter is valid
  if (!locale || !isValidLocale(locale)) {
    locale = getDefaultLocale();
  }

  return {
    locale,
    messages: (await import(`../messages/${locale}.json`)).default
  };
});
