"use client";

/**
 * ThreatIntelCard Component
 * 威胁情报展示卡片
 */

import React from "react";
import { Shield, AlertTriangle, CheckCircle, Clock, Globe, Server } from "lucide-react";

interface IOC {
  type: "ip" | "domain" | "url" | "hash" | "email";
  value: string;
  reputation: "malicious" | "suspicious" | "benign" | "unknown";
  confidence: number;
  first_seen?: string;
  last_seen?: string;
  sources?: string[];
}

interface MITRETactic {
  tactic: string;
  techniques: string[];
}

interface ThreatIntelData {
  iocs: IOC[];
  mitre_tactics: MITRETactic[];
  threat_score: number;
  enrichment_status: "pending" | "enriched" | "failed";
  enriched_at?: string;
}

interface ThreatIntelCardProps {
  data: ThreatIntelData;
  onRefresh?: () => void;
}

const REPUTATION_CONFIG = {
  malicious: {
    color:
      "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300 border-red-300 dark:border-red-700",
    icon: AlertTriangle,
    label: "Malicious",
  },
  suspicious: {
    color:
      "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300 border-yellow-300 dark:border-yellow-700",
    icon: Clock,
    label: "Suspicious",
  },
  benign: {
    color:
      "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300 border-green-300 dark:border-green-700",
    icon: CheckCircle,
    label: "Benign",
  },
  unknown: {
    color:
      "bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300 border-gray-300 dark:border-gray-700",
    icon: Shield,
    label: "Unknown",
  },
};

const IOC_ICONS = {
  ip: Server,
  domain: Globe,
  url: Globe,
  hash: Shield,
  email: Shield,
};

export const ThreatIntelCard = React.memo(function ThreatIntelCard({
  data,
  onRefresh,
}: ThreatIntelCardProps) {
  const { iocs, mitre_tactics, threat_score, enrichment_status, enriched_at } = data;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Shield className="w-5 h-5 text-blue-600 dark:text-blue-400" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Threat Intelligence
          </h3>
        </div>

        <div className="flex items-center gap-3">
          {/* Enrichment Status */}
          <div
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
              enrichment_status === "enriched"
                ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300"
                : enrichment_status === "pending"
                  ? "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300"
                  : "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300"
            }`}
          >
            <div
              className={`w-1.5 h-1.5 rounded-full ${
                enrichment_status === "enriched"
                  ? "bg-green-500"
                  : enrichment_status === "pending"
                    ? "bg-yellow-500 animate-pulse"
                    : "bg-red-500"
              }`}
            />
            {enrichment_status}
          </div>

          {/* Refresh Button */}
          {onRefresh && (
            <button
              onClick={onRefresh}
              className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
              title="Refresh threat intelligence"
            >
              <svg
                className="w-4 h-4 text-gray-600 dark:text-gray-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* Threat Score */}
      <div className="bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-800 dark:to-gray-900 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-1">
              Threat Score
            </div>
            <div className="text-3xl font-bold text-gray-900 dark:text-white">
              {threat_score}/100
            </div>
          </div>

          {/* Score Gauge */}
          <div className="relative w-24 h-24">
            <svg className="w-full h-full transform -rotate-90">
              <circle
                cx="48"
                cy="48"
                r="40"
                stroke="currentColor"
                strokeWidth="8"
                fill="none"
                className="text-gray-200 dark:text-gray-700"
              />
              <circle
                cx="48"
                cy="48"
                r="40"
                stroke="currentColor"
                strokeWidth="8"
                fill="none"
                strokeDasharray={`${(threat_score / 100) * 251} 251`}
                className={`${
                  threat_score >= 70
                    ? "text-red-500"
                    : threat_score >= 40
                      ? "text-yellow-500"
                      : "text-green-500"
                }`}
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <Shield
                className={`w-8 h-8 ${
                  threat_score >= 70
                    ? "text-red-500"
                    : threat_score >= 40
                      ? "text-yellow-500"
                      : "text-green-500"
                }`}
              />
            </div>
          </div>
        </div>

        {enriched_at && (
          <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
            Last enriched: {new Date(enriched_at).toLocaleString()}
          </div>
        )}
      </div>

      {/* IOCs */}
      {iocs && iocs.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
            <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
              Indicators of Compromise ({iocs.length})
            </h4>
          </div>

          <div className="divide-y divide-gray-200 dark:divide-gray-700">
            {iocs.map((ioc, index) => {
              const Icon = IOC_ICONS[ioc.type] || Shield;
              const config = REPUTATION_CONFIG[ioc.reputation];
              const ReputationIcon = config.icon;

              return (
                <div
                  key={index}
                  className="px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3 flex-1 min-w-0">
                      <Icon className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />

                      <div className="flex-1 min-w-0">
                        <div className="font-mono text-sm text-gray-900 dark:text-white break-all">
                          {ioc.value}
                        </div>

                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-xs text-gray-500 dark:text-gray-400 uppercase">
                            {ioc.type}
                          </span>

                          {ioc.first_seen && (
                            <>
                              <span className="text-gray-300 dark:text-gray-600">•</span>
                              <span className="text-xs text-gray-500 dark:text-gray-400">
                                First: {new Date(ioc.first_seen).toLocaleDateString()}
                              </span>
                            </>
                          )}

                          {ioc.last_seen && (
                            <>
                              <span className="text-gray-300 dark:text-gray-600">•</span>
                              <span className="text-xs text-gray-500 dark:text-gray-400">
                                Last: {new Date(ioc.last_seen).toLocaleDateString()}
                              </span>
                            </>
                          )}
                        </div>

                        {ioc.sources && ioc.sources.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-2">
                            {ioc.sources.map((source, i) => (
                              <span
                                key={i}
                                className="px-2 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 text-xs rounded"
                              >
                                {source}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="flex flex-col items-end gap-2 flex-shrink-0">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium border ${config.color}`}
                      >
                        <ReputationIcon className="w-3 h-3" />
                        {config.label}
                      </span>

                      {ioc.confidence > 0 && (
                        <div className="text-xs text-gray-500 dark:text-gray-400">
                          {ioc.confidence}% confidence
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* MITRE ATT&CK */}
      {mitre_tactics && mitre_tactics.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
            <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
              MITRE ATT&CK Tactics
            </h4>
          </div>

          <div className="p-4 space-y-3">
            {mitre_tactics.map((item, index) => (
              <div key={index} className="border-l-4 border-blue-500 pl-3">
                <div className="font-medium text-sm text-gray-900 dark:text-white">
                  {item.tactic}
                </div>
                <div className="flex flex-wrap gap-1.5 mt-1.5">
                  {item.techniques.map((technique, i) => (
                    <span
                      key={i}
                      className="px-2 py-0.5 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 text-xs rounded border border-blue-200 dark:border-blue-800"
                    >
                      {technique}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {(!iocs || iocs.length === 0) && (!mitre_tactics || mitre_tactics.length === 0) && (
        <div className="text-center py-8 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-dashed border-gray-300 dark:border-gray-700">
          <Shield className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
          <p className="text-sm text-gray-500 dark:text-gray-400">
            No threat intelligence data available
          </p>
          {onRefresh && (
            <button
              onClick={onRefresh}
              className="mt-3 px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
            >
              Enrich Now
            </button>
          )}
        </div>
      )}
    </div>
  );
});
