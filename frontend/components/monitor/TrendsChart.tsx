"use client";

/**
 * TrendsChart Component
 * 告警趋势图表 - 使用 Recharts
 */

import React, { useMemo, useState, useEffect } from "react";
import { useTranslations, useLocale } from "next-intl";
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
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

interface TrendData {
  timestamp: string;
  date: string;
  total: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
}

interface TrendsChartProps {
  data: TrendData[];
  type?: "line" | "area" | "bar";
  showLegend?: boolean;
  height?: number;
}

export function TrendsChart({
  data,
  type = "area",
  showLegend = true,
  height = 300,
}: TrendsChartProps) {
  const tSeverity = useTranslations("severity");
  const t = useTranslations("threatIntel.dashboard");
  const locale = useLocale();
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    setIsDark(document.documentElement.classList.contains("dark"));

    const observer = new MutationObserver(() => {
      setIsDark(document.documentElement.classList.contains("dark"));
    });
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["class"],
    });
    return () => observer.disconnect();
  }, []);

  const mode = isDark ? ("dark" as const) : ("light" as const);
  const themeAxis = getAxisProps(mode);
  const themeGrid = getGridProps(mode);
  const themeTooltip = getTooltipProps(mode);
  const themeLegend = getLegendProps(mode);

  const colors = severityChartColors;

  // 格式化数据
  const chartData = useMemo(() => {
    return data.map((item) => ({
      ...item,
      date: new Date(item.timestamp).toLocaleDateString(locale === "zh-CN" ? "zh-CN" : "en-US", {
        month: "short",
        day: "numeric",
      }),
    }));
  }, [data, locale]);

  // 自定义 Tooltip
  const CustomTooltip = ({
    active,
    payload,
  }: {
    active?: boolean;
    payload?: Array<{ value: number; name: string; color: string; payload: { date: string } }>;
  }) => {
    if (!active || !payload || !payload.length) return null;

    return (
      <div style={themeTooltip.contentStyle}>
        <p style={{ ...themeTooltip.labelStyle, marginBottom: "8px", fontWeight: 500 }}>
          {payload[0].payload.date}
        </p>
        {payload.map((entry: { value: number; name: string; color: string }, index: number) => (
          <div key={index} className="flex items-center gap-2 text-xs">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: entry.color }} />
            <span style={{ color: themeTooltip.labelStyle.color }}>{entry.name}:</span>
            <span style={{ fontWeight: 600 }}>{entry.value}</span>
          </div>
        ))}
      </div>
    );
  };

  const renderChart = () => {
    const commonProps = {
      data: chartData,
      margin: { top: 10, right: 10, left: 0, bottom: 0 },
    };

    switch (type) {
      case "line":
        return (
          <LineChart {...commonProps}>
            <CartesianGrid {...themeGrid} />
            <XAxis dataKey="date" {...themeAxis} />
            <YAxis {...themeAxis} />
            <Tooltip content={<CustomTooltip />} />
            {showLegend && (
              <Legend
                wrapperStyle={themeLegend.wrapperStyle}
                // 图例文字走语义色：recharts 默认沿用系列描边色（500/600 级），
                // 落在白底上只有 3.19–3.77:1。与 SeverityDistribution 里已有的写法保持一致。
                formatter={(value) => (
                  <span className="text-sm text-text-secondary">{value as string}</span>
                )}
              />
            )}
            <Line
              type="monotone"
              dataKey="critical"
              stroke={colors.critical}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
              name={tSeverity("critical")}
            />
            <Line
              type="monotone"
              dataKey="high"
              stroke={colors.high}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
              name={tSeverity("high")}
            />
            <Line
              type="monotone"
              dataKey="medium"
              stroke={colors.medium}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
              name={tSeverity("medium")}
            />
            <Line
              type="monotone"
              dataKey="low"
              stroke={colors.low}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
              name={tSeverity("low")}
            />
          </LineChart>
        );

      case "bar":
        return (
          <BarChart {...commonProps}>
            <CartesianGrid {...themeGrid} />
            <XAxis dataKey="date" {...themeAxis} />
            <YAxis {...themeAxis} />
            <Tooltip content={<CustomTooltip />} />
            {showLegend && (
              <Legend
                wrapperStyle={themeLegend.wrapperStyle}
                // 图例文字走语义色：recharts 默认沿用系列描边色（500/600 级），
                // 落在白底上只有 3.19–3.77:1。与 SeverityDistribution 里已有的写法保持一致。
                formatter={(value) => (
                  <span className="text-sm text-text-secondary">{value as string}</span>
                )}
              />
            )}
            <Bar
              dataKey="critical"
              fill={colors.critical}
              name={tSeverity("critical")}
              radius={[4, 4, 0, 0]}
            />
            <Bar dataKey="high" fill={colors.high} name={tSeverity("high")} radius={[4, 4, 0, 0]} />
            <Bar
              dataKey="medium"
              fill={colors.medium}
              name={tSeverity("medium")}
              radius={[4, 4, 0, 0]}
            />
            <Bar dataKey="low" fill={colors.low} name={tSeverity("low")} radius={[4, 4, 0, 0]} />
          </BarChart>
        );

      case "area":
      default:
        return (
          <AreaChart {...commonProps}>
            <CartesianGrid {...themeGrid} />
            <XAxis dataKey="date" {...themeAxis} />
            <YAxis {...themeAxis} />
            <Tooltip content={<CustomTooltip />} />
            {showLegend && (
              <Legend
                wrapperStyle={themeLegend.wrapperStyle}
                // 图例文字走语义色：recharts 默认沿用系列描边色（500/600 级），
                // 落在白底上只有 3.19–3.77:1。与 SeverityDistribution 里已有的写法保持一致。
                formatter={(value) => (
                  <span className="text-sm text-text-secondary">{value as string}</span>
                )}
              />
            )}
            <Area
              type="monotone"
              dataKey="critical"
              stroke={colors.critical}
              strokeWidth={2}
              fill={colors.critical}
              fillOpacity={0.08}
              name={tSeverity("critical")}
            />
            <Area
              type="monotone"
              dataKey="high"
              stroke={colors.high}
              strokeWidth={2}
              fill={colors.high}
              fillOpacity={0.08}
              name={tSeverity("high")}
            />
            <Area
              type="monotone"
              dataKey="medium"
              stroke={colors.medium}
              strokeWidth={2}
              fill={colors.medium}
              fillOpacity={0.08}
              name={tSeverity("medium")}
            />
            <Area
              type="monotone"
              dataKey="low"
              stroke={colors.low}
              strokeWidth={2}
              fill={colors.low}
              fillOpacity={0.08}
              name={tSeverity("low")}
            />
          </AreaChart>
        );
    }
  };

  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 bg-surface-hover dark:bg-slate-800/50 rounded-lg border border-dashed border-border-subtle dark:border-slate-700">
        <div className="text-center">
          <TrendingUp className="w-12 h-12 text-text-tertiary mx-auto mb-3" />
          <p className="text-sm text-text-tertiary">{t("noTrendData")}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full min-w-0">
      <ResponsiveContainer width="100%" height={height} minWidth={0} minHeight={0}>
        {renderChart()}
      </ResponsiveContainer>
    </div>
  );
}

// 简化版：仅显示总数趋势
export function SimpleTrendChart({ data, height = 200 }: { data: TrendData[]; height?: number }) {
  const t = useTranslations("threatIntel.dashboard");
  const locale = useLocale();
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    setIsDark(document.documentElement.classList.contains("dark"));

    const observer = new MutationObserver(() => {
      setIsDark(document.documentElement.classList.contains("dark"));
    });
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["class"],
    });
    return () => observer.disconnect();
  }, []);

  const mode = isDark ? ("dark" as const) : ("light" as const);
  const themeAxis = getAxisProps(mode);
  const themeGrid = getGridProps(mode);
  const themeTooltip = getTooltipProps(mode);

  const chartData = useMemo(() => {
    return data.map((item) => ({
      date: new Date(item.timestamp).toLocaleDateString(locale === "zh-CN" ? "zh-CN" : "en-US", {
        month: "short",
        day: "numeric",
      }),
      count: item.total,
    }));
  }, [data, locale]);

  if (!data || data.length === 0) {
    return null;
  }

  return (
    <div className="w-full min-w-0">
      <ResponsiveContainer width="100%" height={height} minWidth={0} minHeight={0}>
        <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid {...themeGrid} />
          <XAxis dataKey="date" {...themeAxis} />
          <YAxis {...themeAxis} />
          <Tooltip
            content={({ active, payload }) => {
              if (!active || !payload || !payload.length) return null;
              const data = payload[0] as { value: number; payload: { date: string } };
              return (
                <div style={themeTooltip.contentStyle}>
                  <p style={{ fontSize: "12px", fontWeight: 500 }}>
                    {data.payload.date}: {t("alertsCount", { count: data.value })}
                  </p>
                </div>
              );
            }}
          />
          <Area
            type="monotone"
            dataKey="count"
            stroke={severityChartColors.info}
            strokeWidth={2}
            fill={severityChartColors.info}
            fillOpacity={0.08}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
