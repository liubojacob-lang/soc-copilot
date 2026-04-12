"use client";

import React from "react";
import { Handle, Position, NodeProps } from "reactflow";
import { Clock, CheckCircle, XCircle, AlertTriangle, SkipForward, Loader2 } from "lucide-react";
import { useTranslations } from "next-intl";

export type NodeData = {
  label: string;
  stepId: string;
  status: "pending" | "running" | "success" | "failed" | "skipped" | "waiting_approval";
  duration?: number;
  error?: string;
  output?: Record<string, any>;
};

const statusConfig = {
  pending: {
    bgColor: "bg-slate-100 dark:bg-slate-800",
    borderColor: "border-slate-300 dark:border-slate-600",
    textColor: "text-slate-700 dark:text-slate-300",
    icon: null,
  },
  running: {
    bgColor: "bg-blue-50 dark:bg-blue-950",
    borderColor: "border-blue-400 dark:border-blue-500",
    textColor: "text-blue-700 dark:text-blue-300",
    icon: <Loader2 className="w-4 h-4 animate-spin" />,
  },
  success: {
    bgColor: "bg-green-50 dark:bg-green-950",
    borderColor: "border-green-400 dark:border-green-500",
    textColor: "text-green-700 dark:text-green-300",
    icon: <CheckCircle className="w-4 h-4" />,
  },
  failed: {
    bgColor: "bg-red-50 dark:bg-red-950",
    borderColor: "border-red-400 dark:border-red-500",
    textColor: "text-red-700 dark:text-red-300",
    icon: <XCircle className="w-4 h-4" />,
  },
  skipped: {
    bgColor: "bg-gray-50 dark:bg-gray-900",
    borderColor: "border-gray-400 dark:border-gray-600",
    textColor: "text-gray-500 dark:text-gray-400",
    icon: <SkipForward className="w-4 h-4" />,
  },
  waiting_approval: {
    bgColor: "bg-yellow-50 dark:bg-yellow-950",
    borderColor: "border-yellow-400 dark:border-yellow-500",
    textColor: "text-yellow-700 dark:text-yellow-300",
    icon: <AlertTriangle className="w-4 h-4" />,
  },
};

export function DAGNode({ data, selected }: NodeProps<NodeData>) {
  const t = useTranslations("dag");
  const config = statusConfig[data.status];

  const formatDuration = (ms?: number): string => {
    if (!ms) return "";
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${(ms / 60000).toFixed(1)}m`;
  };

  return (
    <div
      className={`
        px-4 py-3 rounded-lg border-2 min-w-[180px] max-w-[240px]
        ${config.bgColor} ${config.borderColor}
        ${selected ? "ring-2 ring-offset-2 ring-blue-500" : ""}
        transition-all duration-200
      `}
    >
      {/* Input Handle */}
      <Handle
        type="target"
        position={Position.Top}
        className="!bg-slate-400 dark:!bg-slate-600 !border-2 !border-slate-300 dark:!border-slate-700"
      />

      {/* Header */}
      <div className="flex items-center gap-2 mb-1">
        {config.icon}
        <span className={`font-medium text-sm ${config.textColor}`}>{data.label}</span>
      </div>

      {/* Step ID */}
      <div className={`text-xs opacity-70 ${config.textColor}`}>{data.stepId}</div>

      {/* Duration */}
      {data.duration && data.status !== "running" && (
        <div className={`text-xs mt-1 flex items-center gap-1 ${config.textColor}`}>
          <Clock className="w-3 h-3" />
          {formatDuration(data.duration)}
        </div>
      )}

      {/* Error Message (tooltip) */}
      {data.status === "failed" && data.error && (
        <div className="mt-2 text-xs text-red-600 dark:text-red-400 truncate" title={data.error}>
          {data.error}
        </div>
      )}

      {/* Output Preview */}
      {data.output && Object.keys(data.output).length > 0 && data.status === "success" && (
        <details className="mt-2 text-xs">
          <summary className={`cursor-pointer opacity-70 ${config.textColor}`}>
            {t("output")}
          </summary>
          <pre
            className={`mt-1 p-1 rounded bg-white/50 dark:bg-black/20 overflow-auto max-h-20 ${config.textColor}`}
          >
            {JSON.stringify(data.output, null, 2)}
          </pre>
        </details>
      )}

      {/* Output Handle */}
      <Handle
        type="source"
        position={Position.Bottom}
        className="!bg-slate-400 dark:!bg-slate-600 !border-2 !border-slate-300 dark:!border-slate-700"
      />
    </div>
  );
}

export default DAGNode;
