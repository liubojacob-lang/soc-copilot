/**
 * Playbooks API
 * Handles playbook definitions, runs, and execution
 */

import { apiClient as client } from "./client";

interface PlaybookDefinition {
  id: string;
  name: string;
  description?: string;
  dag?: {
    nodes: Array<{
      id: string;
      type: string;
      config: Record<string, unknown>;
    }>;
    edges: Array<{
      from: string;
      to: string;
    }>;
  };
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface PlaybookRun {
  id: string;
  definition_id: string;
  status: "queued" | "running" | "success" | "failed" | "partial";
  mode: "manual" | "auto";
  started_at?: string;
  completed_at?: string;
  duration_ms?: number;
  error_message?: string;
  created_at: string;
}

interface RunQueueStatus {
  running: number;
  queued: number;
  max: number;
}

/**
 * List playbook definitions
 */
export async function listPlaybookDefinitions(params?: {
  is_active?: boolean;
  limit?: number;
  offset?: number;
}): Promise<PlaybookDefinition[]> {
  return client.get<PlaybookDefinition[]>("/api/playbook-definitions", { params } as RequestInit);
}

/**
 * Get playbook definition by ID
 */
export async function getPlaybookDefinition(id: string): Promise<PlaybookDefinition> {
  return client.get<PlaybookDefinition>(`/api/playbook-definitions/${id}`);
}

/**
 * Create playbook definition
 */
export async function createPlaybookDefinition(data: {
  name: string;
  description?: string;
  dag: PlaybookDefinition["dag"];
}): Promise<PlaybookDefinition> {
  return client.post<PlaybookDefinition>("/api/playbook-definitions", data);
}

/**
 * Update playbook definition
 */
export async function updatePlaybookDefinition(
  id: string,
  data: Partial<PlaybookDefinition>
): Promise<PlaybookDefinition> {
  return client.put<PlaybookDefinition>(`/api/playbook-definitions/${id}`, data);
}

/**
 * Delete playbook definition
 */
export async function deletePlaybookDefinition(id: string): Promise<void> {
  return client.delete(`/api/playbook-definitions/${id}`);
}

/**
 * Execute playbook
 */
export async function executePlaybook(
  id: string,
  mode: "manual" | "auto" = "manual"
): Promise<PlaybookRun> {
  return client.post<PlaybookRun>(`/api/playbook-definitions/${id}/run`, { mode });
}

/**
 * List playbook runs
 */
export async function listPlaybookRuns(params?: {
  definition_id?: string;
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<PlaybookRun[]> {
  return client.get<PlaybookRun[]>("/api/playbook/runs", { params } as RequestInit);
}

/**
 * Get playbook run details
 */
export async function getPlaybookRun(id: string): Promise<
  PlaybookRun & {
    steps: Array<{
      id: string;
      node_id: string;
      status: string;
      started_at?: string;
      completed_at?: string;
      error_message?: string;
    }>;
  }
> {
  return client.get(`/api/playbook/runs/${id}`);
}

/**
 * Cancel playbook run
 */
export async function cancelPlaybookRun(id: string): Promise<void> {
  return client.post(`/api/playbook/runs/${id}/cancel`);
}

/**
 * Get run queue status
 */
export async function getRunQueueStatus(): Promise<RunQueueStatus> {
  return client.get<RunQueueStatus>("/api/playbook/runs/queue/status");
}

/**
 * Resume paused playbook run
 */
export async function resumePlaybookRun(runId: string, nodeId?: string): Promise<PlaybookRun> {
  return client.post<PlaybookRun>(`/api/playbook/runs/${runId}/resume`, { nodeId });
}

/**
 * Approve playbook run step (manual approval)
 */
export async function approvePlaybookStep(
  runId: string,
  nodeId: string,
  approved: boolean
): Promise<void> {
  return client.post(`/api/playbook/runs/${runId}/steps/${nodeId}/approve`, { approved });
}

/**
 * Get playbook run history
 */
export async function getPlaybookRunHistory(params?: {
  definition_id?: string;
  status?: string;
  days?: number;
}): Promise<PlaybookRun[]> {
  return client.get<PlaybookRun[]>("/api/playbook/runs/history", { params } as RequestInit);
}

// Export playbooks API object
export const playbooksApi = {
  listDefinitions: listPlaybookDefinitions,
  getDefinition: getPlaybookDefinition,
  createDefinition: createPlaybookDefinition,
  updateDefinition: updatePlaybookDefinition,
  deleteDefinition: deletePlaybookDefinition,
  execute: executePlaybook,
  listRuns: listPlaybookRuns,
  getRun: getPlaybookRun,
  cancelRun: cancelPlaybookRun,
  getQueueStatus: getRunQueueStatus,
  resumeRun: resumePlaybookRun,
  approveStep: approvePlaybookStep,
  getHistory: getPlaybookRunHistory,
};
