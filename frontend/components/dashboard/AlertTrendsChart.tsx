"use client";

/**
 * AlertTrendsChart - Recharts line chart for alert trends (7d/30d)
 */

import { useState, useMemo, useEffect } from "react";
import { useTranslations } from "next-intl";
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { TrendingUp } from "lucide-react";
import {
  severityChartColors,
  getAxisProps,
  getGridProps,
  getTooltipProps,
  getLegendProps,
} from "@/lib/chartThemeAdapter";
import type { AlertTrendPoint } from "@/lib/api/dashboard";
import { cn } from "@/lib/utils";

interface AlertTrendsChartProps {
  data: AlertTrendPoint[];
  isLoading?: boolean;
  className?: string;
  onPeriodChange?: (period: "7d" | "30d") => void;
  currentPeriod?: "7d" | "30d";
}

export function AlertTrendsChart({
  data,
  isLoading = false,
  className,
  onPeriodChange,
  currentPeriod = "7d",
}: AlertTrendsChartProps) {
  const t = useTranslations();
  const [isDark, setIsDark] = useState(false);

  // Detect dark mode
  useEffect(() => {
    setIsDark(document.documentElement.classList.contains("dark"));
    const observer = new MutationObserver(() => {
      setIsDark(document.documentElement.classList.contains("dark"));
    });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
    return () => observer.disconnect();
  }, []);

  const mode = isDark ? ("dark" as const) : ("light" as const);
  const themeAxis = getAxisProps(mode);
  const themeGrid = getGridProps(mode);
  const themeTooltip = getTooltipProps(mode);
  const themeLegend = getLegendProps(mode);

  const colors = severityChartColors;

  const chartData = useMemo(() => {
    if (!data || data.length === 0) return [];
    return data.map((d) => ({
      ...d,
      label: new Date(d.date).toLocaleDateString(undefined, { month: "short", day: "numeric" }),
    }));
  }, [data]);

  if (isLoading) {
    return (
      <div
        className={cn(
          "bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5",
          className
        )}
      >
        <div className="animate-pulse">
          <div className="h-5 bg-gray-200 dark:bg-gray-700 rounded w-40 mb-4" />
          <div className="h-[300px] bg-gray-100 dark:bg-gray-700 rounded" />
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5",
        className
      )}
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-blue-500" />
          {t("dashboard.alertTrends")}
        </h3>
        {onPeriodChange && (
          <div className="flex rounded-lg bg-gray-100 dark:bg-gray-700 p-0.5">
            <button
              onClick={() => onPeriodChange("7d")}
              className={cn(
                "px-3 py-1 text-xs rounded-md transition-colors",
                currentPeriod === "7d"
                  ? "bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm"
                  : "text-gray-500 dark:text-gray-400 hover:text-gray-700"
              )}
            >
              7 {t("dashboard.days") || "d"}
            </button>
            <button
              onClick={() => onPeriodChange("30d")}
              className={cn(
                "px-3 py-1 text-xs rounded-md transition-colors",
                currentPeriod === "30d"
                  ? "bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm"
                  : "text-gray-500 dark:text-gray-400 hover:text-gray-700"
              )}
            >
              30 {t("dashboard.days") || "d"}
            </button>
          </div>
        )}
      </div>

      <div className="w-full min-w-0 h-[300px]">
        {chartData.length === 0 ? (
          <div className="flex items-center justify-center h-full text-sm text-text-tertiary">
            {t("common.noData")}
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={300} minWidth={0}>
            <AreaChart data={chartData} margin={{ top: 5, right: 5, left: -10, bottom: 5 }}>
              <defs>
                {(["critical", "high", "medium", "low"] as const).map((key, idx) => (
                  <linearGradient key={key} id={`gradient-${key}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={colors[key]} stopOpacity={0.15} />
                    <stop offset="95%" stopColor={colors[key]} stopOpacity={0} />
                  </linearGradient>
                ))}
              </defs>
              <CartesianGrid {...themeGrid} />
              <XAxis
                dataKey="label"
                {...themeAxis}
                interval="preserveStartEnd"
                tick={{ fontSize: 11, fill: isDark ? "#94a3b8" : "#64748b" }}
              />
              <YAxis {...themeAxis} allowDecimals={false} width={40} />
              <Tooltip {...themeTooltip} />
              {/* 图例文字走语义色：recharts 默认沿用系列描边色（500/600 级），
                  落在白底上 3.19–3.77:1、深色底上 3.04–4.12:1。
                  仓库里另外 5 处 <Legend> 都加了 formatter，这一处漏了。 */}
              <Legend
                {...themeLegend}
                formatter={(value: string) => (
                  <span className="text-sm text-text-secondary">{value}</span>
                )}
              />
              <Area
                type="monotone"
                dataKey="critical"
                name={t("severity.critical") || "Critical"}
                stroke={colors.critical}
                fill={`url(#gradient-critical)`}
                strokeWidth={2}
                dot={false}
              />
              <Area
                type="monotone"
                dataKey="high"
                name={t("severity.high") || "High"}
                stroke={colors.high}
                fill={`url(#gradient-high)`}
                strokeWidth={2}
                dot={false}
              />
              <Area
                type="monotone"
                dataKey="medium"
                name={t("severity.medium") || "Medium"}
                stroke={colors.medium}
                fill={`url(#gradient-medium)`}
                strokeWidth={2}
                dot={false}
              />
              <Area
                type="monotone"
                dataKey="low"
                name={t("severity.low") || "Low"}
                stroke={colors.low}
                fill={`url(#gradient-low)`}
                strokeWidth={2}
                dot={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
