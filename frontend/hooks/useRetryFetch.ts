/**
 * useRetryFetch Hook
 *
 * React hook for API calls with automatic retry and UI feedback
 */

'use client';

import { useState, useCallback, useRef } from 'react';
import { fetchWithRetryEnhanced } from '@/lib/retryHandler';
import { type RetryState, getRetryState, getRetryStrategy } from '@/lib/retryConfig';

interface UseRetryFetchOptions {
  onSuccess?: (data: any) => void;
  onError?: (error: any) => void;
  onRetry?: (attempt: number, error: any, delay: number) => void;
  showRetryUI?: boolean;
}

interface UseRetryFetchReturn {
  execute: <T>(request: RequestInfo | URL, init?: RequestInit) => Promise<T>;
  data: any;
  error: any;
  isLoading: boolean;
  isRetrying: boolean;
  retryState: RetryState | undefined;
  reset: () => void;
  cancel: () => void;
}

/**
 * Hook for fetch with automatic retry
 *
 * @example
 * ```typescript
 * function AlertList() {
 *   const { execute, data, error, isLoading, isRetrying } = useRetryFetch({
 *     onSuccess: (data) => console.log('Success:', data),
 *   });
 *
 *   useEffect(() => {
 *     execute('/api/alerts');
 *   }, []);
 *
 *   if (isLoading) return <Loading />;
 *   if (error) return <ErrorDisplay error={error} />;
 *   return <AlertList data={data} />;
 * }
 * ```
 */
export function useRetryFetch(options: UseRetryFetchOptions = {}): UseRetryFetchReturn {
  const { onSuccess, onError, onRetry, showRetryUI = true } = options;

  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [retryState, setRetryState] = useState<RetryState | undefined>(undefined);
  const [currentEndpoint, setCurrentEndpoint] = useState<string>('');

  const abortControllerRef = useRef<AbortController | null>(null);
  const retryIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Poll retry state
  const startRetryPolling = useCallback((endpoint: string) => {
    if (retryIntervalRef.current) {
      clearInterval(retryIntervalRef.current);
    }

    retryIntervalRef.current = setInterval(() => {
      const state = getRetryState(endpoint);
      setRetryState(state || undefined);
    }, 100);
  }, []);

  const stopRetryPolling = useCallback(() => {
    if (retryIntervalRef.current) {
      clearInterval(retryIntervalRef.current);
      retryIntervalRef.current = null;
    }
  }, []);

  const execute = useCallback(
    async <T,>(request: RequestInfo | URL, init?: RequestInit): Promise<T> => {
      // Cancel previous request
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      abortControllerRef.current = new AbortController();

      const endpoint =
        typeof request === 'string' ? request : request instanceof URL ? request.href : request.url;
      setCurrentEndpoint(endpoint);

      setIsLoading(true);
      setError(null);
      setRetryState(undefined);

      // Start polling retry state
      if (showRetryUI) {
        startRetryPolling(endpoint);
      }

      try {
        const response = await fetchWithRetryEnhanced(
          request,
          {
            ...init,
            signal: abortControllerRef.current?.signal,
            onRetry: (attempt, error, delay) => {
              console.log(`[Retry] Attempt ${attempt} for ${endpoint} in ${delay}ms`);
              onRetry?.(attempt, error, delay);
            },
          },
          async (input, init) => {
            // Custom fetch that supports auth headers
            const token = localStorage.getItem('token');
            const headers = {
              ...init?.headers,
              ...(token ? { Authorization: `Bearer ${token}` } : {}),
            };

            return fetch(input, { ...init, headers });
          }
        );

        const result: T = await response.json();

        setData(result);
        setIsLoading(false);
        stopRetryPolling();

        onSuccess?.(result);
        return result;
      } catch (err) {
        const errorObj = err instanceof Error ? err : new Error(String(err));
        setError(errorObj);
        setIsLoading(false);
        stopRetryPolling();

        onError?.(errorObj);
        throw errorObj;
      }
    },
    [onSuccess, onError, onRetry, showRetryUI, startRetryPolling, stopRetryPolling]
  );

  const reset = useCallback(() => {
    setData(null);
    setError(null);
    setIsLoading(false);
    setRetryState(undefined);
    stopRetryPolling();
  }, [stopRetryPolling]);

  const cancel = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsLoading(false);
    setRetryState(undefined);
    stopRetryPolling();
  }, [stopRetryPolling]);

  // Cleanup on unmount
  useState(() => {
    return () => {
      stopRetryPolling();
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  });

  return {
    execute,
    data,
    error,
    isLoading,
    isRetrying: retryState?.isRetrying || false,
    retryState,
    reset,
    cancel,
  };
}

/**
 * Hook for multiple parallel fetches with retry
 */
export function useRetryFetchParallel<T = any>(
  requests: Array<RequestInfo | URL>,
  options: UseRetryFetchOptions = {}
) {
  const [results, setResults] = useState<(T | null)[]>(new Array(requests.length).fill(null));
  const [errors, setErrors] = useState<(any | null)[]>(new Array(requests.length).fill(null));
  const [loadingStates, setLoadingStates] = useState<boolean[]>(new Array(requests.length).fill(false));
  const [retryStates, setRetryStates] = useState<(RetryState | undefined)[]>(
    new Array(requests.length).fill(undefined)
  );

  const executeAll = useCallback(async () => {
    const promises = requests.map(async (request, index) => {
      const endpoint =
        typeof request === 'string' ? request : request instanceof URL ? request.href : request.url;

      setLoadingStates(prev => {
        const next = [...prev];
        next[index] = true;
        return next;
      });

      try {
        const response = await fetchWithRetryEnhanced(
          request,
          {
            endpoint,
            onRetry: (attempt, error, delay) => {
              console.log(`[Parallel Retry] Request ${index}: attempt ${attempt}`);
              options.onRetry?.(attempt, error, delay);
            },
          },
          async (input, init) => {
            const token = localStorage.getItem('token');
            const headers = {
              ...init?.headers,
              ...(token ? { Authorization: `Bearer ${token}` } : {}),
            };
            return fetch(input, { ...init, headers });
          }
        );

        const result: T = await response.json();

        setResults(prev => {
          const next = [...prev];
          next[index] = result;
          return next;
        });

        setLoadingStates(prev => {
          const next = [...prev];
          next[index] = false;
          return next;
        });

        return result;
      } catch (err) {
        setErrors(prev => {
          const next = [...prev];
          next[index] = err;
          return next;
        });

        setLoadingStates(prev => {
          const next = [...prev];
          next[index] = false;
          return next;
        });

        throw err;
      }
    });

    return Promise.allSettled(promises);
  }, [requests, options]);

  return {
    executeAll,
    results,
    errors,
    loadingStates,
    retryStates,
    isLoading: loadingStates.some(Boolean),
  };
}
