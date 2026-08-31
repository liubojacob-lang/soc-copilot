"use client";

/**
 * Threat Intelligence Dashboard Page
 * 威胁情报仪表盘
 */

import { useState, useEffect } from "react";
import dynamic from "next/dynamic";
import { useTranslations } from "next-intl";
import { RefreshCw, Download } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { Skeleton, SkeletonCard } from "@/components/common/Skeleton";
import { AlertWebSocket } from "@/components/AlertWebSocket";
import { useToast } from "@/components/Toast";
import { authFetch } from "@/lib/auth";

// Dynamic import chart components (recharts ~100KB, load only when needed)
const TrendsChart = dynamic(
  () => import("@/components/monitor/TrendsChart").then((mod) => ({ default: mod.TrendsChart })),
  { ssr: false }
);
const SeverityDistribution = dynamic(
  () =>
    import("@/components/monitor/SeverityDistribution").then((mod) => ({
      default: mod.SeverityDistribution,
    })),
  { ssr: false }
);
const SeverityBars = dynamic(
  () =>
    import("@/components/monitor/SeverityDistribution").then((mod) => ({
      default: mod.SeverityBars,
    })),
  { ssr: false }
);
const TopSources = dynamic(
  () => import("@/components/monitor/TopSources").then((mod) => ({ default: mod.TopSources })),
  { ssr: false }
);
const IOCStats = dynamic(
  () => import("@/components/monitor/IOCStats").then((mod) => ({ default: mod.IOCStats })),
  { ssr: false }
);

// API payload types (backend: schemas/alert_lifecycle.py)
interface AlertTrendItem {
  timestamp: string;
  count: number;
  by_severity: Record<string, number>;
}
interface AlertSummaryItem {
  total: number;
  by_severity: Record<string, number>;
}
interface TopThreatItem {
  type: string;
  value: string;
  count: number;
  severity: string;
  first_seen: string;
  last_seen: string;
}
interface ThreatIntelStatsItem {
  total_iocs: number;
  malicious_ips: number;
  suspicious_ips: number;
  malicious_domains: number;
  mitre_tactics: Record<string, number>;
}
interface TrendPoint {
  timestamp: string;
  date: string;
  total: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
}
interface ThreatSourceRow {
  type: "ip" | "domain";
  value: string;
  count: number;
  severity: "critical" | "high" | "medium" | "low";
  country: string;
  first_seen: string;
  last_seen: string;
}

const asSeverity = (s: string): ThreatSourceRow["severity"] =>
  s === "critical" || s === "high" || s === "low" ? s : "medium";

export default function ThreatIntelDashboardPage() {
  const t = useTranslations();
  const { showToast } = useToast();
  const [loading, setLoading] = useState(false);
  const [dateRange, setDateRange] = useState<"7d" | "30d" | "90d">("7d");

  // 获取仪表盘数据 — 空值初始化，绝不展示假数据
  const [trendData, setTrendData] = useState<TrendPoint[]>([]);
  const [severityData, setSeverityData] = useState({
    critical: 0,
    high: 0,
    medium: 0,
    low: 0,
    info: 0,
  });
  const [topSources, setTopSources] = useState<ThreatSourceRow[]>([]);
  const [iocStats, setIocStats] = useState({
    total: 0,
    malicious: 0,
    suspicious: 0,
    benign: 0,
    unknown: 0,
  });
  const [error, setError] = useState<string | null>(null);

  const fetchDashboardData = async () => {
    setLoading(true);
    setError(null);
    try {
      const days = dateRange === "7d" ? 7 : dateRange === "30d" ? 30 : 90;
      const end = new Date();
      const start = new Date(end.getTime() - days * 24 * 60 * 60 * 1000);
      const range = `start_date=${encodeURIComponent(start.toISOString())}&end_date=${encodeURIComponent(end.toISOString())}`;

      const [trendsRes, summaryRes, topThreatsRes, threatIntelRes] = await Promise.all([
        authFetch(`/api/v1/alerts/statistics/trends?${range}&interval=day`),
        authFetch(`/api/v1/alerts/statistics/summary?${range}`),
        authFetch(`/api/v1/alerts/statistics/top-threats?${range}&limit=10`),
        authFetch(`/api/v1/alerts/statistics/threat-intel?${range}`),
      ]);

      if (!trendsRes.ok || !summaryRes.ok || !topThreatsRes.ok || !threatIntelRes.ok) {
        throw new Error("Failed to fetch dashboard data");
      }

      const [trends, summary, topThreats, threatIntel] = (await Promise.all([
        trendsRes.json(),
        summaryRes.json(),
        topThreatsRes.json(),
        threatIntelRes.json(),
      ])) as [AlertTrendItem[], AlertSummaryItem, TopThreatItem[], ThreatIntelStatsItem];

      // 转换API数据为组件所需格式
      setTrendData(
        (trends ?? []).map((item) => ({
          timestamp: item.timestamp,
          date: new Date(item.timestamp).toISOString().split("T")[0],
          total: item.count,
          critical: item.by_severity?.critical ?? 0,
          high: item.by_severity?.high ?? 0,
          medium: item.by_severity?.medium ?? 0,
          low: item.by_severity?.low ?? 0,
        }))
      );

      if (summary?.by_severity) {
        setSeverityData({
          critical: summary.by_severity.critical ?? 0,
          high: summary.by_severity.high ?? 0,
          medium: summary.by_severity.medium ?? 0,
          low: summary.by_severity.low ?? 0,
          info: summary.by_severity.info ?? 0,
        });
      }

      setTopSources(
        (topThreats ?? []).map((threat) => ({
          type: threat.type === "domain" ? "domain" : "ip",
          value: threat.value,
          count: threat.count,
          severity: asSeverity(threat.severity),
          country: "",
          first_seen: (threat.first_seen ?? "").split("T")[0],
          last_seen: (threat.last_seen ?? "").split("T")[0],
        }))
      );

      if (threatIntel) {
        setIocStats({
          total: threatIntel.total_iocs ?? 0,
          malicious: (threatIntel.malicious_ips ?? 0) + (threatIntel.malicious_domains ?? 0),
          suspicious: threatIntel.suspicious_ips ?? 0,
          benign: 0,
          unknown: 0,
        });
      }
    } catch (err) {
      console.error("Failed to fetch dashboard data:", err);
      setError("Failed to load dashboard data");
    } finally {
      setLoading(false);
    }
  };

  // 导出报告
  const handleExport = async () => {
    try {
      setLoading(true);

      // Prepare export data
      const exportData = {
        generated_at: new Date().toISOString(),
        date_range: dateRange,
        summary: {
          total_alerts:
            severityData.critical +
            severityData.high +
            severityData.medium +
            severityData.low +
            severityData.info,
          by_severity: severityData,
        },
        top_threats: topSources,
        ioc_stats: iocStats,
        trends: trendData,
      };

      // Create and download JSON file
      const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: "application/json" });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `threat-intel-report-${new Date().toISOString().split("T")[0]}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      showToast("Export Complete: Threat intelligence report has been downloaded.", "success");
    } catch (error) {
      console.error("Failed to export:", error);
      showToast("Export Failed: Failed to generate export file.", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, [dateRange]);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <AlertWebSocket />
      <PageHeader
        title={t("threatIntel.dashboard.title")}
        subtitle={t("threatIntel.dashboard.subtitle")}
      />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <p className="text-red-700 dark:text-red-300">{error}</p>
            <button
              onClick={fetchDashboardData}
              className="mt-2 text-sm text-red-600 dark:text-red-400 hover:underline"
            >
              Retry
            </button>
          </div>
        )}

        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              Threat Intelligence Overview
            </h1>

            {/* Date Range Selector */}
            <div className="flex items-center gap-2 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-1">
              {(["7d", "30d", "90d"] as const).map((range) => (
                <button
                  key={range}
                  onClick={() => setDateRange(range)}
                  className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                    dateRange === range
                      ? "bg-blue-600 text-white"
                      : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700"
                  }`}
                >
                  {range === "7d" ? "7 Days" : range === "30d" ? "30 Days" : "90 Days"}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={fetchDashboardData}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </button>
            <button
              onClick={handleExport}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              <Download className="w-4 h-4" />
              Export
            </button>
          </div>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          {loading ? (
            <>
              {[1, 2, 3, 4].map((i) => (
                <div
                  key={i}
                  className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4"
                >
                  <Skeleton height="1rem" width="60%" className="mb-2" />
                  <Skeleton height="2rem" width="40%" className="mb-1" />
                  <Skeleton height="0.875rem" width="30%" />
                </div>
              ))}
            </>
          ) : (
            <>
              <KPICard
                label={t("threatIntel.dashboard.totalAlerts")}
                value={
                  severityData.critical +
                  severityData.high +
                  severityData.medium +
                  severityData.low +
                  severityData.info
                }
                color="blue"
              />
              <KPICard
                label={t("threatIntel.dashboard.criticalThreats")}
                value={severityData.critical}
                color="red"
              />
              <KPICard
                label={t("threatIntel.dashboard.maliciousIocs")}
                value={iocStats.malicious}
                color="orange"
              />
              <KPICard
                label={t("threatIntel.dashboard.activeCampaigns")}
                value={topSources.length}
                color="purple"
              />
            </>
          )}
        </div>

        {/* Charts Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {loading ? (
            <>
              <SkeletonCard hasHeader lines={0} className="h-[350px]" />
              <SkeletonCard hasHeader lines={0} className="h-[350px]" />
            </>
          ) : (
            <>
              {/* Trends Chart */}
              <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  Alert Trends (Last {dateRange === "7d" ? "7" : dateRange === "30d" ? "30" : "90"}{" "}
                  Days)
                </h3>
                <TrendsChart data={trendData} type="area" height={250} />
              </div>

              {/* Severity Distribution */}
              <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  Severity Distribution
                </h3>
                <SeverityDistribution data={severityData} type="donut" height={250} />
              </div>
            </>
          )}
        </div>

        {/* Middle Section */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          {loading ? (
            <>
              <SkeletonCard hasHeader lines={5} className="lg:col-span-2" />
              <SkeletonCard hasHeader lines={3} />
            </>
          ) : (
            <>
              {/* Top Threat Sources */}
              <div className="lg:col-span-2 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  Top Threat Sources
                </h3>
                <TopSources sources={topSources} limit={8} />
              </div>

              {/* Severity Breakdown */}
              <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  Severity Breakdown
                </h3>
                <SeverityBars data={severityData} limit={5} />
              </div>
            </>
          )}
        </div>

        {/* Bottom Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {loading ? (
            <>
              <SkeletonCard hasHeader lines={4} />
              <SkeletonCard hasHeader lines={4} />
            </>
          ) : (
            <>
              {/* IOC Statistics */}
              <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  IOC Statistics
                </h3>
                <IOCStats stats={iocStats} />
              </div>
            </>
          )}
        </div>
      </main>
    </div>
  );
}

// KPI Card Component
interface KPICardProps {
  label: string;
  value: number;
  color: "blue" | "red" | "orange" | "purple";
}

function KPICard({ label, value, color }: KPICardProps) {
  const colorClasses = {
    blue: "bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800",
    red: "bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800",
    orange: "bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-800",
    purple: "bg-purple-50 dark:bg-purple-900/20 border-purple-200 dark:border-purple-800",
  };

  return (
    <div className={`${colorClasses[color]} rounded-lg border p-4`}>
      <div className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-1">{label}</div>
      <div className="text-3xl font-bold text-gray-900 dark:text-white">{value}</div>
    </div>
  );
}
