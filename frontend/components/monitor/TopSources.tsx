'use client';

/**
 * TopSources Component
 * Top 攻击源展示 - IP/域名统计
 */

import React, { useState } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { Globe, Server, ChevronDown, ChevronUp, ExternalLink } from 'lucide-react';

interface ThreatSource {
  type: 'ip' | 'domain';
  value: string;
  count: number;
  severity: 'critical' | 'high' | 'medium' | 'low';
  country?: string;
  first_seen: string;
  last_seen: string;
}

interface TopSourcesProps {
  sources: ThreatSource[];
  type?: 'ip' | 'domain' | 'both';
  limit?: number;
  showDetails?: boolean;
}

const SEVERITY_COLORS = {
  critical: '#dc2626',
  high: '#f97316',
  medium: '#eab308',
  low: '#3b82f6',
};

export function TopSources({
  sources,
  type = 'both',
  limit = 10,
  showDetails = true,
}: TopSourcesProps) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  // 过滤和限制数据
  const filteredSources = sources
    .filter(s => type === 'both' || s.type === type)
    .slice(0, limit);

  // 图表数据
  const chartData = filteredSources.map(s => ({
    name: s.value,
    count: s.count,
    color: SEVERITY_COLORS[s.severity],
  }));

  const toggleExpand = (value: string) => {
    setExpanded(prev => {
      const next = new Set(prev);
      if (next.has(value)) {
        next.delete(value);
      } else {
        next.add(value);
      }
      return next;
    });
  };

  if (!sources || sources.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-dashed border-gray-300 dark:border-gray-700">
        <div className="text-center">
          <Globe className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
          <p className="text-sm text-gray-500 dark:text-gray-400">No threat sources found</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 柱状图 */}
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} layout="horizontal" margin={{ top: 10, right: 10, left: 80, bottom: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" strokeOpacity={0.5} />
            <XAxis type="number" stroke="#6b7280" fontSize={12} tickLine={false} axisLine={false} />
            <YAxis
              type="category"
              dataKey="name"
              stroke="#6b7280"
              fontSize={11}
              tickLine={false}
              axisLine={false}
              width={70}
            />
            <Tooltip
              content={({ active, payload }: any) => {
                if (!active || !payload || !payload.length) return null;
                return (
                  <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 p-2">
                    <p className="text-xs font-medium text-gray-900 dark:text-white">
                      {payload[0].payload.name}: {payload[0].value} alerts
                    </p>
                  </div>
                );
              }}
            />
            <Bar dataKey="count" radius={[0, 4, 4, 0]}>
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* 列表视图 */}
      {showDetails && (
        <div className="space-y-2">
          {filteredSources.map((source) => {
            const isExpanded = expanded.has(source.value);
            const Icon = source.type === 'ip' ? Server : Globe;

            return (
              <div
                key={source.value}
                className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden"
              >
                {/* Header */}
                <div
                  className="flex items-center justify-between p-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                  onClick={() => toggleExpand(source.value)}
                >
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    {/* 图标 */}
                    <div
                      className={`p-2 rounded-lg ${
                        source.severity === 'critical'
                          ? 'bg-red-100 dark:bg-red-900/30'
                          : source.severity === 'high'
                          ? 'bg-orange-100 dark:bg-orange-900/30'
                          : source.severity === 'medium'
                          ? 'bg-yellow-100 dark:bg-yellow-900/30'
                          : 'bg-blue-100 dark:bg-blue-900/30'
                      }`}
                    >
                      <Icon
                        className={`w-4 h-4 ${
                          source.severity === 'critical'
                            ? 'text-red-600 dark:text-red-400'
                            : source.severity === 'high'
                            ? 'text-orange-600 dark:text-orange-400'
                            : source.severity === 'medium'
                            ? 'text-yellow-600 dark:text-yellow-400'
                            : 'text-blue-600 dark:text-blue-400'
                        }`}
                      />
                    </div>

                    {/* 值和计数 */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-sm font-medium text-gray-900 dark:text-white truncate">
                          {source.value}
                        </span>
                        {source.country && (
                          <span className="text-xs text-gray-500 dark:text-gray-400">
                            {source.country}
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        {source.count} alert{source.count !== 1 ? 's' : ''}
                      </div>
                    </div>
                  </div>

                  {/* 展开按钮 */}
                  <button className="p-1 hover:bg-gray-200 dark:hover:bg-gray-600 rounded">
                    {isExpanded ? (
                      <ChevronUp className="w-4 h-4 text-gray-500" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-gray-500" />
                    )}
                  </button>
                </div>

                {/* 详情 */}
                {isExpanded && (
                  <div className="px-3 pb-3 pt-0 border-t border-gray-200 dark:border-gray-700">
                    <div className="grid grid-cols-2 gap-3 mt-3 text-xs">
                      <div>
                        <span className="text-gray-500 dark:text-gray-400">Type:</span>
                        <span className="ml-2 font-medium text-gray-900 dark:text-white capitalize">
                          {source.type}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-500 dark:text-gray-400">Severity:</span>
                        <span
                          className={`ml-2 font-medium capitalize ${
                            source.severity === 'critical'
                              ? 'text-red-600 dark:text-red-400'
                              : source.severity === 'high'
                              ? 'text-orange-600 dark:text-orange-400'
                              : source.severity === 'medium'
                              ? 'text-yellow-600 dark:text-yellow-400'
                              : 'text-blue-600 dark:text-blue-400'
                          }`}
                        >
                          {source.severity}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-500 dark:text-gray-400">First Seen:</span>
                        <span className="ml-2 text-gray-900 dark:text-white">
                          {new Date(source.first_seen).toLocaleDateString()}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-500 dark:text-gray-400">Last Seen:</span>
                        <span className="ml-2 text-gray-900 dark:text-white">
                          {new Date(source.last_seen).toLocaleDateString()}
                        </span>
                      </div>
                    </div>

                    {/* 快速操作 */}
                    <div className="flex gap-2 mt-3">
                      <button
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 text-xs font-medium rounded hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors"
                        onClick={(e) => {
                          e.stopPropagation();
                          // TODO: Block IP
                        }}
                      >
                        <Server className="w-3 h-3" />
                        Block IP
                      </button>
                      <button
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 text-xs font-medium rounded hover:bg-blue-100 dark:hover:bg-blue-900/30 transition-colors"
                        onClick={(e) => {
                          e.stopPropagation();
                          // TODO: View details
                        }}
                      >
                        <ExternalLink className="w-3 h-3" />
                        Details
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// 简化版：仅显示列表
export function SimpleTopSources({
  sources,
  limit = 5,
  type = 'both',
}: {
  sources: ThreatSource[];
  limit?: number;
  type?: 'ip' | 'domain' | 'both';
}) {
  const filteredSources = sources
    .filter(s => type === 'both' || s.type === type)
    .slice(0, limit);

  if (filteredSources.length === 0) {
    return null;
  }

  return (
    <div className="space-y-2">
      {filteredSources.map((source) => {
        const Icon = source.type === 'ip' ? Server : Globe;

        return (
          <div
            key={source.value}
            className="flex items-center gap-3 p-2 bg-gray-50 dark:bg-gray-900/50 rounded-lg"
          >
            <Icon
              className={`w-4 h-4 ${
                source.severity === 'critical'
                  ? 'text-red-500'
                  : source.severity === 'high'
                  ? 'text-orange-500'
                  : 'text-yellow-500'
              }`}
            />
            <div className="flex-1 min-w-0">
              <div className="font-mono text-sm text-gray-900 dark:text-white truncate">
                {source.value}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">
                {source.count} alert{source.count !== 1 ? 's' : ''}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
