import type { Metadata, Viewport } from "next";
import { cookies, headers } from "next/headers";
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

      // Sidebar collapse state must be on <html> before first paint, otherwise the
      // content area would render at the wrong padding and snap into place.
      const collapsed = localStorage.getItem('sidebar-collapsed') === 'true';
      document.documentElement.setAttribute('data-sidebar-collapsed', String(collapsed));

      // Synchronize role and sidebar state from localStorage to cookies if missing,
      // ensuring subsequent SSR renders produce identical markup and avoid hydration shift.
      if (typeof document !== 'undefined') {
        const userStr = localStorage.getItem('user');
        if (userStr) {
          try {
            const user = JSON.parse(userStr);
            if (user && user.role && !document.cookie.includes('user_role=')) {
              document.cookie = 'user_role=' + encodeURIComponent(user.role) + '; path=/; max-age=2592000; SameSite=Lax';
            }
          } catch (e) {}
        }
        if (localStorage.getItem('sidebar-collapsed') !== null && !document.cookie.includes('sidebar_collapsed=')) {
          document.cookie = 'sidebar_collapsed=' + (collapsed ? 'true' : 'false') + '; path=/; max-age=2592000; SameSite=Lax';
        }
        const groupsStr = localStorage.getItem('sidebar-collapsed-groups');
        if (groupsStr && !document.cookie.includes('sidebar_collapsed_groups=')) {
          document.cookie = 'sidebar_collapsed_groups=' + encodeURIComponent(groupsStr) + '; path=/; max-age=2592000; SameSite=Lax';
        }
      }
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

  const cookieStore = await cookies();
  const initialRole = cookieStore.get("user_role")?.value
    ? decodeURIComponent(cookieStore.get("user_role")!.value)
    : null;
  const initialSidebarCollapsed = cookieStore.get("sidebar_collapsed")?.value === "true";
  const collapsedGroupsRaw = cookieStore.get("sidebar_collapsed_groups")?.value;
  let initialCollapsedGroups: string[] = [];
  if (collapsedGroupsRaw) {
    try {
      const parsed = JSON.parse(decodeURIComponent(collapsedGroupsRaw));
      if (Array.isArray(parsed)) {
        initialCollapsedGroups = parsed;
      }
    } catch {}
  }

  return (
    <html
      lang={locale}
      data-sidebar-collapsed={initialSidebarCollapsed ? "true" : "false"}
      suppressHydrationWarning
    >
      <head>
        <meta name="format-detection" content="telephone=no" />
        <meta name="mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="default" />
      </head>
      <body className="font-sans antialiased min-h-screen">
        {/* The theme script must exist in the SSR HTML before first paint, but a
            <script> element rendered by React errors on client re-renders
            (locale switches) because scripts are never executed there. Emitting
            it as raw HTML inside a host element keeps it invisible to React:
            SSR still outputs a real script, and client updates never touch it. */}
        <div
          hidden
          suppressHydrationWarning
          dangerouslySetInnerHTML={{
            __html: `<script id="theme-init"${nonce ? ` nonce="${nonce}"` : ""}>${THEME_INIT_SCRIPT}</script>`,
          }}
        />
        <I18nClientProvider messages={messages} locale={locale}>
          <ResponsiveProvider>
            <PageErrorBoundary>
              <OfflineBanner />
              <ClientLayout
                initialRole={initialRole}
                initialSidebarCollapsed={initialSidebarCollapsed}
                initialCollapsedGroups={initialCollapsedGroups}
              >
                {children}
              </ClientLayout>
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
