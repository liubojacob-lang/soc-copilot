/**
 * Root Cause Analysis API (T2.4)
 *
 * Endpoints:
 * - POST /api/v1/alerts/{id}/root-cause-analysis   → run analysis (refuses when LLM degraded)
 * - GET  /api/v1/alerts/{id}/root-cause-analyses   → analysis history for the alert
 * - POST /api/v1/root-cause-analyses/{id}/feedback → analyst verdict
 *
 * 契约对应 backend/schemas/root_cause.py。
 */

import { apiClient } from "./client";

// ── Types ────────────────────────────────────────────────

export interface RootCauseEvidence {
  evidence?: string;
  supports?: string;
  strength?: string;
  [key: string]: unknown;
}

export interface RootCauseReasoningStep {
  step?: number;
  description?: string;
  findings?: string[];
  [key: string]: unknown;
}

export type RootCauseFeedbackVerdict = "accurate" | "partially_accurate" | "inaccurate";

export interface RootCauseAnalysis {
  id: string;
  alert_id: string;
  root_cause_category: string;
  root_cause_subcategory: string | null;
  confidence: number;
  reasoning_steps: RootCauseReasoningStep[];
  evidence_chain: RootCauseEvidence[];
  verification_steps: string[];
  suggested_remediation: string | null;
  remediation_priority: string;
  ai_model: string;
  analysis_duration_ms: number | null;
  human_verified: boolean;
  human_feedback: string | null;
  feedback_category: RootCauseFeedbackVerdict | null;
  created_at: string;
}

export interface RootCauseAnalysisList {
  items: RootCauseAnalysis[];
  total: number;
}

// ── API ──────────────────────────────────────────────────

export async function runRootCauseAnalysis(alertId: number | string): Promise<RootCauseAnalysis> {
  return apiClient.post<RootCauseAnalysis>(`/api/v1/alerts/${alertId}/root-cause-analysis`);
}

export async function listRootCauseAnalyses(
  alertId: number | string,
  limit = 20
): Promise<RootCauseAnalysisList> {
  return apiClient.get<RootCauseAnalysisList>(
    `/api/v1/alerts/${alertId}/root-cause-analyses?limit=${limit}`
  );
}

export async function submitRootCauseFeedback(
  rcaId: string,
  verdict: RootCauseFeedbackVerdict,
  comment?: string
): Promise<RootCauseAnalysis> {
  return apiClient.post<RootCauseAnalysis>(`/api/v1/root-cause-analyses/${rcaId}/feedback`, {
    verdict,
    comment: comment ?? null,
  });
}
