/**
 * Assets API
 */

import { apiClient as client } from "./client";

export type Criticality = "low" | "medium" | "high" | "critical";

export interface AssetCreate {
  name: string;
  asset_type: string;
  ip_address?: string;
  hostname?: string;
  mac_address?: string;
  os?: string;
  owner?: string;
  department?: string;
  location?: string;
  criticality: Criticality;
  tags?: string[];
  notes?: string;
}

export interface AssetUpdate extends Partial<AssetCreate> {}

export interface AssetResponse {
  id: string;
  name: string;
  asset_type: string;
  ip_address?: string;
  hostname?: string;
  mac_address?: string;
  os?: string;
  owner?: string;
  department?: string;
  location?: string;
  criticality: Criticality;
  tags: string[];
  notes?: string;
  created_at: string;
  updated_at: string;
  last_seen_at?: string;
}

export interface AssetImportRequest {
  assets: AssetCreate[];
  overwrite?: boolean;
}

export interface AssetImportResponse {
  imported: number;
  skipped: number;
  errors: Array<{ index: number; error: string }>;
}

export interface AssetListResponse {
  items: AssetResponse[];
  total: number;
  page: number;
  page_size: number;
}

export async function listAssets(
  params: { query?: string; limit?: number } = {}
): Promise<AssetListResponse> {
  const query = new URLSearchParams();
  if (params.query) query.set("query", params.query);
  if (params.limit) query.set("limit", params.limit.toString());
  return client.get(`/api/assets?${query.toString()}`);
}

export async function getAsset(id: string): Promise<AssetResponse> {
  return client.get(`/api/assets/${id}`);
}

export async function createAsset(data: AssetCreate): Promise<AssetResponse> {
  return client.post("/api/assets", data);
}

export async function updateAsset(id: string, data: AssetUpdate): Promise<AssetResponse> {
  return client.patch(`/api/assets/${id}`, data);
}

export async function deleteAsset(id: string): Promise<void> {
  return client.delete(`/api/assets/${id}`);
}

export async function importAssets(data: AssetImportRequest): Promise<AssetImportResponse> {
  return client.post("/api/assets/import", data);
}
