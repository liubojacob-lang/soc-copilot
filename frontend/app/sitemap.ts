import type { MetadataRoute } from "next";

import { locales } from "@/i18n/routing";
import { getMetadataBase } from "@/lib/seo";

/** Locale-less static routes that should be indexed. */
const STATIC_ROUTES = [
  "/",
  "/login",
  "/alerts",
  "/cases",
  "/playbooks",
  "/playbooks/create",
  "/playbooks/definitions",
  "/playbooks/approvals",
  "/threat-intel",
  "/threat-hunting",
  "/ai-assistant",
  "/audit",
  "/admin",
  "/settings",
  "/reports",
  "/monitor",
  "/marketplace",
  "/assets",
  "/cloud-native",
  "/correlation",
  "/triggers",
  "/ueba",
] as const;

const DYNAMIC_SOURCES: { path: string; prefix: string }[] = [];

/**
 * Best-effort discovery of dynamic detail pages (e.g. `/alerts/:id`).
 * Any failure is swallowed so sitemap generation never blocks the build.
 */
async function getDynamicPaths(): Promise<string[]> {
  const results: string[] = [];

  await Promise.all(
    DYNAMIC_SOURCES.map(async ({ path, prefix }) => {
      try {
        const response = await fetch(path, { next: { revalidate: 3600 } });
        if (!response.ok) return;
        const items: { id?: string; slug?: string }[] = await response.json();
        for (const item of items) {
          const key = item.slug ?? item.id;
          if (key) results.push(`${prefix}/${key}`);
        }
      } catch {
        // Silently skip unavailable sources.
      }
    })
  );

  return results;
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const base = getMetadataBase();
  const dynamicPaths = await getDynamicPaths();
  const now = new Date();

  const entries: MetadataRoute.Sitemap = [];

  for (const route of [...STATIC_ROUTES, ...dynamicPaths]) {
    for (const locale of locales) {
      const localizedPath = `/${locale}${route === "/" ? "" : route}`;
      entries.push({
        url: new URL(localizedPath, base).toString(),
        lastModified: now,
        changeFrequency: route === "/" ? "daily" : "weekly",
        priority: route === "/" ? 1 : 0.7,
        alternates: {
          languages: Object.fromEntries(
            locales.map((l) => [l, new URL(`/${l}${route === "/" ? "" : route}`, base).toString()])
          ),
        },
      });
    }
  }

  return entries;
}
