import type { Metadata, Viewport } from "next";
import { NextIntlClientProvider } from 'next-intl';
import { getMessages, getTranslations, setRequestLocale } from 'next-intl/server';
import { notFound } from "next/navigation";
import "../globals.css";
import BackToTop from "@/components/BackToTop";
import { ResponsiveProvider } from "@/components/common/ResponsiveLayout";
import { PageErrorBoundary } from "@/components/common/ErrorBoundary";
import { ClientLayout } from "@/components/ClientLayout";
import { WebVitals } from "@/components/WebVitals";
import { KeyboardShortcutsHelp } from "@/components/KeyboardShortcutsHelp";
import { locales, type Locale } from '@/i18n';

export async function generateMetadata({
  params
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;

  // Validate locale
  if (!locales.includes(locale as Locale)) {
    return {};
  }

  const t = await getTranslations({ locale });

  return {
    title: t('meta.title'),
    description: t('meta.description'),
  };
}

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  userScalable: true,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#1f2937" },
  ],
};

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

export default async function LocaleLayout({
  children,
  params
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  // Await params before using (Next.js 15 requirement)
  const { locale } = await params;
  
  // Validate locale
  if (!locales.includes(locale as Locale)) {
    notFound();
  }

  // Enable static rendering
  setRequestLocale(locale);

  // Get translation messages
  const messages = await getMessages();

  return (
    <html lang={locale} suppressHydrationWarning>
      <head>
        <meta name="format-detection" content="telephone=no" />
        <meta name="mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="default" />
      </head>
      <body className="antialiased min-h-screen bg-slate-50 dark:bg-gray-900">
        <NextIntlClientProvider messages={messages}>
          <ResponsiveProvider>
            <PageErrorBoundary>
              <ClientLayout>
                {children}
              </ClientLayout>
            </PageErrorBoundary>
            <BackToTop />
            <KeyboardShortcutsHelp />
          </ResponsiveProvider>
        </NextIntlClientProvider>
        <WebVitals />
      </body>
    </html>
  );
}
