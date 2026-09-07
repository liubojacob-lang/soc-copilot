"use client";

/**
 * SOC Operations Dashboard
 *
 * Layout:
 * [Real-time metrics row: 4 cols]
 * [Alert trends chart (2/3 width) | Severity pie (1/3 width)]
 * [MITRE ATT&CK heatmap (full width)]
 * [Asset risk Top 10 (1/2 width) | IOC stats (1/2 width)]
 */

import { useState, useEffect } from "react";
import { useRouter } from "@/i18n/navigation";
import { useFormatter, useTranslations } from "next-intl";
import dynamicImport from "next/dynamic";
import { loadAuthState, isAnalystOrAdmin } from "@/lib/auth";
import { PageHeader } from "@/components/common/PageHeader";
import {
  ShieldCheck,
  AlertTriangle,
  Briefcase,
  Clock,
  Activity,
  RefreshCw,
  Maximize2,
  Minimize2,
} from "lucide-react";
import { StatCard } from "@/components/dashboard/StatCard";
import { AlertTrendsChart } from "@/components/dashboard/AlertTrendsChart";
import { SeverityPieChart } from "@/components/dashboard/SeverityPieChart";
import { AssetRiskTable } from "@/components/dashboard/AssetRiskTable";
import { useDashboardStats } from "@/hooks/useDashboard";
import { toAlertTrendPoints, toSeverityBuckets, toAssetRiskItems } from "@/lib/api/dashboard";

// Dynamic imports for heavy chart components
const MITREHeatmap = dynamicImport(
  () =>
    import("@/components/monitor/MITREHeatmap").then((mod) => ({
      default: mod.MITREHeatmap,
    })),
  {
    ssr: false,
    loading: () => <div className="h-64 animate-pulse bg-gray-100 dark:bg-gray-800 rounded-xl" />,
  }
);

const IOCStats = dynamicImport(
  () =>
    import("@/components/monitor/IOCStats").then((mod) => ({
      default: mod.IOCStats,
    })),
  {
    ssr: false,
    loading: () => <div className="h-64 animate-pulse bg-gray-100 dark:bg-gray-800 rounded-xl" />,
  }
);

export default function DashboardPage() {
  const router = useRouter();
  const t = useTranslations();
  const format = useFormatter();
  const [mounted, setMounted] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [trendsPeriod, setTrendsPeriod] = useState<"7d" | "30d">("7d");

  // Time-based greeting
  const [greeting, setGreeting] = useState("");

  useEffect(() => {
    setMounted(true);
    const hour = new Date().getHours();
    if (hour < 12) setGreeting(t("dashboard.greeting.morning"));
    else if (hour < 18) setGreeting(t("dashboard.greeting.afternoon"));
    else setGreeting(t("dashboard.greeting.evening"));

    try {
      setIsFullscreen(typeof document !== "undefined" && !!document.fullscreenElement);
    } catch {
      setIsFullscreen(false);
    }
  }, []);

  // Auth check
  useEffect(() => {
    const auth = loadAuthState();
    if (!auth?.user || !isAnalystOrAdmin(auth.user)) {
      router.push("/");
    }
  }, [router]);

  // Fullscreen sync
  useEffect(() => {
    if (typeof window === "undefined") return;
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };
    document.addEventListener("fullscreenchange", handleFullscreenChange);
    return () => document.removeEventListener("fullscreenchange", handleFullscreenChange);
  }, []);

  const toggleFullscreen = () => {
    if (typeof window === "undefined" || !document) return;
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  // ── Data Hook (single real endpoint; adapters shape it per chart) ──
  const { data: stats, isLoading: statsLoading } = useDashboardStats();

  const summaryLoading = statsLoading;
  const trendsLoading = statsLoading;
  const severityLoading = statsLoading;
  const assetLoading = statsLoading;
  const iocLoading = statsLoading;
  const mitreLoading = statsLoading;

  // ── Transform data for existing components ──────────
  const trendsData = stats ? { points: toAlertTrendPoints(stats) } : undefined;
  const severityData = stats
    ? { buckets: toSeverityBuckets(stats), total: stats.alerts_total }
    : undefined;
  const assetData = stats ? { assets: toAssetRiskItems(stats) } : undefined;
  const mitreChartData: {
    tactic: string;
    tactic_id: string;
    techniques: { technique: string; technique_id: string; count: number }[];
  }[] = [];
  const iocStatsData = stats
    ? {
        total: stats.ioc_hits_today,
        malicious: 0,
        suspicious: 0,
        benign: 0,
        unknown: 0,
      }
    : { total: 0, malicious: 0, suspicious: 0, benign: 0, unknown: 0 };

  // Summary adapter for the metric cards (fields mirror the legacy shape).
  const summary = stats
    ? {
        total_alerts: stats.alerts_total,
        unresolved_alerts: stats.alerts_unresolved,
        active_cases: stats.cases_open,
        mttr_hours: stats.mttr_minutes !== null ? stats.mttr_minutes / 60 : 0,
      }
    : undefined;

  if (!mounted) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-950">
        <PageHeader
          title={t("dashboard.title")}
          subtitle={t("dashboard.overview")}
          apiStatus="checking"
        />
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="space-y-6">
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              {[1, 2, 3, 4].map((i) => (
                <div
                  key={i}
                  className="rounded-xl border p-5 shadow-sm animate-pulse bg-white dark:bg-slate-800 border-gray-200 dark:border-slate-700"
                >
                  <div className="h-3 bg-gray-200 dark:bg-slate-700 rounded w-20 mb-3" />
                  <div className="h-7 bg-gray-200 dark:bg-slate-700 rounded w-16 mb-2" />
                  <div className="h-3 bg-gray-200 dark:bg-slate-700 rounded w-24" />
                </div>
              ))}
            </div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-950">
      <PageHeader
        title={t("dashboard.title")}
        subtitle={`${greeting}, ${loadAuthState()?.user?.username || t("dashboard.fallbackUser")}`}
        apiStatus="healthy"
        actions={
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-green-50 dark:bg-green-900/20">
              <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
              <span className="text-[10px] text-green-700 dark:text-green-300 font-medium">
                {t("monitor.live")}
              </span>
            </div>
            <button
              onClick={toggleFullscreen}
              className="p-1.5 rounded-lg text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors"
              title={isFullscreen ? t("monitor.exitFullscreen") : t("monitor.fullscreen")}
            >
              {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
            </button>
          </div>
        }
      />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="space-y-6">
          {/* ── Row 1: Real-time Metrics ───────────────── */}
          <section>
            <h2 className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-3">
              {t("dashboard.realTimeMetrics")}
            </h2>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <StatCard
                title={t("dashboard.totalAlerts")}
                value={summaryLoading ? "—" : format.number(summary?.total_alerts ?? 0)}
                subtitle={t("dashboard.last24h")}
                icon={<AlertTriangle className="w-5 h-5" />}
                variant="blue"
                loading={summaryLoading}
              />
              <StatCard
                title={t("dashboard.unresolvedAlerts")}
                value={summaryLoading ? "—" : format.number(summary?.unresolved_alerts ?? 0)}
                subtitle={t("dashboard.needsAction")}
                icon={<AlertTriangle className="w-5 h-5" />}
                variant="red"
                loading={summaryLoading}
              />
              <StatCard
                title={t("dashboard.activeCases")}
                value={summaryLoading ? "—" : format.number(summary?.active_cases ?? 0)}
                subtitle={t("dashboard.openCases")}
                icon={<Briefcase className="w-5 h-5" />}
                variant="purple"
                loading={summaryLoading}
              />
              <StatCard
                title={t("dashboard.mttr")}
                value={summaryLoading ? "—" : `${(summary?.mttr_hours ?? 0).toFixed(1)}h`}
                subtitle={t("dashboard.meanTimeToResolve")}
                icon={<Clock className="w-5 h-5" />}
                variant="green"
                loading={summaryLoading}
              />
            </div>
          </section>

          {/* ── Row 2: Trends + Severity ──────────────── */}
          <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 min-w-0">
              <AlertTrendsChart
                data={trendsData?.points ?? []}
                isLoading={trendsLoading}
                currentPeriod={trendsPeriod}
                onPeriodChange={setTrendsPeriod}
              />
            </div>
            <div className="min-w-0">
              <SeverityPieChart
                data={severityData?.buckets ?? []}
                total={severityData?.total}
                isLoading={severityLoading}
              />
            </div>
          </section>

          {/* ── Row 3: MITRE Heatmap ──────────────────── */}
          <section>
            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <Activity className="w-4 h-4 text-blue-500" />
                {t("dashboard.mitreAttack")}
              </h3>
              {mitreLoading ? (
                <div className="h-64 animate-pulse bg-gray-100 dark:bg-gray-700 rounded" />
              ) : (
                <MITREHeatmap data={mitreChartData} />
              )}
            </div>
          </section>

          {/* ── Row 4: Asset Risk + IOC Stats ──────────── */}
          <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="min-w-0">
              <AssetRiskTable
                data={assetData?.assets ?? []}
                isLoading={assetLoading}
                title={t("dashboard.assetRiskTop10")}
              />
            </div>
            <div className="min-w-0 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-green-500" />
                {t("dashboard.iocStats")}
              </h3>
              {iocLoading ? (
                <div className="h-64 animate-pulse bg-gray-100 dark:bg-gray-700 rounded" />
              ) : (
                <IOCStats stats={iocStatsData} />
              )}
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}
