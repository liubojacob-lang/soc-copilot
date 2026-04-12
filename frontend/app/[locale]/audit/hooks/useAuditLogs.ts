"use client";

import { useState, useEffect, useCallback } from "react";
import { authFetchJSON } from "@/lib/auth";
import type { AuditLog } from "../types";

interface AuditLogStats {
  total_requests: number;
  last_24h_requests: number;
  failed_requests: number;
}

interface UseAuditLogsOptions {
  page?: number;
  pageSize?: number;
  filterAction?: string;
  filterPath?: string;
  filterStatusCode?: string;
  filterDateFrom?: string;
  filterDateTo?: string;
  filterUserId?: string;
  filterIpAddress?: string;
}

interface UseAuditLogsResult {
  logs: AuditLog[];
  stats: AuditLogStats | null;
  loading: boolean;
  error: string;
  total: number;
  page: number;
  pageSize: number;
  setPage: (page: number) => void;
  setPageSize: (pageSize: number) => void;
  refresh: () => Promise<void>;
}

export function useAuditLogs(options: UseAuditLogsOptions = {}): UseAuditLogsResult {
  const {
    page: initialPage = 1,
    pageSize: initialPageSize = 50,
    filterAction = "",
    filterPath = "",
    filterStatusCode = "",
    filterDateFrom = "",
    filterDateTo = "",
    filterUserId = "",
    filterIpAddress = "",
  } = options;

  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [stats, setStats] = useState<AuditLogStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [page, setPage] = useState(initialPage);
  const [pageSize, setPageSize] = useState(initialPageSize);
  const [total, setTotal] = useState(0);

  const buildQueryParams = useCallback(() => {
    const params = new URLSearchParams();
    params.append("page", page.toString());
    params.append("limit", pageSize.toString());

    if (filterAction) params.append("action", filterAction);
    if (filterPath) params.append("path", filterPath);
    if (filterStatusCode) params.append("status_code", filterStatusCode);
    if (filterDateFrom) params.append("date_from", filterDateFrom);
    if (filterDateTo) params.append("date_to", filterDateTo);
    if (filterUserId) params.append("user_id", filterUserId);
    if (filterIpAddress) params.append("ip_address", filterIpAddress);

    return params.toString();
  }, [
    page,
    pageSize,
    filterAction,
    filterPath,
    filterStatusCode,
    filterDateFrom,
    filterDateTo,
    filterUserId,
    filterIpAddress,
  ]);

  const fetchAuditLogs = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const queryParams = buildQueryParams();
      const response = await authFetchJSON(`/api/audit?${queryParams}`);

      if (response.ok) {
        const data = await response.json();
        setLogs(data.logs || []);
        setTotal(data.total || 0);
        setStats(data.stats || null);
      } else {
        setError("Failed to fetch audit logs");
        setLogs([]);
        setTotal(0);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
      setLogs([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [buildQueryParams]);

  const refresh = useCallback(async () => {
    await fetchAuditLogs();
  }, [fetchAuditLogs]);

  useEffect(() => {
    fetchAuditLogs();
  }, [fetchAuditLogs]);

  return {
    logs,
    stats,
    loading,
    error,
    total,
    page,
    pageSize,
    setPage,
    setPageSize,
    refresh,
  };
}
