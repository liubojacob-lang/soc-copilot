"use client";

/**
 * SeverityPieChart - Recharts pie chart for severity distribution
 */

import { useState, useMemo, useEffect } from "react";
import { useFormatter, useTranslations } from "next-intl";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts";
import { PieChartIcon } from "lucide-react";
import { severityChartColors, getTooltipProps, getLegendProps } from "@/lib/chartThemeAdapter";
import type { SeverityBucket } from "@/lib/api/dashboard";
import { cn } from "@/lib/utils";

interface SeverityPieChartProps {
  data: SeverityBucket[];
  total?: number;
  isLoading?: boolean;
  className?: string;
}

const SEVERITY_LABEL_KEYS: Record<string, string> = {
  critical: "critical",
  high: "high",
  medium: "medium",
  low: "low",
  info: "info",
};

export function SeverityPieChart({
  data,
  total,
  isLoading = false,
  className,
}: SeverityPieChartProps) {
  const tChart = useTranslations("monitor.severityChart");
  const tMonitor = useTranslations("monitor");
  const tCommon = useTranslations("common");
  const tSeverity = useTranslations("severity");
  const format = useFormatter();
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    setIsDark(document.documentElement.classList.contains("dark"));
    const observer = new MutationObserver(() => {
      setIsDark(document.documentElement.classList.contains("dark"));
    });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
    return () => observer.disconnect();
  }, []);

  const mode = isDark ? ("dark" as const) : ("light" as const);
  const themeTooltip = getTooltipProps(mode);
  const themeLegend = getLegendProps(mode);

  const chartData = useMemo(() => {
    if (!data || data.length === 0) return [];
    return data
      .filter((d) => d.count > 0)
      .map((d) => ({
        name: SEVERITY_LABEL_KEYS[d.severity]
          ? tSeverity(SEVERITY_LABEL_KEYS[d.severity])
          : d.severity,
        value: d.count,
        color: severityChartColors[d.severity as keyof typeof severityChartColors] || "#6b7280",
        percentage: d.percentage,
      }));
  }, [data, tSeverity]);

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
          <div className="h-[300px] bg-gray-100 dark:bg-gray-700 rounded-full w-[200px] mx-auto" />
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
          <PieChartIcon className="w-4 h-4 text-purple-500" />
          {tChart("title")}
        </h3>
        {total !== undefined && (
          <span className="text-xs text-text-tertiary">
            {tMonitor("total")}: {format.number(total)}
          </span>
        )}
      </div>

      <div className="w-full min-w-0 h-[300px]">
        {chartData.length === 0 ? (
          <div className="flex items-center justify-center h-full text-sm text-gray-400">
            {tCommon("noData")}
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={300} minWidth={0}>
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius={55}
                outerRadius={100}
                paddingAngle={3}
                dataKey="value"
                nameKey="name"
              >
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} stroke="none" />
                ))}
              </Pie>
              <Tooltip {...themeTooltip} />
              <Legend
                {...themeLegend}
                formatter={(value: string) => (
                  <span className="text-xs text-gray-600 dark:text-gray-300">{value}</span>
                )}
              />
            </PieChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
