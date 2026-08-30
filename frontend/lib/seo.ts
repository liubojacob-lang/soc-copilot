import type { Metadata } from "next";

import { locales, type Locale } from "@/i18n/routing";

const SITE_NAME = "SOC Copilot";

export function getMetadataBase(): URL {
  return new URL(process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000");
}

/**
 * Builds per-page canonical + hreflang alternates for every supported
 * locale. `pathname` is locale-less (e.g. `/alerts`).
 *
 * Usage inside a page's `generateMetadata`:
 *   return { alternates: buildAlternates("/alerts") };
 */
export function buildAlternates(pathname: string): Metadata["alternates"] {
  const languages: Record<string, string> = {};
  for (const locale of locales) {
    languages[locale] = `/${locale}${pathname === "/" ? "" : pathname}`;
  }
  // x-default points at the default locale for language-negotiating crawlers.
  languages["x-default"] = `/${locales[0] as Locale}${pathname === "/" ? "" : pathname}`;

  return { canonical: languages["x-default"], languages };
}

export function getSiteName(): string {
  return SITE_NAME;
}
