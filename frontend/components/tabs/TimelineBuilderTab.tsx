"use client";

/**
 * Timeline Builder Tab component
 * v0.8.2: Extracted from page.tsx for better code organization
 */

import { useState } from "react";
import { useTranslations } from "next-intl";
import { api, TimelineResponse, HistoryRecord, SuspiciousEvent } from "@/lib/api";
import { Loading, Error, CopyButton } from "@/components/common/UIComponents";
import { PlaybookPanel } from "@/components/playbook/PlaybookPanel";

interface TimelineBuilderTabProps {
  onHistoryToggle: () => void;
}

export function TimelineBuilderTab({ onHistoryToggle }: TimelineBuilderTabProps) {
  const t = useTranslations("tabs");
  const [input, setInput] = useState("");
  const [logType, setLogType] = useState<string>("");
  const [result, setTimelineResult] = useState<TimelineResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentHistoryId, setCurrentHistoryId] = useState<string | undefined>();

  const handleBuild = async () => {
    if (!input.trim()) return;

    setLoading(true);
    setError(null);
    setTimelineResult(null);
    setCurrentHistoryId(undefined);

    try {
      const response = await api.buildTimeline({
        raw_log: input,
        log_type: logType || undefined,
      });
      setTimelineResult(response);

      if (response.history_id) {
        setCurrentHistoryId(response.history_id);
      }
    } catch (e: unknown) {
      setError((e as Error)?.message ?? "Timeline build failed");
    } finally {
      setLoading(false);
    }
  };

  const loadFromHistory = (record: HistoryRecord) => {
    setInput(record.input_text);
    if (record.tags?.log_type) {
      setLogType(record.tags.log_type);
    }
    setTimelineResult(record.output_json as TimelineResponse);
    setCurrentHistoryId(record.id);
  };

  return (
    <div className="flex">
      <div className="flex-1 grid grid-cols-2 gap-6">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
              Input: Raw Log (Sysmon / Windows / Linux / Nginx)
            </h3>
            <button
              onClick={onHistoryToggle}
              className="px-3 py-1 text-sm bg-slate-100 hover:bg-slate-200 rounded transition-colors"
            >
              History
            </button>
          </div>
          <select
            value={logType}
            onChange={(e) => setLogType(e.target.value)}
            className="w-full p-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-soc-500 focus:border-soc-500"
          >
            <option value="">Auto-detect</option>
            <option value="sysmon">Sysmon</option>
            <option value="windows">Windows Event Log</option>
            <option value="linux">Linux auth.log</option>
            <option value="nginx">Nginx access.log</option>
          </select>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={`Paste your log here...

Example (Linux auth.log):
Feb  5 10:23:45 server01 sshd[1234]: Failed password for root from 192.168.1.100 port 22 ssh2
Feb  5 10:23:46 server01 sshd[1234]: Failed password for root from 192.168.1.100 port 22 ssh2`}
            className="w-full h-64 p-3 font-mono text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-soc-500 focus:border-soc-500 resize-none"
          />
          <button
            onClick={handleBuild}
            disabled={loading || !input.trim()}
            className="w-full py-2.5 bg-soc-600 text-white font-medium rounded-lg hover:bg-soc-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? t("buildingTimeline") : t("buildTimeline")}
          </button>
        </div>

        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">Output</h3>
            {result && <CopyButton content={JSON.stringify(result, null, 2)} />}
          </div>

          {loading && <Loading />}
          {error && <Error message={error} />}

          {result && (
            <div className="space-y-4">
              {/* Timeline Events */}
              <div className="bg-white border border-slate-200 rounded-lg p-4">
                <h4 className="text-sm font-semibold text-slate-700 mb-3">Timeline Events</h4>
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {result.timeline.map((event, i) => (
                    <div key={i} className="flex items-start gap-3 p-2 bg-slate-50 rounded">
                      <span className="text-xs text-slate-500 font-mono whitespace-nowrap">
                        {event.timestamp}
                      </span>
                      <div className="flex-1">
                        <p className="text-sm text-slate-700">{event.description}</p>
                        <p className="text-xs text-slate-500">Type: {event.type}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Suspicious Events */}
              {result.suspicious_top5 && result.suspicious_top5.length > 0 && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <h4 className="text-sm font-semibold text-red-700 mb-3">
                    ⚠️ Top {result.suspicious_top5.length} Suspicious Events
                  </h4>
                  <ul className="space-y-2">
                    {result.suspicious_top5.map((event: SuspiciousEvent, i: number) => (
                      <li
                        key={i}
                        className="text-sm text-red-800 p-2 bg-white rounded border border-red-200"
                      >
                        <div className="font-medium">{event.description}</div>
                        <div className="text-xs text-red-600 mt-1">
                          Reason: {event.reasoning} | Severity: {event.severity}
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Next Steps */}
              {result.next_steps && result.next_steps.length > 0 && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <h4 className="text-sm font-semibold text-blue-700 mb-3">
                    🔍 Recommended Next Steps
                  </h4>
                  <ul className="space-y-1">
                    {result.next_steps.map((step, i) => (
                      <li key={i} className="text-sm text-blue-800">
                        {i + 1}. {step}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Playbook Panel */}
              <PlaybookPanel historyId={currentHistoryId} iocs={result.iocs} module="timeline" />

              {result.request_id && (
                <div className="text-xs text-slate-500">Request ID: {result.request_id}</div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
