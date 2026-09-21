"use client";

import { useState, useEffect } from "react";
import { useRouter, Link } from "@/i18n/navigation";
import { useTranslations, useLocale } from "next-intl";
import { loadAuthState, isAdmin } from "@/lib/auth";
import { PageHeader } from "@/components/common/PageHeader";
import { KeyRound, ChevronRight, ShieldAlert } from "lucide-react";
import { TwoFactorSettings } from "./components/TwoFactorSettings";

/**
 * Account security surface of the settings centre.
 *
 * All other configuration sections live under their own routes and are reached
 * from the persistent sidebar in `settings/layout.tsx`.
 */
export default function SettingsPage() {
  const router = useRouter();
  const locale = useLocale();
  const isZh = locale.startsWith("zh");
  const t = useTranslations("settings");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const authState = loadAuthState();
    if (!authState?.isAuthenticated) {
      router.push("/login");
      return;
    }
    if (!isAdmin(authState.user)) {
      setError(t("errors.adminOnly"));
      return;
    }
  }, [router, t]);

  if (error) {
    return (
      <div className="bg-surface-page">
        <PageHeader title={t("title")} />
        <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="rounded-2xl border border-amber-200 dark:border-amber-800/60 bg-amber-50 dark:bg-amber-950/20 p-5 flex items-start gap-3.5">
            <ShieldAlert className="w-5 h-5 mt-0.5 shrink-0 text-amber-600 dark:text-amber-400" />
            <div className="min-w-0">
              <h2 className="text-sm font-semibold text-amber-900 dark:text-amber-200">{error}</h2>
              <p className="text-xs text-amber-800/90 dark:text-amber-300/80 mt-1 leading-relaxed">
                {isZh
                  ? "系统配置与集成设置需要管理员权限。如需调整，请联系你的安全管理员。"
                  : "System and integration settings require administrator privileges. Contact your security admin for changes."}
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-surface-page">
      <PageHeader
        title={t("title")}
        subtitle={
          isZh
            ? "管理账号身份安全与双因素认证策略"
            : "Manage account identity security and two-factor authentication"
        }
      />

      <main className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-6 pb-16 space-y-6">
        {/* Section 1: Two-Factor Authentication */}
        <section aria-label={isZh ? "双因素认证" : "Two-factor authentication"}>
          <TwoFactorSettings />
        </section>

        {/* Section 2: Remaining account security actions */}
        <section className="space-y-3" aria-label={isZh ? "账号安全" : "Account security"}>
          <h2 className="text-[11px] font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400 px-1">
            {isZh ? "账号安全" : "Account security"}
          </h2>

          <Link
            href="/change-password"
            className="group flex items-center justify-between gap-4 rounded-2xl border border-gray-200/90 dark:border-gray-800 bg-white dark:bg-gray-900 p-5 shadow-subtle hover:shadow-md hover:border-accent-500/50 dark:hover:border-accent-500/50 transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-500 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-gray-900"
          >
            <div className="flex items-center gap-3.5 min-w-0">
              <div className="w-10 h-10 rounded-xl bg-gray-50 dark:bg-gray-800 text-gray-600 dark:text-gray-300 border border-gray-200 dark:border-gray-700 flex items-center justify-center shrink-0 transition-colors duration-150 group-hover:bg-accent-600 group-hover:text-white group-hover:border-accent-600">
                <KeyRound className="w-5 h-5" />
              </div>
              <div className="min-w-0">
                <h3 className="text-sm font-semibold text-gray-900 dark:text-white group-hover:text-accent-600 dark:group-hover:text-accent-400 transition-colors">
                  {isZh ? "修改密码" : "Change password"}
                </h3>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 leading-relaxed">
                  {isZh
                    ? "定期更新登录密码，避免长期沿用同一凭据"
                    : "Rotate your password regularly to avoid long-lived credentials"}
                </p>
              </div>
            </div>
            <ChevronRight className="w-4 h-4 text-text-tertiary group-hover:text-accent-600 dark:group-hover:text-accent-400 group-hover:translate-x-0.5 transition-transform duration-150 shrink-0" />
          </Link>
        </section>
      </main>
    </div>
  );
}
