/**
 * Dashboard API — real-time operational statistics.
 *
 * Backend: GET /api/v1/dashboard/stats (routers/dashboard.py).
 * The endpoint aggregates with a 60s server-side cache; the hook adds
 * client-side staleness control on top.
 */

import { apiClient } from "./client";

export interface SeverityDistribution {
  critical: number;
  high: number;
  medium: number;
  low: number;
  info: number;
}

export interface StatusDistribution {
  new: number;
  investigating: number;
  resolved: number;
  false_positive: number;
  escalated: number;
}

export interface TrendPoint {
  date: string;
  count: number;
}

export interface TrendPointBySeverity {
  date: string;
  critical: number;
  high: number;
  medium: number;
  low: number;
  info: number;
}

export interface TopSource {
  source: string;
  count: number;
}

export interface TopRiskyAsset {
  asset: string;
  alert_count: number;
  risk_score: number;
  asset_type: string;
  ip_address: string | null;
  critical_count: number;
  high_count: number;
}

export interface MITRETechniqueItem {
  technique: string;
  technique_id: string;
  count: number;
}

export interface MITRETacticItem {
  tactic: string;
  tactic_id: string;
  techniques: MITRETechniqueItem[];
}

export interface DashboardStats {
  alerts_total: number;
  alerts_unresolved: number;
  alerts_by_severity: SeverityDistribution;
  alerts_by_status: StatusDistribution;
  cases_open: number;
  cases_overdue: number;
  mttr_minutes: number | null;
  alerts_trend: TrendPoint[];
  alerts_trend_by_severity: TrendPointBySeverity[];
  top_alert_sources: TopSource[];
  top_risky_assets: TopRiskyAsset[];
  ioc_hits_today: number;
  playbook_runs_today: number;
  mitre_tactics?: MITRETacticItem[];
}

// ── Chart adapter types (consumed by dashboard chart components) ──────

export interface AlertTrendPoint {
  date: string;
  critical: number;
  high: number;
  medium: number;
  low: number;
  info: number;
}

export interface SeverityBucket {
  severity: string;
  count: number;
  percentage?: number;
}

export interface AssetRiskItem {
  asset_name: string;
  asset_type: string;
  ip_address: string | null;
  risk_score: number;
  alert_count: number;
  critical_count: number;
  high_count: number;
}

/** AlertTrendsChart series data, straight from the stats payload. */
export function toAlertTrendPoints(stats: DashboardStats): AlertTrendPoint[] {
  return stats.alerts_trend_by_severity;
}

/** SeverityPieChart buckets, straight from the stats payload. */
export function toSeverityBuckets(stats: DashboardStats): SeverityBucket[] {
  const s = stats.alerts_by_severity;
  const pct = (count: number) => (stats.alerts_total > 0 ? (count / stats.alerts_total) * 100 : 0);
  return [
    { severity: "critical", count: s.critical, percentage: pct(s.critical) },
    { severity: "high", count: s.high, percentage: pct(s.high) },
    { severity: "medium", count: s.medium, percentage: pct(s.medium) },
    { severity: "low", count: s.low, percentage: pct(s.low) },
    { severity: "info", count: s.info, percentage: pct(s.info) },
  ];
}

/** AssetRiskTable rows, straight from the stats payload. */
export function toAssetRiskItems(stats: DashboardStats): AssetRiskItem[] {
  return stats.top_risky_assets.map((asset) => ({
    asset_name: asset.asset,
    asset_type: asset.asset_type,
    ip_address: asset.ip_address,
    risk_score: asset.risk_score,
    alert_count: asset.alert_count,
    critical_count: asset.critical_count,
    high_count: asset.high_count,
  }));
}

export async function getDashboardStats(): Promise<DashboardStats> {
  return apiClient.get<DashboardStats>("/api/v1/dashboard/stats");
}
