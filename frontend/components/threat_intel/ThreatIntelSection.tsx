"use client";

import { ThreatIntelAnalysis, Verdict } from "@/lib/api";
import { useTranslations } from "next-intl";
import { useState } from "react";

interface ThreatIntelSectionProps {
  threatIntel: ThreatIntelAnalysis;
}

export function ThreatIntelSection({ threatIntel }: ThreatIntelSectionProps) {
  const t = useTranslations('threatIntel');
  const [expandedItem, setExpandedItem] = useState<string | null>(null);
  const [showFiltered, setShowFiltered] = useState(false);

  const getVerdictColor = (verdict: Verdict) => {
    switch (verdict) {
      case "malicious": return "bg-red-600 text-white";
      case "suspicious": return "bg-orange-500 text-white";
      case "unknown": return "bg-gray-500 text-white";
      case "benign": return "bg-green-500 text-white";
      default: return "bg-gray-400 text-white";
    }
  };

  const getVerdictIcon = (verdict: Verdict) => {
    switch (verdict) {
      case "malicious": return "⚠️";
      case "suspicious": return "⚡";
      case "unknown": return "❓";
      case "benign": return "✓";
      default: return "?";
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 70) return "text-red-600";
    if (score >= 40) return "text-orange-600";
    if (score > 0) return "text-yellow-600";
    return "text-green-600";
  };

  const getFilterReasonLabel = (reason?: string) => {
    switch (reason) {
      case "private_ip": return "Private IP";
      case "internal_domain": return t('internalDomain');
      case "blocked_tld": return "Blocked TLD";
      case "url_private_ip_host": return "Private IP in URL";
      case "url_internal_domain": return "Internal Domain in URL";
      case "url_blocked_tld": return "Blocked TLD in URL";
      case "rate_limit": return t('rateLimited');
      default: return reason || "Filtered";
    }
  };

  if (threatIntel.disabled) {
    return (
      <div className="mt-4 border rounded-lg p-4 bg-gray-50">
        <h4 className="text-sm font-medium mb-2 flex items-center text-gray-500">
          <span className="mr-2">🛡️</span>
          Threat Intel (OTX)
        </h4>
        <div className="text-sm text-gray-400 italic">
          External threat intelligence is disabled. Configure ALLOW_EXTERNAL_TI=true and OTX_API_KEY to enable.
        </div>
      </div>
    );
  }

  if (threatIntel.degraded) {
    return (
      <div className="mt-4 border rounded-lg p-4 bg-yellow-50">
        <h4 className="text-sm font-medium mb-2 flex items-center text-yellow-700">
          <span className="mr-2">🛡️</span>
          Threat Intel (OTX)
          <span className="ml-2 px-2 py-0.5 bg-yellow-200 text-yellow-800 text-xs rounded">
            DEGRADED
          </span>
        </h4>
        <div className="text-sm text-yellow-700">
          {threatIntel.error_reason || "Threat intelligence lookup failed. Please try again."}
        </div>
      </div>
    );
  }

  const hasFilteredItems = threatIntel.filtered_items && threatIntel.filtered_items.length > 0;

  return (
    <div className="mt-4 border rounded-lg p-4 bg-gray-50">
      <h4 className="text-sm font-medium mb-3 flex items-center">
        <span className="mr-2">🛡️</span>
        Threat Intel (OTX)
        {(threatIntel as any).cached !== undefined && (
          <span className="ml-2 text-xs text-gray-400">
            {threatIntel.items.some((i: any) => i.cached) ? "(部分来自缓存)" : ""}
          </span>
        )}
        {threatIntel.skipped && (
          <span className="ml-2 px-2 py-0.5 bg-blue-100 text-blue-800 text-xs rounded">
            部分跳过
          </span>
        )}
        {hasFilteredItems && (
          <span className="ml-2 px-2 py-0.5 bg-purple-100 text-purple-800 text-xs rounded">
            {threatIntel.filtered_items.length} 已过滤
          </span>
        )}
      </h4>

      {threatIntel.items.length === 0 && !hasFilteredItems ? (
        <div className="text-sm text-gray-400 italic">
          No threat intelligence data available.
        </div>
      ) : (
        <div className="space-y-2">
          {threatIntel.items.map((item, idx) => (
            <div
              key={idx}
              className="border rounded bg-white p-2 cursor-pointer hover:bg-gray-100"
              onClick={() => setExpandedItem(expandedItem === item.ioc_value ? null : item.ioc_value)}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center flex-1 min-w-0">
                  <span className="text-xs text-gray-400 mr-2">[{item.ioc_type}]</span>
                  <span className="text-sm font-mono truncate">{item.ioc_value}</span>

                  {!item.skipped ? (
                    <>
                      <span className={`ml-3 px-2 py-0.5 rounded text-xs ${getVerdictColor(item.verdict)}`}>
                        {getVerdictIcon(item.verdict)} {item.verdict.toUpperCase()}
                      </span>
                      {item.score > 0 && (
                        <span className={`ml-2 text-xs font-medium ${getScoreColor(item.score)}`}>
                          {item.score}/100
                        </span>
                      )}
                      {item.pulse_count > 0 && (
                        <span className="ml-2 text-xs text-gray-500">
                          🔥 {item.pulse_count} pulses
                        </span>
                      )}
                    </>
                  ) : (
                    <span className="ml-3 px-2 py-0.5 bg-gray-100 text-gray-500 rounded text-xs">
                      {getFilterReasonLabel(item.skipped_reason)}
                    </span>
                  )}
                </div>

                {item.tags.length > 0 || item.references.length > 0 ? (
                  <span className="text-gray-400 text-xs ml-2">
                    {expandedItem === item.ioc_value ? "▼" : "▶"}
                  </span>
                ) : null}
              </div>

              {expandedItem === item.ioc_value && !item.skipped && (
                <div className="mt-2 pt-2 border-t text-xs space-y-2">
                  {item.tags.length > 0 && (
                    <div>
                      <span className="font-medium text-gray-600">Tags: </span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {item.tags.map((tag, tagIdx) => (
                          <span
                            key={tagIdx}
                            className="px-2 py-0.5 bg-gray-100 text-gray-700 rounded"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {item.references.length > 0 && (
                    <div>
                      <span className="font-medium text-gray-600">References: </span>
                      <div className="mt-1 space-y-1">
                        {item.references.slice(0, 3).map((ref, refIdx) => (
                          <a
                            key={refIdx}
                            href={ref}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="block text-blue-600 hover:underline truncate"
                            onClick={(e) => e.stopPropagation()}
                          >
                            {ref}
                          </a>
                        ))}
                      </div>
                    </div>
                  )}

                  {item.cached && (
                    <div className="text-gray-400 italic">
                      Result from cache
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* v0.4.1: Filtered Items Section (Compliance) */}
      {hasFilteredItems && (
        <div className="mt-3 pt-3 border-t border-gray-200">
          <button
            onClick={() => setShowFiltered(!showFiltered)}
            className="text-xs text-purple-700 hover:text-purple-900 font-medium"
          >
            {showFiltered ? "▼" : "▶"} 已过滤的 IOC ({threatIntel.filtered_items.length}) - 未发送至外部服务
          </button>

          {showFiltered && (
            <div className="mt-2 space-y-1">
              {threatIntel.filtered_items.map((item, idx) => (
                <div
                  key={idx}
                  className="text-xs bg-purple-50 border border-purple-100 rounded p-2"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center flex-1 min-w-0">
                      <span className="text-gray-400 mr-2">[{item.ioc_type}]</span>
                      <span className="font-mono truncate">{item.ioc_value}</span>
                    </div>
                    <span className="ml-2 px-2 py-0.5 bg-purple-100 text-purple-700 rounded">
                      {getFilterReasonLabel(item.skipped_reason)}
                    </span>
                  </div>
                  <div className="text-purple-600 italic mt-1">
                    此 IOC 根据合规策略被过滤，未发送至外部威胁情报服务
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {threatIntel.skipped && !hasFilteredItems && (
        <div className="mt-2 text-xs text-gray-400">
          Note: Some IOCs were skipped due to rate limiting (TI_MAX_IOCS_PER_REQUEST)
        </div>
      )}
    </div>
  );
}
