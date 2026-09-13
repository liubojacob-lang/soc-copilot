"use client";

/**
 * Playbook Definition Detail Page
 *
 * Features:
 * - Definition basic info (name, version, status, description, counts, audit fields)
 * - Readonly DAG topology visualization (canvas) with JSON source view
 * - Edit entry point and back navigation
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
import { Edit2, Layers, Code2, Play, Info } from "lucide-react";
import type { DagDefinition } from "../../constants";

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

interface PlaybookDefinitionDetail {
  id: string;
  name: string;
  version: string;
  description: string | null;
  dag: DagDefinition | null;
  created_by_user_id: string | null;
  created_at: string;
  updated_at: string;
  is_active: boolean;
  status: string;
  node_count: number;
  edge_count: number;
}

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

export default function PlaybookDefinitionDetailPage() {
  const params = useParams();
  const router = useRouter();
  const t = useTranslations("playbooks.detail");
  const tCommon = useTranslations("common");
  const format = useFormatter();
  const definitionId = params.id as string;

  const [definition, setDefinition] = useState<PlaybookDefinitionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<"notFound" | "loadFailed" | null>(null);
  const [viewMode, setViewMode] = useState<"visual" | "json">("visual");

  const loadDefinition = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      let res = await authFetch(`/api/v1/playbook-definitions/${definitionId}`);

      // Fallback to legacy endpoint if v1 prefix returned 404
      if (!res.ok && res.status === 404) {
        res = await authFetch(`/api/playbook-definitions/${definitionId}`);
      }

      if (res.status === 404) {
        setDefinition(null);
        setError("notFound");
        return;
      }
      if (!res.ok) {
        setDefinition(null);
        setError("loadFailed");
        return;
      }

      const data = await res.json();
      setDefinition({
        id: String(data.id),
        name: String(data.name || ""),
        version: String(data.version || "1.0.0"),
        description: (data.description as string) || null,
        dag: (data.dag as DagDefinition) || null,
        created_by_user_id: (data.created_by_user_id as string) || null,
        created_at: String(data.created_at || ""),
        updated_at: String(data.updated_at || ""),
        is_active: Boolean(data.is_active),
        status: (data.status as string) || (data.is_active ? "published" : "draft"),
        node_count: Number(data.node_count || (data.dag?.nodes as unknown[])?.length || 0),
        edge_count: Number(data.edge_count || (data.dag?.edges as unknown[])?.length || 0),
      });
    } catch {
      setDefinition(null);
      setError("loadFailed");
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

  const dag = useMemo(() => definition?.dag ?? { nodes: [], edges: [] }, [definition]);

  const dagDefinition = useMemo(
    () => ({
      nodes: dag.nodes.map((n) => ({
        id: n.id,
        step_id: n.step_id || n.id,
        name: n.name || n.id,
        position_x: n.position_x,
        position_y: n.position_y,
      })),
      edges: dag.edges.map((e) => ({
        source: e.source,
        target: e.target,
        condition: e.condition || undefined,
      })),
    }),
    [dag]
  );

  const statusPill = definition
    ? definition.status === "published"
      ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-400"
      : definition.status === "draft"
        ? "bg-amber-100 text-amber-800 dark:bg-amber-950/40 dark:text-amber-400"
        : "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400"
    : "";

  const backButton = (
    <BackButton fallbackUrl="/playbooks?tab=definitions" label={tCommon("back")} />
  );

  // ── Loading ─────────────────────────────────────────────
  if (loading) {
    return (
      <div className="min-h-screen bg-surface-canvas transition-colors">
        <PageHeader title={t("title")} subtitle={t("subtitle")} backButton={backButton} />
        <main className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 pt-6">
          <LoadingState isLoading={true} type="skeleton" skeletonType="card" />
        </main>
      </div>
    );
  }

  // ── Error / Not Found ───────────────────────────────────
  if (error || !definition) {
    return (
      <div className="min-h-screen bg-surface-canvas transition-colors">
        <PageHeader title={t("title")} subtitle={t("subtitle")} backButton={backButton} />
        <main className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 pt-6">
          <LoadingState
            isLoading={false}
            error={error === "notFound" ? t("notFound") : t("loadFailed")}
            onRetry={error === "notFound" ? undefined : () => loadDefinition()}
          />
        </main>
      </div>
    );
  }

  // ── Loaded ──────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-surface-canvas transition-colors pb-16">
      {/* Header */}
      <PageHeader
        backButton={backButton}
        title={t("title")}
        subtitle={definition.name || t("subtitle")}
        actions={
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => router.push(`/playbooks/definitions/${definitionId}/edit`)}
              className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-xl bg-accent-600 hover:bg-accent-700 text-white text-xs font-semibold shadow-sm transition-all"
            >
              <Edit2 className="w-3.5 h-3.5" />
              <span>{t("edit")}</span>
            </button>
          </div>
        }
      />

      <main className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 pt-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Basic Info */}
          <div className="bg-surface-card border border-border-subtle rounded-2xl p-5 shadow-subtle space-y-4">
            <div className="flex items-center gap-2 pb-3 border-b border-border-subtle">
              <Info className="w-4 h-4 text-accent-600 dark:text-accent-400" />
              <h3 className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                {t("basicInfo")}
              </h3>
            </div>

            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="text-sm font-semibold text-text-primary">{definition.name}</h2>
                <span
                  className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium ${statusPill}`}
                >
                  {definition.status}
                </span>
              </div>
              <p className="mt-1.5 text-xs text-text-tertiary leading-relaxed">
                {definition.description || t("noDescription")}
              </p>
            </div>

            <div className="grid grid-cols-3 gap-2">
              <div className="px-2.5 py-2 rounded-xl bg-surface-hover/60">
                <div className="text-[10px] text-text-tertiary">{t("version")}</div>
                <div className="text-xs font-mono font-medium text-text-primary mt-0.5">
                  {definition.version}
                </div>
              </div>
              <div className="px-2.5 py-2 rounded-xl bg-surface-hover/60">
                <div className="text-[10px] text-text-tertiary">{t("nodes")}</div>
                <div className="text-xs font-mono font-medium text-text-primary mt-0.5">
                  {definition.node_count}
                </div>
              </div>
              <div className="px-2.5 py-2 rounded-xl bg-surface-hover/60">
                <div className="text-[10px] text-text-tertiary">{t("edges")}</div>
                <div className="text-xs font-mono font-medium text-text-primary mt-0.5">
                  {definition.edge_count}
                </div>
              </div>
            </div>

            <div className="pt-2 border-t border-border-subtle space-y-2 text-xs">
              <div className="flex items-center justify-between gap-3">
                <span className="text-text-tertiary shrink-0">{t("createdBy")}</span>
                <span className="text-text-secondary font-mono truncate">
                  {definition.created_by_user_id || "-"}
                </span>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="text-text-tertiary shrink-0">{t("createdAt")}</span>
                <span className="text-text-secondary">
                  {formatDateTime(definition.created_at, format)}
                </span>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="text-text-tertiary shrink-0">{t("updatedAt")}</span>
                <span className="text-text-secondary">
                  {formatDateTime(definition.updated_at, format)}
                </span>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="text-text-tertiary shrink-0">{t("definitionId")}</span>
                <span className="text-text-secondary font-mono truncate" title={definition.id}>
                  {definition.id}
                </span>
              </div>
            </div>
          </div>

          {/* DAG Topology */}
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

            <div className="min-h-[460px] rounded-xl overflow-hidden border border-border-subtle bg-surface-canvas/50 relative">
              {viewMode === "visual" ? (
                <DAGCanvas
                  definition={dagDefinition}
                  readonly={true}
                  className="w-full h-[460px]"
                />
              ) : (
                <pre className="h-[460px] w-full p-3 font-mono text-xs bg-surface-card rounded-lg border border-border-subtle overflow-auto text-text-primary whitespace-pre-wrap break-all">
                  {JSON.stringify(dag, null, 2)}
                </pre>
              )}
            </div>

            {/* Footer hint */}
            <div className="mt-4 pt-3 border-t border-border-subtle flex items-center justify-between text-xs text-text-tertiary">
              <span>
                {t("footerNodes", { nodes: definition.node_count, edges: definition.edge_count })}
              </span>
              <span>{t("footerHint")}</span>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
