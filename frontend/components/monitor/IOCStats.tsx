"use client";

/**
 * IOCStats Component
 * IOC 统计和趋势
 */

import React, { useMemo } from "react";
import { useTranslations } from "next-intl";
import { Shield, AlertTriangle, CheckCircle, HelpCircle } from "lucide-react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts";

interface IOCStats {
  total: number;
  malicious: number;
  suspicious: number;
  benign: number;
  unknown: number;
}

interface IOCBreakdown {
  type: "ip" | "domain" | "url" | "hash" | "email";
  total: number;
  malicious: number;
  suspicious: number;
  trend: "up" | "down" | "stable";
}

interface IOCStatsProps {
  stats: IOCStats;
  breakdown?: IOCBreakdown[];
  showTrend?: boolean;
}

const REPUTATION_COLORS = {
  malicious: "#dc2626",
  suspicious: "#f97316",
  benign: "#22c55e",
  unknown: "#6b7280",
};

const REPUTATION_CONFIG = {
  malicious: {
    label: "Malicious",
    icon: AlertTriangle,
    color: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
    iconColor: "text-red-500",
  },
  suspicious: {
    label: "Suspicious",
    icon: Shield,
    color: "bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300",
    iconColor: "text-orange-500",
  },
  benign: {
    label: "Benign",
    icon: CheckCircle,
    color: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
    iconColor: "text-green-500",
  },
  unknown: {
    label: "Unknown",
    icon: HelpCircle,
    color: "bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300",
    iconColor: "text-gray-500",
  },
};

const TYPE_ICONS = {
  ip: "🌐",
  domain: "🔗",
  url: "📄",
  hash: "🔐",
  email: "📧",
};

export const IOCStats = React.memo(function IOCStats({
  stats,
  breakdown,
  showTrend = true,
}: IOCStatsProps) {
  const tReputation = useTranslations("reputation");
  const tCommon = useTranslations("common");
  const tMonitor = useTranslations("monitor");
  const tSeverity = useTranslations("severity");
  const tIoc = useTranslations("ioc");

  // 使用 useMemo 创建 REPUTATION_CONFIG，使其可以访问翻译函数
  const reputationConfig = useMemo(
    () => ({
      malicious: {
        label: tReputation("malicious"),
        icon: AlertTriangle,
        color: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
        iconColor: "text-red-500",
      },
      suspicious: {
        label: tReputation("suspicious"),
        icon: Shield,
        color: "bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300",
        iconColor: "text-orange-500",
      },
      benign: {
        label: tReputation("benign"),
        icon: CheckCircle,
        color: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
        iconColor: "text-green-500",
      },
      unknown: {
        label: tReputation("unknown"),
        icon: HelpCircle,
        color: "bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300",
        iconColor: "text-gray-500",
      },
    }),
    [tReputation]
  );

  // 饼图数据
  const chartData = useMemo(() => {
    return [
      {
        name: tReputation("malicious"),
        value: stats.malicious,
        color: REPUTATION_COLORS.malicious,
      },
      {
        name: tReputation("suspicious"),
        value: stats.suspicious,
        color: REPUTATION_COLORS.suspicious,
      },
      { name: tReputation("benign"), value: stats.benign, color: REPUTATION_COLORS.benign },
      { name: tReputation("unknown"), value: stats.unknown, color: REPUTATION_COLORS.unknown },
    ].filter((item) => item.value > 0);
  }, [stats, tReputation]);

  // 自定义 Tooltip
  const CustomTooltip = ({
    active,
    payload,
  }: {
    active?: boolean;
    payload?: Array<{ value: number; name: string; color: string; payload: { color: string } }>;
  }) => {
    if (!active || !payload || !payload.length) return null;

    const data = payload[0];
    const percentage = ((data.value / stats.total) * 100).toFixed(1);

    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 p-3">
        <div className="flex items-center gap-2 mb-1">
          <div className="w-3 h-3 rounded-full" style={{ backgroundColor: data.color }} />
          <span className="text-sm font-medium text-gray-900 dark:text-white">{data.name}</span>
        </div>
        <div className="space-y-1 text-xs">
          <div className="flex justify-between gap-4">
            <span className="text-gray-600 dark:text-gray-400">{tMonitor("count")}:</span>
            <span className="font-semibold text-gray-900 dark:text-white">{data.value}</span>
          </div>
          <div className="flex justify-between gap-4">
            <span className="text-gray-600 dark:text-gray-400">{tMonitor("percentage")}:</span>
            <span className="font-semibold text-gray-900 dark:text-white">{percentage}%</span>
          </div>
        </div>
      </div>
    );
  };

  // 计算威胁百分比
  const threatPercentage = useMemo(() => {
    return ((stats.malicious + stats.suspicious) / stats.total) * 100;
  }, [stats]);

  return (
    <div className="space-y-6">
      {/* 总览卡片 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label={tIoc("totalIocs")} value={stats.total} icon={Shield} color="blue" />
        <StatCard
          label={tIoc("malicious")}
          value={stats.malicious}
          icon={AlertTriangle}
          color="red"
        />
        <StatCard
          label={tIoc("suspicious")}
          value={stats.suspicious}
          icon={Shield}
          color="orange"
        />
        <StatCard label={tIoc("benign")} value={stats.benign} icon={CheckCircle} color="green" />
      </div>

      {/* 威胁级别指示器 */}
      <div className="bg-gradient-to-r from-gray-50 to-gray-100 dark:from-gray-800 dark:to-gray-900 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
            {tMonitor("threatLevel")}
          </h4>
          <span
            className={`text-2xl font-bold ${
              threatPercentage >= 30
                ? "text-red-600 dark:text-red-400"
                : threatPercentage >= 15
                  ? "text-orange-600 dark:text-orange-400"
                  : "text-green-600 dark:text-green-400"
            }`}
          >
            {threatPercentage.toFixed(1)}%
          </span>
        </div>
        <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${
              threatPercentage >= 30
                ? "bg-red-500"
                : threatPercentage >= 15
                  ? "bg-orange-500"
                  : "bg-green-500"
            }`}
            style={{ width: `${Math.min(threatPercentage, 100)}%` }}
          />
        </div>
        <div className="flex justify-between mt-2 text-xs text-gray-600 dark:text-gray-400">
          <span>{tMonitor("safe")}</span>
          <span>{tMonitor("warning")}</span>
          <span>{tSeverity("critical")}</span>
        </div>
      </div>

      {/* 饼图和图例 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* 饼图 */}
        <div className="min-w-0">
          <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">
            {tMonitor("reputationDistribution")}
          </h4>
          <div className="w-full min-w-0 h-64">
            <ResponsiveContainer width="100%" height={256} minWidth={0}>
              <PieChart>
                <Pie
                  data={chartData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={2}
                  dataKey="value"
                >
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
                <Legend
                  verticalAlign="bottom"
                  height={36}
                  iconType="circle"
                  formatter={(value) => (
                    <span className="text-sm text-gray-700 dark:text-gray-300">{value}</span>
                  )}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 详细统计 */}
        <div className="space-y-3">
          <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">
            {tMonitor("breakdownByType")}
          </h4>
          {breakdown?.map((item) => (
            <IOCBreakdownCard key={item.type} data={item} showTrend={showTrend} />
          ))}
        </div>
      </div>
    </div>
  );
});

// Stat Card Component
function StatCard({
  label,
  value,
  icon: Icon,
  color,
}: {
  label: string;
  value: number;
  icon: React.ComponentType<{ className?: string }>;
  color: "blue" | "red" | "orange" | "green";
}) {
  const colorClasses = {
    blue: "bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 border-blue-200 dark:border-blue-800",
    red: "bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300 border-red-200 dark:border-red-800",
    orange:
      "bg-orange-50 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300 border-orange-200 dark:border-orange-800",
    green:
      "bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-300 border-green-200 dark:border-green-800",
  };

  return (
    <div className={`${colorClasses[color]} rounded-lg p-4 border`}>
      <Icon className={`w-5 h-5 mb-2 ${colorClasses[color].split(" ")[1]}`} />
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-xs opacity-80">{label}</div>
    </div>
  );
}

// IOC Breakdown Card
function IOCBreakdownCard({ data, showTrend }: { data: IOCBreakdown; showTrend: boolean }) {
  const config = REPUTATION_CONFIG;
  const maliciousPercent = data.total > 0 ? (data.malicious / data.total) * 100 : 0;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-3">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-lg">{TYPE_ICONS[data.type]}</span>
          <span className="text-sm font-medium text-gray-900 dark:text-white capitalize">
            {data.type}s
          </span>
        </div>
        {showTrend && <TrendIndicator trend={data.trend} />}
      </div>

      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs">
          <span className="text-gray-600 dark:text-gray-400">Total:</span>
          <span className="font-semibold text-gray-900 dark:text-white">{data.total}</span>
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="text-gray-600 dark:text-gray-400">Malicious:</span>
          <span className="font-semibold text-red-600 dark:text-red-400">{data.malicious}</span>
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="text-gray-600 dark:text-gray-400">Suspicious:</span>
          <span className="font-semibold text-orange-600 dark:text-orange-400">
            {data.suspicious}
          </span>
        </div>

        {/* 威胁百分比条 */}
        {data.total > 0 && (
          <div className="mt-2">
            <div className="h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-red-500 rounded-full transition-all duration-300"
                style={{ width: `${maliciousPercent}%` }}
              />
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              {maliciousPercent.toFixed(1)}% malicious
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// Trend Indicator
function TrendIndicator({ trend }: { trend: "up" | "down" | "stable" }) {
  if (trend === "stable") {
    return (
      <span className="flex items-center gap-1 text-xs text-gray-500">
        <span className="w-2 h-2 bg-gray-400 rounded-full" />
        Stable
      </span>
    );
  }

  const isUp = trend === "up";
  return (
    <span
      className={`flex items-center gap-1 text-xs ${isUp ? "text-red-600 dark:text-red-400" : "text-green-600 dark:text-green-400"}`}
    >
      <svg
        className={`w-3 h-3 ${isUp ? "rotate-0" : "rotate-180"}`}
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M5 10l7-7m0 0l7 7m-7-7v18"
        />
      </svg>
      {isUp ? "Increasing" : "Decreasing"}
    </span>
  );
}
