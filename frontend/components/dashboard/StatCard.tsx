"use client";

/**
 * StatCard - Modern KPI metric card for SOC dashboards
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
  { iconBg: string; iconColor: string; trendGood: string; trendBad: string; accentBorder?: string }
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
          "rounded-xl border border-border-subtle bg-surface-card p-5 shadow-subtle animate-pulse",
          className
        )}
      >
        <div className="flex items-start justify-between mb-3">
          <div className="h-3.5 bg-surface-ground rounded w-24" />
          <div className="w-9 h-9 rounded-lg bg-surface-ground" />
        </div>
        <div className="h-8 bg-surface-ground rounded w-16 mb-2" />
        <div className="h-3 bg-surface-ground rounded w-28" />
      </div>
    );
  }

  return (
    <div
      className={cn(
        "rounded-xl border border-border-subtle bg-surface-card p-5 shadow-subtle transition-all duration-200 hover:border-border-default hover:shadow-elevated",
        className
      )}
    >
      <div className="flex items-start justify-between mb-3">
        <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider">
          {title}
        </h3>
        {icon && (
          <div
            className={cn(
              "w-9 h-9 rounded-lg flex items-center justify-center shrink-0 transition-transform duration-200 group-hover:scale-105",
              styles.iconBg
            )}
          >
            <span className={cn("w-4.5 h-4.5 flex items-center justify-center", styles.iconColor)}>
              {icon}
            </span>
          </div>
        )}
      </div>

      <div className="flex items-baseline gap-2 mb-1.5">
        <span className="text-2xl sm:text-3xl font-bold tracking-tight text-text-primary tabular-nums">
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

      {subtitle && <p className="text-xs text-text-muted truncate leading-relaxed">{subtitle}</p>}
    </div>
  );
});

export { StatCard };
export type { StatCardProps };
