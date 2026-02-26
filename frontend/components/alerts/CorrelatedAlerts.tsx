'use client';

/**
 * CorrelatedAlerts Component
 * 关联告警视图
 */

import React, { useState } from 'react';
import { Link2, AlertTriangle, TrendingUp, Clock, ChevronDown, ChevronRight } from 'lucide-react';
import { AlertCard, SeverityBadge } from '@/components/AlertStatusBadge';

interface CorrelationGroup {
  id: string;
  name: string;
  description: string;
  correlation_type: 'temporal' | 'attack_chain' | 'threat_intel' | 'asset_based';
  confidence: number;
  alerts: CorrelatedAlert[];
  created_at: string;
  common_indicators: {
    type: 'ip' | 'domain' | 'hash' | 'agent' | 'user';
    value: string;
    count: number;
  }[];
  mitre_tactics?: string[];
}

interface CorrelatedAlert {
  id: string;
  title: string;
  description?: string;
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  status: 'new' | 'investigating' | 'resolved' | 'false_positive';
  source: string;
  timestamp: string;
  event_type: string;
}

interface CorrelatedAlertsProps {
  groups: CorrelationGroup[];
  onAlertClick?: (alertId: string) => void;
}

const CORRELATION_TYPE_CONFIG = {
  temporal: {
    label: 'Time-based Correlation',
    icon: Clock,
    color: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
    description: 'Alerts occurred within a short time window',
  },
  attack_chain: {
    label: 'Attack Chain',
    icon: TrendingUp,
    color: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
    description: 'Alerts form part of a multi-stage attack',
  },
  threat_intel: {
    label: 'Threat Intelligence',
    icon: AlertTriangle,
    color: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300',
    description: 'Alerts share known threat indicators',
  },
  asset_based: {
    label: 'Asset-based',
    icon: Link2,
    color: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300',
    description: 'Alerts target the same asset or host',
  },
};

export function CorrelatedAlerts({ groups, onAlertClick }: CorrelatedAlertsProps) {
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());

  const toggleGroup = (groupId: string) => {
    setExpandedGroups(prev => {
      const next = new Set(prev);
      if (next.has(groupId)) {
        next.delete(groupId);
      } else {
        next.add(groupId);
      }
      return next;
    });
  };

  if (!groups || groups.length === 0) {
    return (
      <div className="text-center py-8 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-dashed border-gray-300 dark:border-gray-700">
        <Link2 className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
        <p className="text-sm text-gray-500 dark:text-gray-400">
          No correlated alerts found
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Link2 className="w-5 h-5 text-blue-600 dark:text-blue-400" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Correlated Alerts
          </h3>
        </div>
        <span className="text-sm text-gray-500 dark:text-gray-400">
          {groups.length} correlation group{groups.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Correlation Groups */}
      <div className="space-y-3">
        {groups.map((group) => {
          const config = CORRELATION_TYPE_CONFIG[group.correlation_type];
          const Icon = config.icon;
          const isExpanded = expandedGroups.has(group.id);

          return (
            <div
              key={group.id}
              className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden"
            >
              {/* Group Header */}
              <div
                className="px-4 py-3 bg-gray-50 dark:bg-gray-900/50 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-900 transition-colors"
                onClick={() => toggleGroup(group.id)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    {/* Expand Icon */}
                    <button className="flex-shrink-0">
                      {isExpanded ? (
                        <ChevronDown className="w-4 h-4 text-gray-500" />
                      ) : (
                        <ChevronRight className="w-4 h-4 text-gray-500" />
                      )}
                    </button>

                    {/* Correlation Type Badge */}
                    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${config.color} flex-shrink-0`}>
                      <Icon className="w-3 h-3" />
                      {config.label}
                    </span>

                    {/* Group Info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <h4 className="text-sm font-semibold text-gray-900 dark:text-white truncate">
                          {group.name}
                        </h4>
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                          group.confidence >= 80
                            ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300'
                            : group.confidence >= 50
                            ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300'
                            : 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300'
                        }`}>
                          {group.confidence}% confidence
                        </span>
                      </div>
                      <p className="text-xs text-gray-600 dark:text-gray-400 mt-0.5 truncate">
                        {group.description}
                      </p>
                    </div>

                    {/* Alert Count */}
                    <span className="text-sm font-semibold text-gray-900 dark:text-white flex-shrink-0">
                      {group.alerts.length}
                      <span className="text-gray-500 dark:text-gray-400 font-normal ml-1">
                        alerts
                      </span>
                    </span>
                  </div>
                </div>
              </div>

              {/* Expanded Content */}
              {isExpanded && (
                <div className="border-t border-gray-200 dark:border-gray-700">
                  {/* Common Indicators */}
                  {group.common_indicators && group.common_indicators.length > 0 && (
                    <div className="px-4 py-3 bg-blue-50 dark:bg-blue-900/20 border-b border-gray-200 dark:border-gray-700">
                      <div className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Common Indicators
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {group.common_indicators.map((indicator, index) => (
                          <span
                            key={index}
                            className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-white dark:bg-gray-800 rounded-lg text-xs border border-blue-200 dark:border-blue-800"
                          >
                            <span className="font-mono text-blue-700 dark:text-blue-300">
                              {indicator.value}
                            </span>
                            <span className="text-gray-500 dark:text-gray-400">
                              ({indicator.count})
                            </span>
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* MITRE Tactics */}
                  {group.mitre_tactics && group.mitre_tactics.length > 0 && (
                    <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
                      <div className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">
                        MITRE ATT&CK Tactics
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {group.mitre_tactics.map((tactic, index) => (
                          <span
                            key={index}
                            className="px-2 py-1 bg-purple-50 dark:bg-purple-900/20 text-purple-700 dark:text-purple-300 text-xs rounded border border-purple-200 dark:border-purple-800"
                          >
                            {tactic}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Alerts List */}
                  <div className="p-4 space-y-2">
                    {group.alerts.map((alert) => (
                      <div
                        key={alert.id}
                        className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-3 hover:bg-gray-100 dark:hover:bg-gray-900 transition-colors cursor-pointer"
                        onClick={() => onAlertClick?.(alert.id)}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <SeverityBadge severity={alert.severity} size="sm" />
                              <span className="text-xs text-gray-500 dark:text-gray-400">
                                {alert.source}
                              </span>
                              <span className="text-gray-300 dark:text-gray-600">•</span>
                              <span className="text-xs text-gray-500 dark:text-gray-400">
                                {new Date(alert.timestamp).toLocaleString()}
                              </span>
                            </div>
                            <h5 className="text-sm font-medium text-gray-900 dark:text-white truncate">
                              {alert.title}
                            </h5>
                            {alert.description && (
                              <p className="text-xs text-gray-600 dark:text-gray-400 mt-0.5 line-clamp-2">
                                {alert.description}
                              </p>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Footer */}
                  <div className="px-4 py-2 bg-gray-50 dark:bg-gray-900/50 border-t border-gray-200 dark:border-gray-700">
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      Correlation detected {new Date(group.created_at).toLocaleString()}
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// 简化版：仅显示关联告警列表
export function SimpleCorrelationList({ groups, onAlertClick }: CorrelatedAlertsProps) {
  if (!groups || groups.length === 0) {
    return null;
  }

  const allAlerts = groups.flatMap(group => group.alerts);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
          Related Alerts ({allAlerts.length})
        </h4>
        <Link2 className="w-4 h-4 text-gray-400" />
      </div>

      <div className="space-y-2">
        {allAlerts.slice(0, 5).map((alert) => (
          <div
            key={alert.id}
            className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-3 hover:bg-gray-100 dark:hover:bg-gray-900 transition-colors cursor-pointer"
            onClick={() => onAlertClick?.(alert.id)}
          >
            <div className="flex items-center gap-2 mb-1">
              <SeverityBadge severity={alert.severity} size="sm" />
              <span className="text-xs text-gray-500 dark:text-gray-400">
                {new Date(alert.timestamp).toLocaleString()}
              </span>
            </div>
            <h5 className="text-sm font-medium text-gray-900 dark:text-white truncate">
              {alert.title}
            </h5>
          </div>
        ))}

        {allAlerts.length > 5 && (
          <div className="text-center py-2">
            <button className="text-xs text-blue-600 dark:text-blue-400 hover:underline">
              View all {allAlerts.length} related alerts
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
