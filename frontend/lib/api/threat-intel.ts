/**
 * Threat Intelligence API — typed client for backend /api/v1/ti/* endpoints.
 *
 * Contract mirrors backend/schemas/threat_intel.py and
 * backend/routers/threat_intel.py:
 *   GET  /api/v1/ti/otx           — single IOC lookup (OTX provider)
 *   POST /api/v1/ti/batch         — batch IOC query (max 50)
 *   GET  /api/v1/ti/stats         — cache statistics
 */

import { apiClient as client } from "./client";

export type TIIOCType = "ip" | "domain" | "url" | "hash";
export type TIVerdict = "benign" | "unknown" | "suspicious" | "malicious";

/** GET /api/v1/ti/otx response (backend: ThreatIntelResponse). */
export interface ThreatIntelLookupResponse {
  request_id: string;
  provider: string;
  disabled: boolean;
  cached: boolean;
  degraded: boolean;
  ioc_type: string;
  ioc_value: string;
  verdict: TIVerdict;
  score: number;
  pulse_count: number;
  tags: string[];
  references: string[];
  raw: Record<string, unknown>;
  error_reason: string | null;
  skipped_reason: string | null;
  provider_status?: string | null;
}

/** POST /api/v1/ti/batch request item. */
export interface IOCBatchRequestItem {
  ioc_type: TIIOCType;
  ioc_value: string;
}

/** POST /api/v1/ti/batch result item (backend: IOCBatchResultItem). */
export interface IOCBatchResultItem {
  ioc_type: string;
  ioc_value: string;
  verdict: TIVerdict;
  score: number;
  source: string;
  pulse_count: number;
  tags: string[];
  references: string[];
  details: Record<string, unknown>;
  cached: boolean;
  error: string | null;
}

/** POST /api/v1/ti/batch response (backend: IOCBatchResponse). */
export interface IOCBatchResponse {
  request_id: string;
  provider: string;
  total: number;
  results: IOCBatchResultItem[];
  skipped_count: number;
  errors: Array<{ ioc_type: string; ioc_value: string; error: string }>;
}

/** Single IOC lookup against OTX. */
export async function lookupIoc(
  iocType: TIIOCType,
  iocValue: string
): Promise<ThreatIntelLookupResponse> {
  return client.get(
    `/api/v1/ti/otx?ioc_type=${encodeURIComponent(iocType)}&ioc_value=${encodeURIComponent(iocValue)}`
  );
}

/** Batch IOC query (1–50 items per backend limit). */
export async function batchIocQuery(items: IOCBatchRequestItem[]): Promise<IOCBatchResponse> {
  return client.post("/api/v1/ti/batch", { items });
}

/** Threat-intel cache statistics. */
export async function getTICacheStats(): Promise<{
  cache_stats: {
    total?: number;
    active?: number;
    expired?: number;
    by_provider?: Record<string, number>;
  };
  config: Record<string, unknown>;
}> {
  return client.get("/api/v1/ti/stats");
}

export interface IOCHitItem {
  id: string;
  created_at: string;
  history_id: string | null;
  asset_id: string | null;
  ioc_type: string;
  ioc_value: string;
  confidence: number;
  source: string;
  context_snippet: string | null;
  notes: string | null;
}

export interface IOCHitListResponse {
  items: IOCHitItem[];
  total: number;
}

/** Get recent active IOC detections/hits from database. */
export async function getRecentIocHits(limit = 100): Promise<IOCHitListResponse> {
  return client.get(`/api/v1/ioc-hits?limit=${limit}`);
}

/** Heuristic IOC type detection for pasted/free-form input. */
export function detectIocType(value: string): TIIOCType | null {
  const s = value.trim();
  if (!s) return null;
  if (/^https?:\/\//i.test(s)) return "url";
  // IPv4
  if (/^(\d{1,3}\.){3}\d{1,3}$/.test(s)) return "ip";
  // MD5 / SHA-1 / SHA-256 hex digests
  if (/^[a-fA-F0-9]{32}$/.test(s) || /^[a-fA-F0-9]{40}$/.test(s) || /^[a-fA-F0-9]{64}$/.test(s)) {
    return "hash";
  }
  // Domain (dotted labels)
  if (
    /^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)+$/.test(s)
  ) {
    return "domain";
  }
  return null;
}
