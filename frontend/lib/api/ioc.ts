/**
 * IOC Hits API
 */

import { apiClient as client } from "./client";

export type IOCType = "ip" | "domain" | "url" | "hash";
export type IOCSource = "local" | "llm" | "manual";

export interface IOCHitCreate {
  ioc_type: IOCType;
  ioc_value: string;
  source: IOCSource;
  history_id?: string;
  asset_id?: string;
  context?: string;
  confidence?: number;
}

export interface IOCHitResponse {
  id: string;
  ioc_type: IOCType;
  ioc_value: string;
  source: IOCSource;
  history_id?: string;
  asset_id?: string;
  context?: string;
  confidence: number;
  first_seen: string;
  last_seen: string;
  hit_count: number;
  created_at: string;
}

export interface IOCHitListResponse {
  items: IOCHitResponse[];
  total: number;
}

export async function listIOCHits(ioc: string, limit: number = 100): Promise<IOCHitListResponse> {
  return client.get(`/api/ioc-hits?ioc=${encodeURIComponent(ioc)}&limit=${limit}`);
}

export async function listIOCHitsByAsset(
  assetId: string,
  limit: number = 100
): Promise<IOCHitListResponse> {
  return client.get(`/api/ioc-hits/by-asset/${assetId}?limit=${limit}`);
}

export async function listIOCHitsByHistory(
  historyId: string,
  limit: number = 100
): Promise<IOCHitResponse[]> {
  return client.get(`/api/ioc-hits/by-history/${historyId}?limit=${limit}`);
}

export async function createManualIOCHit(data: IOCHitCreate): Promise<IOCHitResponse> {
  return client.post("/api/ioc-hits/manual", data);
}
