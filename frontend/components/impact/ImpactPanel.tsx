"use client";

import { ImpactAnalysis } from "@/lib/api";

interface ImpactPanelProps {
  impact: ImpactAnalysis;
}

export function ImpactPanel({ impact }: ImpactPanelProps) {
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "critical": return "bg-red-600 text-white";
      case "high": return "bg-orange-500 text-white";
      case "medium": return "bg-yellow-500 text-black";
      case "low": return "bg-green-500 text-white";
      default: return "bg-gray-500 text-white";
    }
  };

  const getCriticalityColor = (criticality: string) => {
    switch (criticality) {
      case "critical": return "text-red-600 font-semibold";
      case "high": return "text-orange-600";
      case "medium": return "text-yellow-600";
      case "low": return "text-green-600";
      default: return "text-gray-600";
    }
  };

  const getRiskScoreColor = (score: number) => {
    if (score >= 80) return "bg-red-500";
    if (score >= 60) return "bg-orange-500";
    if (score >= 40) return "bg-yellow-500";
    return "bg-green-500";
  };

  return (
    <div className="mt-6 border rounded-lg p-4 bg-gray-50">
      <h3 className="text-lg font-bold mb-4">Impact Analysis</h3>

      {/* Risk Score */}
      <div className="mb-4">
        <div className="flex justify-between items-center mb-2">
          <span className="font-medium">Risk Score</span>
          <span className="text-2xl font-bold">{impact.risk_score}/100</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3">
          <div
            className={`h-3 rounded-full ${getRiskScoreColor(impact.risk_score)}`}
            style={{ width: `${impact.risk_score}%` }}
          />
        </div>
      </div>

      {/* Severity */}
      <div className="mb-4">
        <span className="font-medium">Severity: </span>
        <span className={`px-3 py-1 rounded ${getSeverityColor(impact.severity)}`}>
          {impact.severity.toUpperCase()}
        </span>
      </div>

      {/* Business Impact */}
      <div className="mb-4 p-3 bg-white rounded border">
        <h4 className="font-medium text-sm mb-1">Business Impact</h4>
        <p className="text-sm text-gray-700">{impact.business_impact}</p>
      </div>

      {/* Affected Assets */}
      {impact.affected_assets.length > 0 && (
        <div className="mb-4">
          <h4 className="font-medium text-sm mb-2">Affected Assets ({impact.affected_assets.length})</h4>
          <div className="space-y-2">
            {impact.affected_assets.map((asset) => (
              <div key={asset.asset_id} className="flex items-center justify-between p-2 bg-white rounded border text-sm">
                <div className="flex-1">
                  <span className="font-medium">{asset.hostname || asset.ip || "Unknown"}</span>
                  <span className={`ml-2 ${getCriticalityColor(asset.criticality)}`}>
                    ({asset.criticality})
                  </span>
                </div>
                <span className="text-gray-500 text-xs ml-2">{asset.reason}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Containment Priority */}
      {impact.containment_priority.length > 0 && (
        <div className="mb-4">
          <h4 className="font-medium text-sm mb-2">Containment Priority</h4>
          <div className="space-y-1">
            {impact.containment_priority.slice(0, 5).map((item, idx) => (
              <div key={item.asset_id} className="flex items-center text-sm p-2 bg-white rounded border">
                <span className="font-mono font-bold w-8">{idx + 1}</span>
                <span className="flex-1">{item.asset_id}</span>
                <span className="text-gray-600 text-xs">{item.reason}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommended Queries */}
      {impact.recommended_next_queries.length > 0 && (
        <div>
          <h4 className="font-medium text-sm mb-2">Recommended Next Queries</h4>
          <div className="space-y-1">
            {impact.recommended_next_queries.map((query, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-2 bg-white rounded border text-sm cursor-pointer hover:bg-gray-100"
                onClick={() => navigator.clipboard.writeText(query)}
              >
                <span className="flex-1">{query}</span>
                <span className="text-gray-400 text-xs">📋</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
