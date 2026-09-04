import { QueryClient, QueryCache, MutationCache } from "@tanstack/react-query";
import { apiClient, ApiError } from "./api/client";

/**
 * Global QueryClient configuration with optimized caching strategies
 *
 * Features:
 * - Stale time: 30 seconds (data considered fresh for 30s)
 * - Cache time: 5 minutes (data kept in cache for 5min)
 * - Smart retry: skip 4xx client errors, max 2 attempts for server/network errors
 * - Refetch on window focus: disabled for better UX
 * - Garbage collection: 5 minutes
 */
export const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: (error, query) => {
      // Ignore AbortError (e.g. cancelled queries on unmount or navigation)
      if (error instanceof Error && error.name === "AbortError") {
        return;
      }
      // 401 errors are handled by auth redirection/refresh
      if (error instanceof ApiError && error.status === 401) {
        return;
      }
      if (process.env.NODE_ENV !== "production") {
        const queryKeyStr = Array.isArray(query.queryKey)
          ? query.queryKey
              .map((k) => (typeof k === "object" ? JSON.stringify(k) : String(k)))
              .join("/")
          : String(query.queryKey);

        console.warn(`[React Query] Query failed: [${queryKeyStr}]`, {
          message: error instanceof Error ? error.message : String(error),
          status: error instanceof ApiError ? error.status : undefined,
          data: error instanceof ApiError ? error.data : undefined,
        });
      }
    },
  }),
  mutationCache: new MutationCache({
    onError: (error, _variables, _context, mutation) => {
      if (process.env.NODE_ENV !== "production") {
        const mutationKeyStr = mutation.options.mutationKey
          ? String(mutation.options.mutationKey)
          : "unnamed";
        console.warn(`[React Query] Mutation failed: [${mutationKeyStr}]`, {
          message: error instanceof Error ? error.message : String(error),
          status: error instanceof ApiError ? error.status : undefined,
        });
      }
    },
  }),
  defaultOptions: {
    queries: {
      // Data is considered fresh for 30 seconds
      staleTime: 30 * 1000, // 30 seconds

      // Data is kept in cache for 5 minutes after it becomes stale
      gcTime: 5 * 60 * 1000, // 5 minutes

      // Smart retry: do not retry 4xx errors (client errors), retry network/5xx max 2 times
      retry: (failureCount, error) => {
        if (error instanceof ApiError && error.status >= 400 && error.status < 500) {
          return false;
        }
        return failureCount < 2;
      },
      retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 10000),

      // Don't refetch on window focus (better UX for data-heavy apps)
      refetchOnWindowFocus: false,

      // Don't refetch on reconnect by default
      refetchOnReconnect: false,

      // Don't refetch on mount if data is fresh
      refetchOnMount: false,

      // Network mode (optimistic updates)
      networkMode: "offlineFirst",
    },
    mutations: {
      // Never auto-retry mutations: a retried delete/status-change fires the
      // destructive action twice. Callers opt into retries explicitly.
      retry: 0,
    },
  },
});

/**
 * Query keys for consistent cache invalidation
 */
export const queryKeys = {
  // Audit logs
  audit: {
    all: ["audit"] as const,
    lists: () => [...queryKeys.audit.all, "list"] as const,
    list: (filters: Record<string, any>) => [...queryKeys.audit.lists(), filters] as const,
    stats: () => [...queryKeys.audit.all, "stats"] as const,
  },

  // Alerts
  alerts: {
    all: ["alerts"] as const,
    lists: () => [...queryKeys.alerts.all, "list"] as const,
    list: (filters: Record<string, any>) => [...queryKeys.alerts.lists(), filters] as const,
    details: () => [...queryKeys.alerts.all, "detail"] as const,
    detail: (id: string) => [...queryKeys.alerts.details(), id] as const,
  },

  // Assets
  assets: {
    all: ["assets"] as const,
    lists: () => [...queryKeys.assets.all, "list"] as const,
    list: (filters: Record<string, any>) => [...queryKeys.assets.lists(), filters] as const,
    detail: (id: string) => [...queryKeys.assets.all, "detail", id] as const,
  },

  // Playbooks
  playbooks: {
    all: ["playbooks"] as const,
    definitions: () => [...queryKeys.playbooks.all, "definitions"] as const,
    definition: (id: string) => [...queryKeys.playbooks.definitions(), id] as const,
    runs: () => [...queryKeys.playbooks.all, "runs"] as const,
    run: (id: string) => [...queryKeys.playbooks.runs(), id] as const,
  },

  // Users
  // Cases
  cases: {
    all: ["cases"] as const,
    detail: (id: string) => [...queryKeys.cases.all, "detail", id] as const,
  },
  users: {
    all: ["users"] as const,
    lists: () => [...queryKeys.users.all, "list"] as const,
    list: (filters: Record<string, any>) => [...queryKeys.users.lists(), filters] as const,
    detail: (id: string) => [...queryKeys.users.all, "detail", id] as const,
  },
};

/**
 * Cache utilities
 */
export const cacheUtils = {
  /**
   * Prefetch data for common queries
   */
  async prefetchCommonQueries() {
    // Prefetch audit stats (commonly used)
    await queryClient.prefetchQuery({
      queryKey: queryKeys.audit.stats(),
      queryFn: async () => {
        return apiClient.get("/api/v1/audit-logs/stats/summary");
      },
    });

    // Prefetch user profile
    await queryClient.prefetchQuery({
      queryKey: ["user", "profile"],
      queryFn: async () => {
        return apiClient.get("/api/v1/auth/me");
      },
    });
  },

  /**
   * Clear all cache
   */
  clearAll() {
    queryClient.clear();
  },

  /**
   * Clear cache for specific query key
   */
  clearQuery(key: any[]) {
    queryClient.removeQueries({ queryKey: key });
  },

  /**
   * Invalidate cache for specific query key (marks as stale)
   */
  invalidateQuery(key: any[]) {
    queryClient.invalidateQueries({ queryKey: key });
  },

  /**
   * Get cache statistics
   */
  getStats() {
    const queries = queryClient.getQueryCache().getAll();
    return {
      totalQueries: queries.length,
      freshQueries: queries.filter((q) => q.state.status === "success" && !q.isStale()).length,
      staleQueries: queries.filter((q) => q.isStale()).length,
      fetchingQueries: queries.filter((q) => q.state.fetchStatus === "fetching").length,
      errorQueries: queries.filter((q) => q.state.status === "error").length,
    };
  },
};
