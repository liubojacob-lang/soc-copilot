"use client";

import { useState, useEffect } from "react";
import { useRouter } from "@/i18n/navigation";
import { useTranslations, useLocale } from "next-intl";
import { login, saveAuthState } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const locale = useLocale();
  const t = useTranslations("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [redirectPath, setRedirectPath] = useState(`/${locale}`);

  // Get redirect path from session storage (validate against open redirect)
  useEffect(() => {
    const storedRedirect = sessionStorage.getItem("redirect_after_login");
    if (storedRedirect) {
      // Only allow relative paths starting with / to prevent open redirect attacks
      try {
        const url = new URL(storedRedirect, window.location.origin);
        if (url.origin === window.location.origin && storedRedirect.startsWith("/")) {
          setRedirectPath(storedRedirect);
        }
      } catch {
        // Invalid URL, ignore
      }
      sessionStorage.removeItem("redirect_after_login");
    }
  }, [locale]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const authState = await login(username, password);
      saveAuthState(authState);
      router.push(redirectPath);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t("error"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
      <div className="max-w-md w-full mx-4">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-8">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">SOC Copilot</h1>
            <p className="text-gray-600 dark:text-gray-400 mt-2">{t("subtitle")}</p>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label
                htmlFor="username"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
              >
                {t("username")}
              </label>
              <input
                id="username"
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                disabled={loading}
                autoComplete="username"
              />
            </div>

            <div>
              <label
                htmlFor="password"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
              >
                {t("password")}
              </label>
              <input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                disabled={loading}
                autoComplete="current-password"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? t("signingIn") : t("signIn")}
            </button>
          </form>

          <div className="mt-6 text-center">
            {process.env.NODE_ENV === "development" && (
              <p className="text-sm text-yellow-600 dark:text-yellow-400">
                {t("devMode")}: <span className="text-xs">{t("checkServerLogs")}</span>
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
