"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, PlaybookRunWithStepsResponse, RunStatus, api_v73 } from "@/lib/api";
import { DAGCanvas } from "@/components/dag";
import { Activity, GitBranch, RotateCcw, History, Database, Download, Upload } from "lucide-react";

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-gray-100 text-gray-700",
  running: "bg-blue-100 text-blue-700",
  success: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
  partial: "bg-amber-100 text-amber-700",
  skipped: "bg-gray-100 text-gray-500",
  waiting_approval: "bg-yellow-100 text-yellow-700 border-2 border-yellow-400",
  cancelled: "bg-gray-200 text-gray-600",
  timeout: "bg-orange-100 text-orange-700",
};

const STATUS_ICONS: Record<string, string> = {
  pending: "⏳",
  running: "🔄",
  success: "✅",
  failed: "❌",
  partial: "⚠️",
  skipped: "⏭️",
  waiting_approval: "🙋",
  cancelled: "🛑",
  timeout: "⏰",
};

type ExecutionMode = "linear" | "dag";

export default function PlaybookRunDetailPage() {
  const params = useParams();
  const router = useRouter();
  const runId = params.run_id as string;

  const [data, setData] = useState<PlaybookRunWithStepsResponse | null>(null);
  const [nodeData, setNodeData] = useState<any>(null);
  const [executionMode, setExecutionMode] = useState<ExecutionMode>("linear");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [resuming, setResuming] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);

  // v0.7.3: Context and Replay state
  const [contextData, setContextData] = useState<any>(null);
  const [replayChain, setReplayChain] = useState<any>(null);
  const [showReplayModal, setShowReplayModal] = useState(false);
  const [replaying, setReplaying] = useState(false);
  const [replayMode, setReplayMode] = useState<"dry_run" | "apply">("dry_run");

  useEffect(() => {
    loadRun();
    // v0.7.3: Load context and replay chain
    loadContext();
    loadReplayChain();
  }, [runId]);

  useEffect(() => {
    if (!autoRefresh || !data) return;
    const isRunning = data.run.status === "running";

    const interval = setInterval(() => {
      if (executionMode === "dag") {
        loadNodeData();
        loadContext(); // v0.7.3: Also refresh context
      } else {
        loadRun();
      }
    }, isRunning ? 2000 : 5000);
    return () => clearInterval(interval);
  }, [autoRefresh, data, executionMode]);

  // v0.7.3: Load run context
  async function loadContext() {
    try {
      const result = await api_v73.getRunContext(runId);
      setContextData(result);
    } catch (e: unknown) {
      // Context endpoint might not exist in older versions
      console.log("Context not available:", e);
    }
  }

  // v0.7.3: Load replay chain
  async function loadReplayChain() {
    try {
      const result = await api_v73.getReplayChain(runId);
      setReplayChain(result);
    } catch (e: unknown) {
      // Replay endpoint might not exist in older versions
      console.log("Replay chain not available:", e);
    }
  }

  async function loadRun() {
    try {
      const result = await api.getPlaybookRunWithSteps(runId);
      setData(result);

      // Detect execution mode - check if run has execution_mode field
      if (result.run && "execution_mode" in result.run) {
        setExecutionMode((result.run as any).execution_mode || "linear");
      }

      // If DAG mode, also load node data
      if ((result.run as any)?.execution_mode === "dag") {
        await loadNodeData();
      }
    } catch (e: unknown) {
      setError((e as Error)?.message ?? "Failed to load run details");
    } finally {
      setLoading(false);
    }
  }

  async function loadNodeData() {
    try {
      const result = await api.getPlaybookRunNodes(runId);
      setNodeData(result);

      // Update execution mode if not set
      if (!executionMode || executionMode === "linear") {
        setExecutionMode("dag");
      }
    } catch (e: unknown) {
      console.error("Failed to load node data:", e);
    }
  }

  async function handleResume(fromStep: number) {
    setResuming(true);
    try {
      await api.resumePlaybookRun(runId, fromStep);
      setAutoRefresh(true);
      await loadRun();
    } catch (e: unknown) {
      setError((e as Error)?.message ?? "Failed to resume run");
    } finally {
      setResuming(false);
    }
  }

  // v0.7.3: Handle replay
  async function handleReplay() {
    setReplaying(true);
    try {
      const result = await api_v73.replayRun(runId, replayMode);
      setShowReplayModal(false);
      // Navigate to new run
      router.push(`/playbooks/${result.run_id}`);
    } catch (e: unknown) {
      setError((e as Error)?.message ?? "Failed to replay run");
    } finally {
      setReplaying(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <p className="text-slate-600">Loading playbook run...</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <p className="text-red-600">Run not found</p>
      </div>
    );
  }

  const { run, steps } = data;
  const canResume = run.status === "failed" || run.status === "partial";

  // Build node statuses for DAG canvas
  const nodeStatuses = nodeData?.nodes?.reduce((acc: any, node: any) => {
    acc[node.node_id] = {
      status: node.status,
      duration: node.duration_ms,
      error: node.error,
      output: node.output,
    };
    return acc;
  }, {}) || {};

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <button
              onClick={() => router.back()}
              className="text-sm text-slate-600 hover:text-slate-900 mb-2"
            >
              ← Back to Playbooks
            </button>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold text-slate-900">Playbook Run Details</h1>
              {executionMode === "dag" && (
                <span className="inline-flex items-center gap-1 px-2 py-1 bg-purple-100 text-purple-700 rounded-full text-xs font-medium">
                  <GitBranch className="w-3 h-3" />
                  DAG Mode
                </span>
              )}
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => { loadRun(); if (executionMode === "dag") loadNodeData(); loadContext(); }}
              className="px-4 py-2 bg-white border border-slate-300 text-slate-700 font-medium rounded-lg hover:bg-slate-50"
            >
              Refresh
            </button>
            {run.status === "running" && (
              <button
                onClick={() => setAutoRefresh(!autoRefresh)}
                className={`px-4 py-2 font-medium rounded-lg ${autoRefresh ? "bg-green-100 text-green-700" : "bg-white border border-slate-300 text-slate-700"}`}
              >
                {autoRefresh ? "Auto-refresh ON" : "Auto-refresh OFF"}
              </button>
            )}
            {/* v0.7.3: Replay button */}
            {run.status !== "running" && (
              <button
                onClick={() => setShowReplayModal(true)}
                className="px-4 py-2 bg-purple-600 text-white font-medium rounded-lg hover:bg-purple-700 flex items-center gap-2"
              >
                <RotateCcw className="w-4 h-4" />
                Replay
              </button>
            )}
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-800 text-sm">{error}</p>
          </div>
        )}

        {/* Run Info */}
        <div className="bg-white rounded-lg border border-slate-200 p-6 mb-6">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div>
              <div className="text-xs text-slate-500 uppercase tracking-wide">Playbook</div>
              <div className="font-medium text-slate-900 mt-1">{run.playbook_name}</div>
              <div className="text-xs text-slate-500">v{run.playbook_version}</div>
            </div>
            <div>
              <div className="text-xs text-slate-500 uppercase tracking-wide">Status</div>
              <div className="mt-1">
                <span className={`px-2 py-1 rounded text-xs font-medium ${STATUS_COLORS[run.status]}`}>
                  {run.status}
                </span>
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-500 uppercase tracking-wide">Mode</div>
              <div className="font-medium text-slate-900 mt-1 capitalize">{run.mode}</div>
            </div>
            <div>
              <div className="text-xs text-slate-500 uppercase tracking-wide">Execution</div>
              <div className="font-medium text-slate-900 mt-1 capitalize flex items-center gap-1">
                {executionMode === "dag" ? <><GitBranch className="w-3 h-3" /> DAG</> : <><Activity className="w-3 h-3" /> Linear</>}
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-500 uppercase tracking-wide">Run ID</div>
              <div className="text-xs text-slate-600 mt-1 font-mono">{run.id}</div>
            </div>
          </div>

          <div className="mt-4 pt-4 border-t border-slate-200">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-xs text-slate-500 uppercase tracking-wide">Started</div>
                <div className="text-sm text-slate-700 mt-1">
                  {new Date(run.started_at).toLocaleString()}
                </div>
              </div>
              {run.finished_at && (
                <div>
                  <div className="text-xs text-slate-500 uppercase tracking-wide">Finished</div>
                  <div className="text-sm text-slate-700 mt-1">
                    {new Date(run.finished_at).toLocaleString()}
                  </div>
                </div>
              )}
            </div>
          </div>

          {run.error_message && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
              <div className="text-xs font-medium text-red-700 uppercase tracking-wide mb-1">Error</div>
              <div className="text-sm text-red-800">{run.error_message}</div>
            </div>
          )}
        </div>

        {/* DAG Visualization or Linear Steps */}
        {executionMode === "dag" && nodeData ? (
          <div className="bg-white rounded-lg border border-slate-200 overflow-hidden mb-6">
            <div className="px-6 py-4 border-b border-slate-200">
              <h2 className="text-lg font-semibold text-slate-900">DAG Execution</h2>
            </div>
            <div className="p-4" style={{ height: "500px" }}>
              <DAGCanvas
                definition={{
                  nodes: nodeData.nodes.map((n: any) => ({
                    id: n.node_id,
                    step_id: n.step_id,
                    name: n.step_id,
                  })),
                  edges: [], // Edges would need to be fetched from definition
                }}
                nodeStatuses={nodeStatuses}
                readonly={true}
              />
            </div>

            {/* Node List */}
            <div className="px-6 pb-6">
              <h3 className="text-md font-semibold text-slate-900 mb-3">Node Details</h3>
              <div className="space-y-2">
                {nodeData.nodes.map((node: any) => (
                  <div
                    key={node.id}
                    className={`p-3 rounded-lg border-2 transition-all ${
                      node.status === "waiting_approval"
                        ? "bg-yellow-50 border-yellow-400"
                        : "bg-slate-50 border-slate-200"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${STATUS_COLORS[node.status]}`}>
                          {STATUS_ICONS[node.status] || node.status} {node.status}
                        </span>
                        <span className="font-medium text-slate-900">{node.step_id}</span>
                        <span className="text-sm text-slate-500">({node.node_id})</span>
                      </div>
                      {node.duration_ms && (
                        <span className="text-sm text-slate-500">{node.duration_ms}ms</span>
                      )}
                    </div>

                    {/* Waiting Approval Specific Display */}
                    {node.status === "waiting_approval" && node.output && (
                      <div className="mt-3 p-3 bg-yellow-100 border border-yellow-300 rounded-lg">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-lg">🙋</span>
                          <span className="font-medium text-yellow-800">Waiting for Approval</span>
                        </div>
                        {node.output.title && (
                          <div className="text-sm text-yellow-700 mb-1">
                            <span className="font-medium">Title:</span> {node.output.title}
                          </div>
                        )}
                        {node.output.message && (
                          <div className="text-sm text-yellow-700">
                            <span className="font-medium">Message:</span> {node.output.message}
                          </div>
                        )}
                        <button
                          onClick={() => router.push("/playbooks/approvals")}
                          className="mt-2 px-3 py-1 bg-yellow-600 text-white text-sm rounded hover:bg-yellow-700 transition-colors"
                        >
                          View Approvals Page
                        </button>
                      </div>
                    )}

                    {/* Approval Completed Display */}
                    {(node.status === "success" || node.status === "failed") &&
                     node.output?.approval_status && (
                      <div className={`mt-3 p-3 rounded-lg border ${
                        node.output.approval_status === "approved"
                          ? "bg-green-50 border-green-300"
                          : "bg-red-50 border-red-300"
                      }`}>
                        <div className="text-sm">
                          <span className="font-medium">
                            {node.output.approval_status === "approved" ? "✅ Approved" : "❌ Rejected"}
                          </span>
                          {node.output.comments && (
                            <span className="ml-2 text-slate-600">: {node.output.comments}</span>
                          )}
                          {node.output.approved_at && (
                            <div className="text-xs text-slate-500 mt-1">
                              At {new Date(node.output.approved_at).toLocaleString()}
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {node.error && (
                      <div className="mt-2 text-sm text-red-600">{node.error}</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          /* Linear Steps */
          <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900">Execution Steps</h2>
              {canResume && (
                <button
                  onClick={() => handleResume(steps.length)}
                  disabled={resuming}
                  className="px-4 py-2 bg-soc-600 text-white font-medium rounded-lg hover:bg-soc-700 disabled:opacity-50"
                >
                  {resuming ? "Resuming..." : "Resume from Next Step"}
                </button>
              )}
            </div>

            <div className="divide-y divide-slate-200">
              {steps.map((step, idx) => {
                const canResumeFrom = step.status === "failed" || step.status === "skipped";

                return (
                  <div key={step.id} className="p-6">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3">
                          <span className="text-sm font-mono text-slate-500">Step {step.step_index}</span>
                          <h3 className="font-medium text-slate-900">{step.step_name}</h3>
                          <span className={`px-2 py-0.5 rounded text-xs font-medium ${STATUS_COLORS[step.status]}`}>
                            {step.status}
                          </span>
                        </div>
                        <div className="text-xs text-slate-500 mt-1">
                          Type: {step.step_type} • ID: {step.step_id}
                        </div>
                        {step.duration_ms && (
                          <div className="text-xs text-slate-500">
                            Duration: {step.duration_ms}ms
                          </div>
                        )}
                      </div>
                      {canResumeFrom && (
                        <button
                          onClick={() => handleResume(step.step_index)}
                          disabled={resuming}
                          className="px-3 py-1 text-sm bg-slate-100 hover:bg-slate-200 rounded text-slate-700"
                        >
                          Resume from here
                        </button>
                      )}
                    </div>

                    {step.error_text && (
                      <div className="mt-3 p-2 bg-red-50 border border-red-200 rounded">
                        <div className="text-xs font-medium text-red-700">Error</div>
                        <div className="text-sm text-red-800 mt-1">{step.error_text}</div>
                      </div>
                    )}

                    {step.skipped_reason && (
                      <div className="mt-3 p-2 bg-amber-50 border border-amber-200 rounded">
                        <div className="text-xs font-medium text-amber-700">Skipped</div>
                        <div className="text-sm text-amber-800 mt-1">{step.skipped_reason}</div>
                      </div>
                    )}

                    {step.output_json && Object.keys(step.output_json).length > 0 && (
                      <details className="mt-3">
                        <summary className="text-xs text-slate-600 cursor-pointer hover:text-slate-900">
                          View Output
                        </summary>
                        <pre className="mt-2 p-3 bg-slate-900 text-green-400 rounded text-xs overflow-x-auto">
                          {JSON.stringify(step.output_json, null, 2)}
                        </pre>
                      </details>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* v0.7.3: Replay Chain Display */}
        {replayChain && replayChain.total > 1 && (
          <div className="bg-white rounded-lg border border-slate-200 p-6 mb-6">
            <div className="flex items-center gap-2 mb-4">
              <History className="w-5 h-5 text-purple-600" />
              <h2 className="text-lg font-semibold text-slate-900">Replay Chain</h2>
              <span className="text-sm text-slate-500">({replayChain.total} runs)</span>
            </div>
            <div className="space-y-2">
              {replayChain.chain.map((item: any, idx: number) => (
                <div key={item.run_id} className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
                  {idx > 0 && <div className="text-slate-400">↓</div>}
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs text-slate-500">{item.run_id.slice(0, 8)}...</span>
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${STATUS_COLORS[item.status]}`}>
                        {item.status}
                      </span>
                      <span className="text-sm text-slate-700">{item.playbook_name}</span>
                    </div>
                    <div className="text-xs text-slate-500">
                      {new Date(item.started_at).toLocaleString()} ({item.mode})
                    </div>
                  </div>
                  {item.replay_of_run_id && (
                    <span className="text-xs text-purple-600 bg-purple-50 px-2 py-1 rounded">
                      Replay of
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* v0.7.3: Context Viewer */}
        {contextData && (
          <div className="bg-white rounded-lg border border-slate-200 p-6 mb-6">
            <div className="flex items-center gap-2 mb-4">
              <Database className="w-5 h-5 text-blue-600" />
              <h2 className="text-lg font-semibold text-slate-900">Execution Context</h2>
            </div>
            <div className="grid grid-cols-2 gap-6">
              {/* Input Context */}
              <div>
                <h3 className="text-sm font-medium text-slate-700 mb-2">Input Context</h3>
                <pre className="p-3 bg-slate-900 text-green-400 rounded text-xs overflow-x-auto max-h-40">
                  {JSON.stringify(contextData.input_context, null, 2)}
                </pre>
              </div>
              {/* Current Context */}
              <div>
                <h3 className="text-sm font-medium text-slate-700 mb-2">Current Context</h3>
                <pre className="p-3 bg-slate-900 text-green-400 rounded text-xs overflow-x-auto max-h-40">
                  {JSON.stringify(contextData.context, null, 2)}
                </pre>
              </div>
            </div>
            {contextData.node_outputs && Object.keys(contextData.node_outputs).length > 0 && (
              <div className="mt-4">
                <h3 className="text-sm font-medium text-slate-700 mb-2">Node Outputs</h3>
                <div className="space-y-2">
                  {Object.entries(contextData.node_outputs).map(([nodeId, output]) => (
                    <details key={nodeId} className="text-xs">
                      <summary className="cursor-pointer font-mono text-slate-700 hover:text-slate-900 bg-slate-100 p-2 rounded">
                        {nodeId}
                      </summary>
                      <pre className="mt-2 p-2 bg-slate-800 text-green-400 rounded overflow-x-auto">
                        {JSON.stringify(output, null, 2)}
                      </pre>
                    </details>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* v0.7.3: Replay Modal */}
        {showReplayModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 max-w-md w-full">
              <h2 className="text-xl font-semibold mb-4">Replay this Run</h2>
              <p className="text-sm text-slate-600 mb-4">
                Create a new run with the same input and context as this run.
              </p>

              <div className="mb-4">
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Execution Mode
                </label>
                <select
                  value={replayMode}
                  onChange={(e) => setReplayMode(e.target.value as "dry_run" | "apply")}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                >
                  <option value="dry_run">Dry Run (Safe)</option>
                  <option value="apply">Apply (Makes Changes)</option>
                </select>
              </div>

              {replayChain && replayChain.total > 1 && (
                <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                  <p className="text-sm text-blue-800">
                    This is replay #{replayChain.total - 1} of the original run.
                  </p>
                </div>
              )}

              <div className="flex justify-end gap-2">
                <button
                  onClick={() => setShowReplayModal(false)}
                  className="px-4 py-2 bg-slate-100 text-slate-700 rounded-lg hover:bg-slate-200"
                >
                  Cancel
                </button>
                <button
                  onClick={handleReplay}
                  disabled={replaying}
                  className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
                >
                  {replaying ? "Creating..." : "Replay"}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Input JSON */}
        <details className="mt-6 bg-white rounded-lg border border-slate-200 p-4">
          <summary className="text-sm font-medium text-slate-900 cursor-pointer hover:text-slate-700">
            Input Data
          </summary>
          <pre className="mt-3 p-3 bg-slate-900 text-green-400 rounded text-xs overflow-x-auto">
            {JSON.stringify(run.input_json, null, 2)}
          </pre>
        </details>

        {/* Output JSON */}
        {run.output_json && Object.keys(run.output_json).length > 0 && (
          <details className="mt-6 bg-white rounded-lg border border-slate-200 p-4">
            <summary className="text-sm font-medium text-slate-900 cursor-pointer hover:text-slate-700">
              Final Output
            </summary>
            <pre className="mt-3 p-3 bg-slate-900 text-green-400 rounded text-xs overflow-x-auto">
              {JSON.stringify(run.output_json, null, 2)}
            </pre>
          </details>
        )}
      </div>
    </div>
  );
}
