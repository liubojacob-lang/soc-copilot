"use client";

import { useState } from "react";
import { useFormatter, useTranslations } from "next-intl";
import { authFetch } from "@/lib/auth";
import { useAuditLogsQuery } from "../hooks/useAuditLogsQuery";
import { useDebouncedValue } from "../hooks/useDebouncedValue";
import { AuditStats } from "./AuditStats";
import { AuditFilters } from "./AuditFilters";
import { VirtualAuditTable } from "./VirtualAuditTable";
import { getMethodClass, getStatusCodeClass } from "../utils";
import { AuditPagination } from "./AuditPagination";
import { useToast } from "@/components/Toast";

export function AuditPageContainer() {
  const format = useFormatter();
  const t = useTranslations("auditPage");
  const { showToast } = useToast();

  // Filter states
  const [filterAction, setFilterAction] = useState("");
  const [filterPath, setFilterPath] = useState("");
  const [filterStatusCode, setFilterStatusCode] = useState("");
  const [filterDateFrom, setFilterDateFrom] = useState("");
  const [filterDateTo, setFilterDateTo] = useState("");
  const [filterUserId, setFilterUserId] = useState("");
  const [filterIpAddress, setFilterIpAddress] = useState("");

  // 文本类条件防抖：输入即时回显，查询参数 300ms 空闲后才生效
  const debouncedPath = useDebouncedValue(filterPath, 300);
  const debouncedUserId = useDebouncedValue(filterUserId, 300);
  const debouncedIpAddress = useDebouncedValue(filterIpAddress, 300);

  // Use React Query hook for data fetching with caching
  const {
    logs,
    stats,
    isLoading: loading,
    isFetching,
    isError,
    error,
    total,
    page,
    pageSize,
    setPage,
    setPageSize,
    refetch: refresh,
  } = useAuditLogsQuery({
    page: 1,
    pageSize: 50,
    filterAction,
    filterPath: debouncedPath,
    filterStatusCode,
    filterDateFrom,
    filterDateTo,
    filterUserId: debouncedUserId,
    filterIpAddress: debouncedIpAddress,
  });

  const handleFilterChange = (filters: {
    action: string;
    path: string;
    statusCode: string;
    dateFrom: string;
    dateTo: string;
    userId: string;
    ipAddress: string;
  }) => {
    setFilterAction(filters.action);
    setFilterPath(filters.path);
    setFilterStatusCode(filters.statusCode);
    setFilterDateFrom(filters.dateFrom);
    setFilterDateTo(filters.dateTo);
    setFilterUserId(filters.userId);
    setFilterIpAddress(filters.ipAddress);
    setPage(1); // Reset to first page when filters change
    // 查询 key 已包含全部筛选条件，无需手动 invalidate（避免逐字符触发请求）
  };

  const handleResetFilters = () => {
    setFilterAction("");
    setFilterPath("");
    setFilterStatusCode("");
    setFilterDateFrom("");
    setFilterDateTo("");
    setFilterUserId("");
    setFilterIpAddress("");
    setPage(1);
  };

  const handleExport = async () => {
    try {
      const params = new URLSearchParams();
      if (filterAction) params.append("action", filterAction);
      if (debouncedPath) params.append("path", debouncedPath);
      if (filterStatusCode) params.append("status_code", filterStatusCode);
      if (filterDateFrom) params.append("date_from", filterDateFrom);
      if (filterDateTo) params.append("date_to", filterDateTo);
      if (debouncedUserId) params.append("user_id", debouncedUserId);
      if (debouncedIpAddress) params.append("ip_address", debouncedIpAddress);

      const response = await authFetch(`/api/v1/export/audit-logs?format=csv&${params.toString()}`);

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `audit-logs-${new Date().toISOString().split("T")[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        showToast("Audit logs exported successfully", "success");
      } else {
        showToast(t("export.failed"), "error");
      }
    } catch (err) {
      console.error("Export failed:", err);
      showToast(t("export.error"), "error");
    }
  };

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-status-failed-bg border border-status-failed-border rounded-lg p-4">
          <h3 className="text-lg font-medium text-status-failed-fg">{t("error.title")}</h3>
          <p className="mt-2 text-sm text-status-failed-fg opacity-90">{String(error)}</p>
          <button
            onClick={() => refresh()}
            className="mt-4 px-4 py-2 bg-status-failed text-white rounded-md hover:opacity-90 transition-opacity"
          >
            {t("error.retry")}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Statistics Cards */}
      <AuditStats stats={stats} loading={loading} />

      {/* Filters */}
      <AuditFilters
        filterAction={filterAction}
        filterPath={filterPath}
        filterStatusCode={filterStatusCode}
        filterDateFrom={filterDateFrom}
        filterDateTo={filterDateTo}
        filterUserId={filterUserId}
        filterIpAddress={filterIpAddress}
        onFilterChange={handleFilterChange}
        onReset={handleResetFilters}
      />

      {/* Table Header with Actions & Top Pagination */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
        <div>
          <h2 className="text-lg font-medium text-text-primary">{t("logs.title")}</h2>
          <p className="text-sm text-text-muted">{t("logs.count", { count: total })}</p>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          {/* Top Quick Page Size Selector & Mini Pager */}
          {total > 0 && (
            <div className="flex items-center gap-2 bg-surface-card border border-border-subtle px-3 py-1.5 rounded-lg text-xs shadow-subtle">
              <span className="text-text-muted">{t("pagination.perPagePrefix") || "每页"}</span>
              <select
                value={pageSize}
                onChange={(e) => setPageSize(Number(e.target.value))}
                disabled={isFetching}
                className="bg-surface-input border border-border-default rounded px-1.5 py-0.5 text-xs text-text-primary font-medium disabled:opacity-50"
                aria-label="每页显示条数"
              >
                <option value="25">25</option>
                <option value="50">50</option>
                <option value="100">100</option>
                <option value="200">200</option>
              </select>
              <span className="text-text-muted">{t("pagination.perPageSuffix") || "条"}</span>
              <div className="h-3 w-px bg-border-strong mx-1" />
              <span className="text-text-secondary font-medium">
                {page} / {Math.max(1, Math.ceil(total / pageSize))}
              </span>
              <div className="flex items-center gap-0.5">
                <button
                  onClick={() => setPage(Math.max(1, page - 1))}
                  disabled={page <= 1 || isFetching}
                  className="w-5 h-5 flex items-center justify-center rounded text-text-secondary hover:bg-surface-hover disabled:opacity-30 disabled:cursor-not-allowed text-xs"
                  title={t("pagination.prev") || "上一页"}
                >
                  ‹
                </button>
                <button
                  onClick={() => setPage(Math.min(Math.ceil(total / pageSize), page + 1))}
                  disabled={page >= Math.ceil(total / pageSize) || isFetching}
                  className="w-5 h-5 flex items-center justify-center rounded text-text-secondary hover:bg-surface-hover disabled:opacity-30 disabled:cursor-not-allowed text-xs"
                  title={t("pagination.next") || "下一页"}
                >
                  ›
                </button>
              </div>
            </div>
          )}

          <button
            onClick={() => refresh()}
            disabled={loading}
            className="px-4 py-2 text-sm font-medium text-text-secondary bg-surface-card border border-border-subtle hover:bg-surface-hover hover:text-text-primary rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-subtle"
          >
            {t("actions.refresh")}
          </button>
          <button
            onClick={handleExport}
            disabled={loading || logs.length === 0}
            className="px-4 py-2 text-sm font-medium text-white bg-accent-600 hover:bg-accent-700 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {t("actions.export")}
          </button>
        </div>
      </div>

      {/* Desktop: Virtual Audit Table */}
      <div className="hidden sm:block mb-6">
        <VirtualAuditTable logs={logs} height={600} rowHeight={64} isFetching={isFetching} />
      </div>

      {/* Mobile: card list (audit 移动端适配) */}
      <div className="sm:hidden mb-6 space-y-3">
        {logs.length === 0 && !loading ? (
          <div className="bg-surface-card rounded-xl border border-border-subtle p-6 text-center text-sm text-text-muted">
            {t("empty") ?? "No audit logs"}
          </div>
        ) : (
          logs.map((log) => (
            <div
              key={log.id}
              className="bg-surface-card rounded-xl border border-border-subtle p-4 space-y-2 shadow-subtle"
            >
              <div className="flex items-start justify-between gap-2">
                <code className="text-xs font-semibold bg-surface-hover px-2 py-1 rounded text-text-primary truncate">
                  {log.action}
                </code>
                <div className="flex items-center gap-1.5 shrink-0">
                  <span
                    className={`px-2 py-1 text-xs font-semibold rounded ${getMethodClass(log.method)}`}
                  >
                    {log.method}
                  </span>
                  <span
                    className={`px-2 py-1 text-xs font-semibold rounded ${getStatusCodeClass(log.status_code)}`}
                  >
                    {log.status_code}
                  </span>
                </div>
              </div>
              <p className="text-xs font-mono text-text-secondary truncate" title={log.path}>
                {log.path}
              </p>
              <div className="flex items-center justify-between pt-2 border-t border-border-subtle text-xs text-text-muted">
                <span className="truncate">
                  {log.username || <span className="italic">System</span>}
                </span>
                <span className="shrink-0">
                  {format.dateTime(new Date(log.created_at), {
                    dateStyle: "medium",
                    timeStyle: "medium",
                  })}
                </span>
              </div>
              <div className="flex items-center justify-between text-xs text-text-tertiary">
                <span className="truncate">
                  {log.target_type ? `${log.target_type}:${log.target_id}` : "—"}
                </span>
                <span className="shrink-0">
                  {log.duration_ms !== null ? `${log.duration_ms}ms` : ""}
                </span>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Pagination */}
      <AuditPagination
        page={page}
        pageSize={pageSize}
        total={total}
        isFetching={isFetching}
        onPageChange={(newPage) => {
          setPage(newPage);
        }}
        onPageSizeChange={(newPageSize) => {
          setPageSize(newPageSize);
        }}
      />
    </div>
  );
}
