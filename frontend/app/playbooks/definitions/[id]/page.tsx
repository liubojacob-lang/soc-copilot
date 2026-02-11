"use client";

import { useState, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import { api, api_v73 } from "@/lib/api";
import { loadAuthState, logout } from "@/lib/auth";
import Navigation from "@/components/Navigation";
import { DAGCanvas } from "@/components/dag";
import { Play, Save, ArrowLeft, RefreshCw, History, Upload, Download, GitBranch, Check, AlertCircle, Edit, Eye, Database, CloudDownload } from "lucide-react";

interface PlaybookDefinition {
  id: string;
  name: string;
  version: string;
  description?: string;
  status?: "draft" | "published" | "archived";
  dify_app_id?: string;
  definition_json?: {
    nodes: Array<any>;
    edges: Array<any>;
    global_context?: Record<string, any>;
  };
  dag?: {
    nodes: Array<any>;
    edges: Array<any>;
  };
  created_at: string;
  updated_at: string;
  published_at?: string;
  current_version_no?: number;
}

interface DefinitionVersion {
  id: string;
  version_no: number;
  name?: string | null;
  description?: string | null;
  created_at: string;
  change_note?: string | null;
}

export default function PlaybookDefinitionDetailPage() {
  const router = useRouter();
  const params = useParams();
  const definitionId = params.id as string;

  const [definition, setDefinition] = useState<PlaybookDefinition | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [executing, setExecuting] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [currentUser, setCurrentUser] = useState<any>(null);
  const [syncing, setSyncing] = useState(false);

  // v0.7.3: Version history, import/export state
  const [versionHistory, setVersionHistory] = useState<DefinitionVersion[] | null>(null);
  const [loadingVersions, setLoadingVersions] = useState(false);
  const [showVersionsModal, setShowVersionsModal] = useState(false);
  const [exportFormat, setExportFormat] = useState<"json" | "yaml">("json");
  const [exportContent, setExportContent] = useState<string | null>(null);
  const [showExportModal, setShowExportModal] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [importContent, setImportContent] = useState("");
  const [importFormat, setImportFormat] = useState<"json" | "yaml">("json");
  const [importName, setImportName] = useState("");
  const [publishing, setPublishing] = useState(false);
  const [publishNote, setPublishNote] = useState("");
  const [restoring, setRestoring] = useState(false);
  const [processingExport, setProcessingExport] = useState(false);
  const [processingImport, setProcessingImport] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);

  useEffect(() => {
    setMounted(true);

    const authState = loadAuthState();
    if (!authState?.isAuthenticated) {
      router.push("/login");
      return;
    }
    setCurrentUser(authState.user);

    // Only load definition if ID is not "new"
    if (definitionId !== "new") {
      loadDefinition();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [definitionId]);

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  if (!mounted) return null;

  async function loadDefinition() {
    setLoading(true);
    setError(null);
    try {
      const def: any = await api.getPlaybookDefinition(definitionId);
      // Map old API response to include v0.7.3 fields
      setDefinition({
        ...def,
        status: def.status || "draft",
        current_version_no: def.current_version_no || 1,
        published_at: def.published_at || undefined,
      } as PlaybookDefinition);
    } catch (e: unknown) {
      setError((e as Error)?.message ?? "Failed to load definition");
    } finally {
      setLoading(false);
    }
  }

  async function handleExecute() {
    setExecuting(true);
    try {
      const result = await api.executeDAGDefinition(definitionId, "dry_run");
      router.push(`/playbooks/${result.run_id}`);
    } catch (e: unknown) {
      setError((e as Error)?.message ?? "Failed to execute playbook");
    } finally {
      setExecuting(false);
    }
  }

  // v0.7.3: Load version history
  async function loadVersionHistory() {
    setLoadingVersions(true);
    setError(null);
    try {
      const result = await api_v73.getVersionHistory(definitionId);
      setVersionHistory(result.versions);
      setShowVersionsModal(true);
    } catch (e: unknown) {
      setError((e as Error)?.message ?? "Failed to load version history");
    } finally {
      setLoadingVersions(false);
    }
  }

  // v0.7.3: Publish definition
  async function handlePublish() {
    if (definition?.status !== "draft") {
      setError("Only draft definitions can be published");
      return;
    }

    setPublishing(true);
    setError(null);
    try {
      await api_v73.publishDefinition(definitionId, publishNote || undefined);
      setPublishNote("");
      await loadDefinition();
      // Reload version history if modal is open
      if (showVersionsModal) {
        await loadVersionHistory();
      }
    } catch (e: unknown) {
      setError((e as Error)?.message ?? "Failed to publish definition");
    } finally {
      setPublishing(false);
    }
  }

  // v0.7.3: Restore from version
  async function handleRestore(versionNo: number) {
    if (!confirm(`Restore to version ${versionNo}? This will create a new draft version.`)) {
      return;
    }

    setRestoring(true);
    setError(null);
    try {
      await api_v73.restoreDefinition(definitionId, versionNo);
      await loadDefinition();
      setShowVersionsModal(false);
    } catch (e: unknown) {
      setError((e as Error)?.message ?? "Failed to restore version");
    } finally {
      setRestoring(false);
    }
  }

  // v0.7.3: Export definition
  async function handleExport() {
    setProcessingExport(true);
    setError(null);
    try {
      const result = await api_v73.exportDefinition(definitionId, exportFormat);
      setExportContent(result.content);
      setShowExportModal(true);
    } catch (e: unknown) {
      setError((e as Error)?.message ?? "Failed to export definition");
    } finally {
      setProcessingExport(false);
    }
  }

  // v0.7.3: Copy export content
  function handleCopyExport() {
    if (exportContent) {
      navigator.clipboard.writeText(exportContent);
      alert("Copied to clipboard!");
    }
  }

  // v0.7.3: Download export content
  function handleDownloadExport() {
    if (exportContent) {
      const blob = new Blob([exportContent], { type: exportFormat === "yaml" ? "text/yaml" : "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${definition?.name || "playbook"}_v${definition?.current_version_no || 1}.${exportFormat}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }
  }

  // v0.7.3: Import definition
  async function handleImport() {
    if (!importContent.trim()) {
      setImportError("Content is required");
      return;
    }

    setProcessingImport(true);
    setImportError(null);
    try {
      const result = await api_v73.importDefinition(
        importContent,
        importFormat,
        importName || undefined,
        false // don't auto-publish
      );
      setShowImportModal(false);
      setImportContent("");
      setImportName("");
      // Navigate to the new definition
      router.push(`/playbooks/definitions/${result.definition_id}`);
    } catch (e: unknown) {
      setImportError((e as Error)?.message ?? "Failed to import definition");
    } finally {
      setProcessingImport(false);
    }
  }

  // Sync with Dify workflow
  async function handleSyncWithDify() {
    if (!definition?.dify_app_id) {
      setError("This definition is not linked to a Dify workflow");
      return;
    }

    if (!confirm("This will overwrite the current definition with the latest version from Dify. Continue?")) {
      return;
    }

    setSyncing(true);
    setError(null);
    try {
      const response = await fetch(`/api/dify/workflows/sync/${definitionId}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${localStorage.getItem("access_token")}`
        },
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Sync failed");
      }

      const result = await response.json();
      await loadDefinition();
      alert("Successfully synced with Dify workflow!");
    } catch (e: unknown) {
      setError((e as Error)?.message ?? "Failed to sync with Dify");
    } finally {
      setSyncing(false);
    }
  }

  function getStatusBadge(status: string) {
    const styles = {
      draft: "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300",
      published: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
      archived: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400"
    };
    return (
      <span className={`px-2 py-1 text-xs font-medium rounded-full ${styles[status as keyof typeof styles] || styles.draft}`}>
        {status.toUpperCase()}
      </span>
    );
  }

  function canModify(): boolean {
    return definition?.status === "draft" && (currentUser?.role === "ADMIN" || currentUser?.role === "ANALYST");
  }

  // Handle "new" ID - show creation form
  if (definitionId === "new") {
    return <CreateNewDefinitionPage router={router} currentUser={currentUser} onCreate={() => router.push("/playbooks/definitions")} />;
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <Navigation title="Playbook Definition" subtitle="View and execute DAG workflow" />
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center py-12">
            <div className="inline-block w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
            <p className="mt-4 text-gray-600 dark:text-gray-400">Loading definition...</p>
          </div>
        </main>
      </div>
    );
  }

  if (error && !definition) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <Navigation title="Playbook Definition" subtitle="View and execute DAG workflow" />
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 px-4 py-3 rounded-lg">
            {error}
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Navigation title="Playbook Definition" subtitle="View and execute DAG workflow" />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 mb-6">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <button
                onClick={() => router.push("/playbooks/definitions")}
                className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white mb-2"
              >
                <ArrowLeft className="w-4 h-4" />
                Back to Definitions
              </button>
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{definition?.name}</h1>
                {definition && getStatusBadge(definition.status || "draft")}
              </div>
              <p className="text-gray-600 dark:text-gray-400 mt-1">
                Version {definition?.version}{definition?.current_version_no !== undefined ? ` (v${definition.current_version_no})` : ""}
              </p>
            </div>
            <div className="flex gap-3 flex-wrap">
              {/* v0.7.3: Version History Button */}
              <button
                onClick={loadVersionHistory}
                disabled={loadingVersions}
                className="flex items-center gap-2 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              >
                <History className="w-5 h-5" />
                Versions
              </button>

              {/* v0.7.3: Export Button */}
              <button
                onClick={handleExport}
                disabled={processingExport}
                className="flex items-center gap-2 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              >
                <Download className="w-5 h-5" />
                Export
              </button>

              {/* v0.7.3: Import Button (creates new definition) */}
              <button
                onClick={() => setShowImportModal(true)}
                className="flex items-center gap-2 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              >
                <Upload className="w-5 h-5" />
                Import
              </button>

              {/* Sync with Dify Button (only for definitions linked to Dify) */}
              {definition?.dify_app_id && canModify() && (
                <button
                  onClick={handleSyncWithDify}
                  disabled={syncing}
                  className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors disabled:opacity-50"
                >
                  <CloudDownload className="w-5 h-5" />
                  {syncing ? "Syncing..." : "Sync from Dify"}
                </button>
              )}

              {/* v0.7.3: Publish Button (only for draft definitions) */}
              {definition?.status === "draft" && canModify() && (
                <button
                  onClick={() => {
                    const note = prompt("Enter change note (optional):");
                    if (note !== null) {
                      setPublishNote(note);
                      handlePublish();
                    }
                  }}
                  disabled={publishing}
                  className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
                >
                  <GitBranch className="w-5 h-5" />
                  {publishing ? "Publishing..." : "Publish"}
                </button>
              )}

              <button
                onClick={loadDefinition}
                className="flex items-center gap-2 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              >
                <RefreshCw className="w-5 h-5" />
                Refresh
              </button>

              <button
                onClick={handleExecute}
                disabled={executing}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Play className="w-5 h-5" />
                {executing ? "Starting..." : "Run Playbook"}
              </button>
            </div>
          </div>

          {definition?.description && (
            <p className="mt-4 text-gray-600 dark:text-gray-400">{definition.description}</p>
          )}

          <div className="mt-4 flex flex-wrap gap-4 text-sm text-gray-500 dark:text-gray-400">
            <span>Created: {new Date(definition?.created_at || "").toLocaleString()}</span>
            <span>Updated: {new Date(definition?.updated_at || "").toLocaleString()}</span>
            {definition?.published_at && (
              <span>Published: {new Date(definition.published_at).toLocaleString()}</span>
            )}
            <span>Nodes: {definition?.definition_json?.nodes?.length || definition?.dag?.nodes?.length || 0}</span>
            <span>Edges: {definition?.definition_json?.edges?.length || definition?.dag?.edges?.length || 0}</span>
            {definition?.dify_app_id && (
              <span className="text-purple-600 dark:text-purple-400">Dify App: {definition.dify_app_id}</span>
            )}
          </div>

          {/* v0.7.3: Warning for non-draft definitions */}
          {definition && definition.status !== "draft" && (
            <div className="mt-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 text-blue-700 dark:text-blue-300 px-4 py-3 rounded-lg flex items-start gap-2">
              <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
              <div className="text-sm">
                <p className="font-medium">This {definition.status} definition cannot be modified</p>
                <p className="mt-1">To make changes, create a new draft version by restoring from history or importing as a new definition.</p>
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

        {/* v0.7.3: Global Context Display */}
        {definition?.definition_json?.global_context && Object.keys(definition.definition_json.global_context).length > 0 && (
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 mb-6">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
              <Database className="w-5 h-5 text-blue-600" />
              Global Context Variables
            </h2>
            <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 overflow-auto">
              <pre className="text-sm text-gray-700 dark:text-gray-300">
                {JSON.stringify(definition.definition_json.global_context, null, 2)}
              </pre>
            </div>
            <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
              These variables are available as {"{{context.xxx}}"} in all node inputs.
            </p>
          </div>
        )}

        {/* DAG Visualization */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Workflow</h2>
            {canModify() && (
              <button
                onClick={() => router.push(`/playbooks/definitions/${definitionId}/edit`)}
                className="flex items-center gap-2 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors text-sm"
              >
                <Edit className="w-4 h-4" />
                Edit Workflow
              </button>
            )}
          </div>
          <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden" style={{ height: "500px" }}>
            <DAGCanvas
              definition={definition?.definition_json || definition?.dag || { nodes: [], edges: [] }}
              readonly={true}
            />
          </div>
        </div>

        {/* v0.7.3: Node Context Mappings Display */}
        {(definition?.definition_json?.nodes && definition.definition_json.nodes.length > 0) ||
         (definition?.dag?.nodes && definition.dag.nodes.length > 0) ? (
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
              <Eye className="w-5 h-5 text-purple-600" />
              Node Context Mappings
            </h2>
            <div className="space-y-4">
              {(definition.definition_json?.nodes || definition.dag?.nodes || []).map((node: any) => (
                <div key={node.id} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-medium text-gray-900 dark:text-white">{node.name}</h3>
                    <span className="text-xs text-gray-500 dark:text-gray-400">{node.id}</span>
                  </div>

                  {/* Inputs Template */}
                  {node.inputs_template && Object.keys(node.inputs_template).length > 0 && (
                    <div className="mb-3">
                      <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Input Template:</p>
                      <div className="bg-gray-50 dark:bg-gray-900 rounded p-2">
                        <pre className="text-xs text-gray-600 dark:text-gray-400 overflow-auto">
                          {JSON.stringify(node.inputs_template, null, 2)}
                        </pre>
                      </div>
                    </div>
                  )}

                  {/* Outputs Mapping */}
                  {node.outputs_mapping && Object.keys(node.outputs_mapping).length > 0 && (
                    <div>
                      <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Outputs Mapping:</p>
                      <div className="bg-gray-50 dark:bg-gray-900 rounded p-2">
                        <pre className="text-xs text-gray-600 dark:text-gray-400 overflow-auto">
                          {JSON.stringify(node.outputs_mapping, null, 2)}
                        </pre>
                      </div>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                        Maps node outputs to context variables using JSONPath
                      </p>
                    </div>
                  )}

                  {!node.inputs_template && !node.outputs_mapping && (
                    <p className="text-sm text-gray-500 dark:text-gray-400 italic">No context mappings defined</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </main>

      {/* v0.7.3: Version History Modal */}
      {showVersionsModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg max-w-2xl w-full max-h-[80vh] overflow-hidden">
            <div className="p-6 border-b border-gray-200 dark:border-gray-700">
              <h3 className="text-xl font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                <GitBranch className="w-5 h-5" />
                Version History
              </h3>
            </div>
            <div className="p-6 overflow-y-auto max-h-[60vh]">
              {versionHistory && versionHistory.length > 0 ? (
                <div className="space-y-3">
                  {versionHistory.map((version) => (
                    <div key={version.id} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-gray-900 dark:text-white">Version {version.version_no}</span>
                            {version.version_no === definition?.current_version_no && (
                              <span className="text-xs bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400 px-2 py-0.5 rounded-full">Current</span>
                            )}
                          </div>
                          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                            {new Date(version.created_at).toLocaleString()}
                          </p>
                          {version.change_note && (
                            <p className="text-sm text-gray-600 dark:text-gray-300 mt-2">{version.change_note}</p>
                          )}
                        </div>
                        {canModify() && version.version_no !== definition?.current_version_no && (
                          <button
                            onClick={() => handleRestore(version.version_no)}
                            disabled={restoring}
                            className="flex items-center gap-1 px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
                          >
                            <RefreshCw className="w-3 h-3" />
                            Restore
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500 dark:text-gray-400 text-center py-8">No version history available</p>
              )}
            </div>
            <div className="p-4 border-t border-gray-200 dark:border-gray-700">
              <button
                onClick={() => setShowVersionsModal(false)}
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* v0.7.3: Export Modal */}
      {showExportModal && exportContent && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg max-w-3xl w-full max-h-[80vh] overflow-hidden">
            <div className="p-6 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
              <h3 className="text-xl font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                <Download className="w-5 h-5" />
                Export Definition
              </h3>
              <button
                onClick={() => setShowExportModal(false)}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              >
                ✕
              </button>
            </div>
            <div className="p-6">
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Export Format
                </label>
                <div className="flex gap-4">
                  <label className="flex items-center gap-2">
                    <input
                      type="radio"
                      value="json"
                      checked={exportFormat === "json"}
                      onChange={(e) => setExportFormat(e.target.value as "json" | "yaml")}
                      className="text-blue-600"
                    />
                    <span className="text-gray-700 dark:text-gray-300">JSON</span>
                  </label>
                  <label className="flex items-center gap-2">
                    <input
                      type="radio"
                      value="yaml"
                      checked={exportFormat === "yaml"}
                      onChange={(e) => setExportFormat(e.target.value as "json" | "yaml")}
                      className="text-blue-600"
                    />
                    <span className="text-gray-700 dark:text-gray-300">YAML</span>
                  </label>
                </div>
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Exported Content
                </label>
                <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 max-h-96 overflow-auto">
                  <pre className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap break-all">
                    {exportContent}
                  </pre>
                </div>
              </div>
              <div className="flex gap-3">
                <button
                  onClick={handleCopyExport}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
                >
                  <Save className="w-4 h-4" />
                  Copy to Clipboard
                </button>
                <button
                  onClick={handleDownloadExport}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  <Download className="w-4 h-4" />
                  Download File
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* v0.7.3: Import Modal */}
      {showImportModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg max-w-2xl w-full max-h-[80vh] overflow-hidden">
            <div className="p-6 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
              <h3 className="text-xl font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                <Upload className="w-5 h-5" />
                Import Playbook Definition
              </h3>
              <button
                onClick={() => setShowImportModal(false)}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              >
                ✕
              </button>
            </div>
            <div className="p-6">
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Import Format
                </label>
                <div className="flex gap-4">
                  <label className="flex items-center gap-2">
                    <input
                      type="radio"
                      value="json"
                      checked={importFormat === "json"}
                      onChange={(e) => setImportFormat(e.target.value as "json" | "yaml")}
                      className="text-blue-600"
                    />
                    <span className="text-gray-700 dark:text-gray-300">JSON</span>
                  </label>
                  <label className="flex items-center gap-2">
                    <input
                      type="radio"
                      value="yaml"
                      checked={importFormat === "yaml"}
                      onChange={(e) => setImportFormat(e.target.value as "json" | "yaml")}
                      className="text-blue-600"
                    />
                    <span className="text-gray-700 dark:text-gray-300">YAML</span>
                  </label>
                </div>
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Name Override (optional)
                </label>
                <input
                  type="text"
                  value={importName}
                  onChange={(e) => setImportName(e.target.value)}
                  placeholder="Leave empty to use original name"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
                />
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Definition Content
                </label>
                <textarea
                  value={importContent}
                  onChange={(e) => setImportContent(e.target.value)}
                  placeholder={`Paste ${importFormat.toUpperCase()} content here...`}
                  rows={12}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white font-mono text-sm"
                />
              </div>
              {importError && (
                <div className="mb-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 px-4 py-3 rounded-lg text-sm">
                  {importError}
                </div>
              )}
              <div className="flex gap-3">
                <button
                  onClick={() => {
                    setShowImportModal(false);
                    setImportContent("");
                    setImportName("");
                    setImportError(null);
                  }}
                  className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
                  disabled={processingImport}
                >
                  Cancel
                </button>
                <button
                  onClick={handleImport}
                  disabled={processingImport || !importContent.trim()}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  <Upload className="w-4 h-4" />
                  {processingImport ? "Importing..." : "Import as Draft"}
                </button>
              </div>
              <p className="mt-3 text-xs text-gray-500 dark:text-gray-400">
                Imported definitions will be created as new drafts and will not modify the current definition.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Create new definition page component
interface CreateNewDefinitionPageProps {
  router: any;
  currentUser: any;
  onCreate: () => void;
}

function CreateNewDefinitionPage({ router, currentUser, onCreate }: CreateNewDefinitionPageProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleCreate() {
    if (!name.trim()) {
      setError("Name is required");
      return;
    }

    setSaving(true);
    setError(null);
    try {
      const result = await api.createPlaybookDefinition({
        name: name.trim(),
        description: description.trim() || undefined,
        definition_json: { nodes: [], edges: [] },
        version: "1.0.0",
      });
      router.push(`/playbooks/definitions/${result.id}/edit`);
    } catch (e: unknown) {
      setError((e as Error)?.message ?? "Failed to create definition");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Navigation title="Create New Definition" subtitle="Create a new DAG playbook definition" />

      <main className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Back button */}
        <button
          onClick={() => router.push("/playbooks/definitions")}
          className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white mb-6"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Definitions
        </button>

        {/* Create form */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-6">New Playbook Definition</h2>

          {error && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 px-4 py-3 rounded-lg mb-6">
              {error}
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="My Playbook"
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                disabled={saving}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Description
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe what this playbook does..."
                rows={3}
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                disabled={saving}
              />
            </div>

            <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
              <button
                onClick={() => router.push("/playbooks/definitions")}
                className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                disabled={saving}
              >
                Cancel
              </button>
              <button
                onClick={handleCreate}
                disabled={saving}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {saving ? "Creating..." : "Create Definition"}
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
