"use client";

/**
 * System Dashboard Page
 * 系统仪表盘 - 显示系统整体健康状态、资源使用情况、功能开关等
 * 重构：采用 8pt 网格、设计令牌、Typography、StatCard、ChartCard、DataTable
 */

import { useEffect, useState, useMemo } from "react";
import { useTranslations } from "next-intl";
import Navigation from "@/components/Navigation";
import Breadcrumbs from "@/components/common/Breadcrumbs";
import { StatCard } from "@/components/dashboard/StatCard";
import { ChartCard } from "@/components/dashboard/ChartCard";
import { DataTable, ColumnDef } from "@/components/ui/DataTable";
import { Heading, Text, Caption } from "@/components/ui/Typography";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/EmptyState";
import { StatusTimeline } from "@/components/dashboard/StatusTimeline";
import {
  Activity,
  Database,
  HardDrive,
  Cpu,
  MemoryStick,
  Server,
  Clock,
  CheckCircle,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Zap,
} from "lucide-react";

// Types
interface DatabaseStatus {
  status: string;
  latency_ms: number;
  pool?: {
    size: number;
    checked_in: number;
    checked_out: number;
    overflow: number;
    invalid: number;
  };
  version?: string;
  database_size?: string;
  active_connections?: number;
}

interface RedisStatus {
  status: string;
  latency_ms?: number;
  version?: string;
  connected_clients?: number;
  used_memory?: string;
  uptime_seconds?: number;
  pool_connections?: number;
}

interface AIModelStatus {
  id: string;
  name: string;
  provider: string;
  is_active: boolean;
  last_used?: string;
  total_requests: number;
}

interface SystemStats {
  cpu_percent: number;
  memory: {
    total_gb: number;
    available_gb: number;
    used_gb: number;
    percent_used: number;
  };
  disk: {
    total_gb: number;
    used_gb: number;
    free_gb: number;
    percent_used: number;
  };
  uptime_seconds: number;
  platform: string;
  python_version: string;
}

interface SystemDashboard {
  timestamp: string;
  version: string;
  environment: string;
  database: DatabaseStatus;
  redis: RedisStatus;
  ai_models: AIModelStatus[];
  system: SystemStats;
  features: Record<string, boolean>;
}

export default function SystemDashboardPage() {
  const t = useTranslations("adminDashboard");
  const tCommon = useTranslations("common");
  const [dashboard, setDashboard] = useState<SystemDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchDashboard = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch("/api/system/dashboard", {
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      setDashboard(data);
    } catch (err) {
      console.error("Failed to fetch dashboard:", err);
      setError(err instanceof Error ? err.message : "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboard();

    if (autoRefresh) {
      const interval = setInterval(fetchDashboard, 30000);
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);

    if (days > 0) {
      return `${days}d ${hours}h ${minutes}m`;
    } else if (hours > 0) {
      return `${hours}h ${minutes}m`;
    } else {
      return `${minutes}m`;
    }
  };

  const getStatusBadge = (status: string) => {
    const variant: "low" | "critical" | "medium" | "neutral" =
      status === "ok"
        ? "low"
        : status === "error"
          ? "critical"
          : status === "degraded" || status === "disabled"
            ? "medium"
            : "neutral";

    return <Badge severity={variant}>{status.toUpperCase()}</Badge>;
  };

  const aiModelColumns = useMemo<ColumnDef<AIModelStatus>[]>(
    () => [
      {
        key: "name",
        header: t("modelName", { default: "Model" }),
        cell: (row) => (
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-warning-600" />
            <span className="font-medium text-text-primary dark:text-white">{row.name}</span>
          </div>
        ),
        width: "30%",
      },
      {
        key: "provider",
        header: t("provider", { default: "Provider" }),
        cell: (row) => <Caption color="tertiary">{row.provider}</Caption>,
        width: "20%",
      },
      {
        key: "status",
        header: t("status", { default: "Status" }),
        cell: (row) => (
          <Badge severity={row.is_active ? "low" : "neutral"}>
            {row.is_active
              ? t("active", { default: "Active" })
              : t("inactive", { default: "Inactive" })}
          </Badge>
        ),
        width: "15%",
      },
      {
        key: "requests",
        header: t("requests", { default: "Requests" }),
        cell: (row) => (
          <span className="font-mono text-sm text-text-primary dark:text-white">
            {row.total_requests.toLocaleString()}
          </span>
        ),
        width: "15%",
      },
      {
        key: "last_used",
        header: t("lastUsed", { default: "Last Used" }),
        cell: (row) => (
          <Caption color="tertiary">
            {row.last_used ? new Date(row.last_used).toLocaleString() : "--"}
          </Caption>
        ),
        width: "20%",
      },
    ],
    [t]
  );

  const statusSteps = useMemo(() => {
    if (!dashboard) return [];
    return [
      {
        label: "DB",
        status: (dashboard.database.status === "ok" ? "completed" : "current") as
          | "completed"
          | "current"
          | "pending",
      },
      {
        label: "Redis",
        status: (dashboard.redis.status === "ok" ? "completed" : "current") as
          | "completed"
          | "current"
          | "pending",
      },
      {
        label: "System",
        status: "completed" as const,
      },
    ];
  }, [dashboard]);

  if (loading && !dashboard) {
    return (
      <div className="min-h-screen bg-surface-page dark:bg-slate-900">
        <Navigation title={t("title")} />
        <main className="p-6 lg:p-12">
          <div className="flex items-center justify-center min-h-[50vh]">
            <RefreshCw className="w-8 h-8 animate-spin text-text-tertiary" />
          </div>
        </main>
      </div>
    );
  }

  if (error && !dashboard) {
    return (
      <div className="min-h-screen bg-surface-page dark:bg-slate-900">
        <Navigation title={t("title")} />
        <main className="p-6 lg:p-12">
          <EmptyState
            icon="alert"
            title={t("error", { default: "Failed to load dashboard" })}
            description={error}
            action={
              <button
                onClick={fetchDashboard}
                className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 transition-colors"
              >
                {tCommon("retry")}
              </button>
            }
          />
        </main>
      </div>
    );
  }

  if (!dashboard) return null;

  const cpuTrend = dashboard.system.cpu_percent > 80 ? "up" : "neutral";
  const memoryTrend = dashboard.system.memory.percent_used > 80 ? "up" : "neutral";
  const diskTrend = dashboard.system.disk.percent_used > 80 ? "up" : "neutral";

  return (
    <div className="min-h-screen bg-surface-page dark:bg-slate-900">
      <Navigation title={t("title")} />
      <main className="p-6 lg:p-12 space-y-8">
        <Breadcrumbs />

        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <Heading level={1} color="primary">
              {t("title")}
            </Heading>
            <Text color="tertiary" className="mt-1">
              {t("subtitle")}
            </Text>
          </div>
          <div className="flex items-center gap-4 flex-wrap">
            <Caption color="tertiary">
              v{dashboard.version} • {dashboard.environment}
            </Caption>
            <div className="flex items-center gap-2">
              <Caption color="tertiary">{t("autoRefresh", { default: "Auto-refresh" })}</Caption>
              <button
                onClick={() => setAutoRefresh(!autoRefresh)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 ${
                  autoRefresh ? "bg-primary-600" : "bg-slate-300 dark:bg-slate-600"
                }`}
                role="switch"
                aria-checked={autoRefresh}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    autoRefresh ? "translate-x-6" : "translate-x-1"
                  }`}
                />
              </button>
            </div>
            <button
              onClick={fetchDashboard}
              disabled={loading}
              className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
              <span>{tCommon("refresh")}</span>
            </button>
          </div>
        </div>

        {/* KPI Cards - 4 cards in first row, 2 cards in second row = 6 total */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          <StatCard
            title={t("cpuUsage", { default: "CPU Usage" })}
            value={`${dashboard.system.cpu_percent.toFixed(1)}%`}
            trend={dashboard.system.cpu_percent > 80 ? "High" : "Normal"}
            trendDirection={cpuTrend}
            icon={<Cpu className="w-6 h-6 text-primary-600" />}
            subtitle={t("realTime", { default: "Real-time" })}
          />
          <StatCard
            title={t("memoryUsage", { default: "Memory" })}
            value={`${dashboard.system.memory.percent_used.toFixed(1)}%`}
            trend={`${dashboard.system.memory.used_gb.toFixed(1)} / ${dashboard.system.memory.total_gb.toFixed(1)} GB`}
            trendDirection={memoryTrend}
            icon={<MemoryStick className="w-6 h-6 text-primary-600" />}
            subtitle={`${dashboard.system.memory.available_gb.toFixed(1)} GB ${t("available", { default: "available" })}`}
          />
          <StatCard
            title={t("diskUsage", { default: "Disk" })}
            value={`${dashboard.system.disk.percent_used.toFixed(1)}%`}
            trend={`${dashboard.system.disk.free_gb.toFixed(1)} GB ${t("free", { default: "free" })}`}
            trendDirection={diskTrend}
            icon={<HardDrive className="w-6 h-6 text-primary-600" />}
            subtitle={`${dashboard.system.disk.total_gb.toFixed(1)} GB ${t("total", { default: "total" })}`}
          />
          <StatCard
            title={t("database", { default: "Database" })}
            value={`${dashboard.database.latency_ms.toFixed(1)} ms`}
            trend={dashboard.database.status.toUpperCase()}
            trendDirection={dashboard.database.status === "ok" ? "neutral" : "up"}
            icon={<Database className="w-6 h-6 text-primary-600" />}
            subtitle={dashboard.database.version ? `v${dashboard.database.version}` : undefined}
          />
          <StatCard
            title={t("redis", { default: "Redis" })}
            value={
              dashboard.redis.latency_ms ? `${dashboard.redis.latency_ms.toFixed(1)} ms` : "--"
            }
            trend={dashboard.redis.status.toUpperCase()}
            trendDirection={dashboard.redis.status === "ok" ? "neutral" : "up"}
            icon={<Server className="w-6 h-6 text-primary-600" />}
            subtitle={dashboard.redis.version ? `v${dashboard.redis.version}` : undefined}
          />
          <StatCard
            title={t("uptime", { default: "Uptime" })}
            value={formatUptime(dashboard.system.uptime_seconds)}
            trend={dashboard.system.platform}
            trendDirection="neutral"
            icon={<Clock className="w-6 h-6 text-primary-600" />}
            subtitle={`Python ${dashboard.system.python_version}`}
          />
        </div>

        {/* Service Status + Resource Breakdown */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Service Status ChartCard */}
          <ChartCard
            title={t("serviceStatus", { default: "Service Status" })}
            subtitle={t("serviceStatusSubtitle", { default: "Database & Redis health" })}
          >
            <div className="space-y-6">
              <div className="flex items-center justify-between p-4 bg-surface-hover dark:bg-slate-800 rounded-lg">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-primary-100 dark:bg-primary-800 rounded-md">
                    <Database className="w-5 h-5 text-primary-600 dark:text-primary-400" />
                  </div>
                  <div>
                    <Text color="primary" className="font-medium dark:text-white">
                      {t("database", { default: "Database" })}
                    </Text>
                    <Caption color="tertiary">
                      {t("latency", { default: "Latency" })}:{" "}
                      {dashboard.database.latency_ms.toFixed(2)} ms
                      {dashboard.database.active_connections !== undefined &&
                        ` • ${dashboard.database.active_connections} ${t("connections", { default: "connections" })}`}
                    </Caption>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {getStatusBadge(dashboard.database.status)}
                  {dashboard.database.database_size && (
                    <Caption color="tertiary">{dashboard.database.database_size}</Caption>
                  )}
                </div>
              </div>

              <div className="flex items-center justify-between p-4 bg-surface-hover dark:bg-slate-800 rounded-lg">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-primary-100 dark:bg-primary-800 rounded-md">
                    <Server className="w-5 h-5 text-primary-600 dark:text-primary-400" />
                  </div>
                  <div>
                    <Text color="primary" className="font-medium dark:text-white">
                      Redis
                    </Text>
                    <Caption color="tertiary">
                      {dashboard.redis.latency_ms
                        ? `${t("latency", { default: "Latency" })}: ${dashboard.redis.latency_ms.toFixed(2)} ms`
                        : t("status", { default: "Status" })}
                      {dashboard.redis.connected_clients !== undefined &&
                        ` • ${dashboard.redis.connected_clients} ${t("clients", { default: "clients" })}`}
                    </Caption>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {getStatusBadge(dashboard.redis.status)}
                  {dashboard.redis.used_memory && (
                    <Caption color="tertiary">{dashboard.redis.used_memory}</Caption>
                  )}
                </div>
              </div>

              <StatusTimeline steps={statusSteps} />
            </div>
          </ChartCard>

          {/* Resource Breakdown ChartCard */}
          <ChartCard
            title={t("resourceBreakdown", { default: "Resource Breakdown" })}
            subtitle={t("resourceBreakdownSubtitle", { default: "Current utilization" })}
          >
            <div className="space-y-6">
              {/* CPU Bar */}
              <div>
                <div className="flex justify-between mb-2">
                  <Text color="secondary" className="text-sm dark:text-slate-300">
                    {t("cpu", { default: "CPU" })}
                  </Text>
                  <Caption color="tertiary">{dashboard.system.cpu_percent.toFixed(1)}%</Caption>
                </div>
                <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full transition-all duration-500 ${
                      dashboard.system.cpu_percent > 80
                        ? "bg-danger-500"
                        : dashboard.system.cpu_percent > 60
                          ? "bg-warning-500"
                          : "bg-success-500"
                    }`}
                    style={{ width: `${Math.min(dashboard.system.cpu_percent, 100)}%` }}
                  />
                </div>
              </div>

              {/* Memory Bar */}
              <div>
                <div className="flex justify-between mb-2">
                  <Text color="secondary" className="text-sm dark:text-slate-300">
                    {t("memory", { default: "Memory" })}
                  </Text>
                  <Caption color="tertiary">
                    {dashboard.system.memory.used_gb.toFixed(1)} /{" "}
                    {dashboard.system.memory.total_gb.toFixed(1)} GB
                  </Caption>
                </div>
                <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full transition-all duration-500 ${
                      dashboard.system.memory.percent_used > 80
                        ? "bg-danger-500"
                        : dashboard.system.memory.percent_used > 60
                          ? "bg-warning-500"
                          : "bg-success-500"
                    }`}
                    style={{ width: `${Math.min(dashboard.system.memory.percent_used, 100)}%` }}
                  />
                </div>
              </div>

              {/* Disk Bar */}
              <div>
                <div className="flex justify-between mb-2">
                  <Text color="secondary" className="text-sm dark:text-slate-300">
                    {t("disk", { default: "Disk" })}
                  </Text>
                  <Caption color="tertiary">
                    {dashboard.system.disk.used_gb.toFixed(1)} /{" "}
                    {dashboard.system.disk.total_gb.toFixed(1)} GB
                  </Caption>
                </div>
                <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full transition-all duration-500 ${
                      dashboard.system.disk.percent_used > 80
                        ? "bg-danger-500"
                        : dashboard.system.disk.percent_used > 60
                          ? "bg-warning-500"
                          : "bg-success-500"
                    }`}
                    style={{ width: `${Math.min(dashboard.system.disk.percent_used, 100)}%` }}
                  />
                </div>
              </div>

              {/* Database Pool (if available) */}
              {dashboard.database.pool && (
                <div>
                  <div className="flex justify-between mb-2">
                    <Text color="secondary" className="text-sm dark:text-slate-300">
                      {t("poolConnections", { default: "DB Pool" })}
                    </Text>
                    <Caption color="tertiary">
                      {dashboard.database.pool.checked_out} / {dashboard.database.pool.size} active
                    </Caption>
                  </div>
                  <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2">
                    <div
                      className="h-2 rounded-full bg-info-500 transition-all duration-500"
                      style={{
                        width: `${Math.min(
                          (dashboard.database.pool.checked_out / dashboard.database.pool.size) *
                            100,
                          100
                        )}%`,
                      }}
                    />
                  </div>
                </div>
              )}
            </div>
          </ChartCard>
        </div>

        {/* AI Models Table */}
        <ChartCard
          title={t("aiModels", { default: "AI Models" })}
          subtitle={t("aiModelsSubtitle", { default: "Configured AI providers" })}
        >
          <DataTable
            data={dashboard.ai_models}
            columns={aiModelColumns}
            showPagination={false}
            showRowBorder={true}
            emptyState={{
              icon: <Zap className="w-12 h-12" />,
              title: t("noAiModels", { default: "No AI models configured" }),
              description: t("noAiModelsDesc", { default: "Add models in settings" }),
            }}
          />
        </ChartCard>

        {/* Features Grid */}
        <ChartCard
          title={t("features", { default: "Features" })}
          subtitle={t("featuresSubtitle", { default: "Enabled system features" })}
        >
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {Object.entries(dashboard.features).map(([key, value]) => (
              <div
                key={key}
                className="flex items-center gap-3 p-3 bg-surface-hover dark:bg-slate-800 rounded-lg"
              >
                {value ? (
                  <CheckCircle className="w-5 h-5 text-success-500 shrink-0" />
                ) : (
                  <XCircle className="w-5 h-5 text-text-disabled shrink-0" />
                )}
                <Text color="secondary" className="text-sm capitalize dark:text-slate-300">
                  {key.replace(/_/g, " ")}
                </Text>
              </div>
            ))}
          </div>
        </ChartCard>

        <Caption color="tertiary" className="text-center block">
          {t("lastUpdated", { default: "Last updated" })}:{" "}
          {new Date(dashboard.timestamp).toLocaleString()}
        </Caption>
      </main>
    </div>
  );
}
