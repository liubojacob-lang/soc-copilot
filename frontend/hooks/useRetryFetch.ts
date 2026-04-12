/**
 * useRetryFetch Hook
 *
 * React hook for API calls with automatic retry and UI feedback
 */

"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { fetchWithRetryEnhanced } from "@/lib/retryHandler";
import { type RetryState } from "@/lib/retryConfig";

interface UseRetryFetchOptions<T = unknown> {
  onSuccess?: (data: T) => void;
  onError?: (error: Error) => void;
  onRetry?: (attempt: number, error: Error, delay: number) => void;
  showRetryUI?: boolean;
}

interface UseRetryFetchReturn<T = unknown> {
  execute: (request: RequestInfo | URL, init?: RequestInit) => Promise<T>;
  data: T | null;
  error: Error | null;
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
export function useRetryFetch<T = unknown>(
  options: UseRetryFetchOptions<T> = {}
): UseRetryFetchReturn<T> {
  const { onSuccess, onError, onRetry, showRetryUI = true } = options;

  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [retryState, setRetryState] = useState<RetryState | undefined>(undefined);
  const [currentEndpoint, setCurrentEndpoint] = useState<string>("");

  const abortControllerRef = useRef<AbortController | null>(null);

  const execute = useCallback(
    async (request: RequestInfo | URL, init?: RequestInit): Promise<T> => {
      // Cancel previous request
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      abortControllerRef.current = new AbortController();

      const endpoint =
        typeof request === "string" ? request : request instanceof URL ? request.href : request.url;
      setCurrentEndpoint(endpoint);

      setIsLoading(true);
      setError(null);
      setRetryState(undefined);

      try {
        const response = await fetchWithRetryEnhanced(
          request,
          {
            ...init,
            signal: abortControllerRef.current?.signal,
            onRetry: (attempt, err, delay) => {
              onRetry?.(attempt, err instanceof Error ? err : new Error(String(err)), delay);
            },
          },
          async (input, init) => {
            // Custom fetch that supports auth headers
            const token = localStorage.getItem("access_token");
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

        onSuccess?.(result);
        return result;
      } catch (err) {
        const errorObj = err instanceof Error ? err : new Error(String(err));
        setError(errorObj);
        setIsLoading(false);

        onError?.(errorObj);
        throw errorObj;
      }
    },
    [onSuccess, onError, onRetry, showRetryUI]
  );

  const reset = useCallback(() => {
    setData(null);
    setError(null);
    setIsLoading(false);
    setRetryState(undefined);
  }, []);

  const cancel = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsLoading(false);
    setRetryState(undefined);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

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
export function useRetryFetchParallel<T = unknown>(
  requests: Array<RequestInfo | URL>,
  options: UseRetryFetchOptions<T> = {}
) {
  const [results, setResults] = useState<(T | null)[]>(new Array(requests.length).fill(null));
  const [errors, setErrors] = useState<(Error | null)[]>(new Array(requests.length).fill(null));
  const [loadingStates, setLoadingStates] = useState<boolean[]>(
    new Array(requests.length).fill(false)
  );
  const [retryStates, setRetryStates] = useState<(RetryState | undefined)[]>(
    new Array(requests.length).fill(undefined)
  );

  const executeAll = useCallback(async () => {
    const promises = requests.map(async (request, index) => {
      const endpoint =
        typeof request === "string" ? request : request instanceof URL ? request.href : request.url;

      setLoadingStates((prev) => {
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
              options.onRetry?.(attempt, error, delay);
            },
          },
          async (input, init) => {
            const token = localStorage.getItem("access_token");
            const headers = {
              ...init?.headers,
              ...(token ? { Authorization: `Bearer ${token}` } : {}),
            };
            return fetch(input, { ...init, headers });
          }
        );

        const result: T = await response.json();

        setResults((prev) => {
          const next = [...prev];
          next[index] = result;
          return next;
        });

        setLoadingStates((prev) => {
          const next = [...prev];
          next[index] = false;
          return next;
        });

        return result;
      } catch (err) {
        setErrors((prev) => {
          const next = [...prev];
          next[index] = err instanceof Error ? err : new Error(String(err));
          return next;
        });

        setLoadingStates((prev) => {
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
