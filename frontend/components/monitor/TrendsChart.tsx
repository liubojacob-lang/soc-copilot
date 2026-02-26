'use client';

/**
 * TrendsChart Component
 * 告警趋势图表 - 使用 Recharts
 */

import React, { useMemo } from 'react';
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
} from 'recharts';
import { TrendingUp } from 'lucide-react';

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
  type?: 'line' | 'area' | 'bar';
  showLegend?: boolean;
  height?: number;
}

const COLORS = {
  critical: '#dc2626',
  high: '#f97316',
  medium: '#eab308',
  low: '#3b82f6',
  total: '#6b7280',
};

export function TrendsChart({
  data,
  type = 'area',
  showLegend = true,
  height = 300,
}: TrendsChartProps) {
  // 格式化数据
  const chartData = useMemo(() => {
    return data.map(item => ({
      ...item,
      date: new Date(item.timestamp).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
      }),
    }));
  }, [data]);

  // 自定义 Tooltip
  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload || !payload.length) return null;

    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 p-3">
        <p className="text-sm font-medium text-gray-900 dark:text-white mb-2">
          {payload[0].payload.date}
        </p>
        {payload.map((entry: any, index: number) => (
          <div key={index} className="flex items-center gap-2 text-xs">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: entry.color }}
            />
            <span className="text-gray-600 dark:text-gray-400">
              {entry.name}:
            </span>
            <span className="font-semibold text-gray-900 dark:text-white">
              {entry.value}
            </span>
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
      case 'line':
        return (
          <LineChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" strokeOpacity={0.5} />
            <XAxis
              dataKey="date"
              stroke="#6b7280"
              fontSize={12}
              tickLine={false}
              axisLine={false}
            />
            <YAxis stroke="#6b7280" fontSize={12} tickLine={false} axisLine={false} />
            <Tooltip content={<CustomTooltip />} />
            {showLegend && <Legend />}
            <Line
              type="monotone"
              dataKey="critical"
              stroke={COLORS.critical}
              strokeWidth={2}
              dot={{ r: 3 }}
              name="Critical"
            />
            <Line
              type="monotone"
              dataKey="high"
              stroke={COLORS.high}
              strokeWidth={2}
              dot={{ r: 3 }}
              name="High"
            />
            <Line
              type="monotone"
              dataKey="medium"
              stroke={COLORS.medium}
              strokeWidth={2}
              dot={{ r: 3 }}
              name="Medium"
            />
            <Line
              type="monotone"
              dataKey="low"
              stroke={COLORS.low}
              strokeWidth={2}
              dot={{ r: 3 }}
              name="Low"
            />
          </LineChart>
        );

      case 'bar':
        return (
          <BarChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" strokeOpacity={0.5} />
            <XAxis
              dataKey="date"
              stroke="#6b7280"
              fontSize={12}
              tickLine={false}
              axisLine={false}
            />
            <YAxis stroke="#6b7280" fontSize={12} tickLine={false} axisLine={false} />
            <Tooltip content={<CustomTooltip />} />
            {showLegend && <Legend />}
            <Bar dataKey="critical" fill={COLORS.critical} name="Critical" radius={[4, 4, 0, 0]} />
            <Bar dataKey="high" fill={COLORS.high} name="High" radius={[4, 4, 0, 0]} />
            <Bar dataKey="medium" fill={COLORS.medium} name="Medium" radius={[4, 4, 0, 0]} />
            <Bar dataKey="low" fill={COLORS.low} name="Low" radius={[4, 4, 0, 0]} />
          </BarChart>
        );

      case 'area':
      default:
        return (
          <AreaChart {...commonProps}>
            <defs>
              <linearGradient id="colorCritical" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={COLORS.critical} stopOpacity={0.3} />
                <stop offset="95%" stopColor={COLORS.critical} stopOpacity={0} />
              </linearGradient>
              <linearGradient id="colorHigh" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={COLORS.high} stopOpacity={0.3} />
                <stop offset="95%" stopColor={COLORS.high} stopOpacity={0} />
              </linearGradient>
              <linearGradient id="colorMedium" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={COLORS.medium} stopOpacity={0.3} />
                <stop offset="95%" stopColor={COLORS.medium} stopOpacity={0} />
              </linearGradient>
              <linearGradient id="colorLow" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={COLORS.low} stopOpacity={0.3} />
                <stop offset="95%" stopColor={COLORS.low} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" strokeOpacity={0.5} />
            <XAxis
              dataKey="date"
              stroke="#6b7280"
              fontSize={12}
              tickLine={false}
              axisLine={false}
            />
            <YAxis stroke="#6b7280" fontSize={12} tickLine={false} axisLine={false} />
            <Tooltip content={<CustomTooltip />} />
            {showLegend && <Legend />}
            <Area
              type="monotone"
              dataKey="critical"
              stroke={COLORS.critical}
              strokeWidth={2}
              fill="url(#colorCritical)"
              name="Critical"
            />
            <Area
              type="monotone"
              dataKey="high"
              stroke={COLORS.high}
              strokeWidth={2}
              fill="url(#colorHigh)"
              name="High"
            />
            <Area
              type="monotone"
              dataKey="medium"
              stroke={COLORS.medium}
              strokeWidth={2}
              fill="url(#colorMedium)"
              name="Medium"
            />
            <Area
              type="monotone"
              dataKey="low"
              stroke={COLORS.low}
              strokeWidth={2}
              fill="url(#colorLow)"
              name="Low"
            />
          </AreaChart>
        );
    }
  };

  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-dashed border-gray-300 dark:border-gray-700">
        <div className="text-center">
          <TrendingUp className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
          <p className="text-sm text-gray-500 dark:text-gray-400">No trend data available</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full">
      <ResponsiveContainer width="100%" height={height}>
        {renderChart()}
      </ResponsiveContainer>
    </div>
  );
}

// 简化版：仅显示总数趋势
export function SimpleTrendChart({ data, height = 200 }: { data: TrendData[]; height?: number }) {
  const chartData = useMemo(() => {
    return data.map(item => ({
      date: new Date(item.timestamp).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
      }),
      count: item.total,
    }));
  }, [data]);

  if (!data || data.length === 0) {
    return null;
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="colorTotal" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" strokeOpacity={0.3} />
        <XAxis
          dataKey="date"
          stroke="#6b7280"
          fontSize={11}
          tickLine={false}
          axisLine={false}
        />
        <YAxis stroke="#6b7280" fontSize={11} tickLine={false} axisLine={false} />
        <Tooltip
          content={({ active, payload }: any) => {
            if (!active || !payload || !payload.length) return null;
            return (
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 p-2">
                <p className="text-xs font-medium text-gray-900 dark:text-white">
                  {payload[0].payload.date}: {payload[0].value} alerts
                </p>
              </div>
            );
          }}
        />
        <Area
          type="monotone"
          dataKey="count"
          stroke="#3b82f6"
          strokeWidth={2}
          fill="url(#colorTotal)"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
