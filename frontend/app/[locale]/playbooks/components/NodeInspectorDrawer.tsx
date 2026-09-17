"use client";

import React, { useState, useEffect, useMemo } from "react";
import { useLocale } from "next-intl";
import {
  X,
  Trash2,
  Copy,
  Check,
  Shield,
  GitBranch,
  Send,
  Globe,
  UserCheck,
  FileText,
  Database,
  Clock,
  Code2,
  ChevronDown,
  ChevronUp,
  Sliders,
  Sparkles,
} from "lucide-react";
import type { DagNodeDef } from "../constants";
import { ACTION_TYPE_META, normalizeNodeType } from "../constants";

interface NodeInspectorDrawerProps {
  node: DagNodeDef | null;
  isOpen: boolean;
  onClose: () => void;
  onUpdateNode: (updated: DagNodeDef) => void;
  onDeleteNode: (nodeId: string) => void;
  onDuplicateNode: (nodeId: string) => void;
}

const CATEGORY_ICONS: Record<string, React.ElementType> = {
  intel: Shield,
  decision: GitBranch,
  action: Globe,
  data: Database,
};

export function NodeInspectorDrawer({
  node,
  isOpen,
  onClose,
  onUpdateNode,
  onDeleteNode,
  onDuplicateNode,
}: NodeInspectorDrawerProps) {
  const locale = useLocale();
  const isZh = locale !== "en";

  // Form State
  const [name, setName] = useState("");
  const [stepId, setStepId] = useState("");
  const [type, setType] = useState("parse_json");
  const [inputs, setInputs] = useState<Record<string, unknown>>({});
  const [showAdvancedJson, setShowAdvancedJson] = useState(false);
  const [rawJsonText, setRawJsonText] = useState("");
  const [jsonError, setJsonError] = useState<string | null>(null);

  // Sync internal form state when selected node changes
  useEffect(() => {
    if (!node) return;
    setName(node.name || "");
    setStepId(node.step_id || node.id);
    const normalizedType = normalizeNodeType(node.type || node.action);
    setType(normalizedType);

    const mergedInputs = {
      ...(ACTION_TYPE_META[normalizedType]?.defaultInputs || {}),
      ...(node.inputs || {}),
      ...(((node as unknown as Record<string, unknown>).config as Record<string, unknown>) || {}),
    };
    setInputs(mergedInputs);
    setRawJsonText(JSON.stringify(mergedInputs, null, 2));
    setJsonError(null);
  }, [node]);

  const currentMeta = useMemo(() => ACTION_TYPE_META[type] || ACTION_TYPE_META.parse_json, [type]);
  const CategoryIcon = CATEGORY_ICONS[currentMeta.category] || Sliders;

  if (!isOpen || !node) return null;

  // Handle field change and propagate update
  const handleFieldChange = (key: string, value: unknown) => {
    const updatedInputs = { ...inputs, [key]: value };
    setInputs(updatedInputs);
    setRawJsonText(JSON.stringify(updatedInputs, null, 2));
    onUpdateNode({
      ...node,
      name,
      step_id: stepId,
      type,
      inputs: updatedInputs,
      config: updatedInputs,
    });
  };

  // Handle Type Change
  const handleTypeChange = (newType: string) => {
    setType(newType);
    const defaults = ACTION_TYPE_META[newType]?.defaultInputs || {};
    const updatedInputs = { ...defaults, ...inputs };
    setInputs(updatedInputs);
    setRawJsonText(JSON.stringify(updatedInputs, null, 2));
    onUpdateNode({
      ...node,
      name,
      step_id: stepId,
      type: newType,
      inputs: updatedInputs,
      config: updatedInputs,
    });
  };

  // Handle Name Change
  const handleNameChange = (newName: string) => {
    setName(newName);
    onUpdateNode({
      ...node,
      name: newName,
      step_id: stepId,
      type,
      inputs,
      config: inputs,
    });
  };

  // Handle Raw JSON Change
  const handleRawJsonChange = (text: string) => {
    setRawJsonText(text);
    try {
      const parsed = JSON.parse(text);
      if (typeof parsed === "object" && parsed !== null) {
        setInputs(parsed as Record<string, unknown>);
        setJsonError(null);
        onUpdateNode({
          ...node,
          name,
          step_id: stepId,
          type,
          inputs: parsed as Record<string, unknown>,
          config: parsed as Record<string, unknown>,
        });
      }
    } catch (e) {
      setJsonError((e as Error).message);
    }
  };

  return (
    <aside
      role="region"
      aria-label={isZh ? "节点属性配置" : "Step Configuration"}
      className="absolute right-0 top-0 bottom-0 w-80 sm:w-96 bg-surface-card border-l border-border-subtle shadow-2xl z-30 flex flex-col animate-fade-in"
    >
      {/* Header */}
      <div className="px-4 py-3.5 border-b border-border-subtle flex items-center justify-between bg-surface-ground/60">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-7 h-7 rounded-lg bg-accent-500/15 text-accent-700 dark:text-accent-300 flex items-center justify-center shrink-0">
            <CategoryIcon className="w-4 h-4" />
          </div>
          <div className="min-w-0">
            <h3 className="text-xs font-semibold text-text-primary truncate">
              {isZh ? "步骤属性配置" : "Step Configuration"}
            </h3>
            <span className="text-[10px] text-text-tertiary font-mono truncate block">
              {stepId}
            </span>
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="p-1.5 rounded-lg text-text-tertiary hover:text-text-primary hover:bg-surface-hover transition-colors"
          title={isZh ? "关闭" : "Close"}
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Scrollable Form Body */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
        {/* Step Name */}
        <div>
          <label className="block text-[11px] font-medium text-text-secondary mb-1">
            {isZh ? "步骤名称" : "Step Name"} <span className="text-danger-500">*</span>
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => handleNameChange(e.target.value)}
            className="w-full px-3 py-1.5 rounded-xl border border-border-default bg-surface-ground text-text-primary focus:outline-none focus:ring-1 focus:ring-accent-500"
            placeholder={isZh ? "例如: 防火墙下发封禁" : "e.g. Block IP via Firewall"}
          />
        </div>

        {/* Step ID */}
        <div>
          <label className="block text-[11px] font-medium text-text-secondary mb-1">
            {isZh ? "步骤标识 (Step ID)" : "Step ID"}
          </label>
          <input
            type="text"
            value={stepId}
            readOnly
            className="w-full px-3 py-1.5 font-mono text-[11px] rounded-xl border border-border-subtle bg-surface-hover/50 text-text-tertiary cursor-not-allowed"
          />
        </div>

        {/* Action Type Selector */}
        <div>
          <label className="block text-[11px] font-medium text-text-secondary mb-1">
            {isZh ? "动作类型 (Action Type)" : "Action Type"}
          </label>
          <select
            value={type}
            onChange={(e) => handleTypeChange(e.target.value)}
            className="w-full px-3 py-1.5 rounded-xl border border-border-default bg-surface-ground text-text-primary focus:outline-none focus:ring-1 focus:ring-accent-500"
          >
            <optgroup label={isZh ? "威胁情报 (Intel)" : "Threat Intel"}>
              <option value="extract_iocs">
                {isZh ? "提取 IOC 实体 (extract_iocs)" : "Extract IOCs"}
              </option>
              <option value="ti_lookup_otx">
                {isZh ? "OTX 威胁情报比对 (ti_lookup_otx)" : "OTX TI Lookup"}
              </option>
              <option value="asset_enrich">
                {isZh ? "资产信誉富化 (asset_enrich)" : "Asset Enrichment"}
              </option>
            </optgroup>
            <optgroup label={isZh ? "控制分支 (Control Flow)" : "Control Flow"}>
              <option value="decision">
                {isZh ? "条件分支决策 (decision)" : "Decision Branch"}
              </option>
              <option value="human_approval">
                {isZh ? "人工复核审批 (human_approval)" : "Human Approval"}
              </option>
              <option value="sleep">{isZh ? "延时等待 (sleep)" : "Delay / Sleep"}</option>
            </optgroup>
            <optgroup label={isZh ? "响应动作 (Actions)" : "Actions"}>
              <option value="http_request">
                {isZh ? "执行 HTTP / API 请求 (http_request)" : "HTTP Request"}
              </option>
              <option value="slack_notify">
                {isZh ? "即时协同通知 (slack_notify)" : "Alert Notification"}
              </option>
              <option value="generate_report">
                {isZh ? "生成处置报告 (generate_report)" : "Generate Report"}
              </option>
            </optgroup>
            <optgroup label={isZh ? "数据解析 (Data)" : "Data"}>
              <option value="parse_json">
                {isZh ? "结构化数据解析 (parse_json)" : "Parse JSON"}
              </option>
            </optgroup>
          </select>
          <p className="mt-1 text-[10px] text-text-tertiary leading-normal">
            {isZh ? currentMeta.descriptionZh : currentMeta.descriptionEn}
          </p>
        </div>

        {/* Dynamic Type-Specific Fields */}
        <div className="pt-3 border-t border-border-subtle space-y-3">
          <div className="flex items-center gap-1.5 text-text-secondary font-medium text-[11px]">
            <Sliders className="w-3.5 h-3.5 text-accent-600 dark:text-accent-400" />
            <span>{isZh ? "动作参数配置" : "Action Parameters"}</span>
          </div>

          {/* 1. HTTP Request */}
          {type === "http_request" && (
            <div className="space-y-2.5">
              <div>
                <label className="block text-[10px] text-text-tertiary mb-1">
                  {isZh ? "请求方法 (Method)" : "HTTP Method"}
                </label>
                <div className="grid grid-cols-4 gap-1">
                  {["GET", "POST", "PUT", "DELETE"].map((m) => {
                    const currentMethod = String(inputs.method || "POST").toUpperCase();
                    const isSelected = currentMethod === m;
                    return (
                      <button
                        key={m}
                        type="button"
                        onClick={() => handleFieldChange("method", m)}
                        className={`py-1 rounded-lg font-mono text-[10px] font-semibold border transition-all ${
                          isSelected
                            ? "bg-accent-600 text-white border-accent-600 shadow-xs"
                            : "bg-surface-ground border-border-subtle text-text-tertiary hover:text-text-primary"
                        }`}
                      >
                        {m}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div>
                <label className="block text-[10px] text-text-tertiary mb-1">
                  {isZh ? "请求 URL" : "Endpoint URL"}
                </label>
                <input
                  type="text"
                  value={String(inputs.url || "")}
                  onChange={(e) => handleFieldChange("url", e.target.value)}
                  placeholder="https://api.internal/v1/blacklist"
                  className="w-full px-2.5 py-1.5 font-mono text-[11px] rounded-xl border border-border-default bg-surface-ground text-text-primary focus:outline-none focus:ring-1 focus:ring-accent-500"
                />
              </div>

              <div>
                <label className="block text-[10px] text-text-tertiary mb-1">
                  {isZh ? "超时限制 (秒)" : "Timeout (Seconds)"}
                </label>
                <input
                  type="number"
                  value={Number(inputs.timeout ?? 10)}
                  onChange={(e) => handleFieldChange("timeout", Number(e.target.value))}
                  min={1}
                  max={120}
                  className="w-full px-2.5 py-1.5 font-mono text-[11px] rounded-xl border border-border-default bg-surface-ground text-text-primary focus:outline-none focus:ring-1 focus:ring-accent-500"
                />
              </div>
            </div>
          )}

          {/* 2. Decision Branch */}
          {type === "decision" && (
            <div className="space-y-2.5">
              <div>
                <label className="block text-[10px] text-text-tertiary mb-1">
                  {isZh ? "判定表达式 (Condition Expression)" : "Condition Expression"}
                </label>
                <input
                  type="text"
                  value={String(inputs.expression || "")}
                  onChange={(e) => handleFieldChange("expression", e.target.value)}
                  placeholder="$.output.ti.malicious_count >= 2"
                  className="w-full px-2.5 py-1.5 font-mono text-[11px] rounded-xl border border-border-default bg-surface-ground text-text-primary focus:outline-none focus:ring-1 focus:ring-accent-500"
                />
              </div>

              <div>
                <span className="block text-[10px] text-text-tertiary mb-1">
                  {isZh ? "快速表达式预设" : "Quick Snippets"}
                </span>
                <div className="space-y-1">
                  {[
                    "$.output.ti.malicious_count >= 2",
                    "$.output.abuse.confidence >= 80",
                    "$.output.is_malicious == true",
                  ].map((snippet) => (
                    <button
                      key={snippet}
                      type="button"
                      onClick={() => handleFieldChange("expression", snippet)}
                      className="w-full text-left px-2 py-1 rounded-lg bg-surface-hover/80 hover:bg-surface-hover font-mono text-[10px] text-accent-700 dark:text-accent-300 truncate transition-colors flex items-center gap-1.5"
                    >
                      <Sparkles className="w-3 h-3 shrink-0 opacity-70" />
                      <span className="truncate">{snippet}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* 3. Extract IOCs */}
          {type === "extract_iocs" && (
            <div className="space-y-2.5">
              <div>
                <label className="block text-[10px] text-text-tertiary mb-1">
                  {isZh ? "告警输入源字段" : "Source Field"}
                </label>
                <input
                  type="text"
                  value={String(inputs.source_field || "$.input.alert_body")}
                  onChange={(e) => handleFieldChange("source_field", e.target.value)}
                  placeholder="$.input.alert_body"
                  className="w-full px-2.5 py-1.5 font-mono text-[11px] rounded-xl border border-border-default bg-surface-ground text-text-primary focus:outline-none focus:ring-1 focus:ring-accent-500"
                />
              </div>

              <div>
                <label className="block text-[10px] text-text-tertiary mb-1">
                  {isZh ? "识别实体类型" : "Entity Types"}
                </label>
                <div className="grid grid-cols-2 gap-1.5">
                  {["ip", "domain", "url", "email", "cve", "hash"].map((ioc) => {
                    const currentTypes = Array.isArray(inputs.ioc_types)
                      ? (inputs.ioc_types as string[])
                      : ["ip", "domain", "url"];
                    const isChecked = currentTypes.includes(ioc);
                    return (
                      <label
                        key={ioc}
                        className="flex items-center gap-2 p-1.5 rounded-lg bg-surface-ground border border-border-subtle cursor-pointer hover:bg-surface-hover text-[11px]"
                      >
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={(e) => {
                            const next = e.target.checked
                              ? [...currentTypes, ioc]
                              : currentTypes.filter((t) => t !== ioc);
                            handleFieldChange("ioc_types", next);
                          }}
                          className="rounded text-accent-600 focus:ring-accent-500"
                        />
                        <span className="font-mono text-text-secondary">{ioc.toUpperCase()}</span>
                      </label>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {/* 4. OTX TI Lookup */}
          {type === "ti_lookup_otx" && (
            <div className="space-y-2.5">
              <div>
                <label className="block text-[10px] text-text-tertiary mb-1">
                  {isZh ? "脉冲威胁有效天数 (Expiration Days)" : "Pulse Expiration Days"}
                </label>
                <input
                  type="number"
                  value={Number(inputs.pulse_expiration_days ?? 180)}
                  onChange={(e) =>
                    handleFieldChange("pulse_expiration_days", Number(e.target.value))
                  }
                  min={1}
                  max={365}
                  className="w-full px-2.5 py-1.5 font-mono text-[11px] rounded-xl border border-border-default bg-surface-ground text-text-primary focus:outline-none focus:ring-1 focus:ring-accent-500"
                />
              </div>

              <div>
                <label className="block text-[10px] text-text-tertiary mb-1">
                  {isZh ? "判定威胁置信度下限 (Min Confidence)" : "Minimum Confidence Threshold"}
                </label>
                <input
                  type="number"
                  value={Number(inputs.min_confidence ?? 75)}
                  onChange={(e) => handleFieldChange("min_confidence", Number(e.target.value))}
                  min={0}
                  max={100}
                  className="w-full px-2.5 py-1.5 font-mono text-[11px] rounded-xl border border-border-default bg-surface-ground text-text-primary focus:outline-none focus:ring-1 focus:ring-accent-500"
                />
              </div>
            </div>
          )}

          {/* 5. Slack / Alert Notify */}
          {type === "slack_notify" && (
            <div className="space-y-2.5">
              <div>
                <label className="block text-[10px] text-text-tertiary mb-1">
                  {isZh ? "Webhook 环境变量 / URL" : "Webhook URL or Env Variable"}
                </label>
                <input
                  type="text"
                  value={String(inputs.webhook_url_env || "SLACK_SOC_WEBHOOK")}
                  onChange={(e) => handleFieldChange("webhook_url_env", e.target.value)}
                  placeholder="SLACK_SOC_WEBHOOK"
                  className="w-full px-2.5 py-1.5 font-mono text-[11px] rounded-xl border border-border-default bg-surface-ground text-text-primary focus:outline-none focus:ring-1 focus:ring-accent-500"
                />
              </div>

              <div>
                <label className="block text-[10px] text-text-tertiary mb-1">
                  {isZh ? "通知消息模板" : "Message Template"}
                </label>
                <textarea
                  rows={3}
                  value={String(inputs.message || "")}
                  onChange={(e) => handleFieldChange("message", e.target.value)}
                  placeholder="告警已阻断: {{$.output.blocked}}"
                  className="w-full px-2.5 py-1.5 text-[11px] rounded-xl border border-border-default bg-surface-ground text-text-primary focus:outline-none focus:ring-1 focus:ring-accent-500 resize-none font-mono"
                />
              </div>
            </div>
          )}

          {/* 6. Human Approval */}
          {type === "human_approval" && (
            <div className="space-y-2.5">
              <div>
                <label className="block text-[10px] text-text-tertiary mb-1">
                  {isZh ? "审批人用户名 (逗号分隔)" : "Approver Usernames (Comma separated)"}
                </label>
                <input
                  type="text"
                  value={
                    Array.isArray(inputs.approvers)
                      ? (inputs.approvers as string[]).join(", ")
                      : String(inputs.approvers || "admin")
                  }
                  onChange={(e) =>
                    handleFieldChange(
                      "approvers",
                      e.target.value
                        .split(",")
                        .map((s) => s.trim())
                        .filter(Boolean)
                    )
                  }
                  placeholder="admin, sec-duty"
                  className="w-full px-2.5 py-1.5 font-mono text-[11px] rounded-xl border border-border-default bg-surface-ground text-text-primary focus:outline-none focus:ring-1 focus:ring-accent-500"
                />
              </div>

              <div>
                <label className="block text-[10px] text-text-tertiary mb-1">
                  {isZh ? "审批超时限制 (分钟)" : "Timeout (Minutes)"}
                </label>
                <input
                  type="number"
                  value={Number(inputs.timeout_minutes ?? 30)}
                  onChange={(e) => handleFieldChange("timeout_minutes", Number(e.target.value))}
                  min={1}
                  max={1440}
                  className="w-full px-2.5 py-1.5 font-mono text-[11px] rounded-xl border border-border-default bg-surface-ground text-text-primary focus:outline-none focus:ring-1 focus:ring-accent-500"
                />
              </div>
            </div>
          )}

          {/* 7. Sleep */}
          {type === "sleep" && (
            <div>
              <label className="block text-[10px] text-text-tertiary mb-1">
                {isZh ? "等待延迟 (秒)" : "Delay Duration (Seconds)"}
              </label>
              <input
                type="number"
                value={Number(inputs.seconds ?? 10)}
                onChange={(e) => handleFieldChange("seconds", Number(e.target.value))}
                min={1}
                max={3600}
                className="w-full px-2.5 py-1.5 font-mono text-[11px] rounded-xl border border-border-default bg-surface-ground text-text-primary focus:outline-none focus:ring-1 focus:ring-accent-500"
              />
            </div>
          )}
        </div>

        {/* Advanced JSON Accordion */}
        <div className="pt-2 border-t border-border-subtle">
          <button
            type="button"
            onClick={() => setShowAdvancedJson(!showAdvancedJson)}
            className="w-full flex items-center justify-between text-text-tertiary hover:text-text-secondary py-1 text-[11px] font-medium"
          >
            <div className="flex items-center gap-1.5">
              <Code2 className="w-3.5 h-3.5" />
              <span>{isZh ? "高级 JSON 参数配置" : "Raw JSON Config"}</span>
            </div>
            {showAdvancedJson ? (
              <ChevronUp className="w-3.5 h-3.5" />
            ) : (
              <ChevronDown className="w-3.5 h-3.5" />
            )}
          </button>

          {showAdvancedJson && (
            <div className="mt-2 space-y-1.5">
              {jsonError && (
                <div className="p-2 rounded-lg bg-danger-500/10 border border-danger-500/30 text-danger-700 dark:text-danger-300 font-mono text-[10px]">
                  {jsonError}
                </div>
              )}
              <textarea
                rows={5}
                value={rawJsonText}
                onChange={(e) => handleRawJsonChange(e.target.value)}
                spellCheck={false}
                className="w-full p-2.5 font-mono text-[10px] bg-surface-ground rounded-xl border border-border-subtle text-text-primary focus:outline-none focus:ring-1 focus:ring-accent-500 resize-none"
              />
            </div>
          )}
        </div>
      </div>

      {/* Footer Actions */}
      <div className="p-3 border-t border-border-subtle bg-surface-ground/50 flex items-center justify-between gap-2">
        <button
          type="button"
          onClick={() => onDeleteNode(node.id)}
          className="inline-flex items-center gap-1 px-3 py-1.5 rounded-xl border border-danger-500/30 bg-danger-500/10 text-danger-700 dark:text-danger-400 hover:bg-danger-500/20 text-xs font-medium transition-colors"
          title={isZh ? "删除节点" : "Delete Step"}
        >
          <Trash2 className="w-3.5 h-3.5" />
          <span>{isZh ? "删除" : "Delete"}</span>
        </button>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => onDuplicateNode(node.id)}
            className="inline-flex items-center gap-1 px-3 py-1.5 rounded-xl border border-border-subtle bg-surface-card hover:bg-surface-hover text-text-secondary text-xs font-medium transition-colors"
            title={isZh ? "克隆节点" : "Duplicate Step"}
          >
            <Copy className="w-3.5 h-3.5" />
            <span>{isZh ? "克隆" : "Clone"}</span>
          </button>
          <button
            type="button"
            onClick={onClose}
            className="inline-flex items-center gap-1 px-3.5 py-1.5 rounded-xl bg-accent-600 hover:bg-accent-700 text-white text-xs font-semibold shadow-xs transition-colors"
          >
            <Check className="w-3.5 h-3.5" />
            <span>{isZh ? "完成" : "Done"}</span>
          </button>
        </div>
      </div>
    </aside>
  );
}

export default NodeInspectorDrawer;
