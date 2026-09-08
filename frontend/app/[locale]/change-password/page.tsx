"use client";

import { useEffect, useState } from "react";
import { useRouter } from "@/i18n/navigation";
import { useTranslations } from "next-intl";
import { loadAuthState, authFetch, logout } from "@/lib/auth";
import { Button } from "@/components/common/Button";
import { Input } from "@/components/common/Input";
import { useToast } from "@/components/Toast";
import { AlertCircle, KeyRound, ShieldAlert } from "lucide-react";

/**
 * Forced password change screen.
 *
 * Reached when the backend flags the account with must_change_password
 * (e.g. the bootstrap admin still using its initial password). The user
 * cannot proceed into the app until the password is rotated.
 */
export default function ChangePasswordPage() {
  const router = useRouter();
  const t = useTranslations("changePassword");
  const { showToast } = useToast();
  const [checked, setChecked] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // Auth guard: only meaningful for a signed-in session.
  useEffect(() => {
    const state = loadAuthState();
    if (!state?.isAuthenticated) {
      router.push("/login");
      return;
    }
    setChecked(true);
  }, [router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

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
    <div className="relative min-h-screen flex items-center justify-center bg-surface-ground px-4 py-8">
      <div className="w-full max-w-[440px]">
        <div className="bg-surface-card border border-border-subtle rounded-2xl shadow-elevated p-7 sm:p-9 backdrop-blur-sm">
          <div className="text-center mb-7">
            <div className="inline-flex items-center justify-center w-13 h-13 rounded-2xl bg-amber-500/15 text-amber-600 dark:text-amber-400 mb-4 ring-4 ring-amber-500/10">
              <ShieldAlert className="w-7 h-7" strokeWidth={2} />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-text-primary">{t("title")}</h1>
            <p className="text-sm text-text-secondary mt-1.5 leading-relaxed">{t("subtitle")}</p>
          </div>

          {error && (
            <div
              className="mb-5 p-3 rounded-lg bg-danger-500/10 border border-danger-500/25 flex items-start gap-2.5 text-danger-700 dark:text-danger-400 text-xs sm:text-sm"
              role="alert"
            >
              <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
              <span className="leading-snug">{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="current"
                className="block text-xs font-medium text-text-secondary mb-1.5"
              >
                {t("currentPassword")}
              </label>
              <Input
                id="current"
                type="password"
                required
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                disabled={loading}
                autoComplete="current-password"
                autoFocus
                leftIcon={<KeyRound className="w-4 h-4 text-text-muted" />}
              />
            </div>

            <div>
              <label htmlFor="new" className="block text-xs font-medium text-text-secondary mb-1.5">
                {t("newPassword")}
              </label>
              <Input
                id="new"
                type="password"
                required
                minLength={12}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                disabled={loading}
                autoComplete="new-password"
                leftIcon={<KeyRound className="w-4 h-4 text-text-muted" />}
              />
            </div>

            <div>
              <label
                htmlFor="confirm"
                className="block text-xs font-medium text-text-secondary mb-1.5"
              >
                {t("confirmPassword")}
              </label>
              <Input
                id="confirm"
                type="password"
                required
                minLength={12}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                disabled={loading}
                autoComplete="new-password"
                leftIcon={<KeyRound className="w-4 h-4 text-text-muted" />}
              />
            </div>

            <div className="pt-2">
              <Button
                type="submit"
                disabled={loading}
                isLoading={loading}
                variant="primary"
                size="lg"
                className="w-full text-sm font-semibold tracking-wide"
              >
                {loading ? t("changing") : t("submit")}
              </Button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
