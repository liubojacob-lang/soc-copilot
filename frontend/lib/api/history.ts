/**
 * History API
 */

import { apiClient as client } from "./client";

export interface HistoryRecord {
  id: string;
  module: string;
  query: string;
  result: Record<string, unknown>;
  created_at: string;
  user_id?: string;
}

export interface HistoryListRequest {
  module?: string;
  query?: string;
  limit?: number;
}

export interface HistoryListResponse {
  items: HistoryRecord[];
  total: number;
}

export async function listHistory(data: HistoryListRequest = {}): Promise<HistoryListResponse> {
  const params = new URLSearchParams();
  if (data.module) params.set("module", data.module);
  if (data.query) params.set("query", data.query);
  if (data.limit) params.set("limit", data.limit.toString());
  return client.get(`/api/history?${params.toString()}`);
}

export async function getHistory(id: string): Promise<HistoryRecord> {
  return client.get(`/api/history/${id}`);
}

export async function deleteHistory(id: string): Promise<void> {
  return client.delete(`/api/history/${id}`);
}

export async function deleteAllHistory(): Promise<void> {
  return client.delete("/api/history");
}
