"use client";

/**
 * Operations home — live SOC overview.
 *
 * Replaces the former mock workspace (hardcoded stat cards + tool tabs that
 * duplicated /alerts, /assets and /ai-assistant). All numbers come from
 * GET /api/v1/dashboard/stats, which aggregates with a 60s server cache.
 */

import { useEffect, useState } from "react";
import { useRouter } from "@/i18n/navigation";
import { useTranslations, useLocale } from "next-intl";
import Link from "next/link";
import {
  Activity,
  AlertTriangle,
  Briefcase,
  ChevronRight,
  ClipboardCheck,
  Crosshair,
  Flame,
  ShieldCheck,
  Timer,
} from "lucide-react";

import { useDashboardStats } from "@/hooks/useDashboard";
import type { SeverityDistribution } from "@/lib/api/dashboard";
import { loadAuthState } from "@/lib/auth";
import { PageHeader } from "@/components/common/PageHeader";
import Breadcrumbs from "@/components/common/Breadcrumbs";
import { Card, LoadingSpinner, SkeletonCard } from "@/components/common";
import { StatCard } from "@/components/dashboard/StatCard";

const SEVERITY_ORDER: { key: keyof SeverityDistribution; label: string; color: string }[] = [
  { key: "critical", label: "Critical", color: "bg-red-500" },
  { key: "high", label: "High", color: "bg-orange-500" },
  { key: "medium", label: "Medium", color: "bg-amber-400" },
  { key: "low", label: "Low", color: "bg-emerald-500" },
  { key: "info", label: "Info", color: "bg-slate-400" },
];

export default function HomePage() {
  const router = useRouter();
  const locale = useLocale();
  const t = useTranslations("home");
  const tStats = useTranslations("stats");
  const [apiStatus, setApiStatus] = useState<"checking" | "healthy" | "unhealthy">("checking");
  const [mounted, setMounted] = useState(false);

  const { data: stats, isLoading, isError } = useDashboardStats();

  useEffect(() => {
    setMounted(true);
    if (!loadAuthState()?.isAuthenticated) {
      router.push(`/${locale}/login`);
      return;
    }
    // The dashboard query doubles as the API health probe.
    if (!isLoading) {
      setApiStatus(isError ? "unhealthy" : "healthy");
    }
  }, [router, locale, isLoading, isError]);

  if (!mounted) {
    return (
      <div className="min-h-screen bg-surface-page dark:bg-slate-900">
        <div className="flex items-center justify-center min-h-screen">
          <LoadingSpinner size="xl" color="soc" label={t("loading")} />
        </div>
      </div>
    );
  }

  const criticalHigh = stats
    ? stats.alerts_by_severity.critical + stats.alerts_by_severity.high
    : 0;
  const trendMax = stats ? Math.max(1, ...stats.alerts_trend.map((p) => p.count)) : 1;

  return (
    <div className="min-h-screen bg-surface-page dark:bg-slate-900">
      <PageHeader
        title={t("title")}
        subtitle={t("subtitle")}
        apiStatus={
          apiStatus === "unhealthy" ? "error" : (apiStatus as "checking" | "healthy" | undefined)
        }
      />

      <main>
        <div className="mx-auto px-4 py-8 sm:px-6 lg:px-8 max-w-7xl">
          <Breadcrumbs className="mb-6" />

          <div className="mb-6 flex items-center gap-3">
            <div className="p-2.5 bg-primary-100 dark:bg-primary-800 rounded-lg shadow-sm">
              <ShieldCheck className="w-6 h-6 text-primary-600 dark:text-primary-400" />
            </div>
            <div>
              <h1 className="text-xl font-semibold text-gray-900 dark:text-white">
                {t("securityOperations")}
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">{t("subtitle")}</p>
            </div>
          </div>

          {/* ── Real-time stat cards ─────────────────────────── */}
          <div className="grid grid-cols-1 gap-6 mb-6 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              title={t("dashboard.unresolved")}
              value={stats ? stats.alerts_unresolved : "—"}
              subtitle={t("dashboard.unresolvedSub")}
              icon={<AlertTriangle className="w-6 h-6" />}
              variant="red"
              loading={isLoading}
            />
            <StatCard
              title={t("dashboard.criticalHigh")}
              value={stats ? criticalHigh : "—"}
              subtitle={t("dashboard.criticalHighSub")}
              icon={<Flame className="w-6 h-6" />}
              variant="amber"
              loading={isLoading}
            />
            <StatCard
              title={t("dashboard.openCases")}
              value={stats ? stats.cases_open : "—"}
              subtitle={
                stats && stats.cases_overdue > 0
                  ? t("dashboard.openCasesSub", { overdue: stats.cases_overdue })
                  : tStats("investigating")
              }
              icon={<Briefcase className="w-6 h-6" />}
              variant="blue"
              loading={isLoading}
            />
            <StatCard
              title={t("dashboard.iocToday")}
              value={stats ? stats.ioc_hits_today : "—"}
              subtitle={
                stats
                  ? t("dashboard.iocTodaySub", { runs: stats.playbook_runs_today })
                  : tStats("last24h")
              }
              icon={<Crosshair className="w-6 h-6" />}
              variant="purple"
              loading={isLoading}
            />
          </div>

          {isError && (
            <Card variant="default" className="mb-6 p-4 border-red-300 dark:border-red-700">
              <p className="text-sm text-red-600 dark:text-red-400">
                {apiStatus === "unhealthy"
                  ? "API unreachable"
                  : "Failed to load dashboard statistics"}
              </p>
            </Card>
          )}

          <div className="grid grid-cols-1 gap-6 mb-6 lg:grid-cols-3">
            {/* ── 7-day trend ────────────────────────────────── */}
            <Card variant="default" className="p-5 lg:col-span-2">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-semibold text-gray-900 dark:text-white">
                  {t("dashboard.trend7d")}
                </h2>
                {stats && stats.mttr_minutes !== null && (
                  <span className="inline-flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
                    <Timer className="w-3.5 h-3.5" />
                    {t("dashboard.mttr")}: {stats.mttr_minutes} {t("dashboard.minutes")}
                  </span>
                )}
              </div>
              {isLoading ? (
                <SkeletonCard />
              ) : stats && stats.alerts_trend.length > 0 ? (
                <div className="flex items-end gap-2 h-36">
                  {stats.alerts_trend.map((point) => (
                    <div key={point.date} className="flex-1 flex flex-col items-center gap-1.5">
                      <span className="text-[11px] font-medium text-gray-600 dark:text-gray-300">
                        {point.count}
                      </span>
                      <div
                        className="w-full rounded-t bg-primary-500/80 dark:bg-primary-600/80 min-h-[2px]"
                        style={{ height: `${Math.max(2, (point.count / trendMax) * 100)}%` }}
                        title={`${point.date}: ${point.count}`}
                      />
                      <span className="text-[10px] text-gray-400 dark:text-gray-500">
                        {point.date.slice(5)}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="py-10 text-center text-sm text-gray-400 dark:text-gray-500">—</p>
              )}
            </Card>

            {/* ── Severity / status distribution ─────────────── */}
            <Card variant="default" className="p-5">
              <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">
                {t("dashboard.severityDist")}
              </h2>
              {isLoading ? (
                <SkeletonCard />
              ) : stats ? (
                <ul className="space-y-2.5">
                  {SEVERITY_ORDER.map(({ key, label, color }) => (
                    <li key={key} className="flex items-center justify-between text-sm">
                      <span className="flex items-center gap-2 text-gray-600 dark:text-gray-300">
                        <span className={`w-2.5 h-2.5 rounded-full ${color}`} />
                        {label}
                      </span>
                      <span className="font-semibold text-gray-900 dark:text-white tabular-nums">
                        {stats.alerts_by_severity[key]}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : null}
              {stats && stats.alerts_by_status.new > 0 && (
                <div className="mt-4 pt-4 border-t border-gray-100 dark:border-gray-700 flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                  <Activity className="w-3.5 h-3.5" />
                  {t("dashboard.statusDist")}: {stats.alerts_by_status.new} new ·{" "}
                  {stats.alerts_by_status.investigating} investigating ·{" "}
                  {stats.alerts_by_status.escalated} escalated
                </div>
              )}
            </Card>
          </div>

          <div className="grid grid-cols-1 gap-6 mb-6 lg:grid-cols-3">
            {/* ── Top risky assets ───────────────────────────── */}
            <Card variant="default" className="p-5 lg:col-span-2">
              <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">
                {t("dashboard.topAssets")}
              </h2>
              {isLoading ? (
                <SkeletonCard />
              ) : stats && stats.top_risky_assets.length > 0 ? (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs text-gray-400 dark:text-gray-500 border-b border-gray-100 dark:border-gray-700">
                      <th className="pb-2 font-medium">{t("dashboard.asset")}</th>
                      <th className="pb-2 font-medium text-right">{t("dashboard.alerts")}</th>
                      <th className="pb-2 font-medium text-right">{t("dashboard.riskScore")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stats.top_risky_assets.map((asset) => (
                      <tr
                        key={asset.asset}
                        className="border-b border-gray-50 dark:border-gray-800 last:border-0"
                      >
                        <td className="py-2 font-medium text-gray-900 dark:text-white truncate max-w-[16rem]">
                          {asset.asset}
                        </td>
                        <td className="py-2 text-right tabular-nums text-gray-600 dark:text-gray-300">
                          {asset.alert_count}
                        </td>
                        <td className="py-2 text-right tabular-nums">
                          <span
                            className={`font-semibold ${
                              asset.risk_score >= 70
                                ? "text-red-600 dark:text-red-400"
                                : asset.risk_score >= 40
                                  ? "text-amber-600 dark:text-amber-400"
                                  : "text-gray-600 dark:text-gray-300"
                            }`}
                          >
                            {asset.risk_score}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="py-8 text-center text-sm text-gray-400 dark:text-gray-500">
                  {t("dashboard.noAssets")}
                </p>
              )}
            </Card>

            {/* ── Quick actions ──────────────────────────────── */}
            <Card variant="default" className="p-5">
              <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">
                {t("dashboard.quickLinks")}
              </h2>
              <nav className="space-y-2">
                {[
                  {
                    href: `/${locale}/alerts`,
                    icon: AlertTriangle,
                    label: t("dashboard.goAlerts"),
                  },
                  { href: `/${locale}/cases`, icon: Briefcase, label: t("dashboard.goCases") },
                  {
                    href: `/${locale}/playbooks`,
                    icon: ClipboardCheck,
                    label: t("dashboard.goPlaybooks"),
                  },
                  {
                    href: `/${locale}/playbooks/approvals`,
                    icon: ClipboardCheck,
                    label: t("dashboard.goApprovals"),
                  },
                ].map(({ href, icon: Icon, label }) => (
                  <Link
                    key={href}
                    href={href}
                    className="flex items-center justify-between rounded-lg px-3 py-2.5 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                  >
                    <span className="flex items-center gap-2.5">
                      <Icon className="w-4 h-4 text-primary-600 dark:text-primary-400" />
                      {label}
                    </span>
                    <ChevronRight className="w-4 h-4 text-gray-300 dark:text-gray-600" />
                  </Link>
                ))}
              </nav>

              {stats && stats.top_alert_sources.length > 0 && (
                <div className="mt-5 pt-4 border-t border-gray-100 dark:border-gray-700">
                  <h3 className="text-xs font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wide mb-2">
                    {t("dashboard.sources")}
                  </h3>
                  <ul className="space-y-1.5 text-sm">
                    {stats.top_alert_sources.slice(0, 5).map((source) => (
                      <li key={source.source} className="flex items-center justify-between">
                        <span className="text-gray-600 dark:text-gray-300 truncate">
                          {source.source || "unknown"}
                        </span>
                        <span className="tabular-nums text-gray-500 dark:text-gray-400">
                          {source.count}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </Card>
          </div>
        </div>
      </main>
    </div>
  );
}
