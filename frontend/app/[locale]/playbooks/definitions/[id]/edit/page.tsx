"use client";

/**
 * Playbook Definition Edit Page
 *
 * Features:
 * - Loads an existing definition and prefills the metadata form + DAG editor
 * - Edits name/version/description/is_active and the DAG (visual canvas or JSON source)
 * - Canvas edits sync back to state via DAGCanvas change callbacks
 * - Submits PATCH to /api/v1/playbook-definitions/{id} with legacy endpoint fallback
 */

import { useState, useEffect, useCallback, useMemo } from "react";
import dynamic from "next/dynamic";
import { useParams } from "next/navigation";
import { useRouter } from "@/i18n/navigation";
import { useTranslations } from "next-intl";
import type { Edge, Node } from "reactflow";
import { authFetch, loadAuthState } from "@/lib/auth";
import { PageHeader } from "@/components/common/PageHeader";
import { LoadingState } from "@/components/common/LoadingState";
import { BackButton } from "@/components/common";
import { Save, Play, Layers, Code2, CheckCircle2, AlertTriangle, Info } from "lucide-react";
import type { DagNodeDef, DagEdgeDef, DagDefinition } from "../../../constants";
import { parseDagDefinition, normalizeNodeType } from "../../../constants";
import type { NodeData } from "@/components/dag/DAGNode";

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

export default function EditPlaybookDefinitionPage() {
  const params = useParams();
  const router = useRouter();
  const t = useTranslations("playbooks.edit");
  const tCommon = useTranslations("common");
  const definitionId = params.id as string;

  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<"notFound" | "loadFailed" | null>(null);

  // Form State
  const [name, setName] = useState("");
  const [version, setVersion] = useState("1.0.0");
  const [description, setDescription] = useState("");
  const [isActive, setIsActive] = useState(true);

  // DAG State
  const [nodes, setNodes] = useState<DagNodeDef[]>([]);
  const [edges, setEdges] = useState<DagEdgeDef[]>([]);
  const [viewMode, setViewMode] = useState<"visual" | "json">("visual");
  const [jsonText, setJsonText] = useState("");
  const [jsonError, setJsonError] = useState<string | null>(null);

  // Submission State
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(
    null
  );

  const loadDefinition = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      let res = await authFetch(`/api/v1/playbook-definitions/${definitionId}`);

      // Fallback to legacy endpoint if v1 prefix returned 404
      if (!res.ok && res.status === 404) {
        res = await authFetch(`/api/playbook-definitions/${definitionId}`);
      }

      if (res.status === 404) {
        setLoadError("notFound");
        return;
      }
      if (!res.ok) {
        setLoadError("loadFailed");
        return;
      }

      const data = await res.json();
      const dagData = (data.dag as DagDefinition) || { nodes: [], edges: [] };

      setName(String(data.name || ""));
      setVersion(String(data.version || "1.0.0"));
      setDescription((data.description as string) || "");
      setIsActive(Boolean(data.is_active));

      const sanitizedNodes: DagNodeDef[] = (dagData.nodes || []).map((n, idx) => ({
        id: String(n.id || `node-${idx + 1}`),
        type: normalizeNodeType((n.type || n.action || n.step_id) as string),
        step_id: String(n.step_id || n.id || `step_${idx + 1}`),
        name: String(n.name || n.id || `节点 ${idx + 1}`),
        position_x: typeof n.position_x === "number" ? n.position_x : 60 + idx * 260,
        position_y: typeof n.position_y === "number" ? n.position_y : 160,
        action: typeof n.action === "string" ? n.action : undefined,
        inputs: (n.inputs as Record<string, unknown>) || {},
      }));
      const sanitizedEdges: DagEdgeDef[] = (dagData.edges || [])
        .filter((e) => e && typeof e.source === "string" && typeof e.target === "string")
        .map((e) => ({
          source: e.source,
          target: e.target,
          condition: e.condition || undefined,
        }));

      setNodes(sanitizedNodes);
      setEdges(sanitizedEdges);
      setJsonText(JSON.stringify({ nodes: sanitizedNodes, edges: sanitizedEdges }, null, 2));
    } catch {
      setLoadError("loadFailed");
    } finally {
      setLoading(false);
    }
  }, [definitionId]);

  // Auth guard + initial load
  useEffect(() => {
    const authState = loadAuthState();
    if (!authState?.isAuthenticated) {
      router.push("/login");
      return;
    }
    loadDefinition();
  }, [router, loadDefinition]);

  // Sync JSON Text Changes
  const handleJsonChange = (text: string) => {
    setJsonText(text);
    try {
      const parsed = parseDagDefinition(text);
      setNodes(parsed.nodes);
      setEdges(parsed.edges);
      setJsonError(null);
    } catch (e) {
      setJsonError((e as Error).message);
    }
  };

  // Canvas edits sync back into the definition state (positions, deletions, labels)
  const handleCanvasNodesChange = useCallback((rfNodes: Node<NodeData>[]) => {
    if (!rfNodes || rfNodes.length === 0) {
      return;
    }
    setNodes((prev) =>
      rfNodes.map((rf) => {
        const existing = prev.find((p) => p.id === rf.id);
        return {
          id: rf.id,
          type: existing?.type ?? normalizeNodeType(rf.data?.stepId),
          step_id: existing?.step_id || rf.data?.stepId || rf.id,
          name: rf.data?.label || existing?.name || rf.id,
          position_x: rf.position.x,
          position_y: rf.position.y,
          action: existing?.action,
          inputs: existing?.inputs ?? {},
        };
      })
    );
  }, []);

  const handleCanvasEdgesChange = useCallback((rfEdges: Edge[]) => {
    setEdges((prev) =>
      rfEdges.map((rf) => {
        const existing = prev.find((p) => p.source === rf.source && p.target === rf.target);
        const label = typeof rf.label === "string" ? rf.label : undefined;
        return {
          source: rf.source,
          target: rf.target,
          condition: label || existing?.condition,
        };
      })
    );
  }, []);

  // Build DAG definition for canvas
  const dagDefinition = useMemo(
    () => ({
      nodes: nodes.map((n) => ({
        id: n.id,
        step_id: n.step_id,
        name: n.name,
        position_x: n.position_x,
        position_y: n.position_y,
      })),
      edges: edges.map((e) => ({
        source: e.source,
        target: e.target,
        condition: e.condition,
      })),
    }),
    [nodes, edges]
  );

  // Switch to JSON view regenerates the source from current state (canvas is authoritative)
  const switchToView = (mode: "visual" | "json") => {
    if (mode === "json" && viewMode !== "json") {
      setJsonText(JSON.stringify({ nodes, edges }, null, 2));
      setJsonError(null);
    }
    setViewMode(mode);
  };

  // Submit Handler
  const handleSubmit = async () => {
    if (!name.trim()) {
      setFeedback({ type: "error", message: t("nameRequired") });
      return;
    }

    if (nodes.length === 0) {
      setFeedback({ type: "error", message: t("nodesRequired") });
      return;
    }

    // Validate that all edge sources and targets exist
    const nodeIds = new Set(nodes.map((n) => n.id));
    const invalidEdge = edges.find((e) => !nodeIds.has(e.source) || !nodeIds.has(e.target));
    if (invalidEdge) {
      setFeedback({
        type: "error",
        message: t("invalidEdge", { source: invalidEdge.source, target: invalidEdge.target }),
      });
      return;
    }

    setSubmitting(true);
    setFeedback(null);

    const payload = {
      name: name.trim(),
      version: version.trim() || "1.0.0",
      description: description.trim() || null,
      is_active: isActive,
      dag: {
        nodes: nodes.map((n) => ({
          id: n.id,
          type: normalizeNodeType(n.type || n.action || n.step_id),
          step_id: n.step_id || n.id,
          name: n.name || n.id,
          action: n.action || n.step_id || n.type || "parse_json",
          position_x: n.position_x,
          position_y: n.position_y,
          inputs: n.inputs || {},
        })),
        edges: edges.map((e) => ({
          source: e.source,
          target: e.target,
          condition: e.condition || null,
        })),
      },
    };

    try {
      let res = await authFetch(`/api/v1/playbook-definitions/${definitionId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      // Fallback to legacy endpoint if v1 prefix returned 404
      if (!res.ok && res.status === 404) {
        res = await authFetch(`/api/playbook-definitions/${definitionId}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
      }

      if (res.ok) {
        setFeedback({
          type: "success",
          message: t("saveSuccess"),
        });
        setTimeout(() => {
          router.push(`/playbooks/definitions/${definitionId}`);
        }, 1200);
      } else {
        let errMsg = t("saveFailed");
        try {
          const errData = await res.json();
          if (errData?.detail) {
            if (Array.isArray(errData.detail)) {
              errMsg = errData.detail
                .map((d: unknown) =>
                  typeof d === "string" ? d : (d as { msg?: string }).msg || JSON.stringify(d)
                )
                .join("; ");
            } else if (typeof errData.detail === "string") {
              errMsg = errData.detail;
            }
          } else if (errData?.message) {
            errMsg = errData.message;
          }
        } catch {
          // ignore parsing error
        }
        setFeedback({
          type: "error",
          message: errMsg,
        });
      }
    } catch {
      setFeedback({
        type: "error",
        message: t("networkError"),
      });
    } finally {
      setSubmitting(false);
    }
  };

  // ── Loading ─────────────────────────────────────────────
  if (loading) {
    return (
      <div className="min-h-screen bg-surface-canvas transition-colors">
        <PageHeader
          title={t("title")}
          subtitle={t("subtitle")}
          backButton={
            <BackButton
              fallbackUrl={`/playbooks/definitions/${definitionId}`}
              label={tCommon("back")}
            />
          }
        />
        <main className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 pt-6">
          <LoadingState isLoading={true} type="skeleton" skeletonType="card" />
        </main>
      </div>
    );
  }

  // ── Error / Not Found ───────────────────────────────────
  if (loadError) {
    return (
      <div className="min-h-screen bg-surface-canvas transition-colors">
        <PageHeader
          title={t("title")}
          subtitle={t("subtitle")}
          backButton={
            <BackButton
              fallbackUrl={`/playbooks/definitions/${definitionId}`}
              label={tCommon("back")}
            />
          }
        />
        <main className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 pt-6">
          <LoadingState
            isLoading={false}
            error={loadError === "notFound" ? t("notFound") : t("loadFailed")}
            onRetry={loadError === "notFound" ? undefined : () => loadDefinition()}
          />
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-surface-canvas transition-colors pb-16">
      {/* Header */}
      <PageHeader
        title={t("title")}
        subtitle={name || t("subtitle")}
        backButton={
          <BackButton
            fallbackUrl={`/playbooks/definitions/${definitionId}`}
            label={tCommon("back")}
          />
        }
        actions={
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleSubmit}
              disabled={submitting}
              className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-xl bg-accent-600 hover:bg-accent-700 text-white text-xs font-semibold shadow-sm transition-all disabled:opacity-50"
            >
              <Save className="w-3.5 h-3.5" />
              <span>{submitting ? t("saving") : t("save")}</span>
            </button>
          </div>
        }
      />

      <main className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 pt-6 space-y-6">
        {/* Feedback Alert */}
        {feedback && (
          <div
            className={`p-4 rounded-2xl border flex items-center gap-3 animate-fade-in ${
              feedback.type === "success"
                ? "bg-success-500/10 border-success-500/30 text-success-700 dark:text-success-300"
                : "bg-danger-500/10 border-danger-500/30 text-danger-700 dark:text-danger-300"
            }`}
          >
            {feedback.type === "success" ? (
              <CheckCircle2 className="w-5 h-5 shrink-0" />
            ) : (
              <AlertTriangle className="w-5 h-5 shrink-0" />
            )}
            <span className="text-xs font-medium">{feedback.message}</span>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Metadata Config */}
          <div className="bg-surface-card border border-border-subtle rounded-2xl p-5 shadow-subtle space-y-4">
            <div className="flex items-center gap-2 pb-3 border-b border-border-subtle">
              <Info className="w-4 h-4 text-accent-600 dark:text-accent-400" />
              <h3 className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                {t("basicConfig")}
              </h3>
            </div>

            <div>
              <label className="block text-xs font-medium text-text-secondary mb-1.5">
                {t("name")} <span className="text-danger-500">*</span>
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder={t("namePlaceholder")}
                required
                className="w-full px-3 py-2 text-xs rounded-xl border border-border-default bg-surface-card text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-500/20 focus:border-accent-600 transition-colors"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-text-secondary mb-1.5">
                  {t("version")}
                </label>
                <input
                  type="text"
                  value={version}
                  onChange={(e) => setVersion(e.target.value)}
                  placeholder="1.0.0"
                  className="w-full px-3 py-2 text-xs font-mono rounded-xl border border-border-default bg-surface-card text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-500/20 focus:border-accent-600 transition-colors"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-text-secondary mb-1.5">
                  {t("isActive")}
                </label>
                <button
                  type="button"
                  onClick={() => setIsActive(!isActive)}
                  className={`w-full py-2 px-3 rounded-xl border text-xs font-medium flex items-center justify-center gap-2 transition-colors ${
                    isActive
                      ? "bg-success-500/15 border-success-500/30 text-success-700 dark:text-success-400"
                      : "bg-surface-hover border-border-subtle text-text-tertiary"
                  }`}
                >
                  <div
                    className={`w-2 h-2 rounded-full ${
                      isActive ? "bg-success-500 animate-pulse" : "bg-text-tertiary"
                    }`}
                  />
                  <span>{isActive ? t("activeLabel") : t("draftLabel")}</span>
                </button>
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-text-secondary mb-1.5">
                {t("description")}
              </label>
              <textarea
                rows={4}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder={t("descriptionPlaceholder")}
                className="w-full px-3 py-2 text-xs rounded-xl border border-border-default bg-surface-card text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-500/20 focus:border-accent-600 transition-colors resize-none"
              />
            </div>

            {/* Step Summary */}
            <div className="pt-2 border-t border-border-subtle">
              <h4 className="text-[11px] font-semibold text-text-tertiary uppercase tracking-wider mb-2">
                {t("stepSummary", { count: nodes.length })}
              </h4>
              <div className="space-y-1 max-h-48 overflow-y-auto pr-1">
                {nodes.map((n, idx) => (
                  <div
                    key={n.id}
                    className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-surface-hover/60 text-xs"
                  >
                    <span className="w-4 h-4 rounded-full bg-accent-500/10 text-accent-700 dark:text-accent-300 flex items-center justify-center text-[10px] font-mono shrink-0">
                      {idx + 1}
                    </span>
                    <span className="text-text-primary truncate flex-1">{n.name}</span>
                    <span className="text-[10px] font-mono text-text-tertiary">{n.step_id}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Flow Editor */}
          <div className="lg:col-span-2 bg-surface-card border border-border-subtle rounded-2xl p-5 shadow-subtle flex flex-col justify-between">
            <div className="flex items-center justify-between pb-3 border-b border-border-subtle mb-4">
              <div className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-accent-600 dark:text-accent-400" />
                <h3 className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                  {t("dagTitle")}
                </h3>
              </div>
              <div className="flex items-center gap-1 p-0.5 rounded-xl bg-surface-hover border border-border-subtle text-xs">
                <button
                  type="button"
                  onClick={() => switchToView("visual")}
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
                  onClick={() => switchToView("json")}
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

            {/* Canvas / JSON Area */}
            <div className="flex-1 min-h-[460px] rounded-xl overflow-hidden border border-border-subtle bg-surface-canvas/50 relative">
              {viewMode === "visual" ? (
                <DAGCanvas
                  definition={dagDefinition}
                  readonly={false}
                  onNodesChange={handleCanvasNodesChange}
                  onEdgesChange={handleCanvasEdgesChange}
                  className="w-full h-[460px]"
                />
              ) : (
                <div className="h-[460px] flex flex-col p-2">
                  {jsonError && (
                    <div className="mb-2 px-3 py-1.5 rounded-lg bg-danger-500/10 border border-danger-500/30 text-danger-700 dark:text-danger-300 text-xs font-mono">
                      {jsonError}
                    </div>
                  )}
                  <textarea
                    value={jsonText}
                    onChange={(e) => handleJsonChange(e.target.value)}
                    spellCheck={false}
                    className="flex-1 w-full p-3 font-mono text-xs bg-surface-card rounded-lg border border-border-subtle focus:outline-none focus:ring-1 focus:ring-accent-500 text-text-primary resize-none"
                  />
                </div>
              )}
            </div>

            {/* Footer hint */}
            <div className="mt-4 pt-3 border-t border-border-subtle flex items-center justify-between text-xs text-text-tertiary">
              <span>{t("footerStats", { nodes: nodes.length, edges: edges.length })}</span>
              <span>{t("footerHint")}</span>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
