"use client";

import { QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { useState, useEffect } from "react";
import { queryClient } from "@/lib/queryClient";
import { cacheUtils } from "@/lib/queryClient";
import { getAccessToken, usingHttpOnlyCookies } from "@/lib/auth";

interface QueryProviderProps {
  children: React.ReactNode;
  enableDevtools?: boolean;
}

export function QueryProvider({ children, enableDevtools = false }: QueryProviderProps) {
  const [isDevtoolsEnabled, setIsDevtoolsEnabled] = useState(false);

  // Prefetch common queries on mount
  useEffect(() => {
    const prefetchData = async () => {
      try {
        // Skip prefetching while logged out — both queries would 401
        // (e.g. on the login page) and pollute the console with errors.
        if (!getAccessToken() && !usingHttpOnlyCookies()) return;
        await cacheUtils.prefetchCommonQueries();
      } catch (error) {
        console.warn("Failed to prefetch common queries:", error);
      }
    };

    prefetchData();

    // Check if devtools should be enabled
    setIsDevtoolsEnabled(
      enableDevtools ||
        (typeof window !== "undefined" && window.location.search.includes("react-query-devtools"))
    );

    // Setup cache cleanup on page hide (when user navigates away)
    const handleVisibilityChange = () => {
      if (document.visibilityState === "hidden") {
        // Optional: Clean up old cache entries when page is hidden
        // This helps manage memory usage
        const stats = cacheUtils.getStats();
        if (stats.staleQueries > 50) {
          // If we have many stale queries, clean up some old ones
          queryClient
            .getQueryCache()
            .findAll({
              stale: true,
              predicate: (query) => {
                // Clean queries that have been stale for more than 10 minutes
                return query.state.dataUpdatedAt < Date.now() - 10 * 60 * 1000;
              },
            })
            .forEach((query) => {
              queryClient.removeQueries({ queryKey: query.queryKey });
            });
        }
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [enableDevtools]);

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      {isDevtoolsEnabled && <ReactQueryDevtools initialIsOpen={false} />}
    </QueryClientProvider>
  );
}

/**
 * Hook to access query client utilities
 */
export function useQueryClientUtils() {
  return {
    ...cacheUtils,
    queryClient,
  };
}
