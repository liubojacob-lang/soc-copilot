"use client";

import { useEffect, useState, useMemo } from "react";
import { useTranslations } from "next-intl";
import { Modal } from "@/components/common/Modal";
import { TabList, TabButton } from "@/components/ui/Tabs";
import { DataTable, ColumnDef } from "@/components/ui/DataTable";
import { Badge } from "@/components/ui/Badge";
import { Text, Caption } from "@/components/ui/Typography";
import { apiClient } from "@/lib/api/client";
import {
  Database,
  Server,
  Radio,
  RefreshCw,
  AlertTriangle,
  Zap,
  RotateCcw,
  Shield,
  Activity,
  Layers,
  StopCircle,
} from "lucide-react";

export interface DBConnectionItem {
  pid: number;
  usename: string;
  client_addr: string | null;
  state: string;
  duration_seconds: number;
  wait_event_type: string | null;
  wait_event: string | null;
  query: string;
  is_slow: boolean;
  is_idle_tx: boolean;
}

export interface PoolStatus {
  size: number;
  checked_in: number;
  checked_out: number;
  overflow: number;
  invalid: number;
}

export interface DBConnectionsDetail {
  engine: string;
  summary: {
    active?: number;
    idle?: number;
    idle_in_transaction?: number;
    waiting?: number;
    total?: number;
  };
  pool: PoolStatus | null;
  pool_utilization: number;
  connections: DBConnectionItem[];
}

export interface RedisClientItem {
  id: string;
  addr: string;
  age_seconds: number;
  idle_seconds: number;
  cmd: string;
  flags: string;
  name: string;
}

export interface RedisConnectionsDetail {
  status: string;
  summary: {
    connected_clients?: number;
    pubsub_clients?: number;
    blocked_clients?: number;
    max_clients?: number;
    used_memory?: string;
    peak_memory?: string;
    fragmentation_ratio?: number;
    hit_rate_percent?: number;
  };
  clients: RedisClientItem[];
  queue: {
    health?: Record<string, boolean>;
    queues?: Record<string, { stream?: string; length?: number; pending?: number }>;
  };
}

export interface SystemIntegrationsDetail {
  websocket_connections: number;
  wazuh: { enabled: boolean; api_url: string };
  threat_intel: { otx: boolean; virustotal: boolean; misp: boolean; abuseipdb: boolean };
  ai_models_count: number;
}

export interface ConnectionsDashboardResponse {
  timestamp: string;
  health_score: number;
  warnings: string[];
  database: DBConnectionsDetail;
  redis: RedisConnectionsDetail;
  integrations: SystemIntegrationsDetail;
}

interface ConnectionDetailsModalProps {
  open: boolean;
  onClose: () => void;
  initialTab?: "database" | "redis" | "integrations";
}

export function ConnectionDetailsModal({
  open,
  onClose,
  initialTab = "database",
}: ConnectionDetailsModalProps) {
  const t = useTranslations("adminDashboard.connectionDetails");
  const tCommon = useTranslations("common");
  const [activeTab, setActiveTab] = useState<"database" | "redis" | "integrations">(initialTab);
  const [data, setData] = useState<ConnectionsDashboardResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [terminatingPid, setTerminatingPid] = useState<number | null>(null);
  const [replayingDlq, setReplayingDlq] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setActiveTab(initialTab);
      fetchConnections();
    }
  }, [open, initialTab]);

  const fetchConnections = async () => {
    try {
      setLoading(true);
      setError(null);
      setActionMessage(null);
      const res = await apiClient.get<ConnectionsDashboardResponse>("/api/v1/system/connections");
      setData(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load connection details");
    } finally {
      setLoading(false);
    }
  };

  const handleTerminateConnection = async (pid: number) => {
    if (!window.confirm(t("terminateConfirm", { pid }))) return;
    try {
      setTerminatingPid(pid);
      await apiClient.post(`/api/v1/system/connections/db/${pid}/terminate`);
      setActionMessage(t("terminatedSuccess"));
      await fetchConnections();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to terminate connection");
    } finally {
      setTerminatingPid(null);
    }
  };

  const handleReplayDlq = async () => {
    try {
      setReplayingDlq(true);
      const res = await apiClient.post<{ replayed_count: number }>("/api/v1/system/queue/dlq/replay", {
        target_stream: "events:medium",
        limit: 100,
      });
      setActionMessage(t("replayedSuccess", { count: res.replayed_count }));
      await fetchConnections();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to replay DLQ messages");
    } finally {
      setReplayingDlq(false);
    }
  };

  const formatSeconds = (sec: number) => {
    if (sec < 60) return `${sec}s`;
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    if (m < 60) return `${m}m ${s}s`;
    const h = Math.floor(m / 60);
    return `${h}h ${m % 60}m`;
  };

  const dbColumns = useMemo<ColumnDef<DBConnectionItem>[]>(
    () => [
      {
        key: "pid",
        header: t("pid"),
        cell: (row) => <span className="font-mono text-xs font-semibold">{row.pid}</span>,
        width: "8%",
      },
      {
        key: "client_addr",
        header: t("clientAddr"),
        cell: (row) => (
          <Caption color="secondary" className="font-mono text-xs truncate">
            {row.client_addr || "local"}
          </Caption>
        ),
        width: "14%",
      },
      {
        key: "state",
        header: t("state"),
        cell: (row) => {
          const isAct = row.state === "active";
          const isIdleTx = row.state.includes("idle in transaction");
          const sev: "low" | "critical" | "neutral" = isAct
            ? "low"
            : isIdleTx
              ? "critical"
              : "neutral";
          return (
            <Badge severity={sev} size="xs">
              {row.state}
            </Badge>
          );
        },
        width: "14%",
      },
      {
        key: "duration_seconds",
        header: t("duration"),
        cell: (row) => (
          <span
            className={`font-mono text-xs ${
              row.is_slow || row.is_idle_tx ? "text-danger-600 font-bold" : "text-text-secondary"
            }`}
          >
            {row.duration_seconds.toFixed(2)}s
          </span>
        ),
        width: "10%",
      },
      {
        key: "wait_event",
        header: t("waitEvent"),
        cell: (row) => (
          <Caption color="tertiary" className="text-xs truncate">
            {row.wait_event ? `${row.wait_event_type || ""}:${row.wait_event}` : "--"}
          </Caption>
        ),
        width: "14%",
      },
      {
        key: "query",
        header: t("query"),
        cell: (row) => (
          <span
            className="font-mono text-xs text-text-tertiary truncate block max-w-[280px]"
            title={row.query}
          >
            {row.query || "--"}
          </span>
        ),
        width: "30%",
      },
      {
        key: "actions",
        header: t("actions"),
        cell: (row) => (
          <button
            onClick={() => handleTerminateConnection(row.pid)}
            disabled={terminatingPid === row.pid}
            className="text-xs text-danger-600 hover:text-danger-800 dark:text-danger-400 font-medium flex items-center gap-1 disabled:opacity-40"
          >
            <StopCircle className="w-3.5 h-3.5" />
            <span>{t("terminate")}</span>
          </button>
        ),
        width: "10%",
      },
    ],
    [t, terminatingPid]
  );

  const redisColumns = useMemo<ColumnDef<RedisClientItem>[]>(
    () => [
      {
        key: "id",
        header: t("clientId"),
        cell: (row) => <span className="font-mono text-xs font-semibold">{row.id}</span>,
        width: "10%",
      },
      {
        key: "addr",
        header: t("clientAddr"),
        cell: (row) => <span className="font-mono text-xs">{row.addr}</span>,
        width: "25%",
      },
      {
        key: "age_seconds",
        header: t("age"),
        cell: (row) => (
          <span className="font-mono text-xs text-text-secondary">
            {formatSeconds(row.age_seconds)}
          </span>
        ),
        width: "15%",
      },
      {
        key: "idle_seconds",
        header: t("idle"),
        cell: (row) => (
          <span className="font-mono text-xs text-text-tertiary">
            {formatSeconds(row.idle_seconds)}
          </span>
        ),
        width: "15%",
      },
      {
        key: "cmd",
        header: t("lastCmd"),
        cell: (row) => (
          <span className="font-mono text-xs px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-primary-600 dark:text-primary-400">
            {row.cmd}
          </span>
        ),
        width: "20%",
      },
      {
        key: "flags",
        header: t("flags"),
        cell: (row) => <Caption color="tertiary">{row.flags}</Caption>,
        width: "15%",
      },
    ],
    [t]
  );

  const pool = data?.database.pool;
  const dbSummary = data?.database.summary;
  const redisSummary = data?.redis.summary;

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-50 dark:bg-blue-900/30 rounded-lg">
            <Activity className="w-5 h-5 text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-text-primary dark:text-white">
              {t("title")}
            </h3>
            <p className="text-xs text-text-tertiary">{t("subtitle")}</p>
          </div>
        </div>
      }
      contentClassName="w-full max-w-5xl"
    >
      <div className="space-y-4">
        {/* Top Control & Tabs */}
        <div className="flex items-center justify-between border-b border-border-default pb-2">
          <TabList>
            <TabButton
              label={t("tabDatabase")}
              icon={<Database className="w-4 h-4" />}
              active={activeTab === "database"}
              onClick={() => setActiveTab("database")}
              badge={dbSummary?.total}
              badgeSeverity="neutral"
            />
            <TabButton
              label={t("tabRedis")}
              icon={<Server className="w-4 h-4" />}
              active={activeTab === "redis"}
              onClick={() => setActiveTab("redis")}
              badge={redisSummary?.connected_clients}
              badgeSeverity="neutral"
            />
            <TabButton
              label={t("tabIntegrations")}
              icon={<Radio className="w-4 h-4" />}
              active={activeTab === "integrations"}
              onClick={() => setActiveTab("integrations")}
            />
          </TabList>

          <button
            onClick={fetchConnections}
            disabled={loading}
            className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 text-xs font-medium rounded-lg flex items-center gap-1.5 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>{tCommon("refresh")}</span>
          </button>
        </div>

        {/* Action message banner */}
        {actionMessage && (
          <div className="p-3 bg-success-50 dark:bg-success-900/20 border border-success-200 dark:border-success-800/50 rounded-lg text-xs text-success-700 dark:text-success-300">
            {actionMessage}
          </div>
        )}

        {/* Error state */}
        {error && (
          <div className="p-3 bg-danger-50 dark:bg-danger-900/20 border border-danger-200 dark:border-danger-800/50 rounded-lg text-xs text-danger-700 dark:text-danger-300">
            {error}
          </div>
        )}

        {/* Loading state */}
        {loading && !data && (
          <div className="py-12 flex items-center justify-center">
            <RefreshCw className="w-6 h-6 animate-spin text-primary-500" />
          </div>
        )}

        {/* Tab 1: Database */}
        {data && activeTab === "database" && (
          <div className="space-y-4">
            {/* Database Metric Badges */}
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
              <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-border-default">
                <Caption color="tertiary">{t("activeConns")}</Caption>
                <div className="text-lg font-bold text-success-600 dark:text-success-400">
                  {dbSummary?.active || 0}
                </div>
              </div>
              <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-border-default">
                <Caption color="tertiary">{t("idleConns")}</Caption>
                <div className="text-lg font-bold text-text-primary dark:text-white">
                  {dbSummary?.idle || 0}
                </div>
              </div>
              <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-border-default">
                <Caption color="tertiary">{t("idleInTx")}</Caption>
                <div
                  className={`text-lg font-bold ${
                    (dbSummary?.idle_in_transaction || 0) > 0
                      ? "text-danger-600"
                      : "text-text-primary dark:text-white"
                  }`}
                >
                  {dbSummary?.idle_in_transaction || 0}
                </div>
              </div>
              <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-border-default">
                <Caption color="tertiary">{t("poolSize")}</Caption>
                <div className="text-lg font-bold text-text-primary dark:text-white">
                  {pool?.size || 0}
                </div>
              </div>
              <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-border-default">
                <Caption color="tertiary">{t("utilization")}</Caption>
                <div className="text-lg font-bold text-primary-600 dark:text-primary-400">
                  {data.database.pool_utilization.toFixed(1)}%
                </div>
              </div>
            </div>

            {/* Pool Utilization Bar */}
            {pool && (
              <div className="p-3 bg-gray-50 dark:bg-gray-800/40 rounded-lg border border-border-default space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="text-text-secondary">{t("poolSize")}</span>
                  <span className="font-mono font-medium">
                    {pool.checked_out} {t("checkedOut")} / {pool.checked_in} {t("checkedIn")} (
                    {data.database.pool_utilization.toFixed(1)}%)
                  </span>
                </div>
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                  <div
                    className="h-2 rounded-full bg-blue-600 transition-all duration-300"
                    style={{ width: `${Math.min(data.database.pool_utilization, 100)}%` }}
                  />
                </div>
              </div>
            )}

            {/* Active Connections Table */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <Text color="primary" className="text-sm font-semibold">
                  {t("dbConnections")} ({data.database.connections.length})
                </Text>
              </div>
              <DataTable
                data={data.database.connections}
                columns={dbColumns}
                showPagination={data.database.connections.length > 8}
                pageSize={8}
                showRowBorder={true}
              />
            </div>
          </div>
        )}

        {/* Tab 2: Redis & Queues */}
        {data && activeTab === "redis" && (
          <div className="space-y-4">
            {/* Redis Summary Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-border-default">
                <Caption color="tertiary">{t("clients")}</Caption>
                <div className="text-lg font-bold text-text-primary dark:text-white">
                  {redisSummary?.connected_clients || 0}
                </div>
              </div>
              <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-border-default">
                <Caption color="tertiary">{t("pubsubClients")}</Caption>
                <div className="text-lg font-bold text-text-primary dark:text-white">
                  {redisSummary?.pubsub_clients || 0}
                </div>
              </div>
              <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-border-default">
                <Caption color="tertiary">{t("fragmentation")}</Caption>
                <div className="text-lg font-bold text-primary-600 dark:text-primary-400">
                  {redisSummary?.fragmentation_ratio?.toFixed(2) || "1.00"}
                </div>
              </div>
              <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-border-default">
                <Caption color="tertiary">{t("hitRate")}</Caption>
                <div className="text-lg font-bold text-success-600 dark:text-success-400">
                  {redisSummary?.hit_rate_percent?.toFixed(1) || "100.0"}%
                </div>
              </div>
            </div>

            {/* Streams Queue Cards & DLQ */}
            <div className="p-4 bg-gray-50 dark:bg-gray-800/40 rounded-lg border border-border-default space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Layers className="w-4 h-4 text-primary-600" />
                  <Text color="primary" className="text-sm font-semibold">
                    {t("streamsQueue")}
                  </Text>
                </div>
                {/* Replay DLQ Button */}
                <button
                  onClick={handleReplayDlq}
                  disabled={replayingDlq}
                  className="px-2.5 py-1 bg-warning-500 hover:bg-warning-600 text-white rounded text-xs font-medium flex items-center gap-1.5 transition-colors disabled:opacity-50"
                >
                  <RotateCcw className={`w-3.5 h-3.5 ${replayingDlq ? "animate-spin" : ""}`} />
                  <span>{replayingDlq ? t("replaying") : t("replayDlq")}</span>
                </button>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {Object.entries(data.redis.queue.queues || {}).map(([key, q]) => (
                  <div
                    key={key}
                    className="p-2.5 bg-white dark:bg-gray-800 rounded border border-gray-100 dark:border-gray-700/60"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-mono font-medium text-text-primary dark:text-white capitalize">
                        {key}
                      </span>
                      {key === "dlq" && (q.pending || 0) > 0 && (
                        <Badge severity="critical" size="xs">
                          {q.pending} {t("dlqPending")}
                        </Badge>
                      )}
                    </div>
                    <Caption color="tertiary">
                      {t("streamLength")}: {q.length || 0}
                    </Caption>
                  </div>
                ))}
              </div>
            </div>

            {/* Redis Client List */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <Text color="primary" className="text-sm font-semibold">
                  {t("redisClients")} ({data.redis.clients.length})
                </Text>
              </div>
              <DataTable
                data={data.redis.clients}
                columns={redisColumns}
                showPagination={data.redis.clients.length > 8}
                pageSize={8}
                showRowBorder={true}
              />
            </div>
          </div>
        )}

        {/* Tab 3: Integrations & Sessions */}
        {data && activeTab === "integrations" && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* WebSocket Sessions */}
              <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-border-default space-y-2">
                <div className="flex items-center gap-2">
                  <Radio className="w-4 h-4 text-blue-600" />
                  <span className="text-sm font-semibold text-text-primary dark:text-white">
                    {t("websocketSessions")}
                  </span>
                </div>
                <div className="flex items-center justify-between pt-2">
                  <Caption color="tertiary">{t("activeWsSessions")}</Caption>
                  <span className="text-xl font-bold text-success-600">
                    {data.integrations.websocket_connections}
                  </span>
                </div>
              </div>

              {/* Wazuh SIEM */}
              <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-border-default space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Shield className="w-4 h-4 text-primary-600" />
                    <span className="text-sm font-semibold text-text-primary dark:text-white">
                      {t("wazuhStatus")}
                    </span>
                  </div>
                  <Badge severity={data.integrations.wazuh.enabled ? "low" : "neutral"} size="xs">
                    {data.integrations.wazuh.enabled ? "ENABLED" : "DISABLED"}
                  </Badge>
                </div>
                <Caption color="tertiary" className="truncate block font-mono text-xs">
                  {data.integrations.wazuh.api_url}
                </Caption>
              </div>

              {/* Threat Intel Feeds */}
              <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-border-default space-y-3 sm:col-span-2">
                <div className="flex items-center gap-2">
                  <Zap className="w-4 h-4 text-warning-600" />
                  <span className="text-sm font-semibold text-text-primary dark:text-white">
                    {t("threatIntelStatus")}
                  </span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {Object.entries(data.integrations.threat_intel).map(([feed, active]) => (
                    <div
                      key={feed}
                      className="flex items-center justify-between p-2.5 bg-white dark:bg-gray-800 rounded border border-border-default"
                    >
                      <span className="text-xs font-mono uppercase text-text-primary dark:text-white">
                        {feed}
                      </span>
                      <Badge severity={active ? "low" : "neutral"} size="xs">
                        {active ? "READY" : "NO KEY"}
                      </Badge>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}
