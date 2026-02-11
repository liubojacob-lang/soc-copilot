"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { loadAuthState, logout } from "@/lib/auth";
import Navigation from "@/components/Navigation";
import {
  Download,
  RefreshCw,
  ExternalLink,
  CheckCircle,
  XCircle,
  Clock,
  Settings,
  Zap,
  Plus,
  Link
} from "lucide-react";

interface DifyWorkflow {
  id: string;
  name: string;
  description: string;
  mode: string;
  created_at: string;
  updated_at: string;
}

interface DifyConfig {
  configured: boolean;
  connected: boolean;
  api_url: string;
  workspace_id?: string;
}

export default function DifyIntegrationPage() {
  const router = useRouter();
  const [workflows, setWorkflows] = useState<DifyWorkflow[]>([]);
  const [config, setConfig] = useState<DifyConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [importing, setImporting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);
  const [showManualImport, setShowManualImport] = useState(false);
  const [manualAppId, setManualAppId] = useState("");
  const [manualImporting, setManualImporting] = useState(false);

  useEffect(() => {
    setMounted(true);
    const authState = loadAuthState();
    if (!authState?.isAuthenticated) {
      router.push("/login");
      return;
    }
    loadData();
  }, []);

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      // Load workflows and config in parallel
      const [workflowsRes, configRes] = await Promise.all([
        fetch("/api/dify/workflows", {
          headers: { "Authorization": `Bearer ${localStorage.getItem("access_token")}` }
        }),
        fetch("/api/dify/config", {
          headers: { "Authorization": `Bearer ${localStorage.getItem("access_token")}` }
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
  }

  async function handleRefresh() {
    setRefreshing(true);
    await loadData();
    setRefreshing(false);
  }

  async function handleImport(workflow: DifyWorkflow) {
    setImporting(workflow.id);
    setError(null);
    try {
      const response = await fetch(`/api/dify/workflows/${workflow.id}/import`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${localStorage.getItem("access_token")}`
        },
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Import failed");
      }

      const result = await response.json();

      // Navigate to the imported playbook definition
      router.push(`/playbooks/definitions/${result.definition_id}`);
    } catch (e: unknown) {
      setError((e as Error)?.message || "Failed to import workflow");
    } finally {
      setImporting(null);
    }
  }

  async function handleManualImport() {
    if (!manualAppId.trim()) {
      setError("Please enter a Dify App ID");
      return;
    }

    setManualImporting(true);
    setError(null);
    try {
      const response = await fetch(`/api/dify/workflows/${manualAppId.trim()}/import`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${localStorage.getItem("access_token")}`
        },
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Import failed");
      }

      const result = await response.json();
      setShowManualImport(false);
      setManualAppId("");

      // Navigate to the imported playbook definition
      router.push(`/playbooks/definitions/${result.definition_id}`);
    } catch (e: unknown) {
      setError((e as Error)?.message || "Failed to import workflow");
    } finally {
      setManualImporting(false);
    }
  }

  if (!mounted) return null;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Navigation title="Dify Integration" subtitle="Import and manage Dify workflows" />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 mb-6">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                <Zap className="w-6 h-6 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Dify Workflow Integration</h1>
                <p className="text-gray-600 dark:text-gray-400 mt-1">
                  Import and execute workflows from Dify workflow engine
                </p>
              </div>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => setShowManualImport(true)}
                className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
              >
                <Plus className="w-4 h-4" />
                Import by ID
              </button>
              <button
                onClick={() => router.push("/settings")}
                className="flex items-center gap-2 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              >
                <Settings className="w-4 h-4" />
                Configure
              </button>
              <button
                onClick={handleRefresh}
                disabled={refreshing}
                className="flex items-center gap-2 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} />
                Refresh
              </button>
            </div>
          </div>

          {/* Connection Status */}
          {config && (
            <div className="mt-4 flex items-center gap-6">
              <div className="flex items-center gap-2">
                {config.connected ? (
                  <>
                    <CheckCircle className="w-5 h-5 text-green-500" />
                    <span className="text-sm text-gray-700 dark:text-gray-300">
                      Connected to Dify
                    </span>
                  </>
                ) : (
                  <>
                    <XCircle className="w-5 h-5 text-red-500" />
                    <span className="text-sm text-gray-700 dark:text-gray-300">
                      Not connected - Check configuration
                    </span>
                  </>
                )}
              </div>
              <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                <ExternalLink className="w-4 h-4" />
                <a href="https://dify.ai" target="_blank" rel="noopener noreferrer" className="hover:underline">
                  What is Dify?
                </a>
              </div>
            </div>
          )}
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 px-4 py-3 rounded-lg mb-6">
            {error}
          </div>
        )}

        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
            <p className="mt-4 text-gray-600 dark:text-gray-400">Loading workflows...</p>
          </div>
        ) : workflows.length === 0 ? (
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-12 text-center">
            <div className="max-w-md mx-auto">
              <div className="w-16 h-16 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-4">
                <Zap className="w-8 h-8 text-gray-400" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                No workflows found
              </h3>
              <p className="text-gray-600 dark:text-gray-400 mb-6">
                {!config?.configured
                  ? "Dify is not configured. Please configure your Dify API credentials in settings."
                  : "No workflows available in your Dify workspace."}
              </p>
              <button
                onClick={() => router.push("/settings")}
                className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                <Settings className="w-4 h-4" />
                Configure Dify
              </button>
            </div>
          </div>
        ) : (
          /* Workflows List */
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                Available Workflows ({workflows.length})
              </h2>
            </div>
            <div className="divide-y divide-gray-200 dark:divide-gray-700">
              {workflows.map((workflow) => (
                <div
                  key={workflow.id}
                  className="px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
                          <Zap className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                        </div>
                        <div>
                          <h3 className="font-semibold text-gray-900 dark:text-white">
                            {workflow.name}
                          </h3>
                          {workflow.description && (
                            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                              {workflow.description}
                            </p>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-4 mt-2 text-sm text-gray-500 dark:text-gray-400">
                        <span className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded">
                          {workflow.mode}
                        </span>
                        <span>•</span>
                        <span>ID: {workflow.id}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => handleImport(workflow)}
                        disabled={importing === workflow.id}
                        className="flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 text-sm"
                      >
                        {importing === workflow.id ? (
                          <>
                            <Clock className="w-4 h-4 animate-spin" />
                            Importing...
                          </>
                        ) : (
                          <>
                            <Download className="w-4 h-4" />
                            Import
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Quick Start Guide */}
        <div className="mt-8 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-blue-900 dark:text-blue-100 mb-3">
            Quick Start Guide
          </h3>
          <div className="space-y-3 text-sm text-blue-800 dark:text-blue-200">
            <p>
              <strong>1. Install Dify:</strong> Run <code className="px-2 py-1 bg-blue-100 dark:bg-blue-800 rounded">docker run -d -p 3001:3001 langgenius/dify</code>
            </p>
            <p>
              <strong>2. Configure:</strong> Go to <a href="/settings" className="underline hover:text-blue-600">Settings</a> and enter your Dify API URL and key
            </p>
            <p>
              <strong>3. Create Workflow:</strong> Build a workflow in Dify with HTTP request, code execution, and LLM nodes
            </p>
            <p>
              <strong>4. Import:</strong> Click Import button or use "Import by ID" to add the workflow as a SOC Copilot playbook
            </p>
          </div>
        </div>

        {/* Manual Import Modal */}
        {showManualImport && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white dark:bg-gray-800 rounded-lg max-w-lg w-full">
              <div className="p-6 border-b border-gray-200 dark:border-gray-700">
                <h3 className="text-xl font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                  <Link className="w-5 h-5" />
                  Import Dify Workflow by ID
                </h3>
              </div>
              <div className="p-6">
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                  Enter the Dify App ID to import a specific workflow. You can find the App ID in your Dify console URL or app settings.
                </p>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Dify App ID
                  </label>
                  <input
                    type="text"
                    value={manualAppId}
                    onChange={(e) => setManualAppId(e.target.value)}
                    placeholder="e.g., b3940dba-4479-4741-a529-5d2d8c066909"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
                  />
                </div>
                <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-3 mb-4">
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    <strong>How to find App ID:</strong><br />
                    1. Open your workflow in Dify console<br />
                    2. Look at the URL: {`https://your-dify.com/app/{app-id}/workflow`}<br />
                    3. Copy the App ID from the URL
                  </p>
                </div>
                <div className="flex gap-3">
                  <button
                    onClick={() => {
                      setShowManualImport(false);
                      setManualAppId("");
                      setError(null);
                    }}
                    className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
                    disabled={manualImporting}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleManualImport}
                    disabled={manualImporting || !manualAppId.trim()}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                  >
                    {manualImporting ? (
                      <>
                        <Clock className="w-4 h-4 animate-spin" />
                        Importing...
                      </>
                    ) : (
                      <>
                        <Download className="w-4 h-4" />
                        Import
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
