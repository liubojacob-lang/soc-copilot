"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { loadAuthState, logout, isAdmin } from "@/lib/auth";
import Navigation from "@/components/Navigation";
import {
  Settings as SettingsIcon,
  Save,
  RefreshCw,
  CheckCircle,
  XCircle,
  Zap,
  Key,
  Globe,
  AlertCircle,
  Eye,
  EyeOff,
  Download,
  X,
  Loader2
} from "lucide-react";

interface DifyStatus {
  configured: boolean;
  connected: boolean;
  api_url: string;
  api_key?: string;
  workspace_id?: string;
}

interface DifyWorkflow {
  id: string;
  name: string;
  description: string;
  mode: string;
  created_at: string;
}

export default function SettingsPage() {
  const router = useRouter();
  const [difyStatus, setDifyStatus] = useState<DifyStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);

  // Dify config form
  const [difyApiUrl, setDifyApiUrl] = useState("");
  const [difyApiKey, setDifyApiKey] = useState("");
  const [difyWorkspaceId, setDifyWorkspaceId] = useState("");
  const [showApiKey, setShowApiKey] = useState(false);

  // Sync workflow states
  const [showSyncModal, setShowSyncModal] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [workflows, setWorkflows] = useState<DifyWorkflow[]>([]);
  const [importing, setImporting] = useState<string | null>(null);
  const [syncError, setSyncError] = useState<string | null>(null);
  const [syncSuccess, setSyncSuccess] = useState<string | null>(null);

  useEffect(() => {
    setMounted(true);
    const authState = loadAuthState();
    if (!authState?.isAuthenticated) {
      router.push("/login");
      return;
    }
    if (!isAdmin(authState.user)) {
      setError("Only administrators can access settings");
      return;
    }
    loadSettings();
  }, [router]);

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  async function loadSettings() {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/dify/config", {
        headers: { "Authorization": `Bearer ${localStorage.getItem("access_token")}` }
      });
      if (!response.ok) throw new Error("Failed to load settings");

      const data = await response.json();
      setDifyStatus(data);
      setDifyApiUrl(data.api_url || "");
      // 显示 API Key 的前缀部分（用于显示，但保持安全）
      setDifyApiKey(data.api_key || "");
      setDifyWorkspaceId(data.workspace_id || "");
    } catch (e: unknown) {
      setError((e as Error)?.message || "Failed to load settings");
    } finally {
      setLoading(false);
    }
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await fetch("/api/admin/settings", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${localStorage.getItem("access_token")}`
        },
        body: JSON.stringify({
          dify_api_url: difyApiUrl,
          dify_api_key: difyApiKey,
          dify_workspace_id: difyWorkspaceId,
        }),
      });

      if (!response.ok) {
        // Try to parse as JSON first, fall back to text
        let errorMessage = "Failed to save settings";
        try {
          const err = await response.json();
          errorMessage = err.detail || errorMessage;
        } catch {
          // If JSON parsing fails, get text response
          const text = await response.text();
          errorMessage = text || `HTTP ${response.status}: ${response.statusText}`;
        }
        throw new Error(errorMessage);
      }

      setSuccess("Settings saved successfully!");
      await loadSettings();
    } catch (e: unknown) {
      setError((e as Error)?.message || "Failed to save settings");
    } finally {
      setSaving(false);
    }
  }

  async function handleTestConnection() {
    setTesting(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await fetch("/api/dify/config", {
        method: "GET",
        headers: { "Authorization": `Bearer ${localStorage.getItem("access_token")}` }
      });

      if (!response.ok) {
        let errorMessage = "Failed to test connection";
        try {
          const err = await response.json();
          errorMessage = err.detail || errorMessage;
        } catch {
          const text = await response.text();
          errorMessage = text || `HTTP ${response.status}: ${response.statusText}`;
        }
        throw new Error(errorMessage);
      }

      const data = await response.json();
      setDifyStatus(data);

      if (data.connected) {
        setSuccess("Successfully connected to Dify!");
      } else {
        setError("Could not connect to Dify. Please check your configuration.");
      }
    } catch (e: unknown) {
      setError((e as Error)?.message || "Connection test failed");
    } finally {
      setTesting(false);
    }
  }

  async function handleSyncWorkflows() {
    setSyncing(true);
    setSyncError(null);
    setWorkflows([]);

    try {
      const response = await fetch("/api/dify/workflows", {
        headers: { "Authorization": `Bearer ${localStorage.getItem("access_token")}` }
      });

      if (!response.ok) {
        let errorMessage = "Failed to fetch Dify workflows";
        try {
          const err = await response.json();
          errorMessage = err.detail || errorMessage;
        } catch {
          const text = await response.text();
          errorMessage = text || `HTTP ${response.status}: ${response.statusText}`;
        }
        throw new Error(errorMessage);
      }

      const data = await response.json();
      setWorkflows(data.workflows || []);
      setShowSyncModal(true);
    } catch (e: unknown) {
      setSyncError((e as Error)?.message || "Failed to fetch workflows from Dify");
    } finally {
      setSyncing(false);
    }
  }

  async function handleImportWorkflow(workflow: DifyWorkflow) {
    setImporting(workflow.id);
    setSyncError(null);
    setSyncSuccess(null);

    try {
      const response = await fetch(`/api/dify/workflows/${workflow.id}/import`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${localStorage.getItem("access_token")}` }
      });

      if (!response.ok) {
        let errorMessage = "Failed to import workflow";
        try {
          const err = await response.json();
          errorMessage = err.detail || errorMessage;
        } catch {
          const text = await response.text();
          errorMessage = text || `HTTP ${response.status}: ${response.statusText}`;
        }
        throw new Error(errorMessage);
      }

      const result = await response.json();
      setSyncSuccess(`Successfully imported "${workflow.name}" as playbook definition!`);

      // Remove the imported workflow from the list
      setWorkflows(prev => prev.filter(w => w.id !== workflow.id));

      // Close modal if no more workflows
      setTimeout(() => {
        setWorkflows(current => {
          if (current.length <= 1) {
            setShowSyncModal(false);
          }
          return current;
        });
      }, 1500);
    } catch (e: unknown) {
      setSyncError((e as Error)?.message || "Failed to import workflow");
    } finally {
      setImporting(null);
    }
  }

  if (!mounted) return null;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Navigation title="Settings" subtitle="System configuration" />

      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Error Message */}
        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 px-4 py-3 rounded-lg mb-6 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {/* Success Message */}
        {success && (
          <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 text-green-700 dark:text-green-300 px-4 py-3 rounded-lg mb-6 flex items-start gap-3">
            <CheckCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
            <span>{success}</span>
          </div>
        )}

        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
            <p className="mt-4 text-gray-600 dark:text-gray-400">Loading settings...</p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Dify Integration Settings */}
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm">
              <div className="p-6 border-b border-gray-200 dark:border-gray-700">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                    <Zap className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                  </div>
                  <div>
                    <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Dify Integration</h2>
                    <p className="text-sm text-gray-600 dark:text-gray-400">Configure Dify workflow engine connection</p>
                  </div>
                  {difyStatus && (
                    <div className="ml-auto">
                      {difyStatus.connected ? (
                        <span className="inline-flex items-center gap-1 px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm">
                          <CheckCircle className="w-4 h-4" />
                          Connected
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-3 py-1 bg-red-100 text-red-700 rounded-full text-sm">
                          <XCircle className="w-4 h-4" />
                          Not Connected
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* Current Configuration Display */}
              {difyStatus && difyStatus.configured && (
                <div className="px-6 py-4 bg-blue-50 dark:bg-blue-900/20 border-b border-blue-200 dark:border-blue-800">
                  <h3 className="text-sm font-semibold text-blue-900 dark:text-blue-100 mb-3">Current Configuration</h3>
                  <div className="space-y-2 text-sm">
                    <div className="flex items-center gap-2">
                      <span className="text-gray-600 dark:text-gray-400">API URL:</span>
                      <code className="px-2 py-1 bg-white dark:bg-gray-700 rounded text-blue-600 dark:text-blue-400">{difyStatus.api_url || "Not configured"}</code>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-gray-600 dark:text-gray-400">API Key:</span>
                      <code className="px-2 py-1 bg-white dark:bg-gray-700 rounded text-blue-600 dark:text-blue-400">{difyStatus.api_key || "Not configured"}</code>
                    </div>
                    {difyStatus.workspace_id && (
                      <div className="flex items-center gap-2">
                        <span className="text-gray-600 dark:text-gray-400">Workspace ID:</span>
                        <span className="text-gray-800 dark:text-gray-200">{difyStatus.workspace_id}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              <form onSubmit={handleSave} className="p-6 space-y-6">
                {/* API URL */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    <div className="flex items-center gap-2">
                      <Globe className="w-4 h-4" />
                      Dify API URL
                    </div>
                  </label>
                  <input
                    type="url"
                    value={difyApiUrl}
                    onChange={(e) => setDifyApiUrl(e.target.value)}
                    placeholder="http://localhost:3001"
                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                    required
                  />
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                    Base URL of your Dify instance (e.g., http://localhost:3001 or https://dify.example.com)
                  </p>
                </div>

                {/* API Key */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    <div className="flex items-center gap-2">
                      <Key className="w-4 h-4" />
                      API Key
                    </div>
                  </label>
                  <div className="relative">
                    <input
                      type={showApiKey ? "text" : "password"}
                      value={difyApiKey}
                      onChange={(e) => setDifyApiKey(e.target.value)}
                      placeholder="Enter your Dify API key"
                      className="w-full px-4 py-2 pr-20 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                    />
                    <button
                      type="button"
                      onClick={() => setShowApiKey(!showApiKey)}
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                    >
                      {showApiKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                    Get your API key from Dify Settings → API Keys
                  </p>
                  {difyStatus && difyStatus.api_key && (
                    <p className="mt-1 text-xs text-green-600 dark:text-green-400">
                      Current: {difyStatus.api_key}
                    </p>
                  )}
                </div>

                {/* Workspace ID */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Workspace ID (Optional)
                  </label>
                  <input
                    type="text"
                    value={difyWorkspaceId}
                    onChange={(e) => setDifyWorkspaceId(e.target.value)}
                    placeholder="Enter workspace ID"
                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                  />
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                    Optional: Required if using multi-workspace Dify setup
                  </p>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
                  <button
                    type="submit"
                    disabled={saving}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    <Save className="w-4 h-4" />
                    {saving ? "Saving..." : "Save Settings"}
                  </button>
                  <button
                    type="button"
                    onClick={handleTestConnection}
                    disabled={testing}
                    className="inline-flex items-center gap-2 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    <RefreshCw className={`w-4 h-4 ${testing ? "animate-spin" : ""}`} />
                    {testing ? "Testing..." : "Test Connection"}
                  </button>
                  <button
                    type="button"
                    onClick={handleSyncWorkflows}
                    disabled={syncing || !difyStatus?.connected}
                    className="inline-flex items-center gap-2 px-4 py-2 border border-purple-300 dark:border-purple-600 text-purple-700 dark:text-purple-400 rounded-lg hover:bg-purple-50 dark:hover:bg-purple-900/20 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    <Download className={`w-4 h-4 ${syncing ? "animate-pulse" : ""}`} />
                    {syncing ? "Syncing..." : "Sync Workflows"}
                  </button>
                </div>
              </form>
            </div>

            {/* Quick Start Guide */}
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-blue-900 dark:text-blue-100 mb-4 flex items-center gap-2">
                <Zap className="w-5 h-5" />
                Quick Start: Setting up Dify
              </h3>
              <div className="space-y-3 text-sm text-blue-800 dark:text-blue-200">
                <p>
                  <strong>1. Install Dify using Docker:</strong>
                </p>
                <pre className="px-3 py-2 bg-blue-100 dark:bg-blue-800 rounded overflow-x-auto text-xs">
{`docker run -d \\
  -p 3001:3001 \\
  --name dify \\
  langgenius/dify`}
                </pre>
                <p>
                  <strong>2. Get API Key:</strong> Open Dify (http://localhost:3001), go to Settings → API Keys → Create New Key
                </p>
                <p>
                  <strong>3. Configure Above:</strong> Enter API URL (http://localhost:3001) and your API key
                </p>
                <p>
                  <strong>4. Test Connection:</strong> Click "Test Connection" to verify
                </p>
                <p>
                  <strong>5. Sync Workflows:</strong> Click "Sync Workflows" to import Dify workflows as playbook definitions
                </p>
                <p>
                  <strong>6. Manage Workflows:</strong> Go to <a href="/dify" className="underline hover:text-blue-600">Dify Workflows</a> page for advanced workflow management
                </p>
              </div>
            </div>

            {/* Additional Settings Links */}
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm">
              <div className="p-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                  <SettingsIcon className="w-5 h-5" />
                  Other Settings
                </h3>
                <div className="space-y-2">
                  <a
                    href="/settings/api-keys"
                    className="block px-4 py-3 rounded-lg border border-gray-200 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                  >
                    <div className="font-medium text-gray-900 dark:text-white">API Keys</div>
                    <div className="text-sm text-gray-600 dark:text-gray-400">Manage API keys for external integrations</div>
                  </a>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Sync Workflow Modal */}
      {showSyncModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
              <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                  <Download className="w-5 h-5 text-purple-600" />
                  Sync Dify Workflows
                </h3>
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                  Select workflows to import from Dify as playbook definitions
                </p>
              </div>
              <button
                onClick={() => setShowSyncModal(false)}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>

            {/* Sync Error/Success */}
              {syncError && (
                <div className="mx-6 mt-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 px-4 py-3 rounded-lg">
                  {syncError}
                </div>
              )}
              {syncSuccess && (
                <div className="mx-6 mt-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 text-green-700 dark:text-green-300 px-4 py-3 rounded-lg">
                  {syncSuccess}
                </div>
              )}

            {/* Workflows List */}
            <div className="p-6 overflow-y-auto max-h-[60vh]">
              {workflows.length === 0 ? (
                <div className="text-center py-12">
                  <p className="text-gray-500 dark:text-gray-400">No workflows found in Dify</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {workflows.map((workflow) => (
                    <div
                      key={workflow.id}
                      className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:border-purple-300 dark:hover:border-purple-600 transition-colors"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <h4 className="font-medium text-gray-900 dark:text-white">{workflow.name}</h4>
                            <span className="px-2 py-0.5 text-xs font-medium rounded bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400">
                              {workflow.mode}
                            </span>
                          </div>
                          <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                            {workflow.description || "No description"}
                          </p>
                          <p className="text-xs text-gray-500 dark:text-gray-500">
                            ID: {workflow.id} • Created: {new Date(workflow.created_at).toLocaleDateString()}
                          </p>
                        </div>
                        <button
                          onClick={() => handleImportWorkflow(workflow)}
                          disabled={importing === workflow.id}
                          className="ml-4 inline-flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm"
                        >
                          {importing === workflow.id ? (
                            <>
                              <Loader2 className="w-4 h-4 animate-spin" />
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
                  ))}
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="p-6 border-t border-gray-200 dark:border-gray-700 flex justify-end">
              <button
                onClick={() => setShowSyncModal(false)}
                className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
