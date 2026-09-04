/**
 * Security Alerts API (v1)
 *
 * Endpoints:
 * - GET    /api/v1/security-alerts          → list with filters, pagination
 * - GET    /api/v1/security-alerts/{id}      → single alert
 * - PATCH  /api/v1/security-alerts/{id}      → update status/assignment/resolution
 * - POST   /api/v1/security-alerts/ingest    → ingest new alert
 * - GET    /api/v1/security-alerts/stats/summary → statistics
 * - DELETE /api/v1/security-alerts/{id}      → delete alert
 */

import { apiClient, type APIResponse } from "./client";
import type { SecurityAlert, SecurityAlertUpdate } from "@/types/api";

// ── Types ────────────────────────────────────────────────

export type AlertSeverity = "critical" | "high" | "medium" | "low" | "info";

export type AlertStatus = "new" | "investigating" | "resolved" | "false_positive" | "escalated";

export interface SecurityAlertItem extends Omit<SecurityAlert, "severity" | "status"> {
  severity: AlertSeverity;
  status: AlertStatus;
  threat_score?: number | null;
  iocs?: Array<{ type: string; value: string; reputation?: string; confidence?: number }>;
  mitre_tactics?: Array<{ tactic: string; techniques: string[] }>;
  tags?: string[];
  notes?: AlertNoteItem[];
  timeline?: TimelineEvent[];
  resolution_note?: string | null;
  resolved_at?: string | null;
  resolved_by?: string | null;
}

export interface AlertNoteItem {
  id: string;
  user_id: string;
  username: string;
  content: string;
  created_at: string;
}

export interface TimelineEvent {
  id: string;
  timestamp: string;
  event_type:
    | "created"
    | "status_changed"
    | "assigned"
    | "enriched"
    | "correlated"
    | "escalated"
    | "resolved"
    | "noted";
  description: string;
  user?: string;
  details?: Record<string, unknown>;
}

export interface SecurityAlertListResponse {
  total: number;
  alerts: SecurityAlertItem[];
  page: number;
  page_size: number;
}

export interface SecurityAlertUpdatePayload {
  status?: string;
  assigned_to?: string;
  resolution?: string;
}

export interface SecurityAlertStats {
  total: number;
  by_severity: Record<string, number>;
  by_status: Record<string, number>;
  by_source: Record<string, number>;
  last_24h: number;
  last_7d: number;
  last_30d: number;
}

export interface AlertListFilters {
  source?: string;
  severity?: string;
  status?: string;
  agent_name?: string;
  source_ip?: string;
  event_type?: string;
  search?: string;
  page?: number;
  page_size?: number;
}

// ── API Functions ────────────────────────────────────────

export async function listSecurityAlerts(
  filters: AlertListFilters = {}
): Promise<SecurityAlertListResponse> {
  const params = new URLSearchParams();
  if (filters.source) params.set("source", filters.source);
  if (filters.severity) params.set("severity", filters.severity);
  if (filters.status) params.set("status", filters.status);
  if (filters.agent_name) params.set("agent_name", filters.agent_name);
  if (filters.source_ip) params.set("source_ip", filters.source_ip);
  if (filters.event_type) params.set("event_type", filters.event_type);
  if (filters.search) params.set("search", filters.search);
  if (filters.page) params.set("page", String(filters.page));
  if (filters.page_size) params.set("page_size", String(filters.page_size));
  const query = params.toString();
  return apiClient.get<SecurityAlertListResponse>(
    `/api/v1/security-alerts${query ? `?${query}` : ""}`
  );
}

export async function getSecurityAlert(id: number): Promise<SecurityAlertItem> {
  return apiClient.get<SecurityAlertItem>(`/api/v1/security-alerts/${id}`);
}

export async function updateSecurityAlert(
  id: number,
  payload: SecurityAlertUpdatePayload
): Promise<SecurityAlertItem> {
  return apiClient.patch<SecurityAlertItem>(`/api/v1/security-alerts/${id}`, payload);
}

export async function deleteSecurityAlert(
  id: number
): Promise<{ status: string; message: string }> {
  return apiClient.delete(`/api/v1/security-alerts/${id}`);
}

export async function getAlertStats(): Promise<SecurityAlertStats> {
  return apiClient.get<SecurityAlertStats>("/api/v1/security-alerts/stats/summary");
}

export async function getAlertLifecycle(id: string | number): Promise<{
  notes: AlertNoteItem[];
  timeline: TimelineEvent[];
  status?: string;
  assigned_to?: string;
}> {
  return apiClient.get(`/api/v1/alerts/${id}/lifecycle`);
}

export async function addAlertNote(
  alertId: string | number,
  content: string
): Promise<AlertNoteItem> {
  return apiClient.post(`/api/v1/alerts/${alertId}/notes`, { content });
}

// ═══════════════════════════════════════════════════════════════════
// v1.1 – Alert Import
// ═══════════════════════════════════════════════════════════════════

export interface AlertImportPayload {
  content: string;
  format?: string;
  source?: string;
}

export interface AlertImportResponse {
  alert?: SecurityAlertItem;
  parsed: Record<string, unknown>;
  format_detected: string;
}

export interface AlertBatchImportPayload {
  content: string;
  format?: string;
  source?: string;
  preview_only?: boolean;
}

export interface AlertBatchImportResponse {
  total_parsed: number;
  total_created: number;
  format_detected: string;
  preview: Array<Record<string, unknown>>;
  errors: Array<{ row: number; error: string; title?: string }>;
}

/**
 * Import a single alert from CEF, Syslog, JSON, or CSV text.
 */
export async function importAlert(
  payload: AlertImportPayload
): Promise<APIResponse<AlertImportResponse>> {
  return apiClient.post<APIResponse<AlertImportResponse>>("/api/alerts/import", payload);
}

/**
 * Preview a single alert import (parse only, no create).
 */
export async function previewAlertImport(
  payload: AlertImportPayload
): Promise<APIResponse<{ parsed: Record<string, unknown>; format_detected: string }>> {
  return apiClient.post<APIResponse<{ parsed: Record<string, unknown>; format_detected: string }>>(
    "/api/alerts/import/preview",
    payload
  );
}

/**
 * Batch import alerts from multiline text, JSON array, or CSV.
 */
export async function importAlertsBatch(
  payload: AlertBatchImportPayload
): Promise<APIResponse<AlertBatchImportResponse>> {
  return apiClient.post<APIResponse<AlertBatchImportResponse>>("/api/alerts/import/batch", payload);
}

/**
 * Preview batch import (parse only, no create).
 */
export async function previewBatchImport(payload: AlertBatchImportPayload): Promise<
  APIResponse<{
    total_parsed: number;
    format_detected: string;
    preview: Array<Record<string, unknown>>;
  }>
> {
  return apiClient.post<
    APIResponse<{
      total_parsed: number;
      format_detected: string;
      preview: Array<Record<string, unknown>>;
    }>
  >("/api/alerts/import/batch/preview", payload);
}
