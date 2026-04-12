"use client";

/**
 * Threat Intelligence Dashboard Page
 * 威胁情报仪表盘
 */

import { useState, useEffect } from "react";
import dynamic from "next/dynamic";
import { useTranslations } from "next-intl";
import { RefreshCw, Download, Calendar, Filter } from "lucide-react";
import Navigation from "@/components/Navigation";
import { Skeleton, SkeletonCard } from "@/components/common/Skeleton";
import { AlertWebSocket } from "@/components/AlertWebSocket";
import { useToast } from "@/components/Toast";

// Dynamic import chart components (recharts ~100KB, load only when needed)
const TrendsChart = dynamic(
  () => import("@/components/monitor/TrendsChart").then((mod) => ({ default: mod.TrendsChart })),
  { ssr: false }
);
const SimpleTrendChart = dynamic(
  () =>
    import("@/components/monitor/TrendsChart").then((mod) => ({ default: mod.SimpleTrendChart })),
  { ssr: false }
);
const SeverityDistribution = dynamic(
  () =>
    import("@/components/monitor/SeverityDistribution").then((mod) => ({
      default: mod.SeverityDistribution,
    })),
  { ssr: false }
);
const SeverityCards = dynamic(
  () =>
    import("@/components/monitor/SeverityDistribution").then((mod) => ({
      default: mod.SeverityCards,
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
const SimpleTopSources = dynamic(
  () =>
    import("@/components/monitor/TopSources").then((mod) => ({ default: mod.SimpleTopSources })),
  { ssr: false }
);
const MITREHeatmap = dynamic(
  () => import("@/components/monitor/MITREHeatmap").then((mod) => ({ default: mod.MITREHeatmap })),
  { ssr: false }
);
const SimpleMITRETactics = dynamic(
  () =>
    import("@/components/monitor/MITREHeatmap").then((mod) => ({
      default: mod.SimpleMITRETactics,
    })),
  { ssr: false }
);
const IOCStats = dynamic(
  () => import("@/components/monitor/IOCStats").then((mod) => ({ default: mod.IOCStats })),
  { ssr: false }
);

// Mock Data - TODO: Replace with API calls
const mockTrendData = [
  {
    timestamp: "2026-02-19T00:00:00Z",
    date: "2026-02-19",
    total: 45,
    critical: 2,
    high: 8,
    medium: 15,
    low: 20,
  },
  {
    timestamp: "2026-02-20T00:00:00Z",
    date: "2026-02-20",
    total: 52,
    critical: 3,
    high: 10,
    medium: 18,
    low: 21,
  },
  {
    timestamp: "2026-02-21T00:00:00Z",
    date: "2026-02-21",
    total: 38,
    critical: 1,
    high: 7,
    medium: 12,
    low: 18,
  },
  {
    timestamp: "2026-02-22T00:00:00Z",
    date: "2026-02-22",
    total: 65,
    critical: 5,
    high: 15,
    medium: 20,
    low: 25,
  },
  {
    timestamp: "2026-02-23T00:00:00Z",
    date: "2026-02-23",
    total: 48,
    critical: 2,
    high: 9,
    medium: 16,
    low: 21,
  },
  {
    timestamp: "2026-02-24T00:00:00Z",
    date: "2026-02-24",
    total: 55,
    critical: 4,
    high: 12,
    medium: 18,
    low: 21,
  },
  {
    timestamp: "2026-02-25T00:00:00Z",
    date: "2026-02-25",
    total: 62,
    critical: 3,
    high: 14,
    medium: 22,
    low: 23,
  },
];

const mockSeverityData = {
  critical: 20,
  high: 75,
  medium: 121,
  low: 149,
  info: 45,
};

const mockTopSources = [
  {
    type: "ip" as const,
    value: "192.168.1.100",
    count: 45,
    severity: "critical" as const,
    country: "CN",
    first_seen: "2026-02-20",
    last_seen: "2026-02-25",
  },
  {
    type: "ip" as const,
    value: "203.0.113.50",
    count: 32,
    severity: "high" as const,
    country: "RU",
    first_seen: "2026-02-19",
    last_seen: "2026-02-25",
  },
  {
    type: "domain" as const,
    value: "malicious-example.com",
    count: 28,
    severity: "critical" as const,
    country: "US",
    first_seen: "2026-02-21",
    last_seen: "2026-02-25",
  },
  {
    type: "ip" as const,
    value: "10.0.0.55",
    count: 25,
    severity: "medium" as const,
    country: "DE",
    first_seen: "2026-02-22",
    last_seen: "2026-02-25",
  },
  {
    type: "domain" as const,
    value: "suspicious-site.net",
    count: 22,
    severity: "high" as const,
    country: "UK",
    first_seen: "2026-02-23",
    last_seen: "2026-02-25",
  },
];

const mockMITREData = [
  {
    tactic: "Initial Access",
    tactic_id: "TA0001",
    techniques: [
      { technique: "Spearphishing Link", technique_id: "T1566", count: 25 },
      { technique: "Exploit Public-Facing Application", technique_id: "T1190", count: 18 },
      { technique: "Valid Accounts", technique_id: "T1078", count: 12 },
    ],
  },
  {
    tactic: "Execution",
    tactic_id: "TA0002",
    techniques: [
      { technique: "Command and Scripting Interpreter", technique_id: "T1059", count: 35 },
      { technique: "User Execution", technique_id: "T1204", count: 22 },
    ],
  },
  {
    tactic: "Persistence",
    tactic_id: "TA0003",
    techniques: [
      { technique: "Scheduled Task/Job", technique_id: "T1053", count: 15 },
      { technique: "Create Account", technique_id: "T1136", count: 8 },
    ],
  },
  {
    tactic: "Defense Evasion",
    tactic_id: "TA0005",
    techniques: [
      { technique: "Obfuscated Files or Information", technique_id: "T1027", count: 20 },
      { technique: "Process Injection", technique_id: "T1055", count: 14 },
    ],
  },
];

const mockIOCStats = {
  total: 410,
  malicious: 45,
  suspicious: 82,
  benign: 156,
  unknown: 127,
};

const mockIOCBreakdown = [
  { type: "ip" as const, total: 125, malicious: 20, suspicious: 30, trend: "up" as const },
  { type: "domain" as const, total: 85, malicious: 15, suspicious: 18, trend: "stable" as const },
  { type: "url" as const, total: 92, malicious: 8, suspicious: 20, trend: "down" as const },
  { type: "hash" as const, total: 108, malicious: 2, suspicious: 14, trend: "stable" as const },
];

export default function ThreatIntelDashboardPage() {
  const t = useTranslations();
  const { showToast } = useToast();
  const [loading, setLoading] = useState(false);
  const [dateRange, setDateRange] = useState<"7d" | "30d" | "90d">("7d");

  // 获取仪表盘数据
  const [trendData, setTrendData] = useState(mockTrendData);
  const [severityData, setSeverityData] = useState(mockSeverityData);
  const [topSources, setTopSources] = useState(mockTopSources);
  const [mitreData, setMitreData] = useState(mockMITREData);
  const [iocStats, setIocStats] = useState(mockIOCStats);
  const [iocBreakdown, setIocBreakdown] = useState(mockIOCBreakdown);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboardData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [trendsRes, summaryRes, topThreatsRes, threatIntelRes] = await Promise.all([
        fetch(`/api/v1/alerts/statistics/trends?range=${dateRange}`),
        fetch("/api/v1/alerts/statistics/summary"),
        fetch("/api/v1/alerts/statistics/top-threats"),
        fetch("/api/v1/alerts/statistics/threat-intel"),
      ]);

      if (!trendsRes.ok || !summaryRes.ok || !topThreatsRes.ok || !threatIntelRes.ok) {
        throw new Error("Failed to fetch dashboard data");
      }

      const [trends, summary, topThreats, threatIntel] = await Promise.all([
        trendsRes.json(),
        summaryRes.json(),
        topThreatsRes.json(),
        threatIntelRes.json(),
      ]);

      // 转换API数据为组件所需格式
      if (trends && trends.length > 0) {
        setTrendData(
          trends.map(
            (item: {
              timestamp: string;
              total: number;
              critical: number;
              high: number;
              medium: number;
              low: number;
            }) => ({
              timestamp: item.timestamp,
              date: new Date(item.timestamp).toISOString().split("T")[0],
              total: item.total,
              critical: item.critical,
              high: item.high,
              medium: item.medium,
              low: item.low,
            })
          )
        );
      }

      if (summary) {
        setSeverityData({
          critical: summary.by_severity?.critical || 0,
          high: summary.by_severity?.high || 0,
          medium: summary.by_severity?.medium || 0,
          low: summary.by_severity?.low || 0,
          info: summary.by_severity?.info || 0,
        });
      }

      if (topThreats && topThreats.length > 0) {
        setTopSources(
          topThreats.map(
            (threat: {
              indicator: string;
              type: string;
              count: number;
              severity: string;
              first_seen?: string;
              last_seen?: string;
            }) => ({
              type: threat.type || "ip",
              value: threat.indicator,
              count: threat.count,
              severity: threat.severity,
              country: "Unknown",
              first_seen: threat.first_seen || new Date().toISOString().split("T")[0],
              last_seen: threat.last_seen || new Date().toISOString().split("T")[0],
            })
          )
        );
      }

      if (threatIntel) {
        setIocStats({
          total: threatIntel.total_iocs || 0,
          malicious: threatIntel.malicious || 0,
          suspicious: threatIntel.suspicious || 0,
          benign: threatIntel.benign || 0,
          unknown: threatIntel.unknown || 0,
        });
      }
    } catch (error) {
      console.error("Failed to fetch dashboard data:", error);
      setError("Failed to load dashboard data");
      // 使用Mock数据作为fallback
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
      <Navigation
        title="Threat Intelligence Dashboard"
        subtitle="Security threat overview and analysis"
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
                label="Total Alerts"
                value={
                  severityData.critical +
                  severityData.high +
                  severityData.medium +
                  severityData.low +
                  severityData.info
                }
                change="+12%"
                trend="up"
                color="blue"
              />
              <KPICard
                label="Critical Threats"
                value={severityData.critical}
                change="+5%"
                trend="up"
                color="red"
              />
              <KPICard
                label="Malicious IOCs"
                value={iocStats.malicious}
                change="-8%"
                trend="down"
                color="orange"
              />
              <KPICard
                label="Active Campaigns"
                value={topSources.length}
                change="+2"
                trend="up"
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
              {/* MITRE ATT&CK Heatmap */}
              <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  MITRE ATT&CK Coverage
                </h3>
                <MITREHeatmap data={mitreData} />
              </div>

              {/* IOC Statistics */}
              <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  IOC Statistics
                </h3>
                <IOCStats stats={iocStats} breakdown={iocBreakdown} />
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
  change: string;
  trend: "up" | "down";
  color: "blue" | "red" | "orange" | "purple";
}

function KPICard({ label, value, change, trend, color }: KPICardProps) {
  const colorClasses = {
    blue: "bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800",
    red: "bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800",
    orange: "bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-800",
    purple: "bg-purple-50 dark:bg-purple-900/20 border-purple-200 dark:border-purple-800",
  };

  const trendColor =
    trend === "up" && (color === "red" || color === "orange")
      ? "text-red-600"
      : trend === "up"
        ? "text-green-600"
        : "text-green-600";

  return (
    <div className={`${colorClasses[color]} rounded-lg border p-4`}>
      <div className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-1">{label}</div>
      <div className="flex items-end justify-between">
        <div className="text-3xl font-bold text-gray-900 dark:text-white">{value}</div>
        <div className={`text-sm font-medium ${trendColor}`}>{change}</div>
      </div>
    </div>
  );
}
