"use client";

/**
 * Operations home — live SOC overview.
 *
 * All numbers come from GET /api/v1/dashboard/stats, which aggregates with a 60s server cache.
 */

import { useEffect, useMemo, useState } from "react";
import { useRouter, Link } from "@/i18n/navigation";
import { useTranslations } from "next-intl";
import {
  Activity,
  AlertTriangle,
  Briefcase,
  ChevronRight,
  ClipboardCheck,
  Crosshair,
  Flame,
  Timer,
  Server,
  ArrowUpRight,
} from "lucide-react";

import { useDashboardStats } from "@/hooks/useDashboard";
import type { DashboardStats, SeverityDistribution } from "@/lib/api/dashboard";
import { loadAuthState } from "@/lib/auth";
import { Card, LoadingSpinner, SkeletonCard } from "@/components/common";
import { StatCard } from "@/components/dashboard/StatCard";
import { Badge, type Severity } from "@/components/ui/Badge";

// 严重程度统一走 severity-* 设计令牌，不再裸写 danger/amber/yellow/emerald。
type SeverityLevel = Extract<Severity, "critical" | "high" | "medium" | "low" | "info">;

const SEVERITY_CONFIG: { key: keyof SeverityDistribution; severity: SeverityLevel }[] = [
  { key: "critical", severity: "critical" },
  { key: "high", severity: "high" },
  { key: "medium", severity: "medium" },
  { key: "low", severity: "low" },
  { key: "info", severity: "info" },
];

const SEVERITY_TOKENS: Record<SeverityLevel, { dot: string; bar: string }> = {
  critical: { dot: "bg-severity-critical", bar: "bg-severity-critical" },
  high: { dot: "bg-severity-high", bar: "bg-severity-high" },
  medium: { dot: "bg-severity-medium", bar: "bg-severity-medium" },
  low: { dot: "bg-severity-low", bar: "bg-severity-low" },
  info: { dot: "bg-severity-info", bar: "bg-severity-info" },
};

interface PriorityItem {
  severity: Severity;
  label: string;
  href: string;
}

/**
 * 由**真实统计数据**推导的优先级队列，回答 "What should I do next?"。
 * 这里是首页唯一的数据驱动建议区 —— 静态快捷入口不回答这个问题。
 */
function buildPriorities(stats: DashboardStats | undefined, t: (k: string, v?: object) => string) {
  if (!stats) return [];
  const items: PriorityItem[] = [];

  if (stats.alerts_by_severity.critical > 0) {
    items.push({
      severity: "critical",
      label: t("priority.criticalAlerts", { count: stats.alerts_by_severity.critical }),
      href: "/alerts",
    });
  }
  if (stats.cases_overdue > 0) {
    items.push({
      severity: "high",
      label: t("priority.overdueCases", { count: stats.cases_overdue }),
      href: "/cases",
    });
  }
  const topAsset = stats.top_risky_assets[0];
  if (topAsset && topAsset.risk_score >= 70) {
    items.push({
      severity: "high",
      label: t("priority.assetRisk", { asset: topAsset.asset, score: topAsset.risk_score }),
      href: "/assets",
    });
  }
  if (stats.alerts_by_severity.high > 0) {
    items.push({
      severity: "medium",
      label: t("priority.highAlerts", { count: stats.alerts_by_severity.high }),
      href: "/alerts",
    });
  }
  if (stats.ioc_hits_today > 0) {
    items.push({
      severity: "low",
      label: t("priority.iocHits", { count: stats.ioc_hits_today }),
      href: "/threat-intel",
    });
  }

  return items;
}

export default function HomePage() {
  const router = useRouter();
  const t = useTranslations("home");
  const tStats = useTranslations("stats");
  const tAlerts = useTranslations("alerts");
  const [apiStatus, setApiStatus] = useState<"checking" | "healthy" | "unhealthy">("checking");
  const [mounted, setMounted] = useState(false);

  const { data: stats, isLoading, isError } = useDashboardStats();

  useEffect(() => {
    setMounted(true);
    if (!loadAuthState()?.isAuthenticated) {
      router.push("/login");
      return;
    }
    // The dashboard query doubles as the API health probe.
    if (!isLoading) {
      setApiStatus(isError ? "unhealthy" : "healthy");
    }
  }, [router, isLoading, isError]);

  const criticalHigh = stats
    ? stats.alerts_by_severity.critical + stats.alerts_by_severity.high
    : 0;
  const trendMax = stats ? Math.max(1, ...stats.alerts_trend.map((p) => p.count)) : 1;
  const totalSeverityCount = stats
    ? Object.values(stats.alerts_by_severity).reduce((acc, n) => acc + n, 0)
    : 0;

  const priorities = useMemo(
    () => buildPriorities(stats, (k, v) => t(k as never, v as never)),
    [stats, t]
  );

  if (!mounted) {
    return (
      <div className="min-h-screen bg-surface-ground">
        <div className="flex items-center justify-center min-h-[60vh]">
          <LoadingSpinner size="xl" color="soc" label={t("loading")} />
        </div>
      </div>
    );
  }

  return (
    <div className="pb-12 pt-4 sm:pt-6">
      <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8">
        {/* ── Real-time stat cards ─────────────────────────── */}
        <div className="grid grid-cols-1 gap-4 sm:gap-6 mb-6 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            title={t("dashboard.unresolved")}
            value={stats ? stats.alerts_unresolved : "—"}
            subtitle={t("dashboard.unresolvedSub")}
            icon={<AlertTriangle className="w-5 h-5" />}
            variant="red"
            loading={isLoading}
          />
          <StatCard
            title={t("dashboard.criticalHigh")}
            value={stats ? criticalHigh : "—"}
            subtitle={t("dashboard.criticalHighSub")}
            icon={<Flame className="w-5 h-5" />}
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
            icon={<Briefcase className="w-5 h-5" />}
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
            icon={<Crosshair className="w-5 h-5" />}
            variant="purple"
            loading={isLoading}
          />
        </div>

        {isError && (
          <Card className="mb-6 p-4 border-severity-critical-border bg-severity-critical-bg">
            <p className="text-sm font-medium text-severity-critical-fg">
              {apiStatus === "unhealthy" ? t("apiUnreachable") : t("loadFailed")}
            </p>
          </Card>
        )}

        {/* ── Priority Queue: What should I do next? ─────── */}
        <Card className="mb-6 p-5 sm:p-6">
          <div className="mb-4">
            <h2 className="text-sm font-semibold tracking-tight text-text-primary">
              {t("priority.title")}
            </h2>
            <p className="text-xs text-text-muted mt-0.5">{t("priority.subtitle")}</p>
          </div>

          {isLoading ? (
            <SkeletonCard />
          ) : priorities.length > 0 ? (
            <ul className="divide-y divide-border-subtle">
              {priorities.map((item) => (
                <li key={`${item.severity}-${item.label}`}>
                  <Link
                    href={item.href}
                    className="flex items-center justify-between gap-3 py-2.5 group rounded-lg px-1 -mx-1 hover:bg-surface-hover transition-colors"
                  >
                    <span className="flex min-w-0 items-center gap-2.5">
                      <Badge severity={item.severity} size="xs" dot>
                        {tAlerts(item.severity)}
                      </Badge>
                      <span className="truncate text-[13px] font-medium text-text-primary">
                        {item.label}
                      </span>
                    </span>
                    <span className="flex shrink-0 items-center gap-1 text-xs font-medium text-accent-600 dark:text-accent-400">
                      {t("priority.investigate")}
                      <ChevronRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <div className="py-8 text-center">
              <p className="text-sm font-medium text-text-secondary">{t("priority.empty")}</p>
              <p className="text-xs text-text-muted mt-1">{t("priority.emptySub")}</p>
            </div>
          )}
        </Card>

        <div className="grid grid-cols-1 gap-6 mb-6 lg:grid-cols-3">
          {/* ── 7-day trend ────────────────────────────────── */}
          <Card className="p-5 sm:p-6 lg:col-span-2">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
              <div>
                <h2 className="text-sm font-semibold tracking-tight text-text-primary">
                  {t("dashboard.trend7d")}
                </h2>
                <p className="text-xs text-text-muted mt-0.5">{t("trendSubtitle")}</p>
              </div>
              {stats && stats.mttr_minutes !== null && (
                <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-surface-hover border border-border-subtle text-xs text-text-secondary">
                  <Timer className="w-3.5 h-3.5 text-accent-500" />
                  <span>
                    {t("dashboard.mttr")}:{" "}
                    <strong className="text-text-primary tabular-nums">{stats.mttr_minutes}</strong>{" "}
                    {t("dashboard.minutes")}
                  </span>
                </div>
              )}
            </div>

            {isLoading ? (
              <SkeletonCard />
            ) : stats && stats.alerts_trend.length > 0 ? (
              <div className="flex items-end gap-2 sm:gap-3 h-44 pt-4 px-2">
                {stats.alerts_trend.map((point) => {
                  const percentage = Math.max(4, (point.count / trendMax) * 100);
                  return (
                    <div
                      key={point.date}
                      className="flex-1 flex flex-col items-center gap-2 group h-full justify-end"
                    >
                      <span className="text-[11px] font-semibold text-text-secondary tabular-nums opacity-0 group-hover:opacity-100 transition-opacity">
                        {point.count}
                      </span>
                      <div className="w-full bg-surface-hover rounded-t-md overflow-hidden flex items-end h-full max-h-32">
                        <div
                          className="w-full rounded-t-md bg-accent-500 group-hover:bg-accent-400 transition-colors duration-200"
                          style={{ height: `${percentage}%` }}
                          title={`${point.date}: ${point.count}`}
                        />
                      </div>
                      <span className="text-[10px] font-medium text-text-muted">
                        {point.date.slice(5)}
                      </span>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="py-12 text-center text-sm text-text-muted">{t("noTrend")}</div>
            )}
          </Card>

          {/* ── Severity / status distribution ─────────────── */}
          <Card className="p-5 sm:p-6 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-semibold tracking-tight text-text-primary">
                  {t("dashboard.severityDist")}
                </h2>
                <span className="text-xs text-text-muted tabular-nums">
                  {t("total")}: {totalSeverityCount}
                </span>
              </div>
              {isLoading ? (
                <SkeletonCard />
              ) : stats ? (
                <ul className="space-y-3">
                  {SEVERITY_CONFIG.map(({ key, severity }) => {
                    const count = stats.alerts_by_severity[key] || 0;
                    const pct = totalSeverityCount > 0 ? (count / totalSeverityCount) * 100 : 0;
                    const token = SEVERITY_TOKENS[severity];
                    return (
                      <li key={key} className="space-y-1">
                        <div className="flex items-center justify-between text-xs">
                          <span className="flex items-center gap-2 font-medium text-text-secondary">
                            <span className={`w-2 h-2 rounded-full ${token.dot}`} />
                            {tAlerts(key)}
                          </span>
                          <span className="font-semibold text-text-primary tabular-nums">
                            {count}
                          </span>
                        </div>
                        <div className="w-full h-1.5 bg-surface-hover rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${token.bar}`}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </li>
                    );
                  })}
                </ul>
              ) : null}
            </div>

            {stats && stats.alerts_by_status && (
              <div className="mt-6 pt-4 border-t border-border-subtle flex items-center justify-between gap-2 text-xs text-text-muted">
                <div className="flex items-center gap-1.5">
                  <Activity className="w-3.5 h-3.5 text-accent-500" />
                  <span className="font-medium text-text-secondary">
                    {t("dashboard.statusDist")}
                  </span>
                </div>
                <div className="flex items-center gap-2 tabular-nums">
                  <span>
                    {stats.alerts_by_status.new || 0} {t("statusNew")}
                  </span>
                  <span>·</span>
                  <span>
                    {stats.alerts_by_status.investigating || 0} {t("statusInvestigating")}
                  </span>
                  <span>·</span>
                  <span>
                    {stats.alerts_by_status.escalated || 0} {t("statusEscalated")}
                  </span>
                </div>
              </div>
            )}
          </Card>
        </div>

        <div className="grid grid-cols-1 gap-6 mb-6 lg:grid-cols-3">
          {/* ── Top risky assets ───────────────────────────── */}
          <Card className="p-5 sm:p-6 lg:col-span-2">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-sm font-semibold tracking-tight text-text-primary">
                  {t("dashboard.topAssets")}
                </h2>
                <p className="text-xs text-text-muted mt-0.5">{t("topAssetsSub")}</p>
              </div>
              <Link
                href="/assets"
                className="inline-flex items-center gap-1 text-xs font-medium text-accent-600 dark:text-accent-400 hover:underline"
              >
                {t("viewAll")}
                <ArrowUpRight className="w-3 h-3" />
              </Link>
            </div>

            {isLoading ? (
              <SkeletonCard />
            ) : stats && stats.top_risky_assets.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs font-medium text-text-muted border-b border-border-subtle">
                      <th className="pb-3">{t("dashboard.asset")}</th>
                      <th className="pb-3 text-right">{t("dashboard.alerts")}</th>
                      <th className="pb-3 text-right">{t("dashboard.riskScore")}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-subtle">
                    {stats.top_risky_assets.map((asset) => (
                      <tr
                        key={asset.asset}
                        className="group hover:bg-surface-ground/50 transition-colors"
                      >
                        <td className="py-2.5 font-medium text-text-primary truncate max-w-[16rem]">
                          <div className="flex items-center gap-2">
                            <Server className="w-3.5 h-3.5 text-text-muted group-hover:text-accent-500 transition-colors" />
                            <span className="font-mono text-xs">{asset.asset}</span>
                          </div>
                        </td>
                        <td className="py-2.5 text-right tabular-nums text-text-secondary text-xs">
                          {asset.alert_count}
                        </td>
                        <td className="py-2.5 text-right tabular-nums">
                          <Badge
                            size="xs"
                            severity={
                              asset.risk_score >= 70
                                ? "danger"
                                : asset.risk_score >= 40
                                  ? "warning"
                                  : "neutral"
                            }
                          >
                            {asset.risk_score}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="py-10 text-center text-sm text-text-muted">
                {t("dashboard.noAssets")}
              </div>
            )}
          </Card>

          {/* ── Quick actions & Sources ─────────────────────── */}
          <Card className="p-5 sm:p-6 flex flex-col justify-between">
            <div>
              <h2 className="text-sm font-semibold tracking-tight text-text-primary mb-4">
                {t("dashboard.quickLinks")}
              </h2>
              <nav className="space-y-1.5">
                {[
                  {
                    href: "/alerts",
                    icon: AlertTriangle,
                    label: t("dashboard.goAlerts"),
                    color: "text-amber-500",
                  },
                  {
                    href: "/cases",
                    icon: Briefcase,
                    label: t("dashboard.goCases"),
                    color: "text-accent-500",
                  },
                  {
                    href: "/playbooks",
                    icon: ClipboardCheck,
                    label: t("dashboard.goPlaybooks"),
                    color: "text-emerald-500",
                  },
                  {
                    href: "/playbooks/approvals",
                    icon: Activity,
                    label: t("dashboard.goApprovals"),
                    color: "text-purple-500",
                  },
                ].map(({ href, icon: Icon, label, color }) => (
                  <Link
                    key={href}
                    href={href}
                    className="flex items-center justify-between rounded-lg px-3 py-2 text-xs font-medium text-text-secondary hover:text-text-primary hover:bg-surface-ground transition-all duration-150 group"
                  >
                    <span className="flex items-center gap-2.5">
                      <Icon className={`w-4 h-4 ${color}`} />
                      {label}
                    </span>
                    <ChevronRight className="w-3.5 h-3.5 text-text-muted group-hover:text-text-primary group-hover:translate-x-0.5 transition-all" />
                  </Link>
                ))}
              </nav>
            </div>

            {stats && stats.top_alert_sources.length > 0 && (
              <div className="mt-6 pt-4 border-t border-border-subtle">
                <h3 className="text-[11px] font-semibold text-text-muted uppercase tracking-wider mb-2.5">
                  {t("dashboard.sources")}
                </h3>
                <ul className="space-y-1.5 text-xs">
                  {stats.top_alert_sources.slice(0, 5).map((source) => (
                    <li key={source.source} className="flex items-center justify-between">
                      <span className="text-text-secondary truncate max-w-[180px]">
                        {source.source || t("unknownSource")}
                      </span>
                      <span className="tabular-nums font-medium text-text-muted">
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
    </div>
  );
}
