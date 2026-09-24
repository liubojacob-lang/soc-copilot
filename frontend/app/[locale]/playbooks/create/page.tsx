"use client";

import { useState, useMemo } from "react";
import dynamic from "next/dynamic";
import { useRouter } from "@/i18n/navigation";
import { useTranslations, useLocale } from "next-intl";
import { authFetch } from "@/lib/auth";
import { PageHeader } from "@/components/common/PageHeader";
import {
  ArrowLeft,
  Save,
  Play,
  Layers,
  Code2,
  CheckCircle2,
  AlertTriangle,
  Info,
} from "lucide-react";

function CanvasLoading() {
  const t = useTranslations("playbooks");
  return (
    <div className="h-[460px] w-full flex items-center justify-center bg-surface-hover/30 rounded-2xl border border-dashed border-border-subtle">
      <div className="flex items-center gap-2 text-text-tertiary text-xs">
        <div className="w-4 h-4 border-2 border-accent-500 border-t-transparent rounded-full animate-spin" />
        <span>{t("createPage.loadingVisualEngine")}</span>
      </div>
    </div>
  );
}

// Dynamically import DAGCanvas to prevent SSR issues with ReactFlow
const DAGCanvas = dynamic(() => import("@/components/dag/DAGCanvas").then((mod) => mod.DAGCanvas), {
  ssr: false,
  loading: () => <CanvasLoading />,
});

import type { DagNodeDef, DagEdgeDef } from "../constants";
import { parseDagDefinition, normalizeNodeType } from "../constants";

import { TEMPLATES, type TemplateOption } from "./templates";

export default function CreatePlaybookPage() {
  const router = useRouter();
  const locale = useLocale();
  const t = useTranslations("playbooks");

  const localizeDagNodes = (rawNodes: DagNodeDef[]) => {
    if (locale !== "en") return rawNodes;
    return rawNodes.map((n) => {
      const match = n.name.match(/\((.*?)\)/);
      return {
        ...n,
        name: match ? match[1] : n.name,
      };
    });
  };

  const templates: TemplateOption[] = useMemo(() => {
    return TEMPLATES.map((tmpl) => {
      let key = "ipBlock";
      if (tmpl.id === "phishing-triage") key = "phishing";
      else if (tmpl.id === "endpoint-isolate") key = "endpoint";
      else if (tmpl.id === "custom-blank") key = "custom";
      return {
        ...tmpl,
        name: t(`createPage.templates.${key}.name` as any),
        description: t(`createPage.templates.${key}.description` as any),
        nodes: localizeDagNodes(tmpl.nodes),
      };
    });
  }, [t, locale]);

  // Form State
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>("ip-block");
  const [name, setName] = useState(() => t("createPage.defaultName"));
  const [version, setVersion] = useState("1.0.0");
  const [description, setDescription] = useState(() => t("createPage.defaultDesc"));
  const [isActive, setIsActive] = useState(true);

  // DAG State
  const [nodes, setNodes] = useState<DagNodeDef[]>(() => localizeDagNodes(TEMPLATES[0].nodes));
  const [edges, setEdges] = useState<DagEdgeDef[]>(TEMPLATES[0].edges);
  const [viewMode, setViewMode] = useState<"visual" | "json">("visual");
  const [jsonText, setJsonText] = useState(() =>
    JSON.stringify(
      { nodes: localizeDagNodes(TEMPLATES[0].nodes), edges: TEMPLATES[0].edges },
      null,
      2
    )
  );
  const [jsonError, setJsonError] = useState<string | null>(null);

  // Submission State
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(
    null
  );

  // Handle Template Selection
  const handleSelectTemplate = (template: TemplateOption) => {
    setSelectedTemplateId(template.id);
    setName(template.name);
    setDescription(template.description);
    setNodes(template.nodes);
    setEdges(template.edges);
    setJsonText(JSON.stringify({ nodes: template.nodes, edges: template.edges }, null, 2));
    setJsonError(null);
  };

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

  // Submit Handler
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setFeedback({ type: "error", message: t("createPage.nameRequired") });
      return;
    }

    if (nodes.length === 0) {
      setFeedback({ type: "error", message: t("createPage.nodesRequired") });
      return;
    }

    // Validate that all edge sources and targets exist
    const nodeIds = new Set(nodes.map((n) => n.id));
    const invalidEdge = edges.find((e) => !nodeIds.has(e.source) || !nodeIds.has(e.target));
    if (invalidEdge) {
      setFeedback({
        type: "error",
        message: t("createPage.invalidEdge", {
          source: invalidEdge.source,
          target: invalidEdge.target,
        }),
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
      definition_json: {
        nodes,
        edges,
      },
    };

    try {
      let res = await authFetch("/api/v1/playbook-definitions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      // Fallback to legacy endpoint if v1 prefix returned 404
      if (!res.ok && res.status === 404) {
        res = await authFetch("/api/playbook-definitions", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
      }

      if (res.ok) {
        setFeedback({
          type: "success",
          message: t("createPage.publishSuccess"),
        });
        setTimeout(() => {
          router.push("/playbooks/definitions");
        }, 1200);
      } else {
        let errMsg = t("createPage.publishFailed");
        try {
          const errData = await res.json();
          if (errData?.detail) {
            if (Array.isArray(errData.detail)) {
              errMsg = errData.detail
                .map((d: any) => (typeof d === "string" ? d : d.msg || JSON.stringify(d)))
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
    } catch (err) {
      console.error("API request error:", err);
      setFeedback({
        type: "error",
        message: t("createPage.networkError"),
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-surface-page transition-colors pb-16">
      {/* Header */}
      <PageHeader
        title={t("createPage.title")}
        subtitle={t("createPage.subtitle")}
        actions={
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => router.push("/playbooks/definitions")}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg border border-border-default bg-surface-card hover:bg-surface-hover text-text-secondary text-sm font-medium transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>{t("createPage.backToList")}</span>
            </button>
            <button
              type="button"
              onClick={handleSubmit}
              disabled={submitting}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-accent-600 hover:bg-accent-700 text-white text-sm font-medium shadow-subtle transition-all disabled:opacity-50"
            >
              <Save className="w-3.5 h-3.5" />
              <span>
                {submitting ? t("createPage.publishing") : t("createPage.publishPlaybook")}
              </span>
            </button>
          </div>
        }
      />

      <main className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 pt-6 space-y-6">
        {/* Feedback Alert */}
        {feedback && (
          <div
            className={`p-4 rounded-xl border flex items-center gap-3 animate-fade-in ${
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
            <span className="text-sm font-medium">{feedback.message}</span>
          </div>
        )}

        {/* Section 1: Template Selection Cards */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-sm font-semibold text-text-primary">
                {t("createPage.chooseTemplate")}
              </h2>
              <p className="text-xs text-text-muted mt-0.5">{t("createPage.chooseTemplateDesc")}</p>
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {templates.map((tmpl) => {
              const isSelected = selectedTemplateId === tmpl.id;
              const IconComp = tmpl.icon;
              return (
                <button
                  key={tmpl.id}
                  type="button"
                  onClick={() => handleSelectTemplate(tmpl)}
                  className={`p-4 rounded-xl border text-left transition-all duration-200 flex flex-col justify-between group ${
                    isSelected
                      ? "bg-accent-50/70 dark:bg-accent-950/40 border-accent-500/40 shadow-subtle ring-1 ring-accent-500/30"
                      : "bg-surface-card border-border-subtle hover:bg-surface-hover hover:border-border-default"
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <div
                        className={`w-8 h-8 rounded-lg flex items-center justify-center transition-colors ${
                          isSelected
                            ? "bg-accent-600 text-white"
                            : "bg-surface-hover text-text-secondary group-hover:text-accent-600"
                        }`}
                      >
                        <IconComp className="w-4 h-4" />
                      </div>
                      {isSelected && (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-accent-500/15 text-accent-700 dark:text-accent-300">
                          {t("createPage.selected")}
                        </span>
                      )}
                    </div>
                    <h3 className="text-sm font-semibold text-text-primary mb-1">{tmpl.name}</h3>
                    <p className="text-xs text-text-secondary line-clamp-2 leading-relaxed">
                      {tmpl.description}
                    </p>
                  </div>
                  <div className="mt-3 pt-2 border-t border-border-subtle/50 flex items-center justify-between text-[11px] text-text-secondary font-mono">
                    <span>{t("createPage.nodesCount", { count: tmpl.nodes.length })}</span>
                    <span>{t("createPage.edgesCount", { count: tmpl.edges.length })}</span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Section 2: Metadata Form & Flow Canvas */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Metadata Config */}
          <div className="bg-surface-card border border-border-subtle rounded-xl p-5 shadow-subtle space-y-4">
            <div className="flex items-center gap-2 pb-3 border-b border-border-subtle">
              <Info className="w-4 h-4 text-accent-600 dark:text-accent-400" />
              <h3 className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                {t("edit.basicConfig")}
              </h3>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-secondary mb-1.5">
                {t("edit.name")} <span className="text-danger-700 dark:text-danger-400">*</span>
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder={t("edit.namePlaceholder")}
                required
                className="w-full px-3.5 py-2 text-sm rounded-lg border border-border-default bg-surface-input text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent-500/20 focus:border-accent-600 transition-colors"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-1.5">
                  {t("edit.version")}
                </label>
                <input
                  type="text"
                  value={version}
                  onChange={(e) => setVersion(e.target.value)}
                  placeholder="1.0.0"
                  className="w-full px-3.5 py-2 text-sm font-mono rounded-lg border border-border-default bg-surface-input text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent-500/20 focus:border-accent-600 transition-colors"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-text-secondary mb-1.5">
                  {t("edit.isActive")}
                </label>
                <button
                  type="button"
                  onClick={() => setIsActive(!isActive)}
                  className={`w-full py-2 px-3 rounded-lg border text-sm font-medium flex items-center justify-center gap-2 transition-colors ${
                    isActive
                      ? "bg-success-500/15 border-success-500/30 text-success-700 dark:text-success-400"
                      : "bg-surface-hover border-border-subtle text-text-secondary"
                  }`}
                >
                  <div
                    className={`w-2 h-2 rounded-full ${
                      isActive ? "bg-success-500 animate-pulse" : "bg-text-tertiary"
                    }`}
                  />
                  <span>{isActive ? t("edit.activeLabel") : t("edit.draftLabel")}</span>
                </button>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-secondary mb-1.5">
                {t("edit.description")}
              </label>
              <textarea
                rows={4}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder={t("edit.descriptionPlaceholder")}
                className="w-full px-3.5 py-2 text-sm rounded-lg border border-border-default bg-surface-input text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent-500/20 focus:border-accent-600 transition-colors resize-none"
              />
            </div>

            {/* Step Summary */}
            <div className="pt-2 border-t border-border-subtle">
              <h4 className="text-[11px] font-semibold text-text-muted uppercase tracking-wider mb-2">
                {t("edit.stepSummary", { count: nodes.length })}
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

          {/* Flow Preview & Editor */}
          <div className="lg:col-span-2 bg-surface-card border border-border-subtle rounded-xl p-5 shadow-subtle flex flex-col justify-between">
            <div className="flex items-center justify-between pb-3 border-b border-border-subtle mb-4">
              <div className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-accent-600 dark:text-accent-400" />
                <h3 className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                  {t("edit.dagTitle")}
                </h3>
              </div>
              {/*
               * 分段控件：轨道用 bg-surface-hover，激活项是白色浮起的 pill。
               * 未激活文字必须用 secondary —— tertiary 落在 surface-hover 上
               * 浅色只有 4.34:1（低于 AA），正是 check-contrast.mjs 按根因登记的
               * 弱文本层级放在 hover/active 背景上那一类。
               * 两个按钮的圆角也要一致（原为 rounded-md / rounded-lg 混用）。
               */}
              <div className="flex items-center gap-1 p-0.5 rounded-lg bg-surface-hover border border-border-subtle text-xs">
                <button
                  type="button"
                  onClick={() => setViewMode("visual")}
                  className={`flex items-center gap-1 px-2.5 py-1 rounded-md transition-colors font-medium ${
                    viewMode === "visual"
                      ? "bg-surface-card text-text-primary shadow-subtle"
                      : "text-text-secondary hover:text-text-primary"
                  }`}
                >
                  <Play className="w-3 h-3" />
                  <span>{t("edit.canvasView")}</span>
                </button>
                <button
                  type="button"
                  onClick={() => setViewMode("json")}
                  className={`flex items-center gap-1 px-2.5 py-1 rounded-md transition-colors font-medium ${
                    viewMode === "json"
                      ? "bg-surface-card text-text-primary shadow-subtle"
                      : "text-text-secondary hover:text-text-primary"
                  }`}
                >
                  <Code2 className="w-3 h-3" />
                  <span>{t("edit.jsonView")}</span>
                </button>
              </div>
            </div>

            {/* Canvas / JSON Area */}
            <div className="flex-1 min-h-[460px] rounded-xl overflow-hidden border border-border-subtle bg-surface-page relative">
              {viewMode === "visual" ? (
                <DAGCanvas
                  definition={dagDefinition}
                  readonly={false}
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
              <span>
                {t("createPage.totalNodesAndEdges", { nodes: nodes.length, edges: edges.length })}
              </span>
              <span>{t("createPage.canvasHint")}</span>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
