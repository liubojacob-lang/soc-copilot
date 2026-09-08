"use client";

/**
 * React Query hooks for Security Alerts.
 *
 * Features:
 * - useAlerts: paginated list with filters
 * - useAlertDetail: single alert by ID
 * - useAlertStats: dashboard statistics
 * - useUpdateAlert: mutation for status/assignment/resolution
 * - useDeleteAlert: mutation for deletion
 * - useAlertLifecycle: notes + timeline
 * - useAddAlertNote: mutation for adding notes
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/queryClient";
import {
  listSecurityAlerts,
  getSecurityAlert,
  updateSecurityAlert,
  deleteSecurityAlert,
  getAlertStats,
  getAlertLifecycle,
  addAlertNote,
  type AlertListFilters,
  type SecurityAlertUpdatePayload,
} from "@/lib/api";
import { useCallback } from "react";

// ── useAlerts ──────────────────────────────────────────

export function useAlerts(filters: AlertListFilters = {}) {
  return useQuery({
    queryKey: queryKeys.alerts.list(filters),
    queryFn: () => listSecurityAlerts(filters),
    staleTime: 30 * 1000,
  });
}

// ── useAlertDetail ─────────────────────────────────────

export function useAlertDetail(id: string | number | null | undefined) {
  const enabled = id !== null && id !== undefined && id !== "";
  return useQuery({
    queryKey: queryKeys.alerts.detail(String(id)),
    queryFn: () => getSecurityAlert(Number(id)),
    enabled,
    staleTime: 15 * 1000,
  });
}

// ── useAlertStats ──────────────────────────────────────

export function useAlertStats() {
  return useQuery({
    queryKey: ["alerts", "stats"],
    queryFn: getAlertStats,
    staleTime: 60 * 1000,
  });
}

// ── useAlertLifecycle ──────────────────────────────────

export function useAlertLifecycle(id: string | number | null | undefined) {
  const enabled = id !== null && id !== undefined && id !== "";
  return useQuery({
    queryKey: [...queryKeys.alerts.detail(String(id)), "lifecycle"],
    queryFn: () => getAlertLifecycle(String(id)),
    enabled,
    staleTime: 15 * 1000,
  });
}

// ── useUpdateAlert ─────────────────────────────────────

export function useUpdateAlert() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: SecurityAlertUpdatePayload }) =>
      updateSecurityAlert(id, payload),
    onSuccess: (_data, variables) => {
      // Invalidate the specific alert detail
      queryClient.invalidateQueries({
        queryKey: queryKeys.alerts.detail(String(variables.id)),
      });
      // Invalidate the alert list (status may have changed)
      queryClient.invalidateQueries({ queryKey: queryKeys.alerts.lists() });
      // Invalidate stats
      queryClient.invalidateQueries({ queryKey: ["alerts", "stats"] });
    },
  });
}

// ── useDeleteAlert ─────────────────────────────────────

export function useDeleteAlert() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) => deleteSecurityAlert(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.alerts.lists() });
      queryClient.invalidateQueries({ queryKey: ["alerts", "stats"] });
    },
  });
}

// ── useBatchUpdateAlerts ───────────────────────────────

export function useBatchUpdateAlerts() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      ids,
      payload,
    }: {
      ids: number[];
      payload: SecurityAlertUpdatePayload;
    }) => {
      const results = await Promise.allSettled(ids.map((id) => updateSecurityAlert(id, payload)));
      const failures = results.filter((r) => r.status === "rejected");
      if (failures.length > 0) {
        throw new Error(`${failures.length}/${ids.length} updates failed`);
      }
      return results;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.alerts.lists() });
      queryClient.invalidateQueries({ queryKey: ["alerts", "stats"] });
    },
  });
}

// ── useAddAlertNote ────────────────────────────────────

export function useAddAlertNote() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ alertId, content }: { alertId: string | number; content: string }) =>
      addAlertNote(alertId, content),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: [...queryKeys.alerts.detail(String(variables.alertId)), "lifecycle"],
      });
    },
  });
}

// ── Alert Filter Helpers ───────────────────────────────

export const ALERT_STATUS_OPTIONS: Array<{ value: string; labelKey: string }> = [
  { value: "new", labelKey: "alerts.statusNew" },
  { value: "investigating", labelKey: "alerts.statusInvestigating" },
  { value: "resolved", labelKey: "alerts.statusResolved" },
  { value: "false_positive", labelKey: "alerts.statusFalsePositive" },
  { value: "escalated", labelKey: "alerts.statusEscalated" },
];

export const ALERT_SEVERITY_OPTIONS: Array<{ value: string; labelKey: string }> = [
  { value: "critical", labelKey: "alerts.severityCritical" },
  { value: "high", labelKey: "alerts.severityHigh" },
  { value: "medium", labelKey: "alerts.severityMedium" },
  { value: "low", labelKey: "alerts.severityLow" },
  { value: "info", labelKey: "alerts.severityInfo" },
];

export function useAlertFilters(initialFilters?: AlertListFilters) {
  return { initialFilters };
}
