"use client";

/**
 * Playbook Run Detail Page
 *
 * Features:
 * - Run summary (status, mode, timing, counters, error message)
 * - DAG execution topology with live node statuses (readonly canvas)
 * - Node execution detail list (status, attempts, duration, last error)
 * - Cancel action for active runs + auto refresh while the run is active
 * - Loading/Error/Not-found state coverage
 */

import { useState, useEffect, useCallback, useMemo } from "react";
import dynamic from "next/dynamic";
import { useParams } from "next/navigation";
import { useRouter } from "@/i18n/navigation";
import { useFormatter, useTranslations } from "next-intl";
import { authFetch, loadAuthState } from "@/lib/auth";
import { PageHeader } from "@/components/common/PageHeader";
import { LoadingState } from "@/components/common/LoadingState";
import { BackButton } from "@/components/common";
import { Layers, Code2, Play, Info, Ban, RefreshCw } from "lucide-react";
import type { DagDefinition } from "../constants";

type Formatter = ReturnType<typeof useFormatter>;

// Dynamically import DAGCanvas to prevent SSR issues with ReactFlow
const DAGCanvas = dynamic(() => import("@/components/dag/DAGCanvas").then((mod) => mod.DAGCanvas), {
  ssr: false,
  loading: () => (
    <div className="h-[460px] w-full flex items-center justify-center bg-surface-hover/30 rounded-2xl border border-dashed border-border-subtle">
      <div className="flex items-center gap-2 text-text-tertiary text-xs">
        <div className="w-4 h-4 border-2 border-accent-500 border-t-transparent rounded-full animate-spin" />
        <span>加载可视化流程引擎...</span>
      </div>
    </div>
  ),
});

interface PlaybookRunDetail {
  id: string;
  playbook_name: string;
  playbook_version: string;
  engine_version?: string | null;
  mode: string;
  status: string;
  failure_strategy?: string | null;
  created_by_user_id: string | null;
  input_json: Record<string, unknown> | null;
  output_json: Record<string, unknown> | null;
  started_at: string | null;
  finished_at: string | null;
  error_message: string | null;
  definition_id: string | null;
  total_nodes: number;
  completed_nodes: number;
  failed_nodes: number;
  running_nodes: number;
  pending_nodes: number;
}

interface PlaybookNodeRun {
  node_id: string;
  node_name: string;
  node_type: string;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  attempt_count: number;
  last_error: string | null;
}

type CanvasNodeStatus = "pending" | "running" | "success" | "failed" | "skipped";

const ACTIVE_RUN_STATUSES = ["pending", "queued", "running"];

const RUN_STATUS_PILL: Record<string, string> = {
  success: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-400",
  failed: "bg-red-100 text-red-700 dark:bg-red-950/40 dark:text-red-400",
  running: "bg-blue-100 text-blue-700 dark:bg-blue-950/40 dark:text-blue-400",
  partial: "bg-amber-100 text-amber-800 dark:bg-amber-950/40 dark:text-amber-400",
  pending: "bg-surface-hover text-text-secondary dark:bg-surface-card dark:text-text-muted",
  queued: "bg-purple-100 text-purple-700 dark:bg-purple-950/40 dark:text-purple-300",
  cancelled: "bg-surface-hover text-text-tertiary dark:bg-surface-card dark:text-text-muted",
};

const NODE_STATUS_PILL: Record<string, string> = {
  success: "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300",
  failed: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300",
  running: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",
  pending: "bg-surface-hover text-text-secondary dark:bg-surface-card dark:text-text-muted",
  skipped: "bg-surface-hover text-text-tertiary dark:bg-surface-card dark:text-text-muted",
  cancelled: "bg-surface-hover text-text-tertiary dark:bg-surface-card dark:text-text-muted",
};

function formatDateTime(ts: string | null | undefined, format: Formatter): string {
  if (!ts) return "-";
  try {
    const d = new Date(ts);
    if (isNaN(d.getTime())) return "-";
    return format.dateTime(d, { dateStyle: "medium", timeStyle: "medium" });
  } catch {
    return "-";
  }
}

function formatDurationSec(startedAt: string | null, finishedAt: string | null): string {
  if (!startedAt || !finishedAt) return "-";
  const start = new Date(startedAt).getTime();
  const end = new Date(finishedAt).getTime();
  if (isNaN(start) || isNaN(end) || end < start) return "-";
  return `${((end - start) / 1000).toFixed(1)}s`;
}

function nodeDurationMs(startedAt: string | null, finishedAt: string | null): number | undefined {
  if (!startedAt || !finishedAt) return undefined;
  const start = new Date(startedAt).getTime();
  const end = new Date(finishedAt).getTime();
  if (isNaN(start) || isNaN(end) || end < start) return undefined;
  return end - start;
}

export default function PlaybookRunDetailPage() {
  const params = useParams();
  const router = useRouter();
  const t = useTranslations("playbooks.runDetail");
  const tCommon = useTranslations("common");
  const tNodeStatus = useTranslations("playbooks.runDetail.nodeStatuses");
  const format = useFormatter();
  const runId = params.id as string;

  const [run, setRun] = useState<PlaybookRunDetail | null>(null);
  const [nodeRuns, setNodeRuns] = useState<PlaybookNodeRun[]>([]);
  const [definitionDag, setDefinitionDag] = useState<DagDefinition | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<"notFound" | "loadFailed" | null>(null);
  const [viewMode, setViewMode] = useState<"visual" | "json">("visual");
  const [cancelling, setCancelling] = useState(false);

  const fetchWithFallback = useCallback(
    async (path: string, options?: RequestInit): Promise<Response | null> => {
      let res = await authFetch(`/api/v1${path}`, options);
      if (!res.ok && res.status === 404) {
        res = await authFetch(path, options);
      }
      return res;
    },
    []
  );

  const loadRun = useCallback(async (): Promise<string | null> => {
    try {
      let res = await fetchWithFallback(`/playbook-definitions/runs/${runId}`);
      if (res && res.status === 404) {
        res = await fetchWithFallback(`/playbook/runs/${runId}`);
      }
      if (!res) {
        setError("loadFailed");
        return null;
      }
      if (res.status === 404) {
        setError("notFound");
        return null;
      }
      if (!res.ok) {
        setError("loadFailed");
        return null;
      }
      const data = await res.json();
      setRun({
        id: String(data.id),
        playbook_name: String(data.playbook_name || ""),
        playbook_version: String(data.playbook_version || "-"),
        engine_version: (data.engine_version as string) || null,
        mode: String(data.mode || ""),
        status: String(data.status || ""),
        failure_strategy: (data.failure_strategy as string) || null,
        created_by_user_id: (data.created_by_user_id as string) || null,
        input_json: (data.input_json as Record<string, unknown>) || null,
        output_json: (data.output_json as Record<string, unknown>) || null,
        started_at: (data.started_at as string) || null,
        finished_at: (data.finished_at as string) || null,
        error_message: (data.error_message as string) || null,
        definition_id: (data.definition_id as string) || null,
        total_nodes: Number(data.total_nodes || 0),
        completed_nodes: Number(data.completed_nodes || 0),
        failed_nodes: Number(data.failed_nodes || 0),
        running_nodes: Number(data.running_nodes || 0),
        pending_nodes: Number(data.pending_nodes || 0),
      });
      setError(null);
      return (data.definition_id as string) || null;
    } catch {
      setError("loadFailed");
      return null;
    }
  }, [runId, fetchWithFallback]);

  const loadNodeRuns = useCallback(async () => {
    try {
      const res = await fetchWithFallback(`/playbook-definitions/runs/${runId}/nodes`);
      if (!res || !res.ok) return;
      const data = await res.json();
      setNodeRuns(
        (Array.isArray(data) ? data : []).map((n: Record<string, unknown>) => ({
          node_id: String(n.node_id || ""),
          node_name: String(n.node_name || ""),
          node_type: String(n.node_type || ""),
          status: String(n.status || "pending"),
          started_at: (n.started_at as string) || null,
          finished_at: (n.finished_at as string) || null,
          attempt_count: Number(n.attempt_count || 0),
          last_error: (n.last_error as string) || null,
        }))
      );
    } catch {
      // Node list is auxiliary; keep previous state on failure
    }
  }, [runId, fetchWithFallback]);

  const loadDefinitionDag = useCallback(
    async (defId?: string | null) => {
      // Best effort: the run response carries no DAG structure, fetch it via the definition
      try {
        let definitionId = defId;
        if (!definitionId) {
          const runRes = await fetchWithFallback(`/playbook-definitions/runs/${runId}`);
          if (!runRes || !runRes.ok) return;
          const runData = await runRes.json();
          definitionId = runData.definition_id as string | undefined;
        }
        if (!definitionId) return;
        const defRes = await fetchWithFallback(`/playbook-definitions/${definitionId}`);
        if (!defRes || !defRes.ok) return;
        const defData = await defRes.json();
        setDefinitionDag((defData.dag as DagDefinition) || null);
      } catch {
        // Canvas is optional; node list still renders without it
      }
    },
    [runId, fetchWithFallback]
  );

  const handleRetry = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const defId = await loadRun();
      await Promise.all([loadNodeRuns(), defId ? loadDefinitionDag(defId) : Promise.resolve()]);
    } finally {
      setLoading(false);
    }
  }, [loadRun, loadNodeRuns, loadDefinitionDag]);

  // Auth guard + initial load
  useEffect(() => {
    const authState = loadAuthState();
    if (!authState?.isAuthenticated) {
      router.push("/login");
      return;
    }
    handleRetry();
  }, [router, handleRetry]);

  // Auto refresh while the run is active
  useEffect(() => {
    if (!run || !ACTIVE_RUN_STATUSES.includes(run.status)) return;
    const interval = setInterval(() => {
      loadRun();
      loadNodeRuns();
    }, 5000);
    return () => clearInterval(interval);
  }, [run?.status, loadRun, loadNodeRuns]);

  // Cancel Handler
  const handleCancel = async () => {
    setCancelling(true);
    try {
      const res = await fetchWithFallback(`/playbook-definitions/runs/${runId}/cancel`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      if (res && res.ok) {
        await loadRun();
        await loadNodeRuns();
      }
    } catch {
      // Feedback surfaces through refreshed run status
    } finally {
      setCancelling(false);
    }
  };

  const dag = useMemo(() => definitionDag ?? { nodes: [], edges: [] }, [definitionDag]);

  const dagDefinition = useMemo(
    () => ({
      nodes: dag.nodes.map((n) => ({
        id: n.id,
        step_id: n.step_id || n.id,
        name: n.name || n.id,
        position_x: n.position_x,
        position_y: n.position_y,
      })),
      edges: (dag.edges || []).map(
        (e: {
          source?: string;
          from?: string;
          target?: string;
          to?: string;
          condition?: string;
        }) => ({
          source: e.source || e.from || "",
          target: e.target || e.to || "",
          condition: e.condition || undefined,
        })
      ),
    }),
    [dag]
  );

  const nodeStatuses = useMemo(() => {
    const map: Record<string, { status: CanvasNodeStatus; duration?: number; error?: string }> = {};
    nodeRuns.forEach((nr) => {
      const status: CanvasNodeStatus = [
        "pending",
        "running",
        "success",
        "failed",
        "skipped",
      ].includes(nr.status)
        ? (nr.status as CanvasNodeStatus)
        : "skipped"; // cancelled etc. are not supported by the canvas palette
      map[nr.node_id] = {
        status,
        duration: nodeDurationMs(nr.started_at, nr.finished_at),
        error: nr.last_error || undefined,
      };
    });
    return map;
  }, [nodeRuns]);

  const backButton = (
    <BackButton fallbackUrl="/playbooks" label={tCommon("back")} variant="ghost" />
  );

  const refreshButton = (
    <button
      type="button"
      onClick={handleRetry}
      className="inline-flex items-center justify-center p-2 rounded-lg border border-border-subtle bg-surface-card hover:bg-surface-hover text-text-secondary text-sm font-medium transition-colors"
      title={tCommon("refresh")}
    >
      <RefreshCw className="w-4 h-4" />
    </button>
  );

  const isActiveRun = run ? ACTIVE_RUN_STATUSES.includes(run.status) : false;

  // ── Loading ─────────────────────────────────────────────
  if (loading) {
    return (
      <div className="min-h-screen bg-surface-page transition-colors">
        <PageHeader title={t("title")} subtitle={t("subtitle")} backButton={backButton} />
        <main className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 pt-6">
          <LoadingState isLoading={true} type="skeleton" skeletonType="card" />
        </main>
      </div>
    );
  }

  // ── Error / Not Found ───────────────────────────────────
  if (error || !run) {
    return (
      <div className="min-h-screen bg-surface-page transition-colors">
        <PageHeader title={t("title")} subtitle={t("subtitle")} backButton={backButton} />
        <main className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 pt-6">
          <LoadingState
            isLoading={false}
            error={error === "notFound" ? t("notFound") : t("loadFailed")}
            onRetry={error === "notFound" ? undefined : handleRetry}
          />
        </main>
      </div>
    );
  }

  const runStatusPill = RUN_STATUS_PILL[run.status] || RUN_STATUS_PILL.pending;

  return (
    <div className="min-h-screen bg-surface-page transition-colors pb-16">
      {/* Header */}
      <PageHeader
        backButton={backButton}
        title={run.playbook_name || t("title")}
        subtitle={t("subtitle")}
        actions={
          <div className="flex items-center gap-2">
            {refreshButton}
            {isActiveRun && (
              <button
                type="button"
                onClick={handleCancel}
                disabled={cancelling}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white text-sm font-medium shadow-subtle transition-all disabled:opacity-50"
              >
                <Ban className="w-4 h-4" />
                <span>{cancelling ? t("cancelling") : t("cancel")}</span>
              </button>
            )}
          </div>
        }
      />

      <main className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 pt-6 space-y-6">
        {/* Status & Node Progress */}
        <div className="bg-surface-card border border-border-subtle rounded-xl p-5 shadow-subtle">
          <div className="flex flex-wrap items-center gap-3 pb-4 border-b border-border-subtle">
            <span
              className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${runStatusPill}`}
            >
              {run.status}
            </span>
            <span
              className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                run.mode === "apply"
                  ? "bg-red-50 text-red-700 dark:bg-red-900/50 dark:text-red-300"
                  : "bg-purple-50 text-purple-700 dark:bg-purple-900/50 dark:text-purple-300"
              }`}
            >
              {run.mode}
            </span>
            {isActiveRun && (
              <span className="inline-flex items-center gap-1.5 text-xs text-text-tertiary">
                <RefreshCw className="w-3.5 h-3.5 animate-spin text-accent-500" />
                {t("autoRefreshHint")}
              </span>
            )}
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 pt-4">
            {[
              { label: t("total"), value: run.total_nodes },
              { label: t("completed"), value: run.completed_nodes },
              { label: t("failed"), value: run.failed_nodes },
              { label: t("running"), value: run.running_nodes },
              { label: t("pending"), value: run.pending_nodes },
            ].map((item) => (
              <div key={item.label} className="px-3 py-2.5 rounded-lg bg-surface-hover/60">
                <div className="text-xs text-text-tertiary">{item.label}</div>
                <div className="text-base font-mono font-semibold text-text-primary mt-0.5">
                  {item.value}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Run Info */}
          <div className="bg-surface-card border border-border-subtle rounded-xl p-5 shadow-subtle space-y-4">
            <div className="flex items-center gap-2 pb-3 border-b border-border-subtle">
              <Info className="w-4 h-4 text-accent-600 dark:text-accent-400" />
              <h3 className="text-sm font-semibold text-text-primary uppercase tracking-wider">
                {t("runInfo")}
              </h3>
            </div>

            <div className="space-y-2.5 text-sm">
              {[
                { label: t("version"), value: run.playbook_version, mono: true },
                { label: t("engineVersion"), value: run.engine_version || "-", mono: true },
                { label: t("failureStrategy"), value: run.failure_strategy || "-", mono: true },
                {
                  label: t("startedAt"),
                  value: formatDateTime(run.started_at, format),
                  mono: false,
                },
                {
                  label: t("finishedAt"),
                  value: formatDateTime(run.finished_at, format),
                  mono: false,
                },
                {
                  label: t("duration"),
                  value: formatDurationSec(run.started_at, run.finished_at),
                  mono: true,
                },
                { label: t("createdBy"), value: run.created_by_user_id || "-", mono: true },
                { label: t("runId"), value: run.id, mono: true },
                { label: t("definitionId"), value: run.definition_id || "-", mono: true },
              ].map((row) => (
                <div key={row.label} className="flex items-center justify-between gap-3">
                  <span className="text-xs text-text-tertiary shrink-0">{row.label}</span>
                  <span
                    className={`text-sm text-text-secondary truncate ${row.mono ? "font-mono" : ""}`}
                    title={row.value}
                  >
                    {row.value}
                  </span>
                </div>
              ))}
            </div>

            {run.error_message && (
              <div className="pt-2 border-t border-border-subtle">
                <div className="text-xs font-semibold text-danger-600 dark:text-danger-400 mb-1">
                  {t("errorMessage")}
                </div>
                <pre className="px-3 py-2 rounded-lg bg-danger-500/10 border border-danger-500/30 text-danger-700 dark:text-danger-300 text-xs font-mono whitespace-pre-wrap break-all max-h-32 overflow-auto">
                  {run.error_message}
                </pre>
              </div>
            )}
          </div>

          {/* DAG Execution Topology */}
          <div className="lg:col-span-2 bg-surface-card border border-border-subtle rounded-xl p-5 shadow-subtle flex flex-col justify-between">
            <div className="flex items-center justify-between pb-3 border-b border-border-subtle mb-4">
              <div className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-accent-600 dark:text-accent-400" />
                <h3 className="text-sm font-semibold text-text-primary uppercase tracking-wider">
                  {t("dagTitle")}
                </h3>
              </div>
              <div className="flex items-center gap-1 p-0.5 rounded-lg bg-surface-hover border border-border-subtle text-xs">
                <button
                  type="button"
                  onClick={() => setViewMode("visual")}
                  className={`flex items-center gap-1 px-2.5 py-1 rounded-lg transition-colors font-medium ${
                    viewMode === "visual"
                      ? "bg-surface-card text-text-primary shadow-subtle"
                      : "text-text-tertiary hover:text-text-secondary"
                  }`}
                >
                  <Play className="w-3 h-3" />
                  <span>{t("canvasView")}</span>
                </button>
                <button
                  type="button"
                  onClick={() => setViewMode("json")}
                  className={`flex items-center gap-1 px-2.5 py-1 rounded-lg transition-colors font-medium ${
                    viewMode === "json"
                      ? "bg-surface-card text-text-primary shadow-subtle"
                      : "text-text-tertiary hover:text-text-secondary"
                  }`}
                >
                  <Code2 className="w-3 h-3" />
                  <span>{t("jsonView")}</span>
                </button>
              </div>
            </div>

            <div className="min-h-[460px] rounded-xl overflow-hidden border border-border-subtle bg-surface-page relative">
              {viewMode === "visual" ? (
                <DAGCanvas
                  definition={dagDefinition}
                  nodeStatuses={nodeStatuses}
                  readonly={true}
                  className="w-full h-[460px]"
                />
              ) : (
                <pre className="h-[460px] w-full p-3 font-mono text-xs bg-surface-card rounded-lg border border-border-subtle overflow-auto text-text-primary whitespace-pre-wrap break-all">
                  {JSON.stringify({ run, nodes: nodeRuns }, null, 2)}
                </pre>
              )}
            </div>
          </div>
        </div>

        {/* Node Execution Detail */}
        <div className="bg-surface-card border border-border-subtle rounded-xl shadow-subtle overflow-hidden">
          <div className="px-5 py-3.5 border-b border-border-subtle flex items-center gap-2">
            <Layers className="w-4 h-4 text-accent-600 dark:text-accent-400" />
            <h3 className="text-sm font-semibold text-text-primary uppercase tracking-wider">
              {t("nodeList")}
            </h3>
          </div>

          {nodeRuns.length === 0 ? (
            <div className="px-5 py-8 text-center text-sm text-text-muted italic">
              {t("noNodes")}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm divide-y divide-border-subtle">
                <thead>
                  <tr className="bg-surface-hover/50">
                    <th className="px-5 py-3 text-left text-xs font-semibold text-text-muted uppercase tracking-wider">
                      {t("node")}
                    </th>
                    <th className="px-5 py-3 text-left text-xs font-semibold text-text-muted uppercase tracking-wider">
                      {t("type")}
                    </th>
                    <th className="px-5 py-3 text-left text-xs font-semibold text-text-muted uppercase tracking-wider">
                      {t("nodeStatus")}
                    </th>
                    <th className="px-5 py-3 text-left text-xs font-semibold text-text-muted uppercase tracking-wider">
                      {t("attempts")}
                    </th>
                    <th className="px-5 py-3 text-left text-xs font-semibold text-text-muted uppercase tracking-wider">
                      {t("duration")}
                    </th>
                    <th className="px-5 py-3 text-left text-xs font-semibold text-text-muted uppercase tracking-wider">
                      {t("error")}
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-subtle">
                  {nodeRuns.map((nr) => (
                    <tr key={nr.node_id} className="hover:bg-surface-hover/50 transition-colors">
                      <td className="px-5 py-3 text-sm text-text-primary">
                        <div className="font-medium truncate max-w-[220px]">{nr.node_name}</div>
                        <div className="text-xs font-mono text-text-muted">{nr.node_id}</div>
                      </td>
                      <td className="px-5 py-3 text-sm font-mono text-text-secondary">
                        {nr.node_type}
                      </td>
                      <td className="px-5 py-3">
                        <span
                          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                            NODE_STATUS_PILL[nr.status] || NODE_STATUS_PILL.pending
                          }`}
                        >
                          {tNodeStatus(nr.status)}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-sm font-mono text-text-secondary">
                        {nr.attempt_count}
                      </td>
                      <td className="px-5 py-3 text-sm font-mono text-text-secondary">
                        {formatDurationSec(nr.started_at, nr.finished_at)}
                      </td>
                      <td className="px-5 py-3 text-sm text-danger-600 dark:text-danger-400 max-w-[240px]">
                        {nr.last_error ? (
                          <span className="line-clamp-2" title={nr.last_error}>
                            {nr.last_error}
                          </span>
                        ) : (
                          <span className="text-text-muted">-</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
