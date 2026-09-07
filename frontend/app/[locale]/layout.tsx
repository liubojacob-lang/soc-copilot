import type { Metadata, Viewport } from "next";
import { headers } from "next/headers";
import { hasLocale } from "next-intl";
import { getMessages, getTranslations, setRequestLocale } from "next-intl/server";
import { notFound } from "next/navigation";

import BackToTop from "@/components/BackToTop";
import { OfflineBanner } from "@/components/common/OfflineBanner";
import { ResponsiveProvider } from "@/components/common/ResponsiveLayout";
import { PageErrorBoundary } from "@/components/common/ErrorBoundary";
import { ClientLayout } from "@/components/ClientLayout";
import { WebVitals } from "@/components/WebVitals";
import { KeyboardShortcutsHelp } from "@/components/KeyboardShortcutsHelp";
import { I18nClientProvider } from "@/components/providers/I18nClientProvider";
import { ThemeClassSync } from "@/components/ThemeClassSync";
import { locales } from "@/i18n/routing";
import { buildAlternates, getMetadataBase } from "@/lib/seo";
import "../globals.css";

const THEME_INIT_SCRIPT = `
  (function() {
    try {
      const stored = localStorage.getItem('theme-storage');
      let theme = 'system';
      if (stored) {
        const parsed = JSON.parse(stored);
        theme = parsed.state?.theme || 'system';
      }
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      const resolved = theme === 'system' ? (prefersDark ? 'dark' : 'light') : theme;
      document.documentElement.classList.remove('light', 'dark');
      document.documentElement.classList.add(resolved);
    } catch (e) {}
  })();
`;

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;

  if (!hasLocale(locales, locale)) {
    return {};
  }

  const t = await getTranslations({ locale, namespace: "meta" });

  return {
    metadataBase: getMetadataBase(),
    title: {
      default: t("title"),
      template: `%s | ${t("title")}`,
    },
    description: t("description"),
    alternates: buildAlternates("/"),
  };
}

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  userScalable: true,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f8fafc" },
    { media: "(prefers-color-scheme: dark)", color: "#1e293b" },
  ],
};

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;

  // Unknown locale segments are handled by the nearest not-found boundary.
  if (!hasLocale(locales, locale)) {
    notFound();
  }

  // Enable static rendering / ISR for this request.
  setRequestLocale(locale);

  const messages = await getMessages();

  // Nonce issued by middleware for the production CSP; the theme script is
  // the only hand-written inline script in the document.
  const nonce = (await headers()).get("x-nonce") ?? undefined;

  return (
    <html lang={locale} suppressHydrationWarning>
      <head>
        <meta name="format-detection" content="telephone=no" />
        <meta name="mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="default" />
      </head>
      <body className="antialiased min-h-screen">
        {/* The theme script must exist in the SSR HTML before first paint, but a
            <script> element rendered by React errors on client re-renders
            (locale switches) because scripts are never executed there. Emitting
            it as raw HTML inside a host element keeps it invisible to React:
            SSR still outputs a real script, and client updates never touch it. */}
        <div
          hidden
          dangerouslySetInnerHTML={{
            __html: `<script id="theme-init"${nonce ? ` nonce="${nonce}"` : ""}>${THEME_INIT_SCRIPT}</script>`,
          }}
        />
        <I18nClientProvider messages={messages} locale={locale}>
          <ResponsiveProvider>
            <PageErrorBoundary>
              <OfflineBanner />
              <ClientLayout>{children}</ClientLayout>
            </PageErrorBoundary>
            <BackToTop />
            <KeyboardShortcutsHelp />
            <ThemeClassSync />
          </ResponsiveProvider>
        </I18nClientProvider>
        <WebVitals />
      </body>
    </html>
  );
}
