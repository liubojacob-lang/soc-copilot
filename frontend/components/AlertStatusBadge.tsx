"use client";

/**
 * AlertStatusBadge Component
 * 告警状态徽章组件
 */

import React from "react";
import { useTranslations } from "next-intl";

export type AlertStatus = "new" | "investigating" | "resolved" | "false_positive" | "escalated";
export type AlertSeverity = "critical" | "high" | "medium" | "low" | "info";

interface AlertStatusBadgeProps {
  status: AlertStatus;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
}

const statusConfig: Record<AlertStatus, { color: string; dotColor: string }> = {
  new: {
    color:
      "bg-sky-50 text-sky-700 border-sky-200/80 dark:bg-sky-500/10 dark:text-sky-400 dark:border-sky-500/25",
    dotColor: "bg-sky-500",
  },
  investigating: {
    color:
      "bg-amber-50 text-amber-700 border-amber-200/80 dark:bg-amber-500/10 dark:text-amber-400 dark:border-amber-500/25",
    dotColor: "bg-amber-500",
  },
  resolved: {
    color:
      "bg-emerald-50 text-emerald-700 border-emerald-200/80 dark:bg-emerald-500/10 dark:text-emerald-400 dark:border-emerald-500/25",
    dotColor: "bg-emerald-500",
  },
  false_positive: {
    color:
      "bg-slate-100 text-slate-700 border-slate-200/80 dark:bg-slate-800/60 dark:text-slate-300 dark:border-slate-700/60",
    dotColor: "bg-slate-400",
  },
  escalated: {
    color:
      "bg-red-50 text-red-700 border-red-200/80 dark:bg-red-500/10 dark:text-red-400 dark:border-red-500/25",
    dotColor: "bg-red-500",
  },
};

const sizeStyles = {
  sm: "px-2 py-0.5 text-xs gap-1.5",
  md: "px-2.5 py-1 text-xs gap-1.5 font-medium",
  lg: "px-3 py-1.5 text-sm gap-2 font-medium",
};

const dotSize = {
  sm: "w-1.5 h-1.5",
  md: "w-2 h-2",
  lg: "w-2 h-2",
};

function AlertStatusBadge_({ status, size = "md", showLabel = true }: AlertStatusBadgeProps) {
  const t = useTranslations("status");
  const config = statusConfig[status] || statusConfig.new;
  const sizeClass = sizeStyles[size];
  const dotClass = dotSize[size];

  const statusLabels: Record<AlertStatus, string> = {
    new: t("new"),
    investigating: t("investigating"),
    resolved: t("resolved"),
    false_positive: t("falsePositive"),
    escalated: t("escalated"),
  };

  return (
    <span
      className={`inline-flex items-center rounded-full font-medium border ${config.color} ${sizeClass} tracking-tight select-none`}
    >
      <span className={`rounded-full ${dotClass} ${config.dotColor} shrink-0`} />
      {showLabel && <span>{statusLabels[status] || status}</span>}
    </span>
  );
}

interface SeverityBadgeProps {
  severity: AlertSeverity;
  size?: "sm" | "md" | "lg";
  showScore?: boolean;
  score?: number;
}

const severityConfig: Record<AlertSeverity, { color: string; dotColor: string }> = {
  critical: {
    color:
      "bg-red-50 text-red-700 border-red-200/80 dark:bg-red-500/10 dark:text-red-400 dark:border-red-500/25",
    dotColor: "bg-red-500",
  },
  high: {
    color:
      "bg-orange-50 text-orange-700 border-orange-200/80 dark:bg-orange-500/10 dark:text-orange-400 dark:border-orange-500/25",
    dotColor: "bg-orange-500",
  },
  medium: {
    color:
      "bg-amber-50 text-amber-700 border-amber-200/80 dark:bg-amber-500/10 dark:text-amber-400 dark:border-amber-500/25",
    dotColor: "bg-amber-500",
  },
  low: {
    color:
      "bg-emerald-50 text-emerald-700 border-emerald-200/80 dark:bg-emerald-500/10 dark:text-emerald-400 dark:border-emerald-500/25",
    dotColor: "bg-emerald-500",
  },
  info: {
    color:
      "bg-sky-50 text-sky-700 border-sky-200/80 dark:bg-sky-500/10 dark:text-sky-400 dark:border-sky-500/25",
    dotColor: "bg-sky-500",
  },
};

function SeverityBadge_({ severity, size = "md", showScore = false, score }: SeverityBadgeProps) {
  const t = useTranslations("severity");
  const config = severityConfig[severity] || severityConfig.info;
  const sizeClass = sizeStyles[size];
  const dotClass = dotSize[size];

  const severityLabels: Record<AlertSeverity, string> = {
    critical: t("critical"),
    high: t("high"),
    medium: t("medium"),
    low: t("low"),
    info: t("info"),
  };

  return (
    <div className="inline-flex items-center gap-1.5">
      <span
        className={`inline-flex items-center rounded-full border font-semibold ${config.color} ${sizeClass} tracking-tight select-none`}
      >
        <span className={`rounded-full ${dotClass} ${config.dotColor} shrink-0`} />
        <span>{severityLabels[severity] || severity}</span>
      </span>
      {showScore !== false && score !== undefined && (
        <span className="text-xs font-mono text-gray-500 dark:text-gray-400 tabular-nums">
          ({score})
        </span>
      )}
    </div>
  );
}

// 告警卡片组件
interface AlertCardProps {
  alert: {
    id: string;
    title: string;
    description?: string;
    severity: AlertSeverity;
    status: AlertStatus;
    source: string;
    event_type: string;
    timestamp: string;
    threat_score?: number;
  };
  onClick?: () => void;
  size?: "sm" | "md" | "lg";
  showActions?: boolean;
  actions?: React.ReactNode;
}

function AlertCard_({ alert, onClick, size = "md", showActions = false, actions }: AlertCardProps) {
  const tTime = useTranslations("time");

  const timeSince = (timestamp: string) => {
    const now = new Date();
    const then = new Date(timestamp);
    const diffMs = now.getTime() - then.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return tTime("justNow");
    if (diffMins < 60) return tTime("minutesAgo", { count: diffMins });
    if (diffHours < 24) return tTime("hoursAgo", { count: diffHours });
    return tTime("daysAgo", { count: diffDays });
  };

  const severityBorderColor =
    {
      critical: "border-l-red-500",
      high: "border-l-orange-500",
      medium: "border-l-amber-500",
      low: "border-l-emerald-500",
      info: "border-l-sky-500",
    }[alert.severity] || "border-l-slate-400";

  return (
    <div
      className={`
        bg-surface-card border border-border-subtle rounded-xl shadow-subtle card-hover
        cursor-pointer border-l-4 ${severityBorderColor}
        ${size === "sm" ? "p-3" : size === "lg" ? "p-5" : "p-4"}
      `}
      onClick={onClick}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <SeverityBadge severity={alert.severity} size="sm" />
            <AlertStatusBadge status={alert.status} size="sm" />
          </div>

          <h3
            className={`font-semibold text-text-primary truncate ${
              size === "sm" ? "text-sm" : size === "lg" ? "text-lg" : "text-base"
            }`}
          >
            {alert.title}
          </h3>

          {alert.description && (
            <p className="text-sm text-text-secondary mt-1 line-clamp-2">{alert.description}</p>
          )}

          <div className="flex items-center gap-3 mt-2.5 text-xs text-text-tertiary">
            <span className="font-mono">{alert.source}</span>
            <span>•</span>
            <span>{alert.event_type}</span>
            <span>•</span>
            <span className="tabular-nums">{timeSince(alert.timestamp)}</span>
          </div>
        </div>

        {showActions && <div className="flex-shrink-0">{actions}</div>}
      </div>
    </div>
  );
}

// React.memo wrappers for performance optimization (F2-9)
const AlertStatusBadge = React.memo(AlertStatusBadge_);
const SeverityBadge = React.memo(SeverityBadge_);
const AlertCard = React.memo(AlertCard_);

export { AlertStatusBadge, SeverityBadge, AlertCard };
