"use client";

/**
 * TimelineView Component
 * 告警时间线视图
 */

import React from "react";
import { useFormatter } from "next-intl";
import {
  Clock,
  Activity,
  User,
  Shield,
  AlertTriangle,
  CheckCircle,
  TrendingUp,
} from "lucide-react";

interface TimelineEvent {
  id: string;
  timestamp: string;
  event_type:
    | "created"
    | "status_changed"
    | "assigned"
    | "enriched"
    | "correlated"
    | "escalated"
    | "resolved"
    | "noted";
  description: string;
  user?: string;
  details?: Record<string, any>;
}

interface TimelineViewProps {
  events: TimelineEvent[];
  showEmpty?: boolean;
}

const EVENT_CONFIG = {
  created: {
    icon: Activity,
    color:
      "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300 border-blue-300 dark:border-blue-700",
    label: "Alert Created",
  },
  status_changed: {
    icon: CheckCircle,
    color:
      "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300 border-green-300 dark:border-green-700",
    label: "Status Changed",
  },
  assigned: {
    icon: User,
    color:
      "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300 border-purple-300 dark:border-purple-700",
    label: "Assigned",
  },
  enriched: {
    icon: Shield,
    color:
      "bg-cyan-100 text-cyan-800 dark:bg-cyan-900/30 dark:text-cyan-300 border-cyan-300 dark:border-cyan-700",
    label: "Threat Intel Enriched",
  },
  correlated: {
    icon: TrendingUp,
    color:
      "bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300 border-orange-300 dark:border-orange-700",
    label: "Correlated",
  },
  escalated: {
    icon: AlertTriangle,
    color:
      "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300 border-red-300 dark:border-red-700",
    label: "Escalated",
  },
  resolved: {
    icon: CheckCircle,
    color:
      "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300 border-green-300 dark:border-green-700",
    label: "Resolved",
  },
  noted: {
    icon: Activity,
    color:
      "bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300 border-gray-300 dark:border-gray-700",
    label: "Note Added",
  },
};

export const TimelineView = React.memo(function TimelineView({
  events,
  showEmpty = true,
}: TimelineViewProps) {
  const format = useFormatter();
  if (!events || events.length === 0) {
    return showEmpty ? (
      <div className="text-center py-8 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-dashed border-gray-300 dark:border-gray-700">
        <Clock className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
        <p className="text-sm text-gray-500 dark:text-gray-400">No timeline events yet</p>
      </div>
    ) : null;
  }

  // 按时间排序（最新的在上面）
  const sortedEvents = [...events].sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  );

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Clock className="w-5 h-5 text-gray-600 dark:text-gray-400" />
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Timeline</h3>
        <span className="text-sm text-gray-500 dark:text-gray-400">({events.length} events)</span>
      </div>

      {/* Timeline */}
      <div className="relative">
        {/* Vertical Line */}
        <div className="absolute left-[19px] top-0 bottom-0 w-0.5 bg-gray-200 dark:bg-gray-700" />

        {/* Events */}
        <div className="space-y-4">
          {sortedEvents.map((event, index) => {
            const config = EVENT_CONFIG[event.event_type];
            const Icon = config.icon;

            return (
              <div key={event.id} className="relative flex items-start gap-4">
                {/* Icon */}
                <div
                  className={`
                  relative z-10 flex-shrink-0 w-10 h-10 rounded-full border-2
                  flex items-center justify-center
                  ${config.color}
                `}
                >
                  <Icon className="w-4 h-4" />
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-3 hover:shadow-md transition-shadow">
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-gray-900 dark:text-white">
                          {config.label}
                        </span>
                        {event.user && (
                          <span className="text-xs text-gray-500 dark:text-gray-400">
                            by {event.user}
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-gray-600 dark:text-gray-400 mt-0.5">
                        {event.description}
                      </p>
                    </div>
                    <span className="text-xs text-gray-500 dark:text-gray-400 flex-shrink-0">
                      {formatRelativeTime(event.timestamp, format)}
                    </span>
                  </div>

                  {/* Details */}
                  {event.details && Object.keys(event.details).length > 0 && (
                    <div className="mt-2 pt-2 border-t border-gray-100 dark:border-gray-700">
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        {Object.entries(event.details).map(([key, value]) => (
                          <div key={key} className="flex items-center gap-2">
                            <span className="text-gray-500 dark:text-gray-400 capitalize">
                              {key.replace(/_/g, " ")}:
                            </span>
                            <span className="font-medium text-gray-900 dark:text-white">
                              {formatValue(value)}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
});

// 简化版：仅显示最近事件
export function RecentTimeline({ events, limit = 5 }: TimelineViewProps & { limit?: number }) {
  const format = useFormatter();
  if (!events || events.length === 0) {
    return null;
  }

  const recentEvents = [...events]
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
    .slice(0, limit);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-gray-900 dark:text-white">Recent Activity</h4>
        <Clock className="w-4 h-4 text-gray-400" />
      </div>

      <div className="space-y-2">
        {recentEvents.map((event) => {
          const config = EVENT_CONFIG[event.event_type];
          const Icon = config.icon;

          return (
            <div key={event.id} className="flex items-start gap-3">
              <div
                className={`flex-shrink-0 w-8 h-8 rounded-full border flex items-center justify-center ${config.color}`}
              >
                <Icon className="w-3.5 h-3.5" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="text-xs font-medium text-gray-900 dark:text-white">
                    {config.label}
                  </span>
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    {formatRelativeTime(event.timestamp, format)}
                  </span>
                </div>
                <p className="text-xs text-gray-600 dark:text-gray-400 line-clamp-1">
                  {event.description}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// Helper Functions
function formatRelativeTime(timestamp: string, format: ReturnType<typeof useFormatter>): string {
  const now = new Date();
  const then = new Date(timestamp);
  const diffMs = now.getTime() - then.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return format.dateTime(then, { dateStyle: "medium" });
}

function formatValue(value: unknown): string {
  if (typeof value === "boolean") {
    return value ? "Yes" : "No";
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}
