/** Custom hook for managing Dify workflows and configuration */

import { useState, useCallback, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { loadAuthState } from '@/lib/auth';
import type { DifyWorkflow, DifyConfig } from '../types';

interface UseDifyWorkflowsResult {
  workflows: DifyWorkflow[];
  config: DifyConfig | null;
  loading: boolean;
  error: string | null;
  loadData: () => Promise<void>;
  importWorkflow: (workflow: DifyWorkflow) => Promise<void>;
  deleteWorkflow: (workflow: DifyWorkflow) => Promise<void>;
}

export function useDifyWorkflows(): UseDifyWorkflowsResult {
  const router = useRouter();
  const [workflows, setWorkflows] = useState<DifyWorkflow[]>([]);
  const [config, setConfig] = useState<DifyConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem("access_token");

      const [workflowsRes, configRes] = await Promise.all([
        fetch("/api/dify/workflows", {
          headers: { "Authorization": `Bearer ${token}` }
        }),
        fetch("/api/dify/config", {
          headers: { "Authorization": `Bearer ${token}` }
        })
      ]);

      if (!workflowsRes.ok) throw new Error("Failed to load workflows");
      if (!configRes.ok) throw new Error("Failed to load config");

      const workflowsData = await workflowsRes.json();
      const configData = await configRes.json();

      setWorkflows(workflowsData.workflows || []);
      setConfig(configData);
    } catch (e: unknown) {
      setError((e as Error)?.message || "Failed to load Dify integration");
    } finally {
      setLoading(false);
    }
  }, []);

  const importWorkflow = useCallback(async (workflow: DifyWorkflow) => {
    const token = localStorage.getItem("access_token");
    setError(null);

    try {
      const response = await fetch(`/api/dify/workflows/${workflow.id}/import`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Import failed");
      }

      const result = await response.json();
      router.push(`/playbooks/definitions/${result.definition_id}`);
    } catch (e: unknown) {
      setError((e as Error)?.message || "Failed to import workflow");
      throw e;
    }
  }, [router]);

  const deleteWorkflow = useCallback(async (workflow: DifyWorkflow) => {
    const token = localStorage.getItem("access_token");
    setError(null);

    try {
      // Find the playbook definition that was imported from this Dify workflow
      const response = await fetch("/api/playbook-definitions", {
        headers: { "Authorization": `Bearer ${token}` }
      });

      if (!response.ok) return;

      const data = await response.json();
      const definition = data.definitions?.find((d: any) => d.dify_app_id === workflow.id);

      if (!definition) {
        throw new Error("Imported playbook definition not found");
      }

      // Delete the definition
      const deleteResponse = await fetch(`/api/playbook-definitions/${definition.id}`, {
        method: "DELETE",
        headers: { "Authorization": `Bearer ${token}` }
      });

      if (!deleteResponse.ok) {
        const error = await deleteResponse.json();
        throw new Error(error.detail || "Delete failed");
      }

      // Remove from local list
      setWorkflows(prev => prev.filter(w => w.id !== workflow.id));
    } catch (e: unknown) {
      setError((e as Error)?.message || "Failed to delete workflow");
      throw e;
    }
  }, []);

  // Initial load
  useEffect(() => {
    const authState = loadAuthState();
    if (!authState?.isAuthenticated) {
      router.push("/login");
      return;
    }
    loadData();
  }, [router, loadData]);

  return {
    workflows,
    config,
    loading,
    error,
    loadData,
    importWorkflow,
    deleteWorkflow
  };
}
