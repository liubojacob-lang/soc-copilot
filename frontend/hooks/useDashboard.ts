"use client";

/**
 * React Query hook for the operational dashboard.
 *
 * Backend caches aggregates for 60s; we poll every 60s on top of that so
 * open dashboards stay current without hammering the database.
 */

import { useQuery } from "@tanstack/react-query";
import { getDashboardStats, type DashboardStats } from "@/lib/api/dashboard";

export function useDashboardStats() {
  return useQuery<DashboardStats>({
    queryKey: ["dashboard", "stats"],
    queryFn: getDashboardStats,
    staleTime: 30 * 1000,
    refetchInterval: 60 * 1000,
  });
}
