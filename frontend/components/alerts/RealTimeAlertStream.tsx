"use client";

import { useState, useEffect, useCallback, useMemo, memo } from "react";
import { useTranslations } from "next-intl";
import { loadAuthState } from "@/lib/auth";
import { getWazuhWebSocketClient, WazuhWebSocketClient } from "@/lib/wazuhWebSocket";
import { AlertData, SeverityLevel } from "@/types/wazuh";
import { VirtualList } from "@/components/common/VirtualList";
import {
  Bell,
  BellOff,
  Filter,
  X,
  CheckCircle,
  AlertTriangle,
  Shield,
  Activity,
  Clock,
  Server,
  RefreshCw,
  Wifi,
  WifiOff,
  Loader2,
} from "lucide-react";

const SEVERITY_COLORS: Record<SeverityLevel, string> = {
  critical:
    "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 border-red-300 dark:border-red-700",
  high: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400 border-orange-300 dark:border-orange-700",
  medium:
    "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400 border-yellow-300 dark:border-yellow-700",
  low: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 border-blue-300 dark:border-blue-700",
  info: "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-400 border-gray-300 dark:border-gray-600",
};

const SEVERITY_ICONS: Record<SeverityLevel, React.ReactNode> = {
  critical: <AlertTriangle className="w-4 h-4" />,
  high: <Shield className="w-4 h-4" />,
  medium: <Activity className="w-4 h-4" />,
  low: <Server className="w-4 h-4" />,
  info: <Clock className="w-4 h-4" />,
};

interface AlertStreamProps {
  maxAlerts?: number;
  autoScroll?: boolean;
  showFilters?: boolean;
  onAlertClick?: (alert: AlertData) => void;
}

export function WazuhAlertStream({
  maxAlerts = 100,
  autoScroll = true,
  showFilters = true,
  onAlertClick,
}: AlertStreamProps) {
  const t = useTranslations("wazuh.stream");
  const tCommon = useTranslations("common");

  // State
  const [alerts, setAlerts] = useState<AlertData[]>([]);
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [wsClient, setWsClient] = useState<WazuhWebSocketClient | null>(null);

  // Filters
  const [filters, setFilters] = useState<{
    minSeverity: SeverityLevel | "all";
    searchQuery: string;
    agentFilter: string;
  }>({
    minSeverity: "all",
    searchQuery: "",
    agentFilter: "",
  });

  const [showFiltersPanel, setShowFiltersPanel] = useState(false);
  const [streamEnabled, setStreamEnabled] = useState(true);

  // Initialize WebSocket client
  useEffect(() => {
    const authState = loadAuthState();
    if (!authState?.isAuthenticated) {
      setError("Not authenticated");
      return;
    }

    const client = getWazuhWebSocketClient({
      token: authState.tokens?.access_token,
      enableAggregation: true,
    });

    setWsClient(client);

    // Set up connection handler
    const unsubscribeConnection = client.onConnectionChange((isConnected) => {
      setConnected(isConnected);
      setConnecting(false);
      if (!isConnected && !client.getState().isManualClose) {
        setConnecting(true);
      }
    });

    // Set up alert handler
    const unsubscribeAlert = client.onAlert((alert) => {
      if (streamEnabled) {
        setAlerts((prev) => {
          const newAlerts = [alert, ...prev];
          return newAlerts.slice(0, maxAlerts);
        });
      }
    });

    // Set up error handler
    const unsubscribeError = client.onError((err) => {
      setError(err.message);
      setConnecting(false);
    });

    // Connect
    setConnecting(true);
    client.connect(authState.tokens?.access_token);

    return () => {
      unsubscribeConnection();
      unsubscribeAlert();
      unsubscribeError();
    };
  }, [maxAlerts, streamEnabled]);

  // Filter alerts
  const filteredAlerts = useMemo(() => {
    return alerts.filter((alert) => {
      // Severity filter
      if (filters.minSeverity !== "all") {
        const severityOrder: Record<SeverityLevel, number> = {
          critical: 0,
          high: 1,
          medium: 2,
          low: 3,
          info: 4,
        };
        const alertOrder = severityOrder[alert.severity];
        const minOrder = severityOrder[filters.minSeverity as SeverityLevel];
        if (alertOrder > minOrder) return false;
      }

      // Search query
      if (filters.searchQuery) {
        const query = filters.searchQuery.toLowerCase();
        const searchableText = [
          alert.title,
          alert.full_log,
          alert.source_ip,
          alert.agent.name,
          ...alert.iocs,
        ]
          .join(" ")
          .toLowerCase();
        if (!searchableText.includes(query)) return false;
      }

      // Agent filter
      if (filters.agentFilter && alert.agent.id !== filters.agentFilter) {
        return false;
      }

      return true;
    });
  }, [alerts, filters]);

  // Statistics - optimized with single reduce
  const stats = useMemo(() => {
    return alerts.reduce(
      (acc, alert) => {
        acc.total++;
        acc[alert.severity] = (acc[alert.severity] || 0) + 1;
        return acc;
      },
      { total: 0, critical: 0, high: 0, medium: 0, low: 0, info: 0 } as Record<string, number>
    );
  }, [alerts]);

  // Handle connection toggle
  const handleToggleConnection = useCallback(() => {
    if (!wsClient) return;

    if (connected) {
      wsClient.disconnect();
      setStreamEnabled(false);
    } else {
      setConnecting(true);
      const authState = loadAuthState();
      wsClient.connect(authState?.tokens?.access_token);
      setStreamEnabled(true);
    }
  }, [wsClient, connected]);

  // Clear alerts
  const handleClearAlerts = useCallback(() => {
    setAlerts([]);
  }, []);

  // Export alerts
  const handleExportAlerts = useCallback(() => {
    const data = JSON.stringify(filteredAlerts, null, 2);
    const blob = new Blob([data], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `wazuh-alerts-${new Date().toISOString()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [filteredAlerts]);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h3 className="text-lg font-semibold">{t("title")}</h3>

          {/* Connection Status */}
          <div className="flex items-center gap-2">
            {connecting && (
              <div className="flex items-center gap-2 px-3 py-1.5 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-full">
                <Loader2 className="w-4 h-4 text-yellow-600 dark:text-yellow-400 animate-spin" />
                <span className="text-sm font-medium text-yellow-700 dark:text-yellow-400">
                  Connecting...
                </span>
              </div>
            )}
            {!connecting && (
              <>
                {/* Status Badge */}
                <div
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-full border transition-colors ${
                    connected
                      ? "bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800"
                      : "bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800"
                  }`}
                >
                  {connected ? (
                    <>
                      <div className="relative">
                        <Wifi className="w-4 h-4 text-green-600 dark:text-green-400" />
                        <div className="absolute -top-1 -right-1 w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                      </div>
                      <span className="text-sm font-medium text-green-700 dark:text-green-400">
                        Live
                      </span>
                    </>
                  ) : (
                    <>
                      <WifiOff className="w-4 h-4 text-red-600 dark:text-red-400" />
                      <span className="text-sm font-medium text-red-700 dark:text-red-400">
                        Disconnected
                      </span>
                    </>
                  )}
                </div>

                {/* Toggle Button */}
                <button
                  onClick={handleToggleConnection}
                  className={`p-2 rounded-lg transition-colors ${
                    connected
                      ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 hover:bg-green-200 dark:hover:bg-green-900/40"
                      : "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600"
                  }`}
                  title={connected ? "Stop streaming" : "Start streaming"}
                >
                  {connected ? <Bell className="w-4 h-4" /> : <BellOff className="w-4 h-4" />}
                </button>
              </>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          {showFilters && (
            <button
              onClick={() => setShowFiltersPanel(!showFiltersPanel)}
              className={`p-2 rounded-lg transition-colors ${
                showFiltersPanel
                  ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                  : "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-400"
              }`}
              title={t("toggleFilters")}
            >
              <Filter className="w-4 h-4" />
            </button>
          )}
          <button
            onClick={handleClearAlerts}
            className="p-2 bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-400 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
            title={t("clearAlerts")}
          >
            <X className="w-4 h-4" />
          </button>
          <button
            onClick={handleExportAlerts}
            className="p-2 bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-400 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
            title={t("exportAlerts")}
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Statistics */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-2">
        <div className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-700">
          <div className="text-2xl font-bold text-gray-900 dark:text-white">{stats.total}</div>
          <div className="text-xs text-gray-500 dark:text-gray-400">{tCommon("total")}</div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-700">
          <div className="text-2xl font-bold text-red-600 dark:text-red-400">{stats.critical}</div>
          <div className="text-xs text-gray-500 dark:text-gray-400">{tCommon("critical")}</div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-700">
          <div className="text-2xl font-bold text-orange-600 dark:text-orange-400">
            {stats.high}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">{tCommon("high")}</div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-700">
          <div className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">
            {stats.medium}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">{tCommon("medium")}</div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-700">
          <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">{stats.low}</div>
          <div className="text-xs text-gray-500 dark:text-gray-400">{tCommon("low")}</div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-700">
          <div className="text-2xl font-bold text-gray-600 dark:text-gray-400">{stats.info}</div>
          <div className="text-xs text-gray-500 dark:text-gray-400">{tCommon("info")}</div>
        </div>
      </div>

      {/* Filters Panel */}
      {showFiltersPanel && (
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between mb-4">
            <h4 className="font-medium">{t("filters")}</h4>
            <button
              onClick={() => setShowFiltersPanel(false)}
              className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Severity Filter */}
            <div>
              <label className="block text-sm font-medium mb-2">{t("minSeverity")}</label>
              <select
                value={filters.minSeverity}
                onChange={(e) =>
                  setFilters({ ...filters, minSeverity: e.target.value as SeverityLevel | "all" })
                }
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              >
                <option value="all">{t("allSeverities")}</option>
                <option value="critical">{tCommon("critical")}</option>
                <option value="high">{tCommon("high")}</option>
                <option value="medium">{tCommon("medium")}</option>
                <option value="low">{tCommon("low")}</option>
                <option value="info">{tCommon("info")}</option>
              </select>
            </div>

            {/* Search Query */}
            <div>
              <label className="block text-sm font-medium mb-2">{t("search")}</label>
              <input
                type="text"
                value={filters.searchQuery}
                onChange={(e) => setFilters({ ...filters, searchQuery: e.target.value })}
                placeholder={t("searchPlaceholder")}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
            </div>

            {/* Agent Filter */}
            <div>
              <label className="block text-sm font-medium mb-2">{t("agent")}</label>
              <select
                value={filters.agentFilter}
                onChange={(e) => setFilters({ ...filters, agentFilter: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              >
                <option value="">{t("allAgents")}</option>
                {/* Add agent options dynamically */}
              </select>
            </div>
          </div>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className="p-1 bg-red-100 dark:bg-red-900/30 rounded-full">
                <AlertTriangle className="w-4 h-4 text-red-600 dark:text-red-400" />
              </div>
              <div>
                <p className="text-sm font-medium text-red-900 dark:text-red-100 mb-1">
                  Connection Error
                </p>
                <p className="text-sm text-red-700 dark:text-red-400">{error}</p>
                {error.includes("Authentication") && (
                  <p className="text-xs text-red-600 dark:text-red-500 mt-2">
                    Please refresh the page to re-authenticate
                  </p>
                )}
              </div>
            </div>
            <button
              onClick={() => {
                setError(null);
                if (wsClient) {
                  setConnecting(true);
                  const authState = loadAuthState();
                  wsClient.connect(authState?.tokens?.access_token);
                }
              }}
              className="px-3 py-1.5 text-sm font-medium text-red-700 dark:text-red-300 bg-red-100 dark:bg-red-900/30 rounded-lg hover:bg-red-200 dark:hover:bg-red-900/50 transition-colors"
            >
              Retry
            </button>
          </div>
        </div>
      )}

      {/* Reconnecting Status */}
      {!connecting &&
        !connected &&
        !error &&
        wsClient &&
        wsClient.getState().reconnectAttempts > 0 && (
          <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
            <div className="flex items-center gap-3">
              <Loader2 className="w-4 h-4 text-yellow-600 dark:text-yellow-400 animate-spin" />
              <div>
                <p className="text-sm font-medium text-yellow-900 dark:text-yellow-100">
                  Reconnecting...
                </p>
                <p className="text-xs text-yellow-700 dark:text-yellow-400">
                  Attempt {wsClient.getState().reconnectAttempts} of{" "}
                  {wsClient.getState().isManualClose ? 0 : 10}
                </p>
              </div>
            </div>
          </div>
        )}

      {/* Alerts List */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
        {filteredAlerts.length === 0 ? (
          <div className="p-8 text-center">
            <Bell className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
            <p className="text-gray-500 dark:text-gray-400">
              {connected ? t("noAlerts") : t("notConnected")}
            </p>
          </div>
        ) : (
          <VirtualList
            items={filteredAlerts}
            itemHeight={120}
            containerHeight={600}
            overscan={5}
            renderItem={(alert, index) => (
              <AlertItem key={alert.id} alert={alert} onClick={() => onAlertClick?.(alert)} />
            )}
            emptyComponent={
              <div className="p-8 text-center">
                <Bell className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
                <p className="text-gray-500 dark:text-gray-400">{t("noAlerts")}</p>
              </div>
            }
          />
        )}
      </div>
    </div>
  );
}

interface AlertItemProps {
  alert: AlertData;
  onClick?: () => void;
}

const AlertItem = memo(function AlertItem({ alert, onClick }: AlertItemProps) {
  return (
    <div
      onClick={onClick}
      className={`p-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors cursor-pointer border-l-4 ${
        SEVERITY_COLORS[alert.severity].split(" ")[2]
      }`}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            {SEVERITY_ICONS[alert.severity]}
            <h4 className="text-sm font-medium text-gray-900 dark:text-white truncate">
              {alert.title}
            </h4>
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                SEVERITY_COLORS[alert.severity]
              }`}
            >
              {alert.severity.toUpperCase()}
            </span>
          </div>

          <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
            {new Date(alert.timestamp).toLocaleString()} • {alert.agent.name} ({alert.agent.ip})
          </p>

          {alert.full_log && (
            <p className="text-sm text-gray-600 dark:text-gray-300 line-clamp-2">
              {alert.full_log}
            </p>
          )}

          {alert.iocs.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {alert.iocs.slice(0, 3).map((ioc, idx) => (
                <span
                  key={idx}
                  className="inline-flex items-center px-2 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 text-xs rounded"
                >
                  {ioc}
                </span>
              ))}
              {alert.iocs.length > 3 && (
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  +{alert.iocs.length - 3} more
                </span>
              )}
            </div>
          )}
        </div>

        {alert.mitre && (
          <div className="flex flex-col items-end gap-1">
            {alert.mitre.tactic && (
              <span className="text-xs text-purple-600 dark:text-purple-400 font-medium">
                {alert.mitre.tactic}
              </span>
            )}
            {alert.mitre.technique && (
              <span className="text-xs text-purple-500 dark:text-purple-500">
                {alert.mitre.technique}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
});
