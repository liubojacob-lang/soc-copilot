"use client";

/**
 * SeverityDistribution Component
 * 告警严重程度分布 - 饼图/环形图
 */

import React, { useMemo, useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts";
import { PieChart as PieChartIcon } from "lucide-react";
import { severityChartColors, getTooltipProps, getLegendProps } from "@/lib/chartThemeAdapter";

interface SeverityData {
  name: string;
  value: number;
  color: string;
}

interface SeverityDistributionProps {
  data: {
    critical: number;
    high: number;
    medium: number;
    low: number;
    info: number;
  };
  type?: "pie" | "donut";
  showLegend?: boolean;
  height?: number;
}

export function SeverityDistribution({
  data,
  type = "donut",
  showLegend = true,
  height = 300,
}: SeverityDistributionProps) {
  const tSeverity = useTranslations("severity");
  const t = useTranslations("threatIntel.dashboard");
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
  const themeTooltip = getTooltipProps(mode);
  const themeLegend = getLegendProps(mode);

  const getSeverityName = (key: string) => {
    try {
      return tSeverity(key) || key;
    } catch {
      return key;
    }
  };

  // 转换数据格式
  const chartData = useMemo(() => {
    return Object.entries(data)
      .filter(([_, value]) => value > 0)
      .map(([key, value]) => ({
        name: getSeverityName(key),
        value,
        color: severityChartColors[key as keyof typeof severityChartColors],
      }))
      .sort((a, b) => b.value - a.value);
  }, [data, tSeverity]);

  // 计算总数
  const total = useMemo(() => {
    return Object.values(data).reduce((sum, val) => sum + val, 0);
  }, [data]);

  // 自定义 Tooltip
  const CustomTooltip = ({
    active,
    payload,
  }: {
    active?: boolean;
    payload?: Array<{ value: number; name: string; payload: { color: string } }>;
  }) => {
    if (!active || !payload || !payload.length) return null;

    const data = payload[0];
    const percentage = ((data.value / total) * 100).toFixed(1);

    return (
      <div style={themeTooltip.contentStyle} className="flex flex-col gap-1">
        <div className="flex items-center gap-2 mb-1">
          <div className="w-3 h-3 rounded-full" style={{ backgroundColor: data.payload.color }} />
          <span style={{ fontWeight: 500, fontSize: 14 }}>{data.name}</span>
        </div>
        <div className="flex justify-between gap-4 text-xs">
          <span style={{ color: themeTooltip.labelStyle.color }}>{t("count")}:</span>
          <span style={{ fontWeight: 600 }}>{data.value}</span>
        </div>
        <div className="flex justify-between gap-4 text-xs">
          <span style={{ color: themeTooltip.labelStyle.color }}>{t("percentage")}:</span>
          <span style={{ fontWeight: 600 }}>{percentage}%</span>
        </div>
      </div>
    );
  };

  // 自定义标签
  const renderCustomizedLabel = ({
    cx,
    cy,
    midAngle,
    innerRadius,
    outerRadius,
    percent,
  }: {
    cx?: number;
    cy?: number;
    midAngle?: number;
    innerRadius?: number;
    outerRadius?: number;
    percent?: number;
  }) => {
    if (
      cx === undefined ||
      cy === undefined ||
      midAngle === undefined ||
      innerRadius === undefined ||
      outerRadius === undefined ||
      percent === undefined
    ) {
      return null;
    }
    const RADIAN = Math.PI / 180;
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);

    if (percent < 0.05) return null;

    return (
      <text
        x={x}
        y={y}
        fill="white"
        textAnchor={x > cx ? "start" : "end"}
        dominantBaseline="central"
        fontSize={12}
        fontWeight="600"
      >
        {`${(percent * 100).toFixed(0)}%`}
      </text>
    );
  };

  if (total === 0) {
    return (
      <div className="flex items-center justify-center h-64 bg-surface-hover dark:bg-slate-800/50 rounded-lg border border-dashed border-border-subtle dark:border-slate-700">
        <div className="text-center">
          <PieChartIcon className="w-12 h-12 text-text-tertiary mx-auto mb-3" />
          <p className="text-sm text-text-tertiary">{t("noSeverityData")}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full min-w-0">
      <ResponsiveContainer width="100%" height={height} minWidth={0} minHeight={0}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={type === "pie" ? renderCustomizedLabel : false}
            outerRadius={type === "donut" ? 80 : 100}
            innerRadius={type === "donut" ? 60 : 0}
            paddingAngle={2}
            dataKey="value"
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
          {showLegend && (
            <Legend
              verticalAlign="bottom"
              height={36}
              iconType="circle"
              wrapperStyle={themeLegend.wrapperStyle}
              formatter={(value, entry) => (
                <span className="text-sm text-text-secondary dark:text-slate-300">
                  {value} ({(entry.payload as { value: number })?.value ?? 0})
                </span>
              )}
            />
          )}
        </PieChart>
      </ResponsiveContainer>

      {/* 中心总数显示（仅环形图） */}
      {type === "donut" && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="text-center">
            <div className="text-3xl font-bold text-text-primary dark:text-white">{total}</div>
            <div className="text-xs text-text-tertiary">{t("totalAlerts")}</div>
          </div>
        </div>
      )}
    </div>
  );
}

// 简化版：水平条形图
export function SeverityBars({
  data,
  limit = 5,
}: {
  data: SeverityDistributionProps["data"];
  limit?: number;
}) {
  const tSeverity = useTranslations("severity");
  const chartData = useMemo(() => {
    return Object.entries(data)
      .filter(([_, value]) => value > 0)
      .map(([key, value]) => ({
        name: tSeverity(key) || key,
        value,
        color: severityChartColors[key as keyof typeof severityChartColors],
      }))
      .sort((a, b) => b.value - a.value)
      .slice(0, limit);
  }, [data, limit, tSeverity]);

  const maxValue = Math.max(...chartData.map((d) => d.value));

  if (chartData.length === 0) {
    return null;
  }

  return (
    <div className="space-y-3">
      {chartData.map((item) => {
        const percentage = (item.value / maxValue) * 100;

        return (
          <div key={item.name} className="space-y-1">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium text-text-primary dark:text-white">{item.name}</span>
              <span className="text-text-tertiary">{item.value}</span>
            </div>
            <div className="h-2 bg-surface-active dark:bg-slate-700 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${percentage}%`,
                  backgroundColor: item.color,
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

// 紧凑版：仅显示统计卡片
export function SeverityCards({ data }: { data: SeverityDistributionProps["data"] }) {
  const tSeverity = useTranslations("severity");
  const cards = useMemo(() => {
    return Object.entries(data)
      .filter(([_, value]) => value > 0)
      .map(([key, value]) => ({
        key,
        label: tSeverity(key) || key,
        value,
        color: severityChartColors[key as keyof typeof severityChartColors],
      }))
      .sort((a, b) => b.value - a.value);
  }, [data, tSeverity]);

  if (cards.length === 0) {
    return null;
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
      {cards.map((card) => (
        <div
          key={card.key}
          className="bg-surface-card dark:bg-slate-800 rounded-lg border border-border-subtle dark:border-slate-700 p-3"
        >
          <div className="flex items-center gap-2 mb-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: card.color }} />
            <span className="text-xs font-medium text-text-tertiary">{card.label}</span>
          </div>
          <div className="text-2xl font-bold text-text-primary dark:text-white">{card.value}</div>
        </div>
      ))}
    </div>
  );
}
