'use client';

/**
 * Custom hooks for data fetching with caching support.
 * 
 * Features:
 * - Automatic caching with TTL
 * - Request deduplication
 * - Loading and error states
 * - Background refetching
 * - Cache invalidation
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { apiCache, cacheKeys, cacheInvalidators } from '../lib/cache';
import { apiClient } from '../lib/api-client';

interface UseCachedQueryOptions {
  ttl?: number;
  enabled?: boolean;
  refetchOnMount?: boolean;
  refetchInterval?: number;
  onSuccess?: (data: any) => void;
  onError?: (error: Error) => void;
}

interface QueryResult<T> {
  data: T | null;
  isLoading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
  invalidate: () => void;
}

/**
 * Generic hook for cached API queries
 */
export function useCachedQuery<T>(
  key: string,
  fetcher: () => Promise<T>,
  options: UseCachedQueryOptions = {}
): QueryResult<T> {
  const {
    ttl = 5 * 60 * 1000,
    enabled = true,
    refetchOnMount = false,
    refetchInterval,
    onSuccess,
    onError,
  } = options;

  const [data, setData] = useState<T | null>(() => {
    // Initialize with cached data if available
    return apiCache.get<T>(key);
  });
  const [isLoading, setIsLoading] = useState(!apiCache.has(key));
  const [error, setError] = useState<Error | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const fetchData = useCallback(async () => {
    if (!enabled) return;

    setIsLoading(true);
    setError(null);

    try {
      const result = await apiCache.getOrFetch(key, fetcher, ttl);
      setData(result);
      onSuccess?.(result);
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err));
      setError(error);
      onError?.(error);
    } finally {
      setIsLoading(false);
    }
  }, [key, fetcher, ttl, enabled, onSuccess, onError]);

  const invalidate = useCallback(() => {
    apiCache.delete(key);
  }, [key]);

  const refetch = useCallback(async () => {
    invalidate();
    await fetchData();
  }, [invalidate, fetchData]);

  // Initial fetch
  useEffect(() => {
    if (enabled) {
      if (refetchOnMount || !apiCache.has(key)) {
        fetchData();
      }
    }
  }, [enabled, refetchOnMount, key, fetchData]);

  // Refetch interval
  useEffect(() => {
    if (refetchInterval && enabled) {
      intervalRef.current = setInterval(() => {
        fetchData();
      }, refetchInterval);

      return () => {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
        }
      };
    }
  }, [refetchInterval, enabled, fetchData]);

  return { data, isLoading, error, refetch, invalidate };
}

/**
 * Hook for playbook runs list
 */
export function usePlaybookRuns(params?: Record<string, string>) {
  const key = cacheKeys.playbookRuns(params);
  
  return useCachedQuery(
    key,
    () => apiClient.get('/playbook/runs', params),
    {
      refetchOnMount: true,
      ttl: 30 * 1000, // 30 seconds
    }
  );
}

/**
 * Hook for single playbook run
 */
export function usePlaybookRun(id: string) {
  const key = cacheKeys.playbookRun(id);
  
  return useCachedQuery(
    key,
    () => apiClient.get(`/playbook/runs/${id}`),
    {
      ttl: 60 * 1000, // 1 minute
    }
  );
}

/**
 * Hook for playbook definitions
 */
export function usePlaybookDefinitions(params?: Record<string, string>) {
  const key = cacheKeys.playbookDefinitions(params);
  
  return useCachedQuery(
    key,
    () => apiClient.get('/playbook/definitions', params),
    {
      refetchOnMount: true,
      ttl: 60 * 1000, // 1 minute
    }
  );
}

/**
 * Hook for single playbook definition
 */
export function usePlaybookDefinition(id: string) {
  const key = cacheKeys.playbookDefinition(id);
  
  return useCachedQuery(
    key,
    () => apiClient.get(`/playbook/definitions/${id}`),
    {
      ttl: 5 * 60 * 1000, // 5 minutes
    }
  );
}

/**
 * Hook for threat intelligence lookup
 */
export function useThreatIntel(ioc: string, type: string, enabled: boolean = true) {
  const key = cacheKeys.threatIntel(ioc, type);
  
  return useCachedQuery(
    key,
    () => apiClient.get(`/threat-intel/${type}/${encodeURIComponent(ioc)}`),
    {
      enabled,
      ttl: 10 * 60 * 1000, // 10 minutes
    }
  );
}

/**
 * Hook for AI models list
 */
export function useAIModels() {
  const key = cacheKeys.aiModels();
  
  return useCachedQuery(
    key,
    () => apiClient.get('/ai/models'),
    {
      ttl: 5 * 60 * 1000, // 5 minutes
    }
  );
}

/**
 * Hook for user settings
 */
export function useUserSettings() {
  const key = cacheKeys.userSettings();
  
  return useCachedQuery(
    key,
    () => apiClient.get('/users/me/settings'),
    {
      ttl: 5 * 60 * 1000, // 5 minutes
    }
  );
}

/**
 * Mutation hook with cache invalidation
 */
export function useMutation<T, V>(
  mutationFn: (variables: V) => Promise<T>,
  options: {
    onSuccess?: (data: T, variables: V) => void;
    onError?: (error: Error, variables: V) => void;
    invalidateKeys?: string[];
  } = {}
) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const mutate = useCallback(
    async (variables: V) => {
      setIsLoading(true);
      setError(null);

      try {
        const result = await mutationFn(variables);
        
        // Invalidate specified keys
        if (options.invalidateKeys) {
          options.invalidateKeys.forEach((key) => {
            apiCache.delete(key);
          });
        }
        
        options.onSuccess?.(result, variables);
        return result;
      } catch (err) {
        const error = err instanceof Error ? err : new Error(String(err));
        setError(error);
        options.onError?.(error, variables);
        throw error;
      } finally {
        setIsLoading(false);
      }
    },
    [mutationFn, options]
  );

  return { mutate, isLoading, error };
}

export { cacheInvalidators };
