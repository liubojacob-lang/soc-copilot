"use client";

import { useTranslations } from "next-intl";
import { TrendingUp, TrendingDown, Activity, AlertTriangle } from "lucide-react";

interface AuditStatsProps {
  stats: {
    total_requests: number;
    last_24h_requests: number;
    failed_requests: number;
  } | null;
  loading: boolean;
}

export function AuditStats({ stats, loading }: AuditStatsProps) {
  const t = useTranslations("auditPage");

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        {[1, 2, 3].map((i) => (
          <div key={i} className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 animate-pulse">
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/3 mb-2"></div>
            <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
          </div>
        ))}
      </div>
    );
  }

  if (!stats) {
    return null;
  }

  const { total_requests, last_24h_requests, failed_requests } = stats;

  // Calculate percentages
  const failureRate = total_requests > 0 ? (failed_requests / total_requests) * 100 : 0;
  const dailyRate = total_requests > 0 ? (last_24h_requests / total_requests) * 100 : 0;

  const statCards = [
    {
      title: t("stats.totalRequests"),
      value: total_requests.toLocaleString(),
      icon: Activity,
      iconColor: "text-blue-500",
      bgColor: "bg-blue-50 dark:bg-blue-900/20",
      trend: null,
    },
    {
      title: t("stats.last24h"),
      value: last_24h_requests.toLocaleString(),
      icon: TrendingUp,
      iconColor: "text-green-500",
      bgColor: "bg-green-50 dark:bg-green-900/20",
      trend: dailyRate > 10 ? "up" : dailyRate > 5 ? "stable" : "down",
      trendValue: `${dailyRate.toFixed(1)}%`,
    },
    {
      title: t("stats.failedRequests"),
      value: failed_requests.toLocaleString(),
      icon: AlertTriangle,
      iconColor: "text-red-500",
      bgColor: "bg-red-50 dark:bg-red-900/20",
      trend: failureRate > 5 ? "high" : failureRate > 2 ? "moderate" : "low",
      trendValue: `${failureRate.toFixed(1)}%`,
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
      {statCards.map((card, index) => (
        <div
          key={index}
          className={`${card.bgColor} rounded-lg shadow p-6 border border-gray-200 dark:border-gray-700`}
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-gray-600 dark:text-gray-300">{card.title}</h3>
            <div className={`p-2 rounded-full ${card.bgColor}`}>
              <card.icon className={`h-5 w-5 ${card.iconColor}`} />
            </div>
          </div>

          <div className="flex items-end justify-between">
            <div>
              <p className="text-3xl font-bold text-gray-900 dark:text-white">{card.value}</p>
              {card.trend && (
                <div className="flex items-center mt-2">
                  {card.trend === "up" || card.trend === "high" ? (
                    <TrendingUp className="h-4 w-4 text-green-500 mr-1" />
                  ) : card.trend === "down" || card.trend === "low" ? (
                    <TrendingDown className="h-4 w-4 text-red-500 mr-1" />
                  ) : null}
                  <span
                    className={`text-sm font-medium ${
                      card.trend === "up" || card.trend === "high"
                        ? "text-green-600 dark:text-green-400"
                        : card.trend === "down" || card.trend === "low"
                          ? "text-red-600 dark:text-red-400"
                          : "text-yellow-600 dark:text-yellow-400"
                    }`}
                  >
                    {card.trendValue}
                  </span>
                </div>
              )}
            </div>

            {card.trend && (
              <div className="text-xs font-medium px-2 py-1 rounded-full bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300">
                {card.trend === "up"
                  ? t("stats.trendUp")
                  : card.trend === "down"
                    ? t("stats.trendDown")
                    : card.trend === "high"
                      ? t("stats.rateHigh")
                      : card.trend === "moderate"
                        ? t("stats.rateModerate")
                        : t("stats.rateLow")}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
