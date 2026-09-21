/**
 * Cases API (v1)
 *
 * Endpoints:
 * - GET    /api/v1/cases              → list with filters, pagination
 * - POST   /api/v1/cases              → create case
 * - GET    /api/v1/cases/{id}         → single case detail
 * - PATCH  /api/v1/cases/{id}         → update case
 * - DELETE /api/v1/cases/{id}         → delete case
 * - GET    /api/v1/cases/{id}/alerts  → linked alerts
 * - POST   /api/v1/cases/{id}/alerts  → link alert
 * - DELETE /api/v1/cases/{id}/alerts/{alertId} → unlink alert
 * - GET    /api/v1/cases/{id}/comments → comments
 * - POST   /api/v1/cases/{id}/comments → add comment
 * - GET    /api/v1/cases/{id}/timeline → timeline/audit log
 * - PATCH  /api/v1/cases/{id}/status  → transition status
 */

import { apiClient } from "./client";

// ── Types ────────────────────────────────────────────────

export type CaseSeverity = "critical" | "high" | "medium" | "low";

export type CaseStatus =
  | "new"
  | "investigating"
  | "contained"
  | "remediated"
  | "closed"
  | "false_positive";

export interface SecurityCase {
  id: string;
  title: string;
  description: string | null;
  severity: CaseSeverity;
  status: CaseStatus;
  assigned_to: string | null;
  assigned_analyst_name?: string | null;
  sla_deadline: string | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
  resolved_by: string | null;
  resolution_note: string | null;
  tags: string[];
  related_alert_count?: number;
  comment_count?: number;
}

export interface CaseListResponse {
  total: number;
  cases: SecurityCase[];
  page: number;
  page_size: number;
}

export interface CaseFilters {
  search?: string;
  severity?: string;
  status?: string;
  assigned_to?: string;
  sort_by?: string;
  sort_order?: "asc" | "desc";
  page?: number;
  page_size?: number;
}

export interface CaseCreatePayload {
  title: string;
  description?: string;
  severity: CaseSeverity;
  status?: CaseStatus;
  assigned_to?: string;
  sla_deadline?: string;
  tags?: string[];
  alert_ids?: (string | number)[];
}

export interface CaseUpdatePayload {
  title?: string;
  description?: string;
  severity?: CaseSeverity;
  assigned_to?: string;
  sla_deadline?: string;
  tags?: string[];
  resolution_note?: string;
}

export interface CaseStatusTransition {
  status: CaseStatus;
  reason?: string;
}

export interface CaseComment {
  id: string;
  case_id: string;
  user_id: string;
  username: string;
  content: string;
  created_at: string;
}

export interface CaseCommentCreate {
  content: string;
}

export interface CaseAlert {
  id: number;
  title: string;
  severity: string;
  status: string;
  source_ip: string | null;
  created_at: string;
  event_type: string | null;
}

export interface CaseTimelineEvent {
  id: string;
  timestamp: string;
  event_type:
    | "created"
    | "status_changed"
    | "assigned"
    | "sla_updated"
    | "alert_linked"
    | "alert_unlinked"
    | "comment_added"
    | "updated";
  description: string;
  user?: string;
  details?: Record<string, unknown>;
}

// ── API Functions ────────────────────────────────────────

export async function listCases(filters: CaseFilters = {}): Promise<CaseListResponse> {
  const params = new URLSearchParams();
  if (filters.search) params.set("search", filters.search);
  if (filters.severity) params.set("severity", filters.severity);
  if (filters.status) params.set("status", filters.status);
  if (filters.assigned_to) params.set("assigned_to", filters.assigned_to);
  if (filters.sort_by) params.set("sort_by", filters.sort_by);
  if (filters.sort_order) params.set("sort_order", filters.sort_order);
  if (filters.page) params.set("page", String(filters.page));
  if (filters.page_size) params.set("page_size", String(filters.page_size));
  const query = params.toString();
  const res = await apiClient.get<any>(`/api/v1/cases${query ? `?${query}` : ""}`);
  const rawList: any[] = res?.cases || res?.items || [];
  const cases: SecurityCase[] = rawList.map((item: any) => ({
    ...item,
    sla_deadline: item.sla_deadline ?? item.sla_due_at ?? null,
    sla_due_at: item.sla_due_at ?? item.sla_deadline ?? null,
    related_alert_count: item.related_alert_count ?? item.alert_count ?? 0,
    comment_count: item.comment_count ?? 0,
    tags: item.tags ?? [],
  }));
  return {
    total: res?.total ?? cases.length,
    cases,
    page: res?.page ?? 1,
    page_size: res?.page_size ?? 20,
  };
}

export async function getCase(id: string): Promise<SecurityCase> {
  const res = await apiClient.get<any>(`/api/v1/cases/${id}`);
  return {
    ...res,
    sla_deadline: res.sla_deadline ?? res.sla_due_at ?? null,
    sla_due_at: res.sla_due_at ?? res.sla_deadline ?? null,
    related_alert_count: res.related_alert_count ?? res.alert_count ?? res.alerts?.length ?? 0,
    comment_count: res.comment_count ?? res.comments?.length ?? 0,
    tags: res.tags ?? [],
  };
}

export async function createCase(payload: CaseCreatePayload): Promise<SecurityCase> {
  return apiClient.post<SecurityCase>("/api/v1/cases", payload);
}

export async function updateCase(id: string, payload: CaseUpdatePayload): Promise<SecurityCase> {
  return apiClient.patch<SecurityCase>(`/api/v1/cases/${id}`, payload);
}

export async function deleteCase(id: string): Promise<{ status: string; message: string }> {
  return apiClient.delete(`/api/v1/cases/${id}`);
}

export async function transitionCaseStatus(
  id: string,
  payload: CaseStatusTransition
): Promise<SecurityCase> {
  return apiClient.patch<SecurityCase>(`/api/v1/cases/${id}/status`, payload);
}

// ── Case Alerts ──────────────────────────────────────────

export async function getCaseAlerts(id: string): Promise<CaseAlert[]> {
  return apiClient.get<CaseAlert[]>(`/api/v1/cases/${id}/alerts`);
}

export async function linkAlertToCase(
  caseId: string,
  alertId: number
): Promise<{ status: string; message: string }> {
  return apiClient.post(`/api/v1/cases/${caseId}/alerts`, { alert_id: alertId });
}

export async function unlinkAlertFromCase(
  caseId: string,
  alertId: number
): Promise<{ status: string; message: string }> {
  return apiClient.delete(`/api/v1/cases/${caseId}/alerts/${alertId}`);
}

// ── Case Comments ────────────────────────────────────────

export async function getCaseComments(id: string): Promise<CaseComment[]> {
  return apiClient.get<CaseComment[]>(`/api/v1/cases/${id}/comments`);
}

export async function addCaseComment(
  caseId: string,
  payload: CaseCommentCreate
): Promise<CaseComment> {
  return apiClient.post(`/api/v1/cases/${caseId}/comments`, payload);
}

// ── Case Timeline ────────────────────────────────────────

export async function getCaseTimeline(id: string): Promise<CaseTimelineEvent[]> {
  return apiClient.get<CaseTimelineEvent[]>(`/api/v1/cases/${id}/timeline`);
}

// ── Helper: map severity to Badge severity ────────────────

export function mapCaseSeverity(s: string): string {
  const m: Record<string, string> = {
    critical: "critical",
    high: "high",
    medium: "medium",
    low: "low",
  };
  return m[s] || "neutral";
}

// ── Status / Severity Option Lists ───────────────────────

export const CASE_STATUS_OPTIONS: Array<{ value: string; labelKey: string }> = [
  { value: "new", labelKey: "cases.statusNew" },
  { value: "investigating", labelKey: "cases.statusInvestigating" },
  { value: "contained", labelKey: "cases.statusContained" },
  { value: "remediated", labelKey: "cases.statusRemediated" },
  { value: "closed", labelKey: "cases.statusClosed" },
  { value: "false_positive", labelKey: "cases.statusFalsePositive" },
];

export const CASE_SEVERITY_OPTIONS: Array<{ value: string; labelKey: string }> = [
  { value: "critical", labelKey: "cases.severityCritical" },
  { value: "high", labelKey: "cases.severityHigh" },
  { value: "medium", labelKey: "cases.severityMedium" },
  { value: "low", labelKey: "cases.severityLow" },
];

export const STATUS_TRANSITIONS: Record<string, string[]> = {
  new: ["investigating", "false_positive"],
  investigating: ["contained", "false_positive"],
  contained: ["remediated", "investigating"],
  remediated: ["closed", "investigating"],
  closed: ["investigating"],
  false_positive: ["new"],
};
