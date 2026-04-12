"use client";

import { useEffect, useState } from "react";

/**
 * Global error boundary for Next.js App Router.
 * This catches errors in the root layout, including the html and body tags.
 *
 * Note: This component is outside the NextIntlClientProvider, so we use
 * client-side locale detection for translations.
 *
 * @see https://nextjs.org/docs/app/building-your-application/routing/error-handling#handling-errors-in-root-layouts
 */

interface GlobalErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

// Simple translation dictionary for error messages
const translations = {
  en: {
    title: "Critical Error",
    description:
      "The application encountered a critical error. Please refresh the page to try again.",
    refresh: "Refresh Page",
    errorDetails: "Error Details",
    errorId: "Error ID",
  },
  zh: {
    title: "发生严重错误",
    description: "应用遇到了一个严重错误，请刷新页面重试。",
    refresh: "刷新页面",
    errorDetails: "错误详情",
    errorId: "错误 ID",
  },
};

type Locale = "en" | "zh";

export default function GlobalError({ error, reset }: GlobalErrorProps) {
  const [locale, setLocale] = useState<Locale>("en");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);

    // Detect locale from URL path or localStorage
    const detectLocale = (): Locale => {
      // Try to get from URL path
      if (typeof window !== "undefined") {
        const pathLocale = window.location.pathname.split("/")[1];
        if (pathLocale === "zh" || pathLocale === "en") {
          return pathLocale;
        }

        // Try to get from localStorage
        const storedLocale = localStorage.getItem("locale");
        if (storedLocale === "zh" || storedLocale === "en") {
          return storedLocale;
        }

        // Try browser language
        const browserLang = navigator.language.toLowerCase();
        if (browserLang.startsWith("zh")) {
          return "zh";
        }
      }

      return "en";
    };

    setLocale(detectLocale());
  }, []);

  const t = translations[locale];

  // Prevent hydration mismatch by rendering nothing until mounted
  if (!mounted) {
    return (
      <html lang="en">
        <body style={{ margin: 0, padding: 0 }}>
          <div style={{ minHeight: "100vh", backgroundColor: "#fff" }} />
        </body>
      </html>
    );
  }

  return (
    <html lang={locale === "zh" ? "zh-CN" : "en"}>
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
            <h2
              style={{
                fontSize: "24px",
                margin: "0 0 12px 0",
                color: "#1a1a1a",
              }}
            >
              {t.title}
            </h2>
            <p
              style={{
                fontSize: "16px",
                color: "#666",
                margin: "0 0 24px 0",
              }}
            >
              {t.description}
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
                {error.digest && `\n\n${t.errorId}: ${error.digest}`}
              </pre>
            )}
            <button
              onClick={reset}
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
              {t.refresh}
            </button>
          </div>
        </div>
      </body>
    </html>
  );
}
