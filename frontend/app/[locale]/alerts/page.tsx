"use client";

import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { loadAuthState, authFetchJSON } from "@/lib/auth";
import Navigation from "@/components/Navigation";
import { TableSkeleton } from "@/components/Skeleton";
import { useAlertWebSocket } from "@/components/AlertWebSocket";
import {
  Search,
  AlertTriangle,
  CheckCircle,
  RefreshCw,
  AlertCircle,
  TrendingUp,
  Shield,
  Activity,
  ChevronLeft,
  ChevronRight,
  Download,
  Wifi,
  WifiOff,
} from "lucide-react";

interface SecurityAlert {
  id: number;
  source: string;
  event_type: string;
  severity: "critical" | "high" | "medium" | "low" | "info";
  title: string;
  description: string | null;
  status: string;
  created_at: string;
  event_timestamp: string | null;
  agent_name: string | null;
}

interface SecurityAlertListResponse {
  total: number;
  alerts: SecurityAlert[];
  page: number;
  page_size: number;
}

const SEVERITY_COLORS = {
  critical: "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300",
  high: "bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300",
  medium: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300",
  low: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300",
  info: "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300",
};

export default function AlertsPage() {
  const router = useRouter();
  const locale = useLocale();
  const t = useTranslations("alerts");

  const [mounted, setMounted] = useState(false);
  const [alerts, setAlerts] = useState<SecurityAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [severityFilter, setSeverityFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [bulkStatus, setBulkStatus] = useState("investigating");
  const [isApplyingBulk, setIsApplyingBulk] = useState(false);
  const [pagination, setPagination] = useState({
    page: 1,
    limit: 20,
    total: 0,
    totalPages: 0,
  });

  const fetchAlerts = async (page = pagination.page) => {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pagination.limit.toString(),
      });

      if (searchQuery.trim()) params.set("search", searchQuery.trim());
      if (severityFilter !== "all") params.set("severity", severityFilter);
      if (statusFilter !== "all") params.set("status", statusFilter);

      const data = await authFetchJSON<SecurityAlertListResponse>(
        `/api/v1/security-alerts/?${params.toString()}`
      );

      setAlerts(data.alerts || []);
      setSelectedIds([]);
      setPagination((prev) => ({
        ...prev,
        page,
        total: data.total || 0,
        totalPages: Math.max(1, Math.ceil((data.total || 0) / prev.limit)),
      }));
    } catch (err: any) {
      setError(err?.message || "Failed to load alerts");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const authState = loadAuthState();
    if (!authState?.isAuthenticated) {
      router.push(`/${locale}/login`);
      return;
    }
    setMounted(true);
  }, [router, locale]);

  useEffect(() => {
    if (!mounted) return;
    fetchAlerts(1);
  }, [mounted, searchQuery, severityFilter, statusFilter]);

  useEffect(() => {
    if (!mounted) return;
    fetchAlerts(pagination.page);
  }, [pagination.page]);

  const stats = useMemo(() => {
    return {
      total: pagination.total,
      critical: alerts.filter((a) => a.severity === "critical").length,
      high: alerts.filter((a) => a.severity === "high").length,
      medium: alerts.filter((a) => a.severity === "medium").length,
    };
  }, [alerts, pagination.total]);

  const { connectionStatus, AlertWebSocketComponent } = useAlertWebSocket({
    enabled: mounted,
    channels: ["alerts"],
    onAlert: (incoming) => {
      const normalized: SecurityAlert = {
        id: Number(incoming?.id || 0),
        source: String(incoming?.source || "unknown"),
        event_type: String(incoming?.event_type || "unknown"),
        severity: (
          ["critical", "high", "medium", "low", "info"].includes(String(incoming?.severity || "").toLowerCase())
            ? String(incoming?.severity).toLowerCase()
            : "info"
        ) as SecurityAlert["severity"],
        title: String(incoming?.title || `Alert #${incoming?.id || "new"}`),
        description: incoming?.description ? String(incoming.description) : null,
        status: String(incoming?.status || "new"),
        created_at: String(incoming?.created_at || new Date().toISOString()),
        event_timestamp: incoming?.event_timestamp ? String(incoming.event_timestamp) : null,
        agent_name: incoming?.agent_name ? String(incoming.agent_name) : null,
      };

      if (!normalized.id) return;
      if (severityFilter !== "all" && normalized.severity !== severityFilter) return;
      if (statusFilter !== "all" && normalized.status !== statusFilter) return;
      if (
        searchQuery.trim() &&
        !`${normalized.title} ${normalized.description || ""}`
          .toLowerCase()
          .includes(searchQuery.trim().toLowerCase())
      ) {
        return;
      }

      setAlerts((prev) => {
        if (prev.some((a) => a.id === normalized.id)) {
          return prev.map((a) => (a.id === normalized.id ? { ...a, ...normalized } : a));
        }
        return [normalized, ...prev].slice(0, pagination.limit);
      });
      setPagination((prev) => ({ ...prev, total: prev.total + 1 }));
    },
  });

  const isAllSelected = alerts.length > 0 && selectedIds.length === alerts.length;

  const toggleSelectAll = () => {
    if (isAllSelected) {
      setSelectedIds([]);
      return;
    }
    setSelectedIds(alerts.map((a) => a.id));
  };

  const toggleSelectOne = (id: number) => {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  const applyBulkStatus = async () => {
    if (selectedIds.length === 0) return;
    try {
      setIsApplyingBulk(true);
      await authFetchJSON("/api/v1/alerts/batch/update", {
        method: "POST",
        body: JSON.stringify({
          alert_ids: selectedIds.map(String),
          status: bulkStatus,
        }),
      });
      await fetchAlerts(pagination.page);
    } catch (err: any) {
      setError(err?.message || "Bulk update failed");
    } finally {
      setIsApplyingBulk(false);
    }
  };

  const exportCurrentPageCsv = () => {
    const headers = ["id", "severity", "status", "source", "event_type", "title", "created_at"];
    const esc = (value: unknown) => `"${String(value ?? "").replace(/"/g, '""')}"`;
    const rows = alerts.map((a) =>
      [a.id, a.severity, a.status, a.source, a.event_type, a.title, a.created_at].map(esc).join(",")
    );
    const csv = [headers.join(","), ...rows].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `alerts_page_${pagination.page}_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  if (!mounted) return null;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Navigation title={t("title", { default: "Alerts" })} subtitle="Security alert management and analysis" />
      <AlertWebSocketComponent />

      <main className="max-w-7xl mx-auto px-4 py-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <StatCard icon={<AlertTriangle className="w-5 h-5 text-blue-600 dark:text-blue-400" />} label="Total Alerts" value={stats.total} />
          <StatCard icon={<Shield className="w-5 h-5 text-red-600 dark:text-red-400" />} label="Critical" value={stats.critical} valueClass="text-red-600 dark:text-red-400" />
          <StatCard icon={<TrendingUp className="w-5 h-5 text-orange-600 dark:text-orange-400" />} label="High" value={stats.high} valueClass="text-orange-600 dark:text-orange-400" />
          <StatCard icon={<Activity className="w-5 h-5 text-yellow-600 dark:text-yellow-400" />} label="Medium" value={stats.medium} valueClass="text-yellow-600 dark:text-yellow-400" />
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 mb-6 shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search alerts..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">All Severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
              <option value="info">Info</option>
            </select>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">All Status</option>
              <option value="new">New</option>
              <option value="investigating">Investigating</option>
              <option value="resolved">Resolved</option>
              <option value="false_positive">False Positive</option>
              <option value="escalated">Escalated</option>
            </select>
            <button
              onClick={() => fetchAlerts(1)}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              Refresh
            </button>
            <button
              onClick={exportCurrentPageCsv}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2"
            >
              <Download className="w-4 h-4" />
              Export CSV
            </button>
            <div className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-sm">
              {connectionStatus === "connected" ? (
                <>
                  <Wifi className="w-4 h-4 text-emerald-600" />
                  <span className="text-emerald-600">Live</span>
                </>
              ) : (
                <>
                  <WifiOff className="w-4 h-4 text-amber-600" />
                  <span className="text-amber-600">Disconnected</span>
                </>
              )}
            </div>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
            <span className="text-red-700 dark:text-red-300">{error}</span>
          </div>
        )}

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
          {alerts.length > 0 && (
            <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/40 flex flex-wrap items-center gap-3">
              <label className="inline-flex items-center gap-2 text-sm text-gray-700 dark:text-gray-200">
                <input type="checkbox" checked={isAllSelected} onChange={toggleSelectAll} />
                Select all on page
              </label>
              <span className="text-sm text-gray-500 dark:text-gray-300">
                Selected: {selectedIds.length}
              </span>
              <select
                value={bulkStatus}
                onChange={(e) => setBulkStatus(e.target.value)}
                className="px-3 py-1.5 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-sm"
              >
                <option value="new">Set New</option>
                <option value="investigating">Set Investigating</option>
                <option value="resolved">Set Resolved</option>
                <option value="false_positive">Set False Positive</option>
                <option value="escalated">Set Escalated</option>
              </select>
              <button
                disabled={selectedIds.length === 0 || isApplyingBulk}
                onClick={applyBulkStatus}
                className="px-3 py-1.5 rounded-lg bg-blue-600 text-white text-sm disabled:opacity-50 hover:bg-blue-700"
              >
                {isApplyingBulk ? "Applying..." : "Apply Bulk Status"}
              </button>
            </div>
          )}
          {loading ? (
            <div className="p-6">
              <TableSkeleton rows={8} cols={5} />
            </div>
          ) : alerts.length === 0 ? (
            <div className="p-12 text-center">
              <AlertTriangle className="w-16 h-16 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">No alerts found</h3>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 dark:bg-gray-700 border-b border-gray-200 dark:border-gray-600">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                        <input type="checkbox" checked={isAllSelected} onChange={toggleSelectAll} />
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Severity</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Source</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Title</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Date</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                    {alerts.map((alert) => (
                      <tr
                        key={alert.id}
                        className="hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer"
                        onClick={() => router.push(`/${locale}/alerts/${alert.id}`)}
                      >
                        <td className="px-4 py-4" onClick={(e) => e.stopPropagation()}>
                          <input
                            type="checkbox"
                            checked={selectedIds.includes(alert.id)}
                            onChange={() => toggleSelectOne(alert.id)}
                          />
                        </td>
                        <td className="px-6 py-4">
                          <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${SEVERITY_COLORS[alert.severity]}`}>
                            {alert.severity}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-gray-900 dark:text-white">{alert.source}</td>
                        <td className="px-6 py-4">
                          <div className="max-w-sm truncate text-gray-600 dark:text-gray-300">
                            {alert.title || alert.description || "-"}
                          </div>
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                          {alert.created_at ? new Date(alert.created_at).toLocaleString() : "-"}
                        </td>
                        <td className="px-6 py-4">
                          {alert.status === "closed" || alert.status === "resolved" ? (
                            <span className="inline-flex items-center gap-1 text-green-600 dark:text-green-400">
                              <CheckCircle className="w-4 h-4" />
                              {alert.status}
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-amber-600 dark:text-amber-400">
                              <AlertCircle className="w-4 h-4" />
                              {alert.status}
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {pagination.totalPages > 1 && (
                <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 dark:border-gray-700">
                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    Showing {(pagination.page - 1) * pagination.limit + 1} to {Math.min(pagination.page * pagination.limit, pagination.total)} of {pagination.total}
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setPagination((p) => ({ ...p, page: p.page - 1 }))}
                      disabled={pagination.page === 1}
                      className="p-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50"
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </button>
                    <span className="text-sm text-gray-600 dark:text-gray-400">
                      Page {pagination.page} of {pagination.totalPages}
                    </span>
                    <button
                      onClick={() => setPagination((p) => ({ ...p, page: p.page + 1 }))}
                      disabled={pagination.page === pagination.totalPages}
                      className="p-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </main>
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
  valueClass,
}: {
  icon: ReactNode;
  label: string;
  value: number;
  valueClass?: string;
}) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700">
      <div className="flex items-center gap-3">
        <div className="p-2 bg-gray-100 dark:bg-gray-700 rounded-lg">{icon}</div>
        <div>
          <p className="text-sm text-gray-500 dark:text-gray-400">{label}</p>
          <p className={`text-2xl font-bold text-gray-900 dark:text-white ${valueClass || ""}`}>{value}</p>
        </div>
      </div>
    </div>
  );
}
