"use client";

import { useState } from "react";
import { useFormatter, useTranslations } from "next-intl";
import { authFetch } from "@/lib/auth";
import { useAuditLogsQuery } from "../hooks/useAuditLogsQuery";
import { AuditStats } from "./AuditStats";
import { AuditFilters } from "./AuditFilters";
import { VirtualAuditTable } from "./VirtualAuditTable";
import { getMethodClass, getStatusCodeClass } from "../utils";
import { AuditPagination } from "./AuditPagination";

export function AuditPageContainer() {
  const format = useFormatter();
  const t = useTranslations("auditPage");

  // Filter states
  const [filterAction, setFilterAction] = useState("");
  const [filterPath, setFilterPath] = useState("");
  const [filterStatusCode, setFilterStatusCode] = useState("");
  const [filterDateFrom, setFilterDateFrom] = useState("");
  const [filterDateTo, setFilterDateTo] = useState("");
  const [filterUserId, setFilterUserId] = useState("");
  const [filterIpAddress, setFilterIpAddress] = useState("");

  // Use React Query hook for data fetching with caching
  const {
    logs,
    stats,
    isLoading: loading,
    isError,
    error,
    total,
    page,
    pageSize,
    setPage,
    setPageSize,
    refetch: refresh,
    invalidate,
  } = useAuditLogsQuery({
    page: 1,
    pageSize: 50,
    filterAction,
    filterPath,
    filterStatusCode,
    filterDateFrom,
    filterDateTo,
    filterUserId,
    filterIpAddress,
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
    // Invalidate cache when filters change
    invalidate();
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
      if (filterPath) params.append("path", filterPath);
      if (filterStatusCode) params.append("status_code", filterStatusCode);
      if (filterDateFrom) params.append("date_from", filterDateFrom);
      if (filterDateTo) params.append("date_to", filterDateTo);
      if (filterUserId) params.append("user_id", filterUserId);
      if (filterIpAddress) params.append("ip_address", filterIpAddress);

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
      } else {
        alert(t("export.failed"));
      }
    } catch (err) {
      console.error("Export failed:", err);
      alert(t("export.error"));
    }
  };

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <h3 className="text-lg font-medium text-red-800 dark:text-red-300">{t("error.title")}</h3>
          <p className="mt-2 text-sm text-red-700 dark:text-red-400">{String(error)}</p>
          <button
            onClick={() => refresh()}
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
          >
            {t("error.retry")}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
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

      {/* Table Header with Actions */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-medium text-gray-900 dark:text-white">{t("logs.title")}</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {t("logs.count", { count: total })}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => refresh()}
            disabled={loading}
            className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {t("actions.refresh")}
          </button>
          <button
            onClick={handleExport}
            disabled={loading || logs.length === 0}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {t("actions.export")}
          </button>
        </div>
      </div>

      {/* Desktop: Virtual Audit Table */}
      <div className="hidden sm:block mb-6">
        <VirtualAuditTable logs={logs} height={600} rowHeight={64} />
      </div>

      {/* Mobile: card list (audit 移动端适配) */}
      <div className="sm:hidden mb-6 space-y-3">
        {logs.length === 0 && !loading ? (
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 text-center text-sm text-gray-500 dark:text-gray-400">
            {t("empty") ?? "No audit logs"}
          </div>
        ) : (
          logs.map((log) => (
            <div
              key={log.id}
              className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-2 shadow-sm"
            >
              <div className="flex items-start justify-between gap-2">
                <code className="text-xs font-semibold bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded text-gray-900 dark:text-white truncate">
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
              <p
                className="text-xs font-mono text-gray-600 dark:text-gray-400 truncate"
                title={log.path}
              >
                {log.path}
              </p>
              <div className="flex items-center justify-between pt-2 border-t border-gray-100 dark:border-gray-700 text-xs text-gray-500 dark:text-gray-400">
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
              <div className="flex items-center justify-between text-xs text-gray-400 dark:text-gray-500">
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
        onPageChange={(newPage) => {
          setPage(newPage);
          invalidate();
        }}
        onPageSizeChange={(newPageSize) => {
          setPageSize(newPageSize);
          setPage(1);
          invalidate();
        }}
      />
    </div>
  );
}
