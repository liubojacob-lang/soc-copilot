/**
 * Secrets & Queue API
 */

import { apiClient as client } from "./client";

export interface Secret {
  id: string;
  name: string;
  value_preview: string;
  created_at: string;
  updated_at: string;
  created_by_user_id: string | null;
}

export interface SecretListResponse {
  items: Secret[];
  total: number;
  page: number;
  page_size: number;
}

export interface QueueStats {
  running: number;
  queued: number;
  max_concurrent: number;
  has_capacity: boolean;
}

export async function listSecrets(page = 1, pageSize = 50): Promise<SecretListResponse> {
  return client.get(`/api/secrets?page=${page}&page_size=${pageSize}`);
}

export async function getSecret(name: string): Promise<Secret> {
  return client.get(`/api/secrets/${name}`);
}

export async function createSecret(name: string, value: string): Promise<Secret> {
  return client.post("/api/secrets", { name, value }, 30000);
}

export async function updateSecret(name: string, value: string): Promise<Secret> {
  return client.patch(`/api/secrets/${name}`, { value });
}

export async function deleteSecret(name: string): Promise<void> {
  return client.delete(`/api/secrets/${name}`);
}

export async function getKeyStatus(): Promise<{
  configured: boolean;
  valid: boolean;
  key_preview?: string;
}> {
  return client.get("/api/secrets/key-status");
}

export async function getQueueStats(): Promise<QueueStats> {
  return client.get("/api/playbook-definitions/queue-stats");
}
