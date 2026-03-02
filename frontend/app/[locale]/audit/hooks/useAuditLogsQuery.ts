'use client';

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { authFetchJSON } from '@/lib/auth';
import { queryKeys } from '@/lib/queryClient';
import type { AuditLog } from '../types';

interface AuditLogStats {
  total_requests: number;
  last_24h_requests: number;
  failed_requests: number;
}

interface UseAuditLogsQueryOptions {
  page?: number;
  pageSize?: number;
  filterAction?: string;
  filterPath?: string;
  filterStatusCode?: string;
  filterDateFrom?: string;
  filterDateTo?: string;
  filterUserId?: string;
  filterIpAddress?: string;
  enabled?: boolean;
}

interface UseAuditLogsQueryResult {
  logs: AuditLog[];
  stats: AuditLogStats | null;
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
  total: number;
  page: number;
  pageSize: number;
  refetch: () => Promise<any>;
  invalidate: () => Promise<void>;
}

/**
 * Fetch audit logs with React Query caching
 */
async function fetchAuditLogs(options: UseAuditLogsQueryOptions) {
  const params = new URLSearchParams();
  params.append('page', (options.page || 1).toString());
  params.append('limit', (options.pageSize || 50).toString());

  if (options.filterAction) params.append('action', options.filterAction);
  if (options.filterPath) params.append('path', options.filterPath);
  if (options.filterStatusCode) params.append('status_code', options.filterStatusCode);
  if (options.filterDateFrom) params.append('date_from', options.filterDateFrom);
  if (options.filterDateTo) params.append('date_to', options.filterDateTo);
  if (options.filterUserId) params.append('user_id', options.filterUserId);
  if (options.filterIpAddress) params.append('ip_address', options.filterIpAddress);

  const response = await authFetchJSON(`/api/audit?${params.toString()}`);
  
  if (!response.ok) {
    throw new Error('Failed to fetch audit logs');
  }

  return response.json();
}

/**
 * Hook to fetch audit logs with React Query caching
 */
export function useAuditLogsQuery(options: UseAuditLogsQueryOptions = {}): UseAuditLogsQueryResult {
  const {
    page = 1,
    pageSize = 50,
    filterAction = '',
    filterPath = '',
    filterStatusCode = '',
    filterDateFrom = '',
    filterDateTo = '',
    filterUserId = '',
    filterIpAddress = '',
    enabled = true,
  } = options;

  const queryClient = useQueryClient();
  
  // Create query key based on all filter options
  const queryKey = queryKeys.audit.list({
    page,
    pageSize,
    filterAction,
    filterPath,
    filterStatusCode,
    filterDateFrom,
    filterDateTo,
    filterUserId,
    filterIpAddress,
  });

  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey,
    queryFn: () => fetchAuditLogs(options),
    enabled,
    // Cache configuration
    staleTime: 30 * 1000, // 30 seconds
    gcTime: 5 * 60 * 1000, // 5 minutes
    // Retry configuration
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    // Don't refetch on window focus
    refetchOnWindowFocus: false,
  });

  // Prefetch next page
  const prefetchNextPage = () => {
    const nextPage = page + 1;
    const nextPageKey = queryKeys.audit.list({
      ...options,
      page: nextPage,
    });
    
    queryClient.prefetchQuery({
      queryKey: nextPageKey,
      queryFn: () => fetchAuditLogs({ ...options, page: nextPage }),
    });
  };

  // Prefetch previous page
  const prefetchPrevPage = () => {
    const prevPage = Math.max(1, page - 1);
    const prevPageKey = queryKeys.audit.list({
      ...options,
      page: prevPage,
    });
    
    queryClient.prefetchQuery({
      queryKey: prevPageKey,
      queryFn: () => fetchAuditLogs({ ...options, page: prevPage }),
    });
  };

  // Invalidate cache for this query
  const invalidate = async () => {
    await queryClient.invalidateQueries({ queryKey });
  };

  // Auto-prefetch adjacent pages
  if (!isLoading && data && page > 1) {
    prefetchPrevPage();
  }
  if (!isLoading && data && page < Math.ceil((data.total || 0) / pageSize)) {
    prefetchNextPage();
  }

  return {
    logs: data?.logs || [],
    stats: data?.stats || null,
    total: data?.total || 0,
    page,
    pageSize,
    isLoading,
    isError,
    error: error as Error | null,
    refetch,
    invalidate,
  };
}

/**
 * Hook to fetch audit stats with separate caching
 */
export function useAuditStatsQuery() {
  return useQuery({
    queryKey: queryKeys.audit.stats(),
    queryFn: async () => {
      const response = await authFetchJSON('/api/audit/stats');
      if (!response.ok) throw new Error('Failed to fetch audit stats');
      return response.json();
    },
    staleTime: 60 * 1000, // 1 minute
    gcTime: 10 * 60 * 1000, // 10 minutes
  });
}

/**
 * Hook to prefetch audit logs for better UX
 */
export function usePrefetchAuditLogs(options: UseAuditLogsQueryOptions) {
  const queryClient = useQueryClient();
  
  return () => {
    const queryKey = queryKeys.audit.list(options);
    queryClient.prefetchQuery({
      queryKey,
      queryFn: () => fetchAuditLogs(options),
    });
  };
}