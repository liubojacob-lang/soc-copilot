"use client";

/**
 * StatCard - Reusable KPI metric card for dashboards
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
  { bg: string; iconBg: string; iconColor: string; trendGood: string; trendBad: string }
> = {
  default: {
    bg: "bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700",
    iconBg: "bg-gray-100 dark:bg-gray-700",
    iconColor: "text-gray-600 dark:text-gray-300",
    trendGood: "text-green-600",
    trendBad: "text-red-600",
  },
  blue: {
    bg: "bg-white dark:bg-gray-800 border-blue-100 dark:border-blue-900/30",
    iconBg: "bg-blue-50 dark:bg-blue-900/20",
    iconColor: "text-blue-600 dark:text-blue-400",
    trendGood: "text-green-600",
    trendBad: "text-red-600",
  },
  red: {
    bg: "bg-white dark:bg-gray-800 border-red-100 dark:border-red-900/30",
    iconBg: "bg-red-50 dark:bg-red-900/20",
    iconColor: "text-red-600 dark:text-red-400",
    trendGood: "text-green-600",
    trendBad: "text-red-600",
  },
  green: {
    bg: "bg-white dark:bg-gray-800 border-green-100 dark:border-green-900/30",
    iconBg: "bg-green-50 dark:bg-green-900/20",
    iconColor: "text-green-600 dark:text-green-400",
    trendGood: "text-green-600",
    trendBad: "text-red-600",
  },
  amber: {
    bg: "bg-white dark:bg-gray-800 border-amber-100 dark:border-amber-900/30",
    iconBg: "bg-amber-50 dark:bg-amber-900/20",
    iconColor: "text-amber-600 dark:text-amber-400",
    trendGood: "text-green-600",
    trendBad: "text-red-600",
  },
  purple: {
    bg: "bg-white dark:bg-gray-800 border-purple-100 dark:border-purple-900/30",
    iconBg: "bg-purple-50 dark:bg-purple-900/20",
    iconColor: "text-purple-600 dark:text-purple-400",
    trendGood: "text-green-600",
    trendBad: "text-red-600",
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
      <div className={cn("rounded-xl border p-5 shadow-sm animate-pulse", styles.bg, className)}>
        <div className="flex items-start justify-between mb-3">
          <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-20" />
          <div className="w-9 h-9 rounded-lg bg-gray-200 dark:bg-gray-700" />
        </div>
        <div className="h-7 bg-gray-200 dark:bg-gray-700 rounded w-16 mb-2" />
        <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-24" />
      </div>
    );
  }

  return (
    <div
      className={cn(
        "rounded-xl border p-5 shadow-sm transition-shadow hover:shadow-md",
        styles.bg,
        className
      )}
    >
      <div className="flex items-start justify-between mb-2">
        <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
          {title}
        </h3>
        {icon && (
          <div
            className={cn(
              "w-9 h-9 rounded-lg flex items-center justify-center shrink-0",
              styles.iconBg
            )}
          >
            <span className={cn("w-5 h-5", styles.iconColor)}>{icon}</span>
          </div>
        )}
      </div>

      <div className="flex items-baseline gap-2 mb-1">
        <span className="text-2xl font-bold text-gray-900 dark:text-white">{value}</span>
        {trend && isNumericTrend(trend) && (
          <span
            className={cn(
              "text-xs font-semibold flex items-center gap-0.5",
              trend.isPositive ? styles.trendGood : styles.trendBad
            )}
          >
            {trend.isPositive ? "↑" : "↓"} {Math.abs(trend.value)}%
            {trend.label && (
              <span className="text-gray-400 dark:text-gray-500 font-normal ml-0.5">
                {trend.label}
              </span>
            )}
          </span>
        )}
        {trend && typeof trend === "string" && (
          <span className="text-xs font-medium text-gray-400 dark:text-gray-500">{trend}</span>
        )}
      </div>

      {subtitle && <p className="text-xs text-gray-400 dark:text-gray-500">{subtitle}</p>}
    </div>
  );
});

export { StatCard };
export type { StatCardProps };
