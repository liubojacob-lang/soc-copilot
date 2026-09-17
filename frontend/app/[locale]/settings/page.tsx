"use client";

import { useState, useEffect } from "react";
import { useRouter, Link } from "@/i18n/navigation";
import { useTranslations, useLocale } from "next-intl";
import { loadAuthState, isAdmin } from "@/lib/auth";
import { PageHeader } from "@/components/common/PageHeader";
import { Settings as SettingsIcon, Brain, ScrollText, ChevronRight } from "lucide-react";
import { TwoFactorSettings } from "./components/TwoFactorSettings";

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
      <div className="min-h-screen bg-surface-page">
        <PageHeader title={t("title")} />
        <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 px-4 py-3 rounded-lg">
            {error}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-surface-page transition-colors">
      <PageHeader
        title={t("title")}
        subtitle={
          isZh
            ? "管理系统身份安全、双因素认证策略与 AI 模型配置"
            : "Manage identity security, two-factor authentication policies, and AI model configurations"
        }
      />

      <main className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-6 pb-16 space-y-6">
        {/* Section 1: Two-Factor Authentication Settings */}
        <section aria-label="Two-factor authentication">
          <TwoFactorSettings />
        </section>

        {/* Section 2: Additional Settings & Integrations */}
        <section className="space-y-4" aria-label="Additional settings">
          <div className="flex items-center gap-2">
            <SettingsIcon className="w-4 h-4 text-accent-600 dark:text-accent-400" />
            <h2 className="text-xs font-bold uppercase tracking-wider text-gray-700 dark:text-gray-300">
              {t("otherSettings")}
            </h2>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* AI Models Card */}
            <Link
              href="/settings/ai-models"
              className="group rounded-2xl border border-gray-200/90 dark:border-gray-800 bg-white dark:bg-gray-900 p-5 shadow-subtle hover:shadow-md hover:border-accent-500/50 dark:hover:border-accent-500/50 transition-colors duration-150 flex items-start justify-between gap-4"
            >
              <div className="flex items-start gap-3.5">
                <div className="w-10 h-10 rounded-xl bg-accent-50 dark:bg-accent-950/40 text-accent-600 dark:text-accent-400 border border-accent-200/80 dark:border-accent-800/60 flex items-center justify-center shrink-0 transition-[transform,background-color,color] duration-150 group-hover:scale-105 group-hover:bg-accent-600 group-hover:text-white group-hover:border-accent-600">
                  <Brain className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-semibold text-gray-900 dark:text-white group-hover:text-accent-600 dark:group-hover:text-accent-400 transition-colors">
                      {isZh ? "AI 模型与引擎配置" : "AI Models & Providers"}
                    </h3>
                    <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-accent-50 dark:bg-accent-950/40 text-accent-700 dark:text-accent-300 border border-accent-200/80 dark:border-accent-800/50">
                      LLM
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 leading-relaxed">
                    {isZh
                      ? "管理大语言模型接入、联通性检测与默认推理引擎"
                      : "Manage LLM providers, test connection latency, and select default reasoning engine"}
                  </p>
                </div>
              </div>
              <ChevronRight className="w-4 h-4 text-gray-400 group-hover:text-accent-600 dark:group-hover:text-accent-400 group-hover:translate-x-0.5 transition-transform duration-150 shrink-0 mt-3" />
            </Link>

            {/* Audit Logs Quick Link */}
            <Link
              href="/audit"
              className="group rounded-2xl border border-gray-200/90 dark:border-gray-800 bg-white dark:bg-gray-900 p-5 shadow-subtle hover:shadow-md hover:border-purple-500/50 dark:hover:border-purple-500/50 transition-colors duration-150 flex items-start justify-between gap-4"
            >
              <div className="flex items-start gap-3.5">
                <div className="w-10 h-10 rounded-xl bg-purple-50 dark:bg-purple-950/40 text-purple-600 dark:text-purple-400 border border-purple-200/80 dark:border-purple-800/60 flex items-center justify-center shrink-0 transition-[transform,background-color,color] duration-150 group-hover:scale-105 group-hover:bg-purple-600 group-hover:text-white group-hover:border-purple-600">
                  <ScrollText className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-semibold text-gray-900 dark:text-white group-hover:text-purple-600 dark:group-hover:text-purple-400 transition-colors">
                      {isZh ? "安全审计日志" : "Security Audit Trail"}
                    </h3>
                    <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-purple-50 dark:bg-purple-950/40 text-purple-700 dark:text-purple-300 border border-purple-200/80 dark:border-purple-800/50">
                      Audit
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 leading-relaxed">
                    {isZh
                      ? "追踪管理员操作轨迹、鉴权事件与全局系统配置变更"
                      : "Inspect administrator activities, authentication attempts, and policy changes"}
                  </p>
                </div>
              </div>
              <ChevronRight className="w-4 h-4 text-gray-400 group-hover:text-purple-600 dark:group-hover:text-purple-400 group-hover:translate-x-0.5 transition-transform duration-150 shrink-0 mt-3" />
            </Link>
          </div>
        </section>
      </main>
    </div>
  );
}
