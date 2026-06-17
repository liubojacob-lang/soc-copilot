"use client";

import { useEffect } from "react";
import { useTranslations } from "next-intl";
import { AlertTriangle, RefreshCw, ArrowLeft, Home } from "lucide-react";

interface ErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function RouteError({ error, reset }: ErrorProps) {
  const t = useTranslations("errors.page");

  useEffect(() => {
    console.error("Route error:", error);
  }, [error]);

  return (
    <div className="flex items-center justify-center min-h-[60vh] p-6">
      <div className="max-w-md w-full p-8 bg-white dark:bg-gray-800 rounded-xl shadow-lg text-center">
        <AlertTriangle className="w-14 h-14 text-amber-500 mx-auto mb-4" />
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
          {t("title")}
        </h1>
        <p className="text-gray-600 dark:text-gray-400 mb-6 leading-relaxed">
          {t("description")}
        </p>

        {process.env.NODE_ENV === "development" && (
          <details className="mb-6 text-left bg-gray-50 dark:bg-gray-900 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
            <summary className="cursor-pointer font-medium text-sm text-gray-700 dark:text-gray-300">
              {t("errorDetails")}
            </summary>
            <div className="mt-3">
              <p className="text-sm text-red-600 dark:text-red-400 font-medium mb-1">
                {error.name}: {error.message}
              </p>
              {error.digest && (
                <p className="text-xs text-gray-500 font-mono mb-2">
                  Error ID: {error.digest}
                </p>
              )}
              {error.stack && (
                <pre className="text-xs text-red-500 dark:text-red-400 bg-white dark:bg-gray-800 p-3 rounded border border-red-200 dark:border-red-800 overflow-auto max-h-48 whitespace-pre-wrap break-words">
                  {error.stack}
                </pre>
              )}
            </div>
          </details>
        )}

        <div className="flex gap-3 justify-center flex-wrap">
          <button
            onClick={reset}
            className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            {t("retry")}
          </button>
          <button
            onClick={() => history.back()}
            className="flex items-center gap-2 px-5 py-2.5 border border-blue-600 text-blue-600 dark:text-blue-400 dark:border-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg text-sm font-medium transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            {t("goBack")}
          </button>
          <a
            href="/"
            className="flex items-center gap-2 px-5 py-2.5 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 rounded-lg text-sm font-medium transition-colors"
          >
            <Home className="w-4 h-4" />
            {t("goHome")}
          </a>
        </div>
      </div>
    </div>
  );
}
