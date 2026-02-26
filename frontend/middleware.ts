import createMiddleware from 'next-intl/middleware';
import { locales, defaultLocale } from './i18n';

export default createMiddleware({
  // A list of all locales that are supported
  locales,
  
  // Default locale
  defaultLocale,
  
  // Always show locale prefix (/en, /zh)
  localePrefix: 'always',
  
  // Locale detection strategy
  // Priority: cookie > Accept-Language header
  localeDetection: true
});

export const config = {
  // Match only internationalized pathnames
  // Exclude: api routes, _next static files, images, favicon, and other static files
  matcher: ['/((?!api|_next|_next/static|_next/image|favicon.ico|.*\\..*).*)']
};
