"use client";

/**
 * Alert Analyzer Tab component
 * v0.8.2: Extracted from page.tsx for better code organization
 */

import { useState } from "react";
import { useTranslations } from "next-intl";
import ReactMarkdown from "react-markdown";
import { api, AlertAnalysisResponse, HistoryRecord } from "@/lib/api";
import { Loading, Error, DegradedWarning, CopyButton } from "@/components/common/UIComponents";
import { IOCSummaryCard } from "@/components/alert/IOCSummaryCard";
import { ImpactPanel } from "@/components/impact/ImpactPanel";
import { PlaybookPanel } from "@/components/playbook/PlaybookPanel";
import { CorrelationPanel } from "@/components/alerts/CorrelationPanel";

type Severity = "high" | "medium" | "low";

const SEVERITY_COLORS: Record<Severity, string> = {
  high: "bg-red-100 text-red-800 border-red-300",
  medium: "bg-amber-100 text-amber-800 border-amber-300",
  low: "bg-green-100 text-green-800 border-green-300",
};

interface AlertAnalyzerTabProps {
  onHistoryToggle: () => void;
}

export function AlertAnalyzerTab({ onHistoryToggle }: AlertAnalyzerTabProps) {
  const t = useTranslations('alertAnalyzer');
  const [input, setInput] = useState("");
  const [result, setResult] = useState<AlertAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentHistoryId, setCurrentHistoryId] = useState<string | undefined>();

  const handleAnalyze = async () => {
    if (!input.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);
    setCurrentHistoryId(undefined);

    try {
      const response = await api.analyzeAlert({ raw_log: input });
      setResult(response);

      if (response.history_id) {
        setCurrentHistoryId(response.history_id);
      }
    } catch (e: unknown) {
      const errorMsg = (e as Error)?.message ?? t('analysisFailed');
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const loadFromHistory = (record: HistoryRecord) => {
    setInput(record.input_text);
    setResult(record.output_json as AlertAnalysisResponse);
    setCurrentHistoryId(record.id);
  };

  return (
    <div className="flex">
      <div className="flex-1 grid grid-cols-2 gap-6">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
              {t('input')}
            </h3>
            <button
              onClick={onHistoryToggle}
              className="px-3 py-1 text-sm bg-slate-100 hover:bg-slate-200 rounded transition-colors"
            >
              {t('history')}
            </button>
          </div>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={t('placeholder')}
            className="w-full h-64 p-3 font-mono text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-soc-500 focus:border-soc-500 resize-none"
          />
          <button
            onClick={handleAnalyze}
            disabled={loading || !input.trim()}
            className="w-full py-2.5 bg-soc-600 text-white font-medium rounded-lg hover:bg-soc-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? t('analyzing') : t('analyze')}
          </button>
        </div>

        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">{t('output')}</h3>
            {result && <CopyButton content={JSON.stringify(result, null, 2)} />}
          </div>

          {loading && <Loading />}
          {error && <Error message={error} />}

          {result && (
            <div className="space-y-4">
              {result.degraded && <DegradedWarning reason={result.error_reason} />}

              <IOCSummaryCard
                iocs_local={result.iocs_local}
                iocs_llm={result.iocs_llm}
                ioc_count={result.ioc_count}
                threat_intel={result.threat_intel}
              />

              <div className="flex gap-4 flex-wrap">
                <span className={`px-3 py-1 rounded-full text-sm font-medium border ${SEVERITY_COLORS[result.severity as Severity]}`}>
                  {result.severity.toUpperCase()}
                </span>
                <span className="px-3 py-1 bg-slate-100 text-slate-700 rounded-full text-sm font-medium">
                  {result.event_type.replace("_", " ").toUpperCase()}
                </span>
                <span className="px-3 py-1 bg-slate-100 text-slate-700 rounded-full text-sm font-medium">
                  {t('confidence')} {result.confidence}%
                </span>
                {result.escalation_needed && (
                  <span className="px-3 py-1 bg-red-100 text-red-800 rounded-full text-sm font-medium">
                    {t('escalate')}
                  </span>
                )}
                {result.request_id && (
                  <span className="px-3 py-1 bg-slate-100 text-slate-500 rounded-full text-xs font-medium">
                    {t('id')} {result.request_id}
                  </span>
                )}
              </div>

              <div className="bg-white border border-slate-200 rounded-lg p-4 space-y-3">
                <div>
                  <h4 className="text-xs font-semibold text-slate-500 uppercase">{t('summary')}</h4>
                  <p className="text-slate-800 mt-1">{result.summary}</p>
                </div>

                {result.entities.users.length || result.entities.hosts.length || result.entities.processes.length ? (
                  <div>
                    <h4 className="text-xs font-semibold text-slate-500 uppercase">{t('entities')}</h4>
                    <div className="mt-1 grid grid-cols-3 gap-2 text-sm">
                      {result.entities.users.length && <div><span className="text-slate-500">{t('users')}</span> {result.entities.users.join(", ")}</div>}
                      {result.entities.hosts.length && <div><span className="text-slate-500">{t('hosts')}</span> {result.entities.hosts.join(", ")}</div>}
                      {result.entities.processes.length && <div><span className="text-slate-500">{t('processes')}</span> {result.entities.processes.join(", ")}</div>}
                    </div>
                  </div>
                ) : null}

                <div>
                  <h4 className="text-xs font-semibold text-slate-500 uppercase">{t('evidencePoints')}</h4>
                  <ul className="mt-1 space-y-1">
                    {result.evidence_points.map((point, i) => (
                      <li key={i} className="text-sm text-slate-700 flex items-start">
                        <span className="text-soc-500 mr-2">•</span>
                        {point}
                      </li>
                    ))}
                  </ul>
                </div>

                <div>
                  <h4 className="text-xs font-semibold text-slate-500 uppercase">{t('recommendedActions')}</h4>
                  <ul className="mt-1 space-y-2">
                    {result.recommended_actions.map((action, i) => (
                      <li key={i} className="text-sm text-slate-700 p-2 bg-slate-50 rounded border border-slate-200">
                        <div className="font-medium text-green-700">•{action.action}</div>
                        <div className="text-xs text-slate-600 mt-1">{action.details}</div>
                        <div className="text-xs text-slate-500 mt-1"><em>{t('verify')} {action.verification}</em></div>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Impact Analysis */}
              <ImpactPanel impact={result.impact_analysis} />

              {/* Playbook Panel */}
              <PlaybookPanel
                historyId={currentHistoryId}
                iocs={result.iocs}
                module="analyzer"
              />

              {/* v0.8: Event Correlation Panel */}
              {result.request_id && (
                <CorrelationPanel alertId={result.request_id} />
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
