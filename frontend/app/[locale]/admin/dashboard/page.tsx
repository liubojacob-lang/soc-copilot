"use client";

/**
 * System Dashboard Page
 * 系统仪表盘 - 显示系统整体健康状态、资源使用情况、功能开关等
 * 重构：采用 8pt 网格、设计令牌、Typography、StatCard、ChartCard、DataTable
 */

import { useEffect, useState, useMemo } from "react";
import { useTranslations } from "next-intl";
import { apiClient } from "@/lib/api/client";
import { PageHeader } from "@/components/common/PageHeader";
import { StatCard } from "@/components/dashboard/StatCard";
import { ChartCard } from "@/components/dashboard/ChartCard";
import { DataTable, ColumnDef } from "@/components/ui/DataTable";
import { Text, Caption } from "@/components/ui/Typography";
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
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Zap,
  ChevronRight,
} from "lucide-react";
import { ConnectionDetailsModal } from "./components/ConnectionDetailsModal";
import { DiagnosticsModal } from "./components/DiagnosticsModal";

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

interface ConnectionSummary {
  health_score: number;
  warnings: string[];
}

interface ModelTestResult {
  testing?: boolean;
  success?: boolean;
  latency_ms?: number;
  error_message?: string | null;
  response?: string | null;
}

interface TestModelApiResponse {
  success: boolean;
  model_id: string;
  latency_ms?: number;
  provider_raw?: string | null;
  error_message?: string | null;
  response?: string | null;
}

export default function SystemDashboardPage() {
  const t = useTranslations("adminDashboard");
  const tCommon = useTranslations("common");
  const [dashboard, setDashboard] = useState<SystemDashboard | null>(null);
  const [connSummary, setConnSummary] = useState<ConnectionSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  // Modals state
  const [connModalOpen, setConnModalOpen] = useState(false);
  const [connModalTab, setConnModalTab] = useState<"database" | "redis" | "integrations">(
    "database"
  );
  const [diagModalOpen, setDiagModalOpen] = useState(false);

  // AI Models test state
  const [modelTestResults, setModelTestResults] = useState<Record<string, ModelTestResult>>({});
  const [testingAllModels, setTestingAllModels] = useState(false);

  const handleTestModel = async (modelId: string) => {
    setModelTestResults((prev) => ({
      ...prev,
      [modelId]: { testing: true },
    }));
    try {
      const res = await apiClient.post<TestModelApiResponse>("/api/v1/ai/models/test", {
        model_id: modelId,
      });
      setModelTestResults((prev) => ({
        ...prev,
        [modelId]: {
          testing: false,
          success: res.success,
          latency_ms: res.latency_ms,
          error_message: res.error_message,
          response: res.response,
        },
      }));
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : "Failed to test model";
      setModelTestResults((prev) => ({
        ...prev,
        [modelId]: {
          testing: false,
          success: false,
          error_message: errMsg,
        },
      }));
    }
  };

  const handleTestAllModels = async () => {
    if (!dashboard?.ai_models || dashboard.ai_models.length === 0) return;
    setTestingAllModels(true);
    const initial: Record<string, ModelTestResult> = {};
    dashboard.ai_models.forEach((m) => {
      initial[m.id] = { testing: true };
    });
    setModelTestResults((prev) => ({ ...prev, ...initial }));

    await Promise.allSettled(
      dashboard.ai_models.map(async (m) => {
        try {
          const res = await apiClient.post<TestModelApiResponse>("/api/v1/ai/models/test", {
            model_id: m.id,
          });
          setModelTestResults((prev) => ({
            ...prev,
            [m.id]: {
              testing: false,
              success: res.success,
              latency_ms: res.latency_ms,
              error_message: res.error_message,
              response: res.response,
            },
          }));
        } catch (err: unknown) {
          const errMsg = err instanceof Error ? err.message : "Failed to test model";
          setModelTestResults((prev) => ({
            ...prev,
            [m.id]: {
              testing: false,
              success: false,
              error_message: errMsg,
            },
          }));
        }
      })
    );
    setTestingAllModels(false);
  };

  const fetchDashboard = async () => {
    try {
      setLoading(true);
      setError(null);

      const [data, conns] = await Promise.all([
        apiClient.get<SystemDashboard>("/api/v1/system/dashboard"),
        apiClient.get<ConnectionSummary>("/api/v1/system/connections").catch(() => null),
      ]);
      setDashboard(data);
      if (conns) {
        setConnSummary(conns);
      }
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
        header: t("modelName"),
        cell: (row) => (
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-warning-600 shrink-0" />
            <span className="font-medium text-text-primary dark:text-white truncate">
              {row.name}
            </span>
          </div>
        ),
        width: "24%",
      },
      {
        key: "provider",
        header: t("provider"),
        cell: (row) => <Caption color="tertiary">{row.provider}</Caption>,
        width: "14%",
      },
      {
        key: "status",
        header: t("status"),
        cell: (row) => (
          <Badge severity={row.is_active ? "low" : "neutral"}>
            {row.is_active ? t("active") : t("inactive")}
          </Badge>
        ),
        width: "12%",
      },
      {
        key: "connection",
        header: t("connectionStatus"),
        cell: (row) => {
          const result = modelTestResults[row.id];
          if (result?.testing) {
            return (
              <div className="flex items-center gap-1.5 text-xs text-primary-600 dark:text-primary-400 font-medium">
                <RefreshCw className="w-3.5 h-3.5 animate-spin shrink-0" />
                <span>{t("testing")}</span>
              </div>
            );
          }
          if (result) {
            return (
              <div className="flex items-center gap-2 flex-wrap">
                {result.success ? (
                  <span
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800"
                    title={`Response: ${result.response || "OK"}`}
                  >
                    <CheckCircle2 className="w-3 h-3 text-emerald-600 dark:text-emerald-400 shrink-0" />
                    <span>{t("connected")}</span>
                    {result.latency_ms !== undefined && (
                      <span className="font-mono opacity-80 text-[11px]">
                        ({result.latency_ms.toFixed(0)}ms)
                      </span>
                    )}
                  </span>
                ) : (
                  <span
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-rose-50 text-rose-700 border border-rose-200 dark:bg-rose-950/40 dark:text-rose-300 dark:border-rose-800"
                    title={result.error_message || t("connectionFailed")}
                  >
                    <XCircle className="w-3 h-3 text-rose-600 dark:text-rose-400 shrink-0" />
                    <span>{t("connectionFailed")}</span>
                    {result.latency_ms !== undefined && (
                      <span className="font-mono opacity-80 text-[11px]">
                        ({result.latency_ms.toFixed(0)}ms)
                      </span>
                    )}
                  </span>
                )}
                <button
                  onClick={() => handleTestModel(row.id)}
                  disabled={!row.is_active}
                  className="p-1 text-gray-400 hover:text-primary-600 dark:hover:text-primary-400 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                  title={t("retest")}
                >
                  <RefreshCw className="w-3 h-3" />
                </button>
              </div>
            );
          }
          return (
            <button
              onClick={() => handleTestModel(row.id)}
              disabled={!row.is_active}
              className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-md border border-gray-200 dark:border-gray-700 bg-white hover:bg-gray-50 text-gray-700 dark:bg-gray-800 dark:hover:bg-gray-750 dark:text-gray-200 transition-colors shadow-2xs disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <Zap className="w-3 h-3 text-warning-500 shrink-0" />
              <span>{t("testConnection")}</span>
            </button>
          );
        },
        width: "26%",
      },
      {
        key: "requests",
        header: t("requests"),
        cell: (row) => (
          <span className="font-mono text-sm text-text-primary dark:text-white">
            {row.total_requests.toLocaleString()}
          </span>
        ),
        width: "12%",
      },
      {
        key: "last_used",
        header: t("lastUsed"),
        cell: (row) => (
          <Caption color="tertiary">
            {row.last_used ? new Date(row.last_used).toLocaleString() : "--"}
          </Caption>
        ),
        width: "12%",
      },
    ],
    [t, modelTestResults]
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

  const headerActions = useMemo(() => {
    if (!dashboard) return null;
    return (
      <div className="flex items-center gap-3 flex-wrap">
        <span className="text-xs px-2.5 py-1 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 font-mono">
          v{dashboard.version} • {dashboard.environment}
        </span>
        {connSummary !== null && (
          <button
            onClick={() => setDiagModalOpen(true)}
            title={t("healthScoreDesc")}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border transition-all cursor-pointer shadow-xs ${
              connSummary.health_score >= 80
                ? "bg-emerald-50 text-emerald-700 border-emerald-300 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800 hover:bg-emerald-100 dark:hover:bg-emerald-900/60"
                : connSummary.health_score >= 60
                  ? "bg-amber-50 text-amber-700 border-amber-300 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800 hover:bg-amber-100 dark:hover:bg-amber-900/60"
                  : "bg-rose-50 text-rose-700 border-rose-300 dark:bg-rose-950/40 dark:text-rose-300 dark:border-rose-800 hover:bg-rose-100 dark:hover:bg-rose-900/60"
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            <span>
              {t("healthScore")}: {connSummary.health_score}
            </span>
          </button>
        )}
        <button
          onClick={() => {
            setConnModalTab("database");
            setConnModalOpen(true);
          }}
          className="px-3 py-1.5 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-200 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-750 flex items-center gap-2 text-sm font-medium transition-colors shadow-xs"
        >
          <Database className="w-3.5 h-3.5 text-primary-600 dark:text-primary-400" />
          <span>{t("viewConnections")}</span>
        </button>
        <button
          onClick={() => setDiagModalOpen(true)}
          className="px-3 py-1.5 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-200 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-750 flex items-center gap-2 text-sm font-medium transition-colors shadow-xs"
        >
          <Zap className="w-3.5 h-3.5 text-warning-500" />
          <span>{t("runDiagnostics")}</span>
        </button>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500 dark:text-gray-400">{t("autoRefresh")}</span>
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
              autoRefresh ? "bg-blue-600" : "bg-gray-300 dark:bg-gray-600"
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
          className="px-3.5 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 text-sm font-medium transition-colors shadow-sm"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          <span>{tCommon("refresh")}</span>
        </button>
      </div>
    );
  }, [dashboard, connSummary, autoRefresh, loading, t, tCommon]);

  if (loading && !dashboard) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <PageHeader title={t("title")} subtitle={t("subtitle")} />
        <main className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex items-center justify-center min-h-[50vh]">
            <RefreshCw className="w-8 h-8 animate-spin text-gray-400" />
          </div>
        </main>
      </div>
    );
  }

  if (error && !dashboard) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <PageHeader title={t("title")} subtitle={t("subtitle")} />
        <main className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <EmptyState
            icon="alert"
            title={t("error")}
            description={error}
            action={
              <button
                onClick={fetchDashboard}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
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
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <PageHeader title={t("title")} subtitle={t("subtitle")} actions={headerActions} />

      <main className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Warnings Banner */}
        {connSummary?.warnings && connSummary.warnings.length > 0 && (
          <div className="p-4 rounded-xl border border-amber-300 dark:border-amber-800/80 bg-amber-50/90 dark:bg-amber-950/30 flex items-start gap-3 shadow-xs">
            <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
            <div className="space-y-1.5 flex-1 min-w-0">
              <div className="text-sm font-semibold text-amber-900 dark:text-amber-200 flex items-center gap-2">
                <span>{t("warningsTitle")}</span>
                <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-amber-200/80 text-amber-900 dark:bg-amber-900/60 dark:text-amber-200">
                  {connSummary.warnings.length}
                </span>
              </div>
              <ul className="list-disc list-inside text-xs text-amber-800 dark:text-amber-300/90 space-y-1">
                {connSummary.warnings.map((warn, idx) => (
                  <li key={idx} className="break-words">
                    {warn}
                  </li>
                ))}
              </ul>
            </div>
            <button
              onClick={() => {
                setConnModalTab("database");
                setConnModalOpen(true);
              }}
              className="text-xs font-semibold text-amber-700 dark:text-amber-300 hover:text-amber-900 dark:hover:text-amber-100 underline shrink-0 px-2 py-1 rounded hover:bg-amber-100 dark:hover:bg-amber-900/40 transition-colors"
            >
              {t("viewConnections")} &rarr;
            </button>
          </div>
        )}
        {/* KPI Cards - 4 cards in first row, 2 cards in second row = 6 total */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          <StatCard
            title={t("cpuUsage")}
            value={`${dashboard.system.cpu_percent.toFixed(1)}%`}
            trend={dashboard.system.cpu_percent > 80 ? "High" : "Normal"}
            trendDirection={cpuTrend}
            icon={<Cpu className="w-6 h-6 text-primary-600" />}
            subtitle={t("realTime")}
          />
          <StatCard
            title={t("memoryUsage")}
            value={`${dashboard.system.memory.percent_used.toFixed(1)}%`}
            trend={`${dashboard.system.memory.used_gb.toFixed(1)} / ${dashboard.system.memory.total_gb.toFixed(1)} GB`}
            trendDirection={memoryTrend}
            icon={<MemoryStick className="w-6 h-6 text-primary-600" />}
            subtitle={`${dashboard.system.memory.available_gb.toFixed(1)} GB ${t("available")}`}
          />
          <StatCard
            title={t("diskUsage")}
            value={`${dashboard.system.disk.percent_used.toFixed(1)}%`}
            trend={`${dashboard.system.disk.free_gb.toFixed(1)} GB ${t("free")}`}
            trendDirection={diskTrend}
            icon={<HardDrive className="w-6 h-6 text-primary-600" />}
            subtitle={`${dashboard.system.disk.total_gb.toFixed(1)} GB ${t("total")}`}
          />
          <StatCard
            title={t("database")}
            value={`${dashboard.database.latency_ms.toFixed(1)} ms`}
            trend={dashboard.database.status.toUpperCase()}
            trendDirection={dashboard.database.status === "ok" ? "neutral" : "up"}
            icon={<Database className="w-6 h-6 text-primary-600" />}
            subtitle={dashboard.database.version ? `v${dashboard.database.version}` : undefined}
          />
          <StatCard
            title={t("redis")}
            value={
              dashboard.redis.latency_ms ? `${dashboard.redis.latency_ms.toFixed(1)} ms` : "--"
            }
            trend={dashboard.redis.status.toUpperCase()}
            trendDirection={dashboard.redis.status === "ok" ? "neutral" : "up"}
            icon={<Server className="w-6 h-6 text-primary-600" />}
            subtitle={dashboard.redis.version ? `v${dashboard.redis.version}` : undefined}
          />
          <StatCard
            title={t("uptime")}
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
          <ChartCard title={t("serviceStatus")} subtitle={t("serviceStatusSubtitle")}>
            <div className="space-y-6">
              <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700/40 border border-gray-100 dark:border-gray-700/50 rounded-lg">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-blue-50 dark:bg-blue-900/30 rounded-lg">
                    <Database className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                  </div>
                  <div>
                    <Text color="primary" className="font-medium dark:text-white">
                      {t("database")}
                    </Text>
                    <Caption color="tertiary">
                      {t("latency")}: {dashboard.database.latency_ms.toFixed(2)} ms
                      {dashboard.database.active_connections !== undefined &&
                        ` • ${dashboard.database.active_connections} ${t("connections")}`}
                    </Caption>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {dashboard.database.database_size && (
                    <Caption color="tertiary">{dashboard.database.database_size}</Caption>
                  )}
                  {getStatusBadge(dashboard.database.status)}
                  <button
                    onClick={() => {
                      setConnModalTab("database");
                      setConnModalOpen(true);
                    }}
                    className="px-2.5 py-1 text-xs font-medium rounded-md border border-gray-200 dark:border-gray-700 bg-white hover:bg-gray-50 text-primary-600 dark:bg-gray-800 dark:hover:bg-gray-750 dark:text-primary-400 transition-colors flex items-center gap-1 shadow-xs"
                    title={t("viewConnections")}
                  >
                    <span>{t("viewConnections")}</span>
                    <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700/40 border border-gray-100 dark:border-gray-700/50 rounded-lg">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-blue-50 dark:bg-blue-900/30 rounded-lg">
                    <Server className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                  </div>
                  <div>
                    <Text color="primary" className="font-medium dark:text-white">
                      Redis
                    </Text>
                    <Caption color="tertiary">
                      {dashboard.redis.latency_ms
                        ? `${t("latency")}: ${dashboard.redis.latency_ms.toFixed(2)} ms`
                        : t("status")}
                      {dashboard.redis.connected_clients !== undefined &&
                        ` • ${dashboard.redis.connected_clients} ${t("clients")}`}
                    </Caption>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {dashboard.redis.used_memory && (
                    <Caption color="tertiary">{dashboard.redis.used_memory}</Caption>
                  )}
                  {getStatusBadge(dashboard.redis.status)}
                  <button
                    onClick={() => {
                      setConnModalTab("redis");
                      setConnModalOpen(true);
                    }}
                    className="px-2.5 py-1 text-xs font-medium rounded-md border border-gray-200 dark:border-gray-700 bg-white hover:bg-gray-50 text-primary-600 dark:bg-gray-800 dark:hover:bg-gray-750 dark:text-primary-400 transition-colors flex items-center gap-1 shadow-xs"
                    title={t("viewConnections")}
                  >
                    <span>{t("viewConnections")}</span>
                    <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              <StatusTimeline steps={statusSteps} />
            </div>
          </ChartCard>

          {/* Resource Breakdown ChartCard */}
          <ChartCard title={t("resourceBreakdown")} subtitle={t("resourceBreakdownSubtitle")}>
            <div className="space-y-6">
              {/* CPU Bar */}
              <div>
                <div className="flex justify-between mb-2">
                  <Text color="secondary" className="text-sm dark:text-slate-300">
                    {t("cpu")}
                  </Text>
                  <Caption color="tertiary">{dashboard.system.cpu_percent.toFixed(1)}%</Caption>
                </div>
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
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
                    {t("memory")}
                  </Text>
                  <Caption color="tertiary">
                    {dashboard.system.memory.used_gb.toFixed(1)} /{" "}
                    {dashboard.system.memory.total_gb.toFixed(1)} GB
                  </Caption>
                </div>
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
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
                    {t("disk")}
                  </Text>
                  <Caption color="tertiary">
                    {dashboard.system.disk.used_gb.toFixed(1)} /{" "}
                    {dashboard.system.disk.total_gb.toFixed(1)} GB
                  </Caption>
                </div>
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
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
                      {t("poolConnections")}
                    </Text>
                    <Caption color="tertiary">
                      {dashboard.database.pool.checked_out} / {dashboard.database.pool.size} active
                    </Caption>
                  </div>
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
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
          title={t("aiModels")}
          subtitle={t("aiModelsSubtitle")}
          action={
            dashboard.ai_models && dashboard.ai_models.length > 0 ? (
              <button
                onClick={handleTestAllModels}
                disabled={testingAllModels}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-primary-200 dark:border-primary-800 bg-primary-50 hover:bg-primary-100 dark:bg-primary-950/40 dark:hover:bg-primary-900/60 text-primary-700 dark:text-primary-300 transition-colors shadow-2xs disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${testingAllModels ? "animate-spin" : ""}`} />
                <span>{testingAllModels ? t("testing") : t("testAllModels")}</span>
              </button>
            ) : undefined
          }
        >
          <DataTable
            data={dashboard.ai_models}
            columns={aiModelColumns}
            showPagination={false}
            showRowBorder={true}
            emptyState={{
              icon: <Zap className="w-12 h-12" />,
              title: t("noAiModels"),
              description: t("noAiModelsDesc"),
            }}
          />
        </ChartCard>

        {/* Features Grid */}
        <ChartCard title={t("features")} subtitle={t("featuresSubtitle")}>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {Object.entries(dashboard.features).map(([key, value]) => (
              <div
                key={key}
                className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-700/40 border border-gray-100 dark:border-gray-700/50 rounded-lg"
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
          {t("lastUpdated")}: {new Date(dashboard.timestamp).toLocaleString()}
        </Caption>
      </main>

      <ConnectionDetailsModal
        open={connModalOpen}
        onClose={() => setConnModalOpen(false)}
        initialTab={connModalTab}
      />

      <DiagnosticsModal open={diagModalOpen} onClose={() => setDiagModalOpen(false)} />
    </div>
  );
}
