"use client";

import { useState, useEffect } from "react";
import { useRouter } from "@/i18n/navigation";
import { useTranslations } from "next-intl";
import { locales } from "@/i18n/routing";
import { login, saveAuthState } from "@/lib/auth";
import { Button } from "@/components/common/Button";
import { Input } from "@/components/common/Input";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { ThemeToggle } from "@/components/ThemeToggle";
import { ShieldCheck, User, Lock, Eye, EyeOff, AlertCircle, Sparkles } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const t = useTranslations("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  // The i18n router auto-prefixes the locale — a leading "/${locale}" here
  // would double up into /en/en (404).
  const [redirectPath, setRedirectPath] = useState("/");

  // Get redirect path from session storage (validate against open redirect)
  useEffect(() => {
    const storedRedirect = sessionStorage.getItem("redirect_after_login");
    // Server-side guard (proxy.ts) hands the intended destination via ?next=
    const searchNext = new URLSearchParams(window.location.search).get("next");
    const candidate = storedRedirect || searchNext;
    if (candidate && candidate.startsWith("/")) {
      try {
        const url = new URL(candidate, window.location.origin);
        if (url.origin === window.location.origin) {
          const segments = candidate.split("/");
          const localeAt = locales.includes(segments[1] as (typeof locales)[number]) ? 1 : -1;
          if (localeAt !== -1) segments.splice(1, 1);
          setRedirectPath(segments.join("/") || "/");
        }
      } catch {
        // Invalid URL, ignore
      }
      sessionStorage.removeItem("redirect_after_login");
    }
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const authState = await login(username, password);
      saveAuthState(authState);
      // Bootstrap/flagged accounts must set a new password before entering
      // the app; the target page is preserved in sessionStorage by the guard.
      if (authState.mustChangePassword) {
        sessionStorage.setItem("redirect_after_login", redirectPath);
        router.push("/change-password");
        return;
      }
      router.push(redirectPath);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t("error"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen flex flex-col justify-between bg-surface-ground overflow-hidden selection:bg-accent-500/20">
      {/* Background ambient lighting */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-[20%] left-1/2 -translate-x-1/2 w-[800px] h-[500px] bg-gradient-to-b from-accent-500/10 via-indigo-500/5 to-transparent blur-3xl rounded-full" />
        <div className="absolute -bottom-[20%] left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-gradient-to-t from-accent-600/10 to-transparent blur-3xl rounded-full" />
      </div>

      {/* Top right utility bar for locale and theme */}
      <header className="relative z-10 flex items-center justify-between p-4 sm:p-6 max-w-7xl mx-auto w-full">
        <div className="flex items-center gap-2.5 text-xs font-medium text-text-muted">
          <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span>SOC Platform v2.0</span>
        </div>
        <div className="flex items-center gap-2 bg-surface-card/60 backdrop-blur-md border border-border-subtle rounded-xl p-1 shadow-subtle">
          <LanguageSwitcher />
          <div className="w-px h-4 bg-border-subtle mx-0.5" />
          <ThemeToggle />
        </div>
      </header>

      {/* Main Card Container */}
      <main className="relative z-10 flex-1 flex items-center justify-center px-4 py-8">
        <div className="w-full max-w-[420px]">
          <div className="bg-surface-card border border-border-subtle rounded-2xl shadow-elevated p-7 sm:p-9 backdrop-blur-sm transition-all">
            {/* Brand Logo & Title */}
            <div className="text-center mb-7">
              <div className="inline-flex items-center justify-center w-13 h-13 rounded-2xl bg-gradient-to-tr from-accent-600 to-indigo-600 text-white shadow-subtle shadow-accent-600/30 mb-4 ring-4 ring-accent-500/10">
                <ShieldCheck className="w-7 h-7" strokeWidth={2} />
              </div>
              <h1 className="text-2xl font-bold tracking-tight text-text-primary">SOC Copilot</h1>
              <p className="text-sm text-text-secondary mt-1.5 leading-relaxed">{t("subtitle")}</p>
            </div>

            {/* Error Message Alert */}
            {error && (
              <div
                className="mb-5 p-3 rounded-lg bg-danger-500/10 border border-danger-500/25 flex items-start gap-2.5 text-danger-700 dark:text-danger-400 text-xs sm:text-sm animate-in fade-in duration-200"
                role="alert"
              >
                <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
                <span className="leading-snug">{error}</span>
              </div>
            )}

            {/* Login Form */}
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label
                  htmlFor="username"
                  className="block text-xs font-medium text-text-secondary mb-1.5"
                >
                  {t("username")}
                </label>
                <Input
                  id="username"
                  name="username"
                  type="text"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  disabled={loading}
                  autoComplete="username"
                  autoFocus
                  placeholder="admin"
                  leftIcon={<User className="w-4 h-4 text-text-muted" />}
                  size="lg"
                />
              </div>

              <div>
                <label
                  htmlFor="password"
                  className="block text-xs font-medium text-text-secondary mb-1.5"
                >
                  {t("password")}
                </label>
                <Input
                  id="password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={loading}
                  autoComplete="current-password"
                  placeholder="••••••••"
                  leftIcon={<Lock className="w-4 h-4 text-text-muted" />}
                  rightIcon={
                    <button
                      type="button"
                      onClick={() => setShowPassword((prev) => !prev)}
                      disabled={loading}
                      aria-label={showPassword ? t("hidePassword") : t("showPassword")}
                      title={showPassword ? t("hidePassword") : t("showPassword")}
                      className="text-text-muted hover:text-text-primary focus:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-500/50 rounded p-0.5 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  }
                  size="lg"
                />
              </div>

              <div className="pt-2">
                <Button
                  type="submit"
                  disabled={loading}
                  isLoading={loading}
                  variant="primary"
                  size="lg"
                  className="w-full text-sm font-semibold tracking-wide shadow-subtle shadow-accent-600/20"
                >
                  {loading ? t("signingIn") : t("signIn")}
                </Button>
              </div>
            </form>

            {/* Dev Mode Banner */}
            {process.env.NODE_ENV === "development" && (
              <div className="mt-6 pt-5 border-t border-border-subtle/80 flex items-center justify-center gap-1.5 text-xs text-text-muted">
                <Sparkles className="w-3.5 h-3.5 text-amber-500 shrink-0" />
                <span>
                  <strong className="font-semibold text-text-secondary">{t("devMode")}</strong>:{" "}
                  {t("checkServerLogs")}
                </span>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Subtle Footer */}
      <footer className="relative z-10 py-4 text-center text-xs text-text-disabled">
        © {new Date().getFullYear()} SOC Copilot Inc. Enterprise Security Operations.
      </footer>
    </div>
  );
}
