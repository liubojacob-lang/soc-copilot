'use client';

/**
 * AlertStatusBadge Component
 * 告警状态徽章组件
 */

import React from 'react';

export type AlertStatus = 'new' | 'investigating' | 'resolved' | 'false_positive' | 'escalated';
export type AlertSeverity = 'critical' | 'high' | 'medium' | 'low' | 'info';

interface AlertStatusBadgeProps {
  status: AlertStatus;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

const statusConfig = {
  new: {
    label: 'New',
    color: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
    dotColor: 'bg-blue-500',
  },
  investigating: {
    label: 'Investigating',
    color: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
    dotColor: 'bg-yellow-500',
  },
  resolved: {
    label: 'Resolved',
    color: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    dotColor: 'bg-green-500',
  },
  false_positive: {
    label: 'False Positive',
    color: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200',
    dotColor: 'bg-gray-500',
  },
  escalated: {
    label: 'Escalated',
    color: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
    dotColor: 'bg-red-500',
  },
};

const sizeStyles = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-2.5 py-1 text-sm',
  lg: 'px-3 py-1.5 text-base',
};

const dotSize = {
  sm: 'w-1.5 h-1.5',
  md: 'w-2 h-2',
  lg: 'w-2.5 h-2.5',
};

export function AlertStatusBadge({
  status,
  size = 'md',
  showLabel = true,
}: AlertStatusBadgeProps) {
  const config = statusConfig[status] || statusConfig.new;
  const sizeClass = sizeStyles[size];
  const dotClass = dotSize[size];

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-medium ${config.color} ${sizeClass}`}
    >
      <span className={`rounded-full ${dotClass} ${config.dotColor}`} />
      {showLabel && config.label}
    </span>
  );
}

interface SeverityBadgeProps {
  severity: AlertSeverity;
  size?: 'sm' | 'md' | 'lg';
  showScore?: boolean;
  score?: number;
}

const severityConfig = {
  critical: {
    label: 'Critical',
    color: 'bg-red-100 text-red-800 dark:bg-red-900/50 dark:text-red-200 border-red-300 dark:border-red-700',
    borderColor: 'border-red-500',
    icon: '🔴',
  },
  high: {
    label: 'High',
    color: 'bg-orange-100 text-orange-800 dark:bg-orange-900/50 dark:text-orange-200 border-orange-300 dark:border-orange-700',
    borderColor: 'border-orange-500',
    icon: '🟠',
  },
  medium: {
    label: 'Medium',
    color: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/50 dark:text-yellow-200 border-yellow-300 dark:border-yellow-700',
    borderColor: 'border-yellow-500',
    icon: '🟡',
  },
  low: {
    label: 'Low',
    color: 'bg-blue-100 text-blue-800 dark:bg-blue-900/50 dark:text-blue-200 border-blue-300 dark:border-blue-700',
    borderColor: 'border-blue-500',
    icon: '🔵',
  },
  info: {
    label: 'Info',
    color: 'bg-gray-100 text-gray-800 dark:bg-gray-900/50 dark:text-gray-200 border-gray-300 dark:border-gray-700',
    borderColor: 'border-gray-500',
    icon: '⚪',
  },
};

export function SeverityBadge({
  severity,
  size = 'md',
  showScore = false,
  score,
}: SeverityBadgeProps) {
  const config = severityConfig[severity] || severityConfig.info;
  const sizeClass = sizeStyles[size];

  return (
    <div className="flex items-center gap-2">
      <span
        className={`inline-flex items-center gap-1.5 rounded-full border-2 ${config.color} ${config.borderColor} ${sizeClass} font-semibold`}
      >
        <span>{config.icon}</span>
        {config.label}
      </span>
      {showScore && score !== undefined && (
        <span className="text-sm font-mono text-gray-600 dark:text-gray-400">
          ({score})
        </span>
      )}
    </div>
  );
}

// 告警卡片组件
interface AlertCardProps {
  alert: {
    id: string;
    title: string;
    description?: string;
    severity: AlertSeverity;
    status: AlertStatus;
    source: string;
    event_type: string;
    timestamp: string;
    threat_score?: number;
  };
  onClick?: () => void;
  size?: 'sm' | 'md' | 'lg';
  showActions?: boolean;
  actions?: React.ReactNode;
}

export function AlertCard({
  alert,
  onClick,
  size = 'md',
  showActions = false,
  actions,
}: AlertCardProps) {
  const timeSince = (timestamp: string) => {
    const now = new Date();
    const then = new Date(timestamp);
    const diffMs = now.getTime() - then.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${diffDays}d ago`;
  };

  return (
    <div
      className={`
        bg-white dark:bg-gray-800 rounded-lg shadow-md hover:shadow-lg
        transition-all duration-200 cursor-pointer border-l-4
        ${
          alert.severity === 'critical'
            ? 'border-red-500'
            : alert.severity === 'high'
            ? 'border-orange-500'
            : alert.severity === 'medium'
            ? 'border-yellow-500'
            : 'border-blue-500'
        }
        ${size === 'sm' ? 'p-3' : size === 'lg' ? 'p-5' : 'p-4'}
      `}
      onClick={onClick}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <SeverityBadge severity={alert.severity} size="sm" />
            <AlertStatusBadge status={alert.status} size="sm" />
          </div>

          <h3 className={`font-semibold text-gray-900 dark:text-white truncate ${
            size === 'sm' ? 'text-sm' : size === 'lg' ? 'text-lg' : 'text-base'
          }`}>
            {alert.title}
          </h3>

          {alert.description && (
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1 line-clamp-2">
              {alert.description}
            </p>
          )}

          <div className="flex items-center gap-3 mt-2 text-xs text-gray-500 dark:text-gray-500">
            <span className="font-mono">{alert.source}</span>
            <span>•</span>
            <span>{alert.event_type}</span>
            <span>•</span>
            <span>{timeSince(alert.timestamp)}</span>
          </div>
        </div>

        {showActions && (
          <div className="flex-shrink-0">
            {actions}
          </div>
        )}
      </div>
    </div>
  );
}
