"use client";

import React, { useState, useEffect } from "react";
import { useLocale } from "next-intl";
import { X, Trash2, Check, GitBranch, ArrowRight, Sparkles } from "lucide-react";
import type { DagEdgeDef, DagNodeDef } from "../constants";

interface EdgeInspectorDrawerProps {
  edge: DagEdgeDef | null;
  nodes: DagNodeDef[];
  isOpen: boolean;
  onClose: () => void;
  onUpdateEdge: (updated: DagEdgeDef) => void;
  onDeleteEdge: (source: string, target: string) => void;
}

export function EdgeInspectorDrawer({
  edge,
  nodes,
  isOpen,
  onClose,
  onUpdateEdge,
  onDeleteEdge,
}: EdgeInspectorDrawerProps) {
  const locale = useLocale();
  const isZh = locale !== "en";

  const [condition, setCondition] = useState("");

  useEffect(() => {
    if (!edge) return;
    setCondition(edge.condition || "");
  }, [edge]);

  if (!isOpen || !edge) return null;

  const sourceNode = nodes.find((n) => n.id === edge.source);
  const targetNode = nodes.find((n) => n.id === edge.target);

  const handleConditionChange = (newCondition: string) => {
    setCondition(newCondition);
    onUpdateEdge({
      ...edge,
      condition: newCondition.trim() || undefined,
    });
  };

  return (
    <aside
      role="region"
      aria-label={isZh ? "分支连线配置" : "Edge Configuration"}
      className="absolute right-0 top-0 bottom-0 w-80 sm:w-96 bg-surface-card border-l border-border-subtle shadow-2xl z-30 flex flex-col animate-fade-in"
    >
      {/* Header */}
      <div className="px-4 py-3.5 border-b border-border-subtle flex items-center justify-between bg-surface-ground/60">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-7 h-7 rounded-lg bg-accent-500/15 text-accent-700 dark:text-accent-300 flex items-center justify-center shrink-0">
            <GitBranch className="w-4 h-4" />
          </div>
          <div className="min-w-0">
            <h3 className="text-xs font-semibold text-text-primary truncate">
              {isZh ? "流转条件配置" : "Branch Routing Condition"}
            </h3>
            <span className="text-[10px] text-text-tertiary font-mono truncate block">
              {edge.source} → {edge.target}
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

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
        {/* Connection Pathway Card */}
        <div className="p-3 rounded-xl bg-surface-ground border border-border-subtle space-y-2">
          <div className="text-[10px] uppercase font-semibold tracking-wider text-text-tertiary">
            {isZh ? "执行拓扑关系" : "Execution Pathway"}
          </div>
          <div className="flex items-center justify-between gap-2 text-xs">
            <div className="flex-1 p-2 rounded-lg bg-surface-card border border-border-subtle truncate text-center">
              <span className="font-medium text-text-primary truncate block">
                {sourceNode?.name || edge.source}
              </span>
              <span className="text-[10px] font-mono text-text-tertiary block truncate">
                {edge.source}
              </span>
            </div>
            <ArrowRight className="w-4 h-4 text-accent-600 dark:text-accent-400 shrink-0" />
            <div className="flex-1 p-2 rounded-lg bg-surface-card border border-border-subtle truncate text-center">
              <span className="font-medium text-text-primary truncate block">
                {targetNode?.name || edge.target}
              </span>
              <span className="text-[10px] font-mono text-text-tertiary block truncate">
                {edge.target}
              </span>
            </div>
          </div>
        </div>

        {/* Condition input */}
        <div className="space-y-2">
          <label className="block text-[11px] font-medium text-text-secondary">
            {isZh ? "分支流转触发条件 (可选)" : "Branch Condition (Optional)"}
          </label>
          <input
            type="text"
            value={condition}
            onChange={(e) => handleConditionChange(e.target.value)}
            placeholder={
              isZh ? "留空代表无条件直接流转，或输入条件表达式" : "e.g. $.output.threat_score >= 80"
            }
            className="w-full px-3 py-1.5 font-mono text-[11px] rounded-xl border border-border-default bg-surface-ground text-text-primary focus:outline-none focus:ring-1 focus:ring-accent-500"
          />
          <p className="text-[10px] text-text-tertiary leading-relaxed">
            {isZh
              ? "当上游节点执行完毕后，仅当该表达式评估为 true 时才继续执行下游节点。留空时无条件继续。"
              : "Downstream step executes only when this expression evaluates to true. Leave blank for unconditional execution."}
          </p>
        </div>

        {/* Quick presets */}
        <div className="space-y-1.5 pt-2 border-t border-border-subtle">
          <span className="block text-[10px] text-text-tertiary">
            {isZh ? "常用条件预设" : "Condition Snippets"}
          </span>
          <div className="space-y-1">
            {[
              "$.output.ti.malicious_count >= 2",
              "$.output.ti.malicious_count < 2",
              "$.output.abuse.confidence >= 80",
              "$.output.is_malicious == true",
              "",
            ].map((snippet, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleConditionChange(snippet)}
                className="w-full text-left px-2 py-1.5 rounded-lg bg-surface-hover/80 hover:bg-surface-hover font-mono text-[10px] text-accent-700 dark:text-accent-300 truncate transition-colors flex items-center gap-1.5"
              >
                <Sparkles className="w-3 h-3 shrink-0 opacity-70" />
                <span className="truncate">
                  {snippet
                    ? snippet
                    : isZh
                      ? "（清空条件 · 设为默认无条件流转）"
                      : "(Unconditional default flow)"}
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-border-subtle bg-surface-ground/50 flex items-center justify-between gap-2">
        <button
          type="button"
          onClick={() => onDeleteEdge(edge.source, edge.target)}
          className="inline-flex items-center gap-1 px-3 py-1.5 rounded-xl border border-danger-500/30 bg-danger-500/10 text-danger-700 dark:text-danger-400 hover:bg-danger-500/20 text-xs font-medium transition-colors"
          title={isZh ? "删除此连线" : "Delete Connection"}
        >
          <Trash2 className="w-3.5 h-3.5" />
          <span>{isZh ? "删除连线" : "Delete"}</span>
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
    </aside>
  );
}

export default EdgeInspectorDrawer;
