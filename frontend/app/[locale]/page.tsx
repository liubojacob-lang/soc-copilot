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
  Server,
  ArrowUpRight,
} from "lucide-react";

import { useDashboardStats } from "@/hooks/useDashboard";
import type { DashboardStats } from "@/lib/api/dashboard";
import { loadAuthState } from "@/lib/auth";
import { Card, LoadingSpinner, SkeletonCard } from "@/components/common";
import { StatCard } from "@/components/dashboard/StatCard";
import { Badge, type Severity } from "@/components/ui/Badge";
import { SeverityBreakdown } from "@/components/ui/SeverityBreakdown";

interface PriorityItem {
  severity: Severity;
  label: string;
  href: string;
}

/**
 * 把原始分钟数格式化为人类可读的时长。
 *
 * 之前直接把后端返回值渲染出来，界面上会出现「平均解决时长：105665.9 分钟」
 * —— 读者要在脑子里做两次除法才知道那大约是 73 天。指标卡不是数据导出，
 * 应该直接给出可理解的量级。
 */
function formatDuration(minutes: number, t: (key: never) => string): string {
  if (!Number.isFinite(minutes) || minutes < 0) return "—";
  if (minutes < 60) return `${Math.round(minutes)} ${t("dashboard.minutes" as never)}`;
  const hours = minutes / 60;
  if (hours < 24) return `${Math.round(hours)} ${t("dashboard.hours" as never)}`;
  const days = hours / 24;
  const rounded = days >= 10 ? Math.round(days) : Number(days.toFixed(1));
  return `${rounded} ${t("dashboard.days" as never)}`;
}

/**
 * 把坐标轴上限取整到好读的刻度（1/1.5/2/2.5/3/4/5/6/8 × 10^n）。
 *
 * 直接用最大值当上限会让最高的那根柱永远顶到画布顶端，既没有呼吸空间，
 * 也让 Y 轴刻度变成 63、71 这种读不出含义的数字。
 */
function niceCeil(value: number): number {
  if (!Number.isFinite(value) || value <= 0) return 1;
  const base = Math.pow(10, Math.floor(Math.log10(value)));
  for (const m of [1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10]) {
    if (value <= m * base) return m * base;
  }
  return 10 * base;
}

/** 由**真实统计数据**推导的优先级队列，回答 "What should I do next?"。
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
  // Y 轴上界取整到好读的刻度，给最高的柱留出呼吸空间
  const trendAxisMax = stats ? niceCeil(Math.max(1, ...stats.alerts_trend.map((p) => p.count))) : 1;
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
            <div className="mb-6">
              <h2 className="text-sm font-semibold tracking-tight text-text-primary">
                {t("dashboard.trend7d")}
              </h2>
              {/* MTTR 从"与标题争抢注意力的药丸"降级为副文本，
                  并把 105665.9 分钟这类原始值格式化成人类可读的 ≈73 天 */}
              <p className="mt-0.5 text-xs text-text-muted">
                {t("trendSubtitle")}
                {stats && stats.mttr_minutes !== null && (
                  <span className="ml-1.5 tabular-nums">
                    · {t("dashboard.mttr")} {formatDuration(stats.mttr_minutes, t)}
                  </span>
                )}
              </p>
            </div>

            {isLoading ? (
              <SkeletonCard />
            ) : stats && stats.alerts_trend.length > 0 ? (
              <div className="flex gap-3">
                {/* Y 轴刻度 —— 没有它就只能比较柱高、读不出绝对值 */}
                <div
                  className="flex h-40 shrink-0 flex-col justify-between text-right text-[10px] font-medium text-text-muted tabular-nums"
                  aria-hidden="true"
                >
                  <span>{trendAxisMax}</span>
                  {trendAxisMax >= 4 && <span>{Math.round(trendAxisMax / 2)}</span>}
                  <span>0</span>
                </div>

                <div className="min-w-0 flex-1">
                  <div className="relative h-40">
                    {/* 轻量基准线：0 / 50% / 100%。
                        此前每根柱背后有一个**等高灰色轨道**，柱与轨道并置形成
                        "双柱"错觉，且轨道会让人误以为那是量程本身。这里改为
                        贯穿全宽的横向基准线，不再产生第二个"柱"。 */}
                    <div
                      className="pointer-events-none absolute inset-0 flex flex-col justify-between"
                      aria-hidden="true"
                    >
                      <div className="border-t border-border-subtle" />
                      <div className="border-t border-border-subtle" />
                      <div className="border-t border-border-default" />
                    </div>

                    <div className="relative flex h-full items-end gap-2 sm:gap-3">
                      {stats.alerts_trend.map((point) => {
                        const pct = trendAxisMax > 0 ? (point.count / trendAxisMax) * 100 : 0;
                        // 0 值不渲染柱体；非 0 值给 2% 的可视下限
                        // （柱高承载数值，因此下限必须极小，不能用它来"救"小值）
                        const height = point.count === 0 ? 0 : Math.max(2, pct);
                        return (
                          <div
                            key={point.date}
                            className="group relative flex h-full flex-1 items-end justify-center"
                          >
                            {/* 悬停数值绝对定位，不参与布局，避免挤压柱体高度 */}
                            <span className="pointer-events-none absolute inset-x-0 top-0 text-center text-[11px] font-semibold text-text-secondary tabular-nums opacity-0 transition-opacity group-hover:opacity-100">
                              {point.count}
                            </span>
                            {height > 0 && (
                              <div
                                className="w-full rounded-t-md bg-accent-500 transition-colors duration-200 group-hover:bg-accent-400"
                                style={{ height: `${height}%` }}
                                title={`${point.date}: ${point.count}`}
                              />
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* X 轴日期与柱体共用同一套 flex 参数，保证对齐 */}
                  <div className="mt-2 flex gap-2 sm:gap-3">
                    {stats.alerts_trend.map((point) => (
                      <span
                        key={point.date}
                        className="flex-1 text-center text-[10px] font-medium text-text-muted"
                      >
                        {point.date.slice(5)}
                      </span>
                    ))}
                  </div>
                </div>
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
                <SeverityBreakdown counts={stats.alerts_by_severity} layout="list" />
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
