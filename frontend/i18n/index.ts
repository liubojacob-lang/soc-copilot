/**
 * Barrel entry so `@/i18n` resolves to this directory.
 * Client components should prefer the specific modules
 * (`@/i18n/routing`, `@/i18n/navigation`) to keep bundles lean.
 */
export { defaultLocale, locales, routing } from "./routing";
export type { Locale } from "./routing";
export {
  Link,
  getPathname,
  permanentRedirect,
  redirect,
  usePathname,
  useRouter,
} from "./navigation";
