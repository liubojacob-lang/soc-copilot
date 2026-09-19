"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "@/i18n/navigation";
import { Link } from "@/i18n/navigation";
import { useTranslations } from "next-intl";
import { loadAuthState, authFetch, logout } from "@/lib/auth";
import type { User } from "@/lib/types";
import { PageHeader } from "@/components/common/PageHeader";
import { BackButton } from "@/components/common/BackButton";
import { Button } from "@/components/common/Button";
import { Input } from "@/components/common/Input";
import { useToast } from "@/components/Toast";
import {
  AlertCircle,
  Check,
  Eye,
  EyeOff,
  KeyRound,
  Lock,
  LogOut,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  User as UserIcon,
  ChevronRight,
  X,
} from "lucide-react";

/**
 * Enterprise Password Change Screen.
 *
 * Provides a balanced two-column console view aligned with SOC platform standards:
 * - Left column: secure password rotation form with 4-stage strength meter and live checklist
 * - Right column: current identity summary and password security best practices
 */
export default function ChangePasswordPage() {
  const router = useRouter();
  const t = useTranslations("changePassword");
  const { showToast } = useToast();
  const [checked, setChecked] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [isForced, setIsForced] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // Auth guard: only meaningful for a signed-in session.
  useEffect(() => {
    const state = loadAuthState();
    if (!state?.isAuthenticated) {
      router.push("/login");
      return;
    }
    setUser(state.user);
    setIsForced(Boolean(state.mustChangePassword));
    setChecked(true);
  }, [router]);

  const handleBack = useCallback(() => {
    if (typeof window !== "undefined") {
      const hasInternalReferrer =
        Boolean(document.referrer) && document.referrer.startsWith(window.location.origin);
      const hasHistory = window.history.length > 1;

      if (hasInternalReferrer || hasHistory) {
        router.back();
        return;
      }
    }
    router.push("/dashboard");
  }, [router]);

  // Validation rules aligned with backend validators & policy
  const hasMinLength = newPassword.length >= 12;
  const hasUpper = /[A-Z]/.test(newPassword);
  const hasLower = /[a-z]/.test(newPassword);
  const hasUpperLower = hasUpper && hasLower;
  const hasDigit = /[0-9]/.test(newPassword);
  const hasSymbol = /[^A-Za-z0-9]/.test(newPassword);
  const hasCurrentPassword = currentPassword.length > 0;
  const isDifferentFromCurrent = !hasCurrentPassword || newPassword !== currentPassword;
  const isConfirmFilled = confirmPassword.length > 0;
  const isMatching = isConfirmFilled && newPassword === confirmPassword;

  // Strength score: 0 to 4
  const strengthScore =
    newPassword.length === 0
      ? 0
      : (hasMinLength ? 1 : 0) + (hasUpperLower ? 1 : 0) + (hasDigit ? 1 : 0) + (hasSymbol ? 1 : 0);

  const getStrengthMeta = () => {
    switch (strengthScore) {
      case 1:
        return { label: t("strengthWeak"), color: "bg-red-500", text: "text-red-500" };
      case 2:
        return { label: t("strengthFair"), color: "bg-amber-500", text: "text-amber-500" };
      case 3:
        return { label: t("strengthGood"), color: "bg-blue-500", text: "text-blue-500" };
      case 4:
        return { label: t("strengthStrong"), color: "bg-emerald-500", text: "text-emerald-500" };
      default:
        return { label: "", color: "bg-gray-200 dark:bg-gray-700", text: "text-text-muted" };
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!hasMinLength || !hasUpperLower || !hasDigit) {
      setError(t("invalidComplexity"));
      return;
    }

    if (hasCurrentPassword && newPassword === currentPassword) {
      setError(t("ruleDifferent"));
      return;
    }

    if (newPassword !== confirmPassword) {
      setError(t("mismatch"));
      return;
    }

    setLoading(true);
    try {
      const response = await authFetch(`/api/auth/change-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
          confirm_password: confirmPassword,
        }),
      });

      if (response.ok) {
        showToast(t("success"), "success");
        // Rotate session: re-authenticate with the new credentials.
        logout();
        router.push("/login");
        return;
      }

      let message = t("failed");
      try {
        const data = await response.json();
        if (typeof data?.detail === "string") message = data.detail;
      } catch {
        // non-JSON error body — keep the generic message
      }
      setError(message);
    } catch {
      setError(t("failed"));
    } finally {
      setLoading(false);
    }
  };

  if (!checked) return null;

  return (
    <div className="min-h-screen bg-surface-page transition-colors">
      {/* Standard SOC PageHeader */}
      <PageHeader
        title={t("title")}
        subtitle={isForced ? t("forcedSubtitle") : t("voluntarySubtitle")}
        backButton={
          !isForced ? <BackButton fallbackUrl="/dashboard" label={t("backToConsole")} /> : undefined
        }
      />

      {/* Main Console Content */}
      <main className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-6 pb-16">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: Password Rotation Form Card */}
          <div className="lg:col-span-7 xl:col-span-8 bg-surface-card border border-border-subtle rounded-2xl shadow-sm p-6 sm:p-8">
            <div className="flex items-center gap-3 pb-6 mb-6 border-b border-border-subtle">
              <div
                className={`w-11 h-11 rounded-xl flex items-center justify-center shrink-0 ${
                  isForced
                    ? "bg-amber-500/15 text-amber-600 dark:text-amber-400"
                    : "bg-gradient-to-tr from-accent-600 to-indigo-600 text-white shadow-subtle"
                }`}
              >
                {isForced ? (
                  <ShieldAlert className="w-5 h-5" strokeWidth={2} />
                ) : (
                  <KeyRound className="w-5 h-5" strokeWidth={2} />
                )}
              </div>
              <div className="min-w-0">
                <h2 className="text-base sm:text-lg font-bold text-text-primary truncate">
                  {isForced ? t("securityRotationBadge") : t("title")}
                </h2>
                <p className="text-xs sm:text-sm text-text-secondary truncate mt-0.5">
                  {isForced ? t("forcedSubtitle") : t("voluntarySubtitle")}
                </p>
              </div>
            </div>

            {error && (
              <div
                className="mb-6 p-3.5 rounded-xl bg-danger-500/10 border border-danger-500/25 flex items-start gap-2.5 text-danger-700 dark:text-danger-400 text-xs sm:text-sm"
                role="alert"
              >
                <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
                <span className="leading-snug">{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Current Password */}
              <div>
                <label
                  htmlFor="current"
                  className="block text-xs font-semibold text-text-secondary mb-1.5"
                >
                  {t("currentPassword")}
                </label>
                <Input
                  id="current"
                  type={showCurrentPassword ? "text" : "password"}
                  required
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  disabled={loading}
                  autoComplete="current-password"
                  autoFocus
                  placeholder="••••••••"
                  size="lg"
                  leftIcon={<Lock className="w-4 h-4 text-text-muted" />}
                  rightIcon={
                    <button
                      type="button"
                      onClick={() => setShowCurrentPassword((prev) => !prev)}
                      disabled={loading}
                      aria-label={showCurrentPassword ? t("hidePassword") : t("showPassword")}
                      title={showCurrentPassword ? t("hidePassword") : t("showPassword")}
                      tabIndex={-1}
                      className="text-text-muted hover:text-text-primary focus:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-500/50 rounded p-1 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center cursor-pointer"
                    >
                      {showCurrentPassword ? (
                        <EyeOff className="w-4 h-4" />
                      ) : (
                        <Eye className="w-4 h-4" />
                      )}
                    </button>
                  }
                />
              </div>

              {/* New Password */}
              <div>
                <label
                  htmlFor="new"
                  className="block text-xs font-semibold text-text-secondary mb-1.5"
                >
                  {t("newPassword")}
                </label>
                <Input
                  id="new"
                  type={showNewPassword ? "text" : "password"}
                  required
                  minLength={12}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  disabled={loading}
                  autoComplete="new-password"
                  placeholder="••••••••••••"
                  size="lg"
                  leftIcon={<KeyRound className="w-4 h-4 text-text-muted" />}
                  rightIcon={
                    <button
                      type="button"
                      onClick={() => setShowNewPassword((prev) => !prev)}
                      disabled={loading}
                      aria-label={showNewPassword ? t("hidePassword") : t("showPassword")}
                      title={showNewPassword ? t("hidePassword") : t("showPassword")}
                      tabIndex={-1}
                      className="text-text-muted hover:text-text-primary focus:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-500/50 rounded p-1 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center cursor-pointer"
                    >
                      {showNewPassword ? (
                        <EyeOff className="w-4 h-4" />
                      ) : (
                        <Eye className="w-4 h-4" />
                      )}
                    </button>
                  }
                />
              </div>

              {/* Permanent Requirements Checklist & Strength Meter */}
              <div className="p-4 rounded-xl bg-surface-hover/50 border border-border-subtle text-xs space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-text-secondary text-xs flex items-center gap-1.5">
                    <ShieldCheck className="w-4 h-4 text-accent-500 shrink-0" />
                    {t("passwordRequirements")}
                  </span>
                  {newPassword.length > 0 && (
                    <span className={`text-[11px] font-bold ${getStrengthMeta().text}`}>
                      {getStrengthMeta().label}
                    </span>
                  )}
                </div>

                {/* 4-bar dynamic password strength meter */}
                {newPassword.length > 0 && (
                  <div className="grid grid-cols-4 gap-1.5 pt-0.5">
                    {[1, 2, 3, 4].map((step) => (
                      <div
                        key={step}
                        className={`h-1.5 rounded-full transition-all duration-300 ${
                          strengthScore >= step
                            ? getStrengthMeta().color
                            : "bg-gray-200 dark:bg-gray-700/60"
                        }`}
                      />
                    ))}
                  </div>
                )}

                {/* Requirement Checklist Items */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
                  {/* 1. Length >= 12 */}
                  <div className="flex items-center gap-2">
                    <div
                      className={`w-4 h-4 rounded-full flex items-center justify-center text-[9px] shrink-0 transition-colors ${
                        hasMinLength
                          ? "bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 font-bold"
                          : "bg-gray-200 dark:bg-gray-700 text-text-tertiary"
                      }`}
                    >
                      {hasMinLength ? <Check className="w-2.5 h-2.5 stroke-[3]" /> : "•"}
                    </div>
                    <span
                      className={`text-xs transition-colors ${
                        hasMinLength
                          ? "text-emerald-700 dark:text-emerald-300 font-medium"
                          : "text-text-muted"
                      }`}
                    >
                      {t("ruleLength")}
                    </span>
                  </div>

                  {/* 2. Uppercase & Lowercase letters */}
                  <div className="flex items-center gap-2">
                    <div
                      className={`w-4 h-4 rounded-full flex items-center justify-center text-[9px] shrink-0 transition-colors ${
                        hasUpperLower
                          ? "bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 font-bold"
                          : "bg-gray-200 dark:bg-gray-700 text-text-tertiary"
                      }`}
                    >
                      {hasUpperLower ? <Check className="w-2.5 h-2.5 stroke-[3]" /> : "•"}
                    </div>
                    <span
                      className={`text-xs transition-colors ${
                        hasUpperLower
                          ? "text-emerald-700 dark:text-emerald-300 font-medium"
                          : "text-text-muted"
                      }`}
                    >
                      {t("ruleUpperLower")}
                    </span>
                  </div>

                  {/* 3. Number */}
                  <div className="flex items-center gap-2">
                    <div
                      className={`w-4 h-4 rounded-full flex items-center justify-center text-[9px] shrink-0 transition-colors ${
                        hasDigit
                          ? "bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 font-bold"
                          : "bg-gray-200 dark:bg-gray-700 text-text-tertiary"
                      }`}
                    >
                      {hasDigit ? <Check className="w-2.5 h-2.5 stroke-[3]" /> : "•"}
                    </div>
                    <span
                      className={`text-xs transition-colors ${
                        hasDigit
                          ? "text-emerald-700 dark:text-emerald-300 font-medium"
                          : "text-text-muted"
                      }`}
                    >
                      {t("ruleNumber")}
                    </span>
                  </div>

                  {/* 4. Different from Current Password */}
                  <div className="flex items-center gap-2">
                    <div
                      className={`w-4 h-4 rounded-full flex items-center justify-center text-[9px] shrink-0 transition-colors ${
                        hasCurrentPassword && newPassword.length > 0
                          ? isDifferentFromCurrent
                            ? "bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 font-bold"
                            : "bg-danger-500/20 text-danger-600 dark:text-danger-400 font-bold"
                          : "bg-gray-200 dark:bg-gray-700 text-text-tertiary"
                      }`}
                    >
                      {hasCurrentPassword && newPassword.length > 0 ? (
                        isDifferentFromCurrent ? (
                          <Check className="w-2.5 h-2.5 stroke-[3]" />
                        ) : (
                          <X className="w-2.5 h-2.5 stroke-[3]" />
                        )
                      ) : (
                        "•"
                      )}
                    </div>
                    <span
                      className={`text-xs transition-colors ${
                        hasCurrentPassword && newPassword.length > 0
                          ? isDifferentFromCurrent
                            ? "text-emerald-700 dark:text-emerald-300 font-medium"
                            : "text-danger-600 dark:text-danger-400 font-medium"
                          : "text-text-muted"
                      }`}
                    >
                      {t("ruleDifferent")}
                    </span>
                  </div>
                </div>
              </div>

              {/* Confirm New Password */}
              <div>
                <label
                  htmlFor="confirm"
                  className="block text-xs font-semibold text-text-secondary mb-1.5"
                >
                  {t("confirmPassword")}
                </label>
                <Input
                  id="confirm"
                  type={showConfirmPassword ? "text" : "password"}
                  required
                  minLength={12}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  disabled={loading}
                  autoComplete="new-password"
                  placeholder="••••••••••••"
                  size="lg"
                  leftIcon={<KeyRound className="w-4 h-4 text-text-muted" />}
                  rightIcon={
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword((prev) => !prev)}
                      disabled={loading}
                      aria-label={showConfirmPassword ? t("hidePassword") : t("showPassword")}
                      title={showConfirmPassword ? t("hidePassword") : t("showPassword")}
                      tabIndex={-1}
                      className="text-text-muted hover:text-text-primary focus:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-500/50 rounded p-1 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center cursor-pointer"
                    >
                      {showConfirmPassword ? (
                        <EyeOff className="w-4 h-4" />
                      ) : (
                        <Eye className="w-4 h-4" />
                      )}
                    </button>
                  }
                />

                {/* Match indicator */}
                {isConfirmFilled && (
                  <div className="mt-2 flex items-center gap-2">
                    <div
                      className={`w-3.5 h-3.5 rounded-full flex items-center justify-center text-[9px] shrink-0 ${
                        isMatching
                          ? "bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 font-bold"
                          : "bg-danger-500/20 text-danger-600 dark:text-danger-400 font-bold"
                      }`}
                    >
                      {isMatching ? (
                        <Check className="w-2.5 h-2.5 stroke-[3]" />
                      ) : (
                        <X className="w-2.5 h-2.5 stroke-[3]" />
                      )}
                    </div>
                    <span
                      className={`text-xs font-medium ${
                        isMatching
                          ? "text-emerald-700 dark:text-emerald-300"
                          : "text-danger-600 dark:text-danger-400"
                      }`}
                    >
                      {isMatching ? t("ruleMatch") : t("mismatch")}
                    </span>
                  </div>
                )}
              </div>

              {/* Form Action Buttons */}
              <div className="pt-4 border-t border-border-subtle">
                {!isForced ? (
                  <div className="flex items-center gap-3">
                    <Button
                      type="button"
                      variant="secondary"
                      size="lg"
                      onClick={handleBack}
                      disabled={loading}
                      className="w-32 text-sm font-medium"
                    >
                      {t("cancel")}
                    </Button>
                    <Button
                      type="submit"
                      variant="primary"
                      size="lg"
                      disabled={loading}
                      isLoading={loading}
                      className="flex-1 text-sm font-semibold tracking-wide shadow-subtle shadow-accent-600/20"
                    >
                      {loading ? t("changing") : t("submit")}
                    </Button>
                  </div>
                ) : (
                  <div className="space-y-2.5">
                    <Button
                      type="submit"
                      variant="primary"
                      size="lg"
                      disabled={loading}
                      isLoading={loading}
                      className="w-full text-sm font-semibold tracking-wide shadow-subtle shadow-accent-600/20"
                    >
                      {loading ? t("changing") : t("submit")}
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        logout();
                        router.push("/login");
                      }}
                      disabled={loading}
                      className="w-full text-xs text-text-muted hover:text-text-primary flex items-center justify-center gap-1.5 pt-1 cursor-pointer"
                    >
                      <LogOut className="w-3.5 h-3.5" />
                      {t("logoutAndExit")}
                    </Button>
                  </div>
                )}
              </div>
            </form>
          </div>

          {/* Right Column: Account Info & Security Best Practices (Fills empty space) */}
          <div className="lg:col-span-5 xl:col-span-4 space-y-6">
            {/* Account Card */}
            {user && (
              <div className="bg-surface-card border border-border-subtle rounded-2xl shadow-sm p-6 space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-border-subtle">
                  <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-text-muted">
                    <UserIcon className="w-4 h-4 text-accent-500" />
                    <span>{t("accountInfo")}</span>
                  </div>
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-accent-500/10 text-accent-600 dark:text-accent-400 border border-accent-500/20">
                    {user.role}
                  </span>
                </div>

                <div className="flex items-center gap-3.5">
                  <div className="w-11 h-11 rounded-xl bg-gradient-to-tr from-accent-600 via-indigo-600 to-purple-600 text-white font-bold text-sm flex items-center justify-center shadow-subtle">
                    {(user.username || "U").charAt(0).toUpperCase()}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-bold text-text-primary truncate">
                      {user.username}
                    </div>
                    <div className="text-xs text-text-muted truncate mt-0.5">
                      {user.email || `${user.username}@soc.local`}
                    </div>
                  </div>
                </div>

                {/* 2FA Posture Row */}
                <div className="pt-2 border-t border-border-subtle">
                  <div className="text-[11px] font-semibold text-text-secondary mb-2">
                    {t("twoFactorStatus")}
                  </div>
                  <div
                    className={`flex items-center justify-between p-2.5 rounded-xl border text-xs ${
                      user.is_totp_enabled
                        ? "bg-emerald-50/60 dark:bg-emerald-950/20 border-emerald-200/70 dark:border-emerald-800/40 text-emerald-800 dark:text-emerald-300"
                        : "bg-amber-50/60 dark:bg-amber-950/20 border-amber-200/70 dark:border-amber-800/40 text-amber-800 dark:text-amber-300"
                    }`}
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      {user.is_totp_enabled ? (
                        <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
                      ) : (
                        <ShieldAlert className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0" />
                      )}
                      <span className="truncate font-medium text-[11px]">
                        {user.is_totp_enabled ? t("twoFactorEnabled") : t("twoFactorDisabled")}
                      </span>
                    </div>

                    {!user.is_totp_enabled && (
                      <Link
                        href="/settings"
                        className="inline-flex items-center gap-0.5 text-[10px] font-semibold text-amber-700 dark:text-amber-300 hover:underline shrink-0"
                      >
                        <span>{t("enable2FA")}</span>
                        <ChevronRight className="w-3 h-3" />
                      </Link>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Security Tips Card */}
            <div className="bg-surface-card border border-border-subtle rounded-2xl shadow-sm p-6 space-y-4">
              <div className="flex items-center gap-2 pb-3 border-b border-border-subtle text-xs font-bold uppercase tracking-wider text-text-muted">
                <ShieldCheck className="w-4 h-4 text-accent-500" />
                <span>{t("securityTipsTitle")}</span>
              </div>

              <div className="space-y-4 text-xs">
                <div className="flex items-start gap-3">
                  <div className="w-7 h-7 rounded-lg bg-accent-500/10 text-accent-600 dark:text-accent-400 flex items-center justify-center shrink-0 mt-0.5">
                    <Lock className="w-3.5 h-3.5" />
                  </div>
                  <div>
                    <div className="font-semibold text-text-primary text-xs">{t("tipUnique")}</div>
                    <div className="text-text-secondary text-[11px] leading-relaxed mt-0.5">
                      {t("tipUniqueDesc")}
                    </div>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <div className="w-7 h-7 rounded-lg bg-purple-500/10 text-purple-600 dark:text-purple-400 flex items-center justify-center shrink-0 mt-0.5">
                    <RefreshCw className="w-3.5 h-3.5" />
                  </div>
                  <div>
                    <div className="font-semibold text-text-primary text-xs">
                      {t("tipRotation")}
                    </div>
                    <div className="text-text-secondary text-[11px] leading-relaxed mt-0.5">
                      {t("tipRotationDesc")}
                    </div>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <div className="w-7 h-7 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center shrink-0 mt-0.5">
                    <ShieldCheck className="w-3.5 h-3.5" />
                  </div>
                  <div>
                    <div className="font-semibold text-text-primary text-xs">{t("tipSession")}</div>
                    <div className="text-text-secondary text-[11px] leading-relaxed mt-0.5">
                      {t("tipSessionDesc")}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
