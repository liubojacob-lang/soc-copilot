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
  ShieldAlert,
  MailWarning,
  Laptop,
  Sparkles,
  Info,
} from "lucide-react";

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

import type { DagNodeDef, DagEdgeDef } from "../constants";
import { parseDagDefinition, normalizeNodeType } from "../constants";

interface TemplateOption {
  id: string;
  name: string;
  description: string;
  icon: typeof ShieldAlert;
  nodes: DagNodeDef[];
  edges: DagEdgeDef[];
}

const TEMPLATES: TemplateOption[] = [
  {
    id: "ip-block",
    name: "恶意 IP 自动封禁",
    description: "检测高危外联告警，经威胁情报研判后自动在防火墙下发阻断规则并通知值班员",
    icon: ShieldAlert,
    nodes: [
      {
        id: "node-1",
        type: "parse_json",
        step_id: "alert_ingest",
        name: "告警数据解析 (Parse Alert)",
        position_x: 60,
        position_y: 160,
      },
      {
        id: "node-2",
        type: "ti_lookup_otx",
        step_id: "enrich_ti",
        name: "威胁情报研判 (TI Lookup)",
        position_x: 320,
        position_y: 160,
      },
      {
        id: "node-3",
        type: "decision",
        step_id: "firewall_decision",
        name: "高危判定决策 (Severity Decision)",
        position_x: 580,
        position_y: 160,
      },
      {
        id: "node-4",
        type: "http_request",
        step_id: "firewall_block",
        name: "防火墙下发封禁 (Block IP via API)",
        position_x: 840,
        position_y: 80,
      },
      {
        id: "node-5",
        type: "slack_notify",
        step_id: "analyst_notify",
        name: "协同告警通知 (Slack / Email)",
        position_x: 840,
        position_y: 240,
      },
    ],
    edges: [
      { source: "node-1", target: "node-2" },
      { source: "node-2", target: "node-3" },
      { source: "node-3", target: "node-4", condition: "threat_score >= 80" },
      { source: "node-4", target: "node-5" },
    ],
  },
  {
    id: "phishing-remediation",
    name: "钓鱼邮件快速处置",
    description: "提取邮件正文与附件 IOC，自动化沙箱引申检测，若发现恶意则全网隔离并重置凭证",
    icon: MailWarning,
    nodes: [
      {
        id: "node-1",
        type: "parse_json",
        step_id: "mail_alert",
        name: "邮件告警接入解析 (Parse Email)",
        position_x: 60,
        position_y: 160,
      },
      {
        id: "node-2",
        type: "extract_iocs",
        step_id: "extract_iocs",
        name: "提取附件与链接 (Extract IOCs)",
        position_x: 320,
        position_y: 160,
      },
      {
        id: "node-3",
        type: "ti_lookup_otx",
        step_id: "sandbox_scan",
        name: "IOC 沙箱威胁分析 (TI Lookup)",
        position_x: 580,
        position_y: 160,
      },
      {
        id: "node-4",
        type: "decision",
        step_id: "verdict_eval",
        name: "恶意邮件研判决策 (Decision)",
        position_x: 840,
        position_y: 160,
      },
      {
        id: "node-5",
        type: "http_request",
        step_id: "purge_mailbox",
        name: "全网邮件撤回与封禁 (Purge Mailbox)",
        position_x: 1100,
        position_y: 80,
      },
      {
        id: "node-6",
        type: "generate_report",
        step_id: "gen_report",
        name: "生成处置复盘报告 (Generate Report)",
        position_x: 1100,
        position_y: 240,
      },
    ],
    edges: [
      { source: "node-1", target: "node-2" },
      { source: "node-2", target: "node-3" },
      { source: "node-3", target: "node-4" },
      { source: "node-4", target: "node-5", condition: "is_malicious == true" },
      { source: "node-5", target: "node-6" },
    ],
  },
  {
    id: "endpoint-containment",
    name: "终端进程应急隔离",
    description: "EDR 捕获异常进程提权，溯源进程链，经审批节点后执行终端逻辑隔离与进程查杀",
    icon: Laptop,
    nodes: [
      {
        id: "node-1",
        type: "parse_json",
        step_id: "edr_alert",
        name: "EDR 异常注入告警 (EDR Alert)",
        position_x: 60,
        position_y: 160,
      },
      {
        id: "node-2",
        type: "timeline_build",
        step_id: "timeline_query",
        name: "溯源进程树时间线 (Timeline Build)",
        position_x: 320,
        position_y: 160,
      },
      {
        id: "node-3",
        type: "risk_score",
        step_id: "risk_eval",
        name: "危害等级风险评分 (Risk Score)",
        position_x: 580,
        position_y: 160,
      },
      {
        id: "node-4",
        type: "human_approval",
        step_id: "analyst_approval",
        name: "值班分析员人工审批 (Approval)",
        position_x: 840,
        position_y: 160,
      },
      {
        id: "node-5",
        type: "http_request",
        step_id: "isolate_host",
        name: "下发主机网络隔离 (Isolate API)",
        position_x: 1100,
        position_y: 160,
      },
    ],
    edges: [
      { source: "node-1", target: "node-2" },
      { source: "node-2", target: "node-3" },
      { source: "node-3", target: "node-4" },
      { source: "node-4", target: "node-5", condition: "approved == true" },
    ],
  },
  {
    id: "custom-blank",
    name: "自定义空白工作流",
    description: "从基础的三节点模板开始构建，自由编排输入输出、条件路由与处置动作",
    icon: Sparkles,
    nodes: [
      {
        id: "node-start",
        type: "parse_json",
        step_id: "start",
        name: "工作流输入解析 (Parse JSON)",
        position_x: 100,
        position_y: 160,
      },
      {
        id: "node-action",
        type: "decision",
        step_id: "decision",
        name: "规则研判决策 (Decision)",
        position_x: 420,
        position_y: 160,
      },
      {
        id: "node-end",
        type: "generate_report",
        step_id: "end",
        name: "响应归档报告 (Generate Report)",
        position_x: 740,
        position_y: 160,
      },
    ],
    edges: [
      { source: "node-start", target: "node-action" },
      { source: "node-action", target: "node-end" },
    ],
  },
];

export default function CreatePlaybookPage() {
  const router = useRouter();
  const locale = useLocale();
  const t = useTranslations("playbooks");

  // Form State
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>("ip-block");
  const [name, setName] = useState("自动化 IP 威胁封禁剧本");
  const [version, setVersion] = useState("1.0.0");
  const [description, setDescription] = useState(
    "检测高危外联告警，经威胁情报研判后自动在防火墙下发阻断规则并通知值班员"
  );
  const [isActive, setIsActive] = useState(true);

  // DAG State
  const [nodes, setNodes] = useState<DagNodeDef[]>(TEMPLATES[0].nodes);
  const [edges, setEdges] = useState<DagEdgeDef[]>(TEMPLATES[0].edges);
  const [viewMode, setViewMode] = useState<"visual" | "json">("visual");
  const [jsonText, setJsonText] = useState(() =>
    JSON.stringify({ nodes: TEMPLATES[0].nodes, edges: TEMPLATES[0].edges }, null, 2)
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
      setFeedback({ type: "error", message: "请输入剧本名称" });
      return;
    }

    if (nodes.length === 0) {
      setFeedback({ type: "error", message: "剧本流程必须包含至少一个节点" });
      return;
    }

    // Validate that all edge sources and targets exist
    const nodeIds = new Set(nodes.map((n) => n.id));
    const invalidEdge = edges.find((e) => !nodeIds.has(e.source) || !nodeIds.has(e.target));
    if (invalidEdge) {
      setFeedback({
        type: "error",
        message: `流程连线异常：节点 "${invalidEdge.source}" 或 "${invalidEdge.target}" 不存在于节点列表中`,
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
          message: "剧本定义发布成功！正在返回剧本工作区...",
        });
        setTimeout(() => {
          router.push("/playbooks?tab=definitions");
        }, 1200);
      } else {
        let errMsg = "提交剧本定义失败，请检查数据格式";
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
        message: "网络请求异常，请检查后端服务连接状态",
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-surface-canvas transition-colors pb-16">
      {/* Header */}
      <PageHeader
        title="新建安全剧本"
        subtitle="基于 DAG 流程图设计、编排与发布自动化安全处置流程"
        actions={
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => router.push("/playbooks?tab=definitions")}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-border-subtle bg-surface-card hover:bg-surface-hover text-text-secondary text-xs font-medium transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>返回列表</span>
            </button>
            <button
              type="button"
              onClick={handleSubmit}
              disabled={submitting}
              className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-xl bg-accent-600 hover:bg-accent-700 text-white text-xs font-semibold shadow-sm transition-all disabled:opacity-50"
            >
              <Save className="w-3.5 h-3.5" />
              <span>{submitting ? "正在保存..." : "发布剧本"}</span>
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

        {/* Section 1: Template Selection Cards */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-sm font-semibold text-text-primary">选择预置模板或空白起步</h2>
              <p className="text-xs text-text-tertiary">
                快速应用经安全验证的编排模版，支持在画布上二次微调
              </p>
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {TEMPLATES.map((tmpl) => {
              const isSelected = selectedTemplateId === tmpl.id;
              const IconComp = tmpl.icon;
              return (
                <button
                  key={tmpl.id}
                  type="button"
                  onClick={() => handleSelectTemplate(tmpl)}
                  className={`p-4 rounded-2xl border text-left transition-all duration-200 flex flex-col justify-between group ${
                    isSelected
                      ? "bg-accent-50/70 dark:bg-accent-950/40 border-accent-500/40 shadow-subtle ring-1 ring-accent-500/30"
                      : "bg-surface-card border-border-subtle hover:bg-surface-hover hover:border-border-default"
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <div
                        className={`w-8 h-8 rounded-xl flex items-center justify-center transition-colors ${
                          isSelected
                            ? "bg-accent-600 text-white"
                            : "bg-surface-hover text-text-secondary group-hover:text-accent-600"
                        }`}
                      >
                        <IconComp className="w-4 h-4" />
                      </div>
                      {isSelected && (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-accent-500/15 text-accent-700 dark:text-accent-300">
                          已选择
                        </span>
                      )}
                    </div>
                    <h3 className="text-xs font-semibold text-text-primary mb-1">{tmpl.name}</h3>
                    <p className="text-[11px] text-text-tertiary line-clamp-2 leading-relaxed">
                      {tmpl.description}
                    </p>
                  </div>
                  <div className="mt-3 pt-2 border-t border-border-subtle/50 flex items-center justify-between text-[10px] text-text-tertiary font-mono">
                    <span>{tmpl.nodes.length} 个节点</span>
                    <span>{tmpl.edges.length} 条边</span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Section 2: Metadata Form & Flow Canvas */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Metadata Config */}
          <div className="bg-surface-card border border-border-subtle rounded-2xl p-5 shadow-subtle space-y-4">
            <div className="flex items-center gap-2 pb-3 border-b border-border-subtle">
              <Info className="w-4 h-4 text-accent-600 dark:text-accent-400" />
              <h3 className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                基础配置
              </h3>
            </div>

            <div>
              <label className="block text-xs font-medium text-text-secondary mb-1.5">
                剧本名称 <span className="text-danger-500">*</span>
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="例如: 自动化 IP 封禁响应"
                required
                className="w-full px-3 py-2 text-xs rounded-xl border border-border-default bg-surface-card text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-500/20 focus:border-accent-600 transition-colors"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-text-secondary mb-1.5">
                  版本号
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
                  立即激活
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
                  <span>{isActive ? "已激活 (Active)" : "草稿 (Draft)"}</span>
                </button>
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-text-secondary mb-1.5">
                功能描述
              </label>
              <textarea
                rows={4}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="简明描述该剧本的触发条件、执行逻辑与应急响应目的..."
                className="w-full px-3 py-2 text-xs rounded-xl border border-border-default bg-surface-card text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-500/20 focus:border-accent-600 transition-colors resize-none"
              />
            </div>

            {/* Step Summary */}
            <div className="pt-2 border-t border-border-subtle">
              <h4 className="text-[11px] font-semibold text-text-tertiary uppercase tracking-wider mb-2">
                步骤概要清单 ({nodes.length})
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
          <div className="lg:col-span-2 bg-surface-card border border-border-subtle rounded-2xl p-5 shadow-subtle flex flex-col justify-between">
            <div className="flex items-center justify-between pb-3 border-b border-border-subtle mb-4">
              <div className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-accent-600 dark:text-accent-400" />
                <h3 className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                  DAG 流程拓扑可视化
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
                  <span>流程画布</span>
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
                  <span>JSON 源码</span>
                </button>
              </div>
            </div>

            {/* Canvas / JSON Area */}
            <div className="flex-1 min-h-[460px] rounded-xl overflow-hidden border border-border-subtle bg-surface-canvas/50 relative">
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
                共计 {nodes.length} 个执行节点，{edges.length} 条转换关系
              </span>
              <span>支持平移缩放、节点选中与链路排查</span>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
