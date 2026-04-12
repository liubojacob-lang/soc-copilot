"use client";

/**
 * SeverityDistribution Component
 * 告警严重程度分布 - 饼图/环形图
 */

import React, { useMemo } from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts";
import { PieChart as PieChartIcon } from "lucide-react";

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

const SEVERITY_COLORS = {
  critical: "#dc2626",
  high: "#f97316",
  medium: "#eab308",
  low: "#3b82f6",
  info: "#6b7280",
};

const SEVERITY_LABELS = {
  critical: "Critical",
  high: "High",
  medium: "Medium",
  low: "Low",
  info: "Info",
};

export function SeverityDistribution({
  data,
  type = "donut",
  showLegend = true,
  height = 300,
}: SeverityDistributionProps) {
  // 转换数据格式
  const chartData = useMemo(() => {
    return Object.entries(data)
      .filter(([_, value]) => value > 0)
      .map(([key, value]) => ({
        name: SEVERITY_LABELS[key as keyof typeof SEVERITY_LABELS],
        value,
        color: SEVERITY_COLORS[key as keyof typeof SEVERITY_COLORS],
      }))
      .sort((a, b) => b.value - a.value);
  }, [data]);

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
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 p-3">
        <div className="flex items-center gap-2 mb-1">
          <div className="w-3 h-3 rounded-full" style={{ backgroundColor: data.payload.color }} />
          <span className="text-sm font-medium text-gray-900 dark:text-white">{data.name}</span>
        </div>
        <div className="space-y-1 text-xs">
          <div className="flex justify-between gap-4">
            <span className="text-gray-600 dark:text-gray-400">Count:</span>
            <span className="font-semibold text-gray-900 dark:text-white">{data.value}</span>
          </div>
          <div className="flex justify-between gap-4">
            <span className="text-gray-600 dark:text-gray-400">Percentage:</span>
            <span className="font-semibold text-gray-900 dark:text-white">{percentage}%</span>
          </div>
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

    if (percent < 0.05) return null; // 小于5%不显示标签

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
      <div className="flex items-center justify-center h-64 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-dashed border-gray-300 dark:border-gray-700">
        <div className="text-center">
          <PieChartIcon className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
          <p className="text-sm text-gray-500 dark:text-gray-400">No severity data available</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full">
      <ResponsiveContainer width="100%" height={height}>
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
              formatter={(value, entry) => (
                <span className="text-sm text-gray-700 dark:text-gray-300">
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
            <div className="text-3xl font-bold text-gray-900 dark:text-white">{total}</div>
            <div className="text-xs text-gray-500 dark:text-gray-400">Total Alerts</div>
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
  const chartData = useMemo(() => {
    return Object.entries(data)
      .filter(([_, value]) => value > 0)
      .map(([key, value]) => ({
        name: SEVERITY_LABELS[key as keyof typeof SEVERITY_LABELS],
        value,
        color: SEVERITY_COLORS[key as keyof typeof SEVERITY_COLORS],
      }))
      .sort((a, b) => b.value - a.value)
      .slice(0, limit);
  }, [data, limit]);

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
              <span className="font-medium text-gray-900 dark:text-white">{item.name}</span>
              <span className="text-gray-600 dark:text-gray-400">{item.value}</span>
            </div>
            <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
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
  const cards = useMemo(() => {
    return Object.entries(data)
      .filter(([_, value]) => value > 0)
      .map(([key, value]) => ({
        key,
        label: SEVERITY_LABELS[key as keyof typeof SEVERITY_LABELS],
        value,
        color: SEVERITY_COLORS[key as keyof typeof SEVERITY_COLORS],
      }))
      .sort((a, b) => b.value - a.value);
  }, [data]);

  if (cards.length === 0) {
    return null;
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
      {cards.map((card) => (
        <div
          key={card.key}
          className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-3"
        >
          <div className="flex items-center gap-2 mb-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: card.color }} />
            <span className="text-xs font-medium text-gray-600 dark:text-gray-400">
              {card.label}
            </span>
          </div>
          <div className="text-2xl font-bold text-gray-900 dark:text-white">{card.value}</div>
        </div>
      ))}
    </div>
  );
}
