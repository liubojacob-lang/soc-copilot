"use client";

/**
 * StatCard - Modern KPI metric card for SOC dashboards
 *
 * 版式对齐 sec-security-dashboard.html 设计稿的 kpi-card：
 * 第一行是「小标签 + 角标」，中间是大号 tabular 数值与趋势，
 * 底部副文案用虚线分隔压成 footer，而不是散落在数值旁边。
 */

import React, { type ReactNode } from "react";
import { cn } from "@/lib/utils";

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: ReactNode;
  /** Numeric trend (renders "↑/↓ n%") or a plain status string (renders as-is). */
  trend?:
    | {
        value: number;
        isPositive: boolean;
        label?: string;
      }
    | string;
  /** Legacy prop accepted for backward compatibility (no longer rendered). */
  trendDirection?: "up" | "down" | "neutral";
  variant?: "default" | "blue" | "red" | "green" | "amber" | "purple";
  className?: string;
  loading?: boolean;
}

function isNumericTrend(
  trend: NonNullable<StatCardProps["trend"]>
): trend is { value: number; isPositive: boolean; label?: string } {
  return typeof trend !== "string";
}

const variantStyles: Record<
  string,
  { iconBg: string; iconColor: string; trendGood: string; trendBad: string }
> = {
  default: {
    iconBg: "bg-surface-ground border border-border-subtle",
    iconColor: "text-text-secondary",
    trendGood: "text-success-600 dark:text-success-400",
    trendBad: "text-danger-600 dark:text-danger-400",
  },
  blue: {
    iconBg: "bg-accent-500/10 border border-accent-500/20",
    iconColor: "text-accent-600 dark:text-accent-400",
    trendGood: "text-success-600 dark:text-success-400",
    trendBad: "text-danger-600 dark:text-danger-400",
  },
  red: {
    iconBg: "bg-danger-500/10 border border-danger-500/20",
    iconColor: "text-danger-600 dark:text-danger-400",
    trendGood: "text-success-600 dark:text-success-400",
    trendBad: "text-danger-600 dark:text-danger-400",
  },
  green: {
    iconBg: "bg-success-500/10 border border-success-500/20",
    iconColor: "text-success-600 dark:text-success-400",
    trendGood: "text-success-600 dark:text-success-400",
    trendBad: "text-danger-600 dark:text-danger-400",
  },
  amber: {
    iconBg: "bg-warning-500/10 border border-warning-500/20",
    iconColor: "text-warning-600 dark:text-warning-400",
    trendGood: "text-success-600 dark:text-success-400",
    trendBad: "text-danger-600 dark:text-danger-400",
  },
  purple: {
    iconBg: "bg-purple-500/10 border border-purple-500/20",
    iconColor: "text-purple-600 dark:text-purple-400",
    trendGood: "text-success-600 dark:text-success-400",
    trendBad: "text-danger-600 dark:text-danger-400",
  },
};

const StatCard = React.memo(function StatCard({
  title,
  value,
  subtitle,
  icon,
  trend,
  variant = "default",
  className,
  loading = false,
}: StatCardProps) {
  const styles = variantStyles[variant] || variantStyles.default;

  if (loading) {
    return (
      <div
        className={cn(
          "flex flex-col rounded-xl border border-border-subtle bg-surface-card p-4 shadow-subtle animate-pulse",
          className
        )}
      >
        <div className="flex items-center justify-between">
          <div className="h-3.5 bg-surface-ground rounded w-24" />
          <div className="h-7 w-7 rounded-lg bg-surface-ground" />
        </div>
        <div className="h-7 bg-surface-ground rounded w-16 mt-3" />
        <div className="border-t border-dashed border-border-subtle mt-4 pt-2.5">
          <div className="h-3 bg-surface-ground rounded w-28" />
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex flex-col rounded-xl border border-border-subtle bg-surface-card p-4 shadow-subtle transition-all duration-200 hover:border-border-default hover:shadow-elevated min-h-[110px]",
        className
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-xs font-medium text-text-muted truncate">{title}</h3>
        {icon && (
          <div
            className={cn(
              "h-7 w-7 shrink-0 rounded-lg flex items-center justify-center",
              styles.iconBg
            )}
          >
            <span className={cn("h-4 w-4 flex items-center justify-center", styles.iconColor)}>
              {icon}
            </span>
          </div>
        )}
      </div>

      <div className="mt-2.5 flex items-baseline gap-2 pb-3">
        <span className="text-[26px] leading-none font-semibold tracking-tight text-text-primary tabular-nums">
          {value}
        </span>
        {trend && isNumericTrend(trend) && (
          <span
            className={cn(
              "text-xs font-semibold flex items-center gap-0.5 tabular-nums",
              trend.isPositive ? styles.trendGood : styles.trendBad
            )}
          >
            {trend.isPositive ? "↑" : "↓"} {Math.abs(trend.value)}%
            {trend.label && (
              <span className="text-text-muted font-normal ml-0.5">{trend.label}</span>
            )}
          </span>
        )}
        {trend && typeof trend === "string" && (
          <span className="text-xs font-medium text-text-muted">{trend}</span>
        )}
      </div>

      {subtitle && (
        <p className="mt-auto pt-2.5 text-[11px] text-text-muted truncate leading-relaxed border-t border-dashed border-border-subtle">
          {subtitle}
        </p>
      )}
    </div>
  );
});

export { StatCard };
export type { StatCardProps };
