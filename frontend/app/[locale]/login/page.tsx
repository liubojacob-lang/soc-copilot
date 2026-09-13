"use client";

import { useState, useEffect } from "react";
import { useRouter } from "@/i18n/navigation";
import { useLocale, useTranslations } from "next-intl";
import { locales } from "@/i18n/routing";
import { login, loginWith2FA, saveAuthState, loadAuthState } from "@/lib/auth";
import { Button } from "@/components/common/Button";
import { Input } from "@/components/common/Input";
import { OtpInput } from "@/components/common/OtpInput";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { ThemeToggle } from "@/components/ThemeToggle";
import {
  ShieldCheck,
  User,
  Lock,
  Eye,
  EyeOff,
  AlertCircle,
  Sparkles,
  KeyRound,
  ArrowLeft,
} from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const locale = useLocale();
  const t = useTranslations("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [is2FA, setIs2FA] = useState(false);
  const [preAuthToken, setPreAuthToken] = useState("");
  const [totpCode, setTotpCode] = useState("");
  const [useBackupCode, setUseBackupCode] = useState(false);
  const [redirectPath, setRedirectPath] = useState("/");

  const getDestinationUrl = (path: string) => {
    let clean = (path || "").trim();
    for (const l of locales) {
      if (clean === `/${l}` || clean === `/${l}/`) {
        clean = "/";
        break;
      }
      if (clean.startsWith(`/${l}/`)) {
        clean = clean.slice(`/${l}`.length);
        break;
      }
    }
    if (!clean || clean === "/" || clean === "/login" || clean.endsWith("/login")) {
      return `/${locale}`;
    }
    return `/${locale}${clean.startsWith("/") ? clean : `/${clean}`}`;
  };

  // Get redirect path from session storage or query params
  useEffect(() => {
    const storedRedirect = sessionStorage.getItem("redirect_after_login");
    const searchNext = new URLSearchParams(window.location.search).get("next");
    const candidate = storedRedirect || searchNext;
    if (candidate && candidate.startsWith("/")) {
      setRedirectPath(candidate);
      sessionStorage.removeItem("redirect_after_login");
    }

    const authState = loadAuthState();
    if (authState?.isAuthenticated && !authState.require2FA) {
      window.location.href = getDestinationUrl(candidate || "");
    }
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const authState = await login(username, password);
      if (authState.require2FA && authState.preAuthToken) {
        setIs2FA(true);
        setPreAuthToken(authState.preAuthToken);
        setTotpCode("");
        return;
      }
      saveAuthState(authState);
      if (authState.mustChangePassword) {
        sessionStorage.setItem("redirect_after_login", redirectPath);
        window.location.href = `/${locale}/change-password`;
        return;
      }
      window.location.href = getDestinationUrl(redirectPath);
    } catch (err: unknown) {
      const rawMsg = err instanceof Error ? err.message : "";
      if (
        !rawMsg ||
        rawMsg.includes("Incorrect username or password") ||
        rawMsg.includes("401") ||
        rawMsg.includes("Invalid credentials") ||
        rawMsg.includes("UNAUTHORIZED") ||
        rawMsg === "登录失败"
      ) {
        setError(t("error"));
      } else if (
        rawMsg.includes("locked") ||
        rawMsg.includes("423") ||
        rawMsg.includes("Too many failed login attempts")
      ) {
        setError(
          locale.startsWith("zh")
            ? "连续登录失败次数过多，账户已被临时锁定，请稍后再试或联系管理员"
            : rawMsg
        );
      } else if (rawMsg.includes("DATABASE_ERROR") || rawMsg.includes("database error")) {
        setError(locale.startsWith("zh") ? "服务暂时不可用，请稍后重试" : rawMsg);
      } else {
        setError(rawMsg);
      }
    } finally {
      setLoading(false);
    }
  };

  const handle2FASubmit = async (e?: React.FormEvent, customCode?: string) => {
    if (e) e.preventDefault();
    const code = (customCode || totpCode).trim();
    if (!code) return;
    setError("");
    setLoading(true);

    try {
      const authState = await loginWith2FA(preAuthToken, code);
      saveAuthState(authState);
      if (authState.mustChangePassword) {
        sessionStorage.setItem("redirect_after_login", redirectPath);
        window.location.href = `/${locale}/change-password`;
        return;
      }
      window.location.href = getDestinationUrl(redirectPath);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t("invalidCode"));
    } finally {
      setLoading(false);
    }
  };

  const handleBackToLogin = () => {
    setIs2FA(false);
    setPreAuthToken("");
    setTotpCode("");
    setUseBackupCode(false);
    setError("");
  };

  return (
    <div className="relative min-h-screen flex flex-col justify-between bg-surface-ground overflow-hidden selection:bg-accent-500/20">
      {/* Background ambient lighting */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-[20%] left-1/2 -translate-x-1/2 w-[800px] h-[500px] bg-gradient-to-b from-accent-500/10 via-indigo-500/5 to-transparent blur-3xl rounded-full" />
        <div className="absolute -bottom-[20%] left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-gradient-to-t from-accent-600/10 to-transparent blur-3xl rounded-full" />
      </div>

      {/* Top right utility bar for locale and theme */}
      <header className="relative z-10 flex items-center justify-between p-4 sm:p-6 max-w-[1600px] mx-auto w-full">
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
              <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-gradient-to-tr from-accent-600 to-indigo-600 text-white shadow-subtle shadow-accent-600/30 mb-4 ring-4 ring-accent-500/10">
                {is2FA ? (
                  <KeyRound className="w-7 h-7" strokeWidth={2} />
                ) : (
                  <ShieldCheck className="w-7 h-7" strokeWidth={2} />
                )}
              </div>
              <h1 className="text-2xl font-bold tracking-tight text-text-primary">
                {is2FA ? t("twoFactorTitle") : "SOC Copilot"}
              </h1>
              <p className="text-sm text-text-secondary mt-1.5 leading-relaxed">
                {is2FA ? t("twoFactorSubtitle") : t("subtitle")}
              </p>
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

            {is2FA ? (
              /* Modern 2FA Challenge Form */
              <form onSubmit={handle2FASubmit} className="space-y-4">
                {useBackupCode ? (
                  <div>
                    <label
                      htmlFor="totpCode"
                      className="block text-xs font-medium text-text-secondary mb-1.5"
                    >
                      {locale.startsWith("zh")
                        ? "8 位紧急备用恢复码"
                        : "8-character emergency backup code"}
                    </label>
                    <Input
                      id="totpCode"
                      name="totpCode"
                      type="text"
                      required
                      value={totpCode}
                      onChange={(e) => setTotpCode(e.target.value)}
                      disabled={loading}
                      autoFocus
                      placeholder="ABC12345"
                      leftIcon={<Lock className="w-4 h-4 text-text-muted" />}
                      size="lg"
                      className="font-mono tracking-widest text-center text-base uppercase"
                    />
                  </div>
                ) : (
                  <div className="space-y-3 py-1">
                    <label className="block text-xs font-semibold text-center text-text-secondary">
                      {locale.startsWith("zh")
                        ? "输入认证器 6 位实时验证码"
                        : "Enter 6-digit authenticator code"}
                    </label>
                    <OtpInput
                      value={totpCode}
                      onChange={setTotpCode}
                      onComplete={(code) => handle2FASubmit(undefined, code)}
                      disabled={loading}
                      autoFocus
                      error={Boolean(error)}
                    />
                  </div>
                )}

                {/* Switch between TOTP and Backup Code */}
                <div className="text-center pt-0.5">
                  <button
                    type="button"
                    onClick={() => {
                      setUseBackupCode(!useBackupCode);
                      setTotpCode("");
                      setError("");
                    }}
                    className="text-xs text-accent-600 hover:text-accent-700 dark:text-accent-400 font-medium transition-colors"
                  >
                    {useBackupCode
                      ? locale.startsWith("zh")
                        ? "使用 6 位动态口令验证码"
                        : "Use 6-digit authenticator code"
                      : locale.startsWith("zh")
                        ? "无法获取验证码？使用备用恢复码"
                        : "Can't access device? Use recovery code"}
                  </button>
                </div>

                <div className="pt-2 space-y-2.5">
                  <Button
                    type="submit"
                    disabled={loading || !totpCode.trim()}
                    isLoading={loading}
                    variant="primary"
                    size="lg"
                    className="w-full text-sm font-semibold tracking-wide shadow-subtle shadow-accent-600/20"
                  >
                    {loading ? t("verifying") : t("verifyAndSignIn")}
                  </Button>

                  <Button
                    type="button"
                    onClick={handleBackToLogin}
                    disabled={loading}
                    variant="ghost"
                    size="md"
                    className="w-full text-xs text-text-muted hover:text-text-primary flex items-center justify-center gap-1.5"
                  >
                    <ArrowLeft className="w-3.5 h-3.5" />
                    {t("backToLogin")}
                  </Button>
                </div>
              </form>
            ) : (
              /* Normal Login Form */
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
                        {showPassword ? (
                          <EyeOff className="w-4 h-4" />
                        ) : (
                          <Eye className="w-4 h-4" />
                        )}
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
            )}

            {/* Dev Mode Banner */}
            {!is2FA && process.env.NODE_ENV === "development" && (
              <div className="mt-6 pt-5 border-t border-border-subtle/80 flex flex-col items-center justify-center gap-2 text-xs text-text-muted">
                <div className="flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-amber-500 shrink-0" />
                  <span>
                    <strong className="font-semibold text-text-secondary">{t("devMode")}</strong>:{" "}
                    {t("devCredentials")}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setUsername("admin");
                    setPassword("Admin123!");
                  }}
                  className="text-xs text-accent-600 dark:text-accent-400 hover:underline cursor-pointer transition-colors"
                >
                  ⚡ {t("fillDevCredentials")}
                </button>
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
