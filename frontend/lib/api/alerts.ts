/**
 * Alerts & Analysis API
 */

import { apiClient as client } from "./client";

export interface AlertAnalysisRequest {
  title: string;
  description: string;
  source?: string;
  severity?: string;
  raw_log?: string;
}

export interface IOCsFinal {
  ips: string[];
  domains: string[];
  urls: string[];
  hashes: string[];
}

export interface IOCsLocal {
  ips: string[];
  domains: string[];
  urls: string[];
  hashes: string[];
}

export interface IOCsLLM {
  ips: string[];
  domains: string[];
  urls: string[];
  hashes: string[];
}

export interface IOCCount {
  total: number;
  ips: number;
  domains: number;
  urls: number;
  hashes: number;
}

export interface RecommendedAction {
  action: string;
  priority: "low" | "medium" | "high" | "critical";
  description: string;
  automated: boolean;
}

export interface AlertAnalysisResponse {
  summary: string;
  severity: "low" | "medium" | "high" | "critical";
  iocs: IOCsFinal;
  ioc_count: IOCCount;
  attack_pattern: string;
  recommended_actions: RecommendedAction[];
  confidence: number;
  model_used: string;
  raw_response?: string;
  trace_id?: string;
}

export interface ResponseMetadata {
  trace_id?: string;
  model_used?: string;
  latency_ms?: number;
}

export interface ReportGenerationRequest {
  title: string;
  events: Array<{
    timestamp: string;
    event_type: string;
    description: string;
    source: string;
  }>;
  format?: "markdown" | "html" | "pdf";
}

export interface ReportGenerationResponse extends ResponseMetadata {
  report: string;
  format: string;
  generated_at: string;
}

/**
 * Timeline types — mirror backend schemas/timeline.py (schemas/impact.py, schemas/threat_intel.py).
 * Endpoint: POST /api/v1/build-timeline (backend/routers/timeline.py).
 */
export interface TimelineRequest {
  /** Raw log content (min_length 1) */
  raw_log: string;
  /** Log type hint: sysmon / windows / linux / nginx; omit for auto-detection */
  log_type?: "sysmon" | "windows" | "linux" | "nginx" | null;
}

export interface TimelineEvent {
  timestamp: string;
  type: string;
  description: string;
  key_fields: Record<string, unknown>;
}

export interface SuspiciousEvent {
  timestamp: string;
  description: string;
  reasoning: string;
  severity: string;
}

export interface IOCsGrouped {
  ips: string[];
  domains: string[];
  urls: string[];
  hashes: string[];
}

export interface IOCCount {
  ips: number;
  domains: number;
  urls: number;
  hashes: number;
  total: number;
}

export interface AffectedAsset {
  asset_id: string;
  hostname?: string | null;
  ip?: string | null;
  criticality: string;
  reason: string;
}

export interface ContainmentPriority {
  asset_id: string;
  /** 1-10 */
  priority: number;
  reason: string;
}

export interface ImpactAnalysis {
  affected_assets: AffectedAsset[];
  business_impact: string;
  /** 0-100 */
  risk_score: number;
  severity: "low" | "medium" | "high" | "critical";
  containment_priority: ContainmentPriority[];
  recommended_next_queries: string[];
}

export interface ThreatIntelItemTL {
  ioc_type: string;
  ioc_value: string;
  verdict: "benign" | "unknown" | "suspicious" | "malicious";
  /** 0-100 */
  score: number;
  pulse_count?: number;
  tags?: string[];
  references?: string[];
  cached?: boolean;
  skipped?: boolean;
  skipped_reason?: string | null;
}

export interface ThreatIntelAnalysisTL {
  provider: string;
  disabled: boolean;
  degraded: boolean;
  skipped: boolean;
  items: ThreatIntelItemTL[];
  /** IOCs filtered by compliance policy (not sent to external TI) */
  filtered_items: ThreatIntelItemTL[];
  error_reason?: string | null;
}

export interface TimelineResponse extends ResponseMetadata {
  timeline: TimelineEvent[];
  suspicious_top5: SuspiciousEvent[];
  next_steps: string[];
  iocs: IOCsGrouped;
  iocs_local: IOCsGrouped;
  iocs_llm: IOCsGrouped;
  ioc_count: IOCCount;
  request_id?: string | null;
  /** Whether the backend fell back to degraded mode (partial analysis) */
  degraded?: boolean;
  error_reason?: string | null;
  history_id?: string | null;
  impact_analysis: ImpactAnalysis;
  threat_intel: ThreatIntelAnalysisTL;
}

export interface ThreatIntelItem {
  ioc_type: string;
  ioc_value: string;
  verdict: "benign" | "unknown" | "suspicious" | "malicious";
  score: number;
  pulse_count: number;
  tags: string[];
  references: string[];
  cached: boolean;
  skipped: boolean;
  skipped_reason?: string | null;
}

export interface ThreatIntelAnalysis {
  provider?: string;
  disabled?: boolean;
  degraded?: boolean;
  skipped?: boolean;
  items: ThreatIntelItem[];
  filtered_items?: ThreatIntelItem[];
  error_reason?: string | null;
  summary: string;
  risk_score: number;
  recommendations: string[];
}

export type Verdict = "benign" | "unknown" | "suspicious" | "malicious";

export type Platform = "splunk" | "elastic_kql" | "sentinel_kql";
export type TimeRange = "last_1h" | "last_24h" | "last_7d";
export type OutputType = "queries" | "actions";
export type RiskLevel = "low" | "medium" | "high" | "critical";
export type ActionCategory = "containment" | "eradication" | "recovery";

export interface QueryTemplate {
  platform: Platform;
  query: string;
  description: string;
  confidence: number;
}

export interface PlatformQueries {
  platform: Platform;
  queries: QueryTemplate[];
}

export interface GeneratePlaybookQueriesResponse extends ResponseMetadata {
  platforms: PlatformQueries[];
  time_ranges: TimeRange[];
  summary: string;
}

export interface RemediationStep {
  step: number;
  action: string;
  command?: string;
  expected_result: string;
  risk_level: RiskLevel;
}

export interface RemediationAction {
  category: ActionCategory;
  title: string;
  description: string;
  steps: RemediationStep[];
  priority: number;
  automated: boolean;
}

export interface GenerateRemediationActionsResponse extends ResponseMetadata {
  actions: RemediationAction[];
  summary: string;
  policy: string;
}

export interface AffectedAsset {
  asset_id: string;
  asset_name: string;
  asset_type: string;
  impact_level: "low" | "medium" | "high" | "critical";
  description: string;
}

export interface ContainmentPriority {
  priority: number;
  action: string;
  target: string;
  urgency: "low" | "medium" | "high" | "critical";
  estimated_time: string;
}

export interface ImpactAnalysis {
  affected_assets: AffectedAsset[];
  containment_priorities: ContainmentPriority[];
  blast_radius: "low" | "medium" | "high" | "critical";
  summary: string;
  recommendations: string[];
}

export type Criticality = "low" | "medium" | "high" | "critical";

export async function analyzeAlert(data: AlertAnalysisRequest): Promise<AlertAnalysisResponse> {
  return client.post<AlertAnalysisResponse>("/api/v1/analyze-alert", data, 120000);
}

export async function generateReport(
  data: ReportGenerationRequest
): Promise<ReportGenerationResponse> {
  return client.post<ReportGenerationResponse>("/api/v1/generate-report", data, 120000);
}

export async function buildTimeline(data: TimelineRequest): Promise<TimelineResponse> {
  return client.post<TimelineResponse>("/api/v1/build-timeline", data, 120000);
}

export async function generatePlaybookQueries(
  module: string,
  historyId?: string,
  iocs?: { ips: string[]; domains: string[]; urls: string[]; hashes: string[] },
  platforms: string[] = ["splunk"],
  timeRanges: string[] = ["last_24h"]
): Promise<GeneratePlaybookQueriesResponse> {
  return client.post<GeneratePlaybookQueriesResponse>(
    "/api/v1/playbook/queries",
    {
      module,
      history_id: historyId,
      iocs,
      platforms,
      time_ranges: timeRanges,
    },
    30000
  );
}

export async function generateRemediationActions(
  historyId: string,
  policy: string = "safe",
  includeVerificationSteps: boolean = true
): Promise<GenerateRemediationActionsResponse> {
  return client.post<GenerateRemediationActionsResponse>(
    "/api/v1/playbook/actions",
    {
      history_id: historyId,
      policy,
      include_verification_steps: includeVerificationSteps,
    },
    30000
  );
}

export async function getPlaybookHistory(
  historyId?: string,
  limit: number = 50
): Promise<{ outputs: Array<Record<string, unknown>> }> {
  const params = new URLSearchParams();
  if (historyId) params.set("history_id", historyId);
  params.set("limit", limit.toString());
  return client.get(`/api/playbook/history?${params.toString()}`);
}

export async function healthCheck(): Promise<{ status: string; version: string }> {
  return client.get("/api/health");
}

export async function getThreatIntelStats(): Promise<Record<string, unknown>> {
  return client.get("/api/ti/stats");
}

export async function lookupOTX(iocType: string, iocValue: string): Promise<unknown> {
  return client.get(
    `/api/ti/otx?ioc_type=${encodeURIComponent(iocType)}&ioc_value=${encodeURIComponent(iocValue)}`
  );
}

export async function bulkLookupOTX(
  items: Array<{ ioc_type: string; ioc_value: string }>
): Promise<unknown> {
  return client.post("/api/ti/otx/bulk", { items });
}
