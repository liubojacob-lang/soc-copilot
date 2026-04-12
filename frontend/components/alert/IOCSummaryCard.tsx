"use client";

/**
 * IOC Summary Card component
 * v0.8.2: Extracted from page.tsx for better code organization
 */

import { useState } from "react";
import { IOCsLocal, IOCsLLM, IOCCount } from "@/lib/api";
import { ThreatIntelSection } from "@/components/threat_intel/ThreatIntelSection";

interface IOCSummaryCardProps {
  iocs_local: IOCsLocal;
  iocs_llm: IOCsLLM;
  ioc_count: IOCCount;
  threat_intel?: import("@/lib/api").ThreatIntelAnalysis;
}

export function IOCSummaryCard({
  iocs_local,
  iocs_llm,
  ioc_count,
  threat_intel,
}: IOCSummaryCardProps) {
  const [expanded, setExpanded] = useState(false);

  const hasIOCs = ioc_count.total > 0;

  if (!hasIOCs) {
    return (
      <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
        <p className="text-sm text-slate-500">No IOCs detected</p>
      </div>
    );
  }

  return (
    <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-semibold text-slate-700">IOC Summary</h4>
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-xs text-soc-600 hover:text-soc-700"
        >
          {expanded ? "▼ Collapse" : "▲ Expand"}
        </button>
      </div>

      {/* Counts */}
      <div className="grid grid-cols-4 gap-3 mb-3">
        <div className="text-center">
          <div className="text-2xl font-bold text-soc-600">{ioc_count.ips}</div>
          <div className="text-xs text-slate-500">IPs</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-soc-600">{ioc_count.domains}</div>
          <div className="text-xs text-slate-500">Domains</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-soc-600">{ioc_count.urls}</div>
          <div className="text-xs text-slate-500">URLs</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-soc-600">{ioc_count.hashes}</div>
          <div className="text-xs text-slate-500">Hashes</div>
        </div>
      </div>

      {/* Expanded: Source breakdown */}
      {expanded && (
        <div className="space-y-3 border-t border-slate-200 pt-3">
          {/* Local IOCs */}
          {(iocs_local.ips.length ||
            iocs_local.domains.length ||
            iocs_local.urls.length ||
            iocs_local.hashes.length) && (
            <div>
              <h5 className="text-xs font-semibold text-slate-600 mb-1">Local (Regex)</h5>
              <div className="grid grid-cols-4 gap-2 text-xs">
                {iocs_local.ips.length > 0 && (
                  <div className="p-1 bg-blue-50 rounded">IPs: {iocs_local.ips.length}</div>
                )}
                {iocs_local.domains.length > 0 && (
                  <div className="p-1 bg-blue-50 rounded">Domains: {iocs_local.domains.length}</div>
                )}
                {iocs_local.urls.length > 0 && (
                  <div className="p-1 bg-blue-50 rounded">URLs: {iocs_local.urls.length}</div>
                )}
                {iocs_local.hashes.length > 0 && (
                  <div className="p-1 bg-blue-50 rounded">Hashes: {iocs_local.hashes.length}</div>
                )}
              </div>
            </div>
          )}

          {/* LLM IOCs */}
          {(iocs_llm.ips.length ||
            iocs_llm.domains.length ||
            iocs_llm.urls.length ||
            iocs_llm.hashes.length) && (
            <div>
              <h5 className="text-xs font-semibold text-slate-600 mb-1">AI Supplement</h5>
              <div className="grid grid-cols-4 gap-2 text-xs">
                {iocs_llm.ips.length > 0 && (
                  <div className="p-1 bg-purple-50 rounded">IPs: {iocs_llm.ips.length}</div>
                )}
                {iocs_llm.domains.length > 0 && (
                  <div className="p-1 bg-purple-50 rounded">Domains: {iocs_llm.domains.length}</div>
                )}
                {iocs_llm.urls.length > 0 && (
                  <div className="p-1 bg-purple-50 rounded">URLs: {iocs_llm.urls.length}</div>
                )}
                {iocs_llm.hashes.length > 0 && (
                  <div className="p-1 bg-purple-50 rounded">Hashes: {iocs_llm.hashes.length}</div>
                )}
              </div>
            </div>
          )}

          {/* Detailed Lists */}
          <div className="text-xs text-slate-600">
            {iocs_local.ips.length > 0 && (
              <div className="mb-1">
                <strong>IPs:</strong> {iocs_local.ips.join(", ")}
              </div>
            )}
            {iocs_local.domains.length > 0 && (
              <div className="mb-1">
                <strong>Domains:</strong> {iocs_local.domains.join(", ")}
              </div>
            )}
            {iocs_local.urls.length > 0 && (
              <div className="mb-1">
                <strong>URLs:</strong> {iocs_local.urls.slice(0, 5).join(", ")}
                {iocs_local.urls.length > 5 && "..."}
              </div>
            )}
            {iocs_local.hashes.length > 0 && (
              <div className="mb-1">
                <strong>Hashes:</strong> {iocs_local.hashes.slice(0, 3).join(", ")}
                {iocs_local.hashes.length > 3 && "..."}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Threat Intel Section */}
      {threat_intel && <ThreatIntelSection threatIntel={threat_intel} />}
    </div>
  );
}
