"use client";

import { useEffect, useState } from "react";

/**
 * Global error boundary for Next.js App Router.
 * This catches errors in the root layout, including the html and body tags.
 *
 * It renders OUTSIDE the NextIntlClientProvider (it replaces the whole
 * document), so translations come from the statically imported catalogs of
 * `errors.global` instead of the next-intl runtime.
 *
 * @see https://nextjs.org/docs/app/building-your-application/routing/error-handling#handling-errors-in-root-layouts
 */

interface GlobalErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

type Locale = "zh-CN" | "en";

export default function GlobalError({ error, reset }: GlobalErrorProps) {
  const [locale, setLocale] = useState<Locale>("zh-CN");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);

    const detectLocale = (): Locale => {
      if (typeof window !== "undefined") {
        // Try to get from URL path
        const pathLocale = window.location.pathname.split("/")[1];
        if (pathLocale === "zh-CN" || pathLocale === "en") {
          return pathLocale;
        }

        // Try the locale cookie written by next-intl middleware
        const cookieLocale = document.cookie
          .split("; ")
          .find((row) => row.startsWith("NEXT_LOCALE="))
          ?.split("=")[1];
        if (cookieLocale === "zh-CN" || cookieLocale === "en") {
          return cookieLocale;
        }

        // Try browser language
        const browserLang = navigator.language.toLowerCase();
        if (browserLang.startsWith("zh")) {
          return "zh-CN";
        }
      }

      return "zh-CN";
    };

    setLocale(detectLocale());
  }, []);

  // Prevent hydration mismatch by rendering nothing until mounted
  if (!mounted) {
    return (
      <html lang={locale}>
        <body style={{ margin: 0, padding: 0 }}>
          <div style={{ minHeight: "100vh", backgroundColor: "#fff" }} />
        </body>
      </html>
    );
  }

  return (
    <html lang={locale}>
      <body
        style={{
          margin: 0,
          padding: 0,
          fontFamily:
            '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            minHeight: "100vh",
            padding: "20px",
            backgroundColor: "#fff",
          }}
        >
          <div
            style={{
              maxWidth: "500px",
              textAlign: "center",
            }}
          >
            <h1
              style={{
                fontSize: "48px",
                margin: "0 0 16px 0",
                color: "#1a1a1a",
              }}
            >
              ⚠️
            </h1>
            <GlobalErrorContent error={error} locale={locale} onReset={reset} />
          </div>
        </div>
      </body>
    </html>
  );
}

function GlobalErrorContent({
  error,
  locale,
  onReset,
}: {
  error: Error & { digest?: string };
  locale: Locale;
  onReset: () => void;
}) {
  const [messages, setMessages] = useState<Record<string, string> | null>(null);

  useEffect(() => {
    let cancelled = false;
    // Lazy-load the catalog so the two full message bundles are not shipped
    // with every page just for this edge-case screen.
    Promise.all([import("@/messages/en.json"), import("@/messages/zh-CN.json")])
      .then(([en, zhCN]) => {
        if (cancelled) return;
        const catalog = locale === "en" ? en.default : zhCN.default;
        setMessages(catalog.errors.global as Record<string, string>);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [locale]);

  const t = (key: string) => messages?.[key] ?? "";

  return (
    <>
      <h2
        style={{
          fontSize: "24px",
          margin: "0 0 12px 0",
          color: "#1a1a1a",
        }}
      >
        {t("title")}
      </h2>
      <p
        style={{
          fontSize: "16px",
          color: "#666",
          margin: "0 0 24px 0",
        }}
      >
        {t("description")}
      </p>
      {process.env.NODE_ENV === "development" && (
        <pre
          style={{
            textAlign: "left",
            padding: "16px",
            backgroundColor: "#f5f5f5",
            borderRadius: "8px",
            overflow: "auto",
            fontSize: "12px",
            color: "#d32f2f",
            marginBottom: "24px",
          }}
        >
          {error.message}
          {error.digest && `\n\n${t("errorId")}: ${error.digest}`}
        </pre>
      )}
      <button
        onClick={onReset}
        style={{
          padding: "12px 32px",
          fontSize: "16px",
          fontWeight: 500,
          color: "#fff",
          backgroundColor: "#1890ff",
          border: "none",
          borderRadius: "6px",
          cursor: "pointer",
        }}
      >
        {t("refresh")}
      </button>
    </>
  );
}
