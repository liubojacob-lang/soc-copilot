import type { Metadata } from "next";
import { hasLocale } from "next-intl";
import { setRequestLocale } from "next-intl/server";
import { notFound } from "next/navigation";

import { locales } from "@/i18n/routing";

interface CatchAllPageProps {
  params: Promise<{ locale: string; rest: string[] }>;
}

/**
 * Catch-all for unknown routes under a valid locale. Calling `notFound()`
 * from `generateMetadata` as well guarantees the streamed response carries
 * a real 404 status code instead of 200.
 */
export async function generateMetadata({ params }: CatchAllPageProps): Promise<Metadata> {
  const { locale } = await params;

  if (hasLocale(locales, locale)) {
    setRequestLocale(locale);
  }

  notFound();
}

export default async function CatchAllPage({ params }: CatchAllPageProps) {
  const { locale } = await params;

  if (!hasLocale(locales, locale)) {
    notFound();
  }

  setRequestLocale(locale);
  notFound();
}
