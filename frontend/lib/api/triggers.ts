/**
 * Triggers API (webhook + cron)
 */

import { apiClient as client } from "./client";

export interface WebhookTriggerCreate {
  definition_id: string;
  name?: string;
  config?: Record<string, unknown>;
  is_active?: boolean;
}

export interface CronTriggerCreate {
  definition_id: string;
  cron_expr: string;
  name?: string;
  config?: Record<string, unknown>;
  is_active?: boolean;
}

export interface TriggerOut {
  id: string;
  definition_id: string;
  type: string;
  name: string | null;
  config: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  last_triggered_at: string | null;
  secret_prefix?: string;
  cron_expr?: string;
  webhook_url?: string;
}

export interface TriggerListResponse {
  items: TriggerOut[];
  total: number;
  page: number;
  page_size: number;
}

export interface WebhookTriggerResponse extends TriggerOut {
  type: "webhook";
  secret: string;
  webhook_url: string;
}

export interface CronTriggerResponse extends TriggerOut {
  type: "cron";
  cron_expr: string;
}

export async function listTriggers(
  params: {
    trigger_type?: string;
    is_active?: boolean;
    page?: number;
    page_size?: number;
  } = {}
): Promise<TriggerListResponse> {
  const query = new URLSearchParams();
  if (params.trigger_type) query.set("trigger_type", params.trigger_type);
  if (params.is_active !== undefined) query.set("is_active", params.is_active.toString());
  if (params.page) query.set("page", params.page.toString());
  if (params.page_size) query.set("page_size", params.page_size.toString());
  return client.get(`/api/triggers?${query.toString()}`);
}

export async function getTrigger(triggerId: string): Promise<TriggerOut> {
  return client.get(`/api/triggers/${triggerId}`);
}

export async function createWebhookTrigger(
  data: WebhookTriggerCreate
): Promise<WebhookTriggerResponse> {
  return client.post("/api/triggers/webhook", data, 30000);
}

export async function createCronTrigger(data: CronTriggerCreate): Promise<CronTriggerResponse> {
  return client.post("/api/triggers/cron", data, 30000);
}

export async function updateTrigger(
  triggerId: string,
  data: { name?: string; config?: Record<string, unknown>; cron_expr?: string; is_active?: boolean }
): Promise<TriggerOut> {
  return client.put(`/api/triggers/${triggerId}`, data);
}

export async function deleteTrigger(triggerId: string): Promise<void> {
  return client.delete(`/api/triggers/${triggerId}`);
}

export async function regenerateWebhookSecret(
  triggerId: string
): Promise<{ secret: string; message: string }> {
  return client.post(`/api/triggers/${triggerId}/webhook/regenerate-secret`);
}

export async function getTriggerInvocations(
  triggerId: string,
  limit: number = 50
): Promise<{ invocations: unknown[] }> {
  return client.get(`/api/triggers/${triggerId}/invocations?limit=${limit}`);
}

export async function testWebhookTrigger(
  triggerId: string,
  payload: Record<string, unknown> = {}
): Promise<unknown> {
  return client.post(`/api/webhooks/${triggerId}`, payload, 30000);
}
