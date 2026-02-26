/** Custom hook for managing audit logs data and fetching */

import { useState, useEffect, useCallback } from 'react';
import { authFetchJSON } from '@/lib/auth';
import type { AuditLog, AuditLogStats, AuditFilters } from '../types';

interface UseAuditLogsOptions {
  page: number;
  pageSize: number;
  filters: AuditFilters;
  autoFetch?: boolean;
}

interface UseAuditLogsResult {
  logs: AuditLog[];
  stats: AuditLogStats | null;
  total: number;
  loading: boolean;
  error: string;
  fetchLogs: () => Promise<void>;
  fetchStats: () => Promise<void>;
  refresh: () => Promise<void>;
}

export function useAuditLogs({
  page,
  pageSize,
  filters,
  autoFetch = true
}: UseAuditLogsOptions): UseAuditLogsResult {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [stats, setStats] = useState<AuditLogStats | null>(null);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchLogs = useCallback(async () => {
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
      });

      if (filters.action) params.append("action", filters.action);
      if (filters.path) params.append("path", filters.path);
      if (filters.statusCode) params.append("status_code", filters.statusCode);
      if (filters.dateFrom) params.append("date_from", filters.dateFrom);
      if (filters.dateTo) params.append("date_to", filters.dateTo);

      const data = await authFetchJSON<{ items: AuditLog[]; total: number }>(
        `/api/audit-logs?${params.toString()}`
      );

      setLogs(data.items);
      setTotal(data.total);
      setError("");
    } catch (err: any) {
      setError(err.message || "Failed to load audit logs");
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, filters]);

  const fetchStats = useCallback(async () => {
    try {
      const data = await authFetchJSON<AuditLogStats>("/api/audit-logs/stats/summary");
      setStats(data);
    } catch (err: any) {
      console.error("Failed to load stats:", err);
    }
  }, []);

  const refresh = useCallback(async () => {
    await Promise.all([fetchLogs(), fetchStats()]);
  }, [fetchLogs, fetchStats]);

  // Initial fetch
  useEffect(() => {
    if (autoFetch) {
      fetchLogs();
      fetchStats();
    }
  }, []);

  // Refetch when dependencies change
  useEffect(() => {
    if (!loading) {
      fetchLogs();
    }
  }, [page, pageSize, filters.action, filters.path, filters.statusCode, filters.dateFrom, filters.dateTo]);

  return {
    logs,
    stats,
    total,
    loading,
    error,
    fetchLogs,
    fetchStats,
    refresh
  };
}
