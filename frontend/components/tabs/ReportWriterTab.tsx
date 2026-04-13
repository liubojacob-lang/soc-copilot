"use client";

/**
 * Report Writer Tab component
 * v0.8.2: Extracted from page.tsx for better code organization
 */

import React, { useState } from "react";
import { useTranslations } from "next-intl";
import ReactMarkdown from "react-markdown";
import { api, ReportGenerationResponse, HistoryRecord } from "@/lib/api";
import { Loading, Error, DegradedWarning, CopyButton } from "@/components/common/UIComponents";

interface ReportWriterTabProps {
  onHistoryToggle: () => void;
}

export const ReportWriterTab = React.memo(function ReportWriterTab({
  onHistoryToggle,
}: ReportWriterTabProps) {
  const t = useTranslations("tabs");
  const [input, setInput] = useState("");
  const [notes, setNotes] = useState("");
  const [result, setReportResult] = useState<ReportGenerationResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reportView, setReportView] = useState<"ticket" | "daily_report" | "postmortem">("ticket");

  const handleGenerate = async () => {
    if (!input.trim()) return;

    setLoading(true);
    setError(null);
    setReportResult(null);

    try {
      const response = await api.generateReport({
        alert_json: input,
        additional_notes: notes || undefined,
      });
      setReportResult(response);
    } catch (e: unknown) {
      setError((e as Error)?.message ?? "Report generation failed");
    } finally {
      setLoading(false);
    }
  };

  const loadFromHistory = (record: HistoryRecord) => {
    setInput(record.input_text);
    if (record.tags?.has_notes) {
      setNotes("See history record");
    }
    setReportResult(record.output_json as ReportGenerationResponse);
  };

  return (
    <div className="flex">
      <div className="flex-1 grid grid-cols-2 gap-6">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
              Input: Alert JSON + Notes
            </h3>
            <button
              onClick={onHistoryToggle}
              className="px-3 py-1 text-sm bg-slate-100 hover:bg-slate-200 rounded transition-colors"
            >
              History
            </button>
          </div>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Paste Tab1 output JSON here..."
            className="w-full h-40 p-3 font-mono text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-soc-500 focus:border-soc-500 resize-none"
          />
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Additional notes (optional)..."
            className="w-full h-20 p-3 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-soc-500 focus:border-soc-500 resize-none"
          />
          <button
            onClick={handleGenerate}
            disabled={loading || !input.trim()}
            className="w-full py-2.5 bg-soc-600 text-white font-medium rounded-lg hover:bg-soc-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? t("generatingReports") : t("generateReports")}
          </button>
        </div>

        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">Output</h3>
            {result && (
              <CopyButton
                content={String(result[`${reportView}_template` as keyof typeof result] || "")}
              />
            )}
          </div>

          {loading && <Loading />}
          {error && <Error message={error} />}

          {result && (
            <div className="space-y-3">
              {result.degraded && <DegradedWarning reason={result.error_reason} />}

              <div className="flex gap-2">
                {[
                  { key: "ticket" as const, label: "Ticket" },
                  { key: "daily_report" as const, label: "Daily Report" },
                  { key: "postmortem" as const, label: "Postmortem" },
                ].map(({ key, label }) => (
                  <button
                    key={key}
                    onClick={() => setReportView(key)}
                    className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                      reportView === key
                        ? "bg-soc-600 text-white"
                        : "bg-white border border-slate-300 text-slate-700 hover:bg-slate-50"
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>

              <div className="bg-white border border-slate-200 rounded-lg p-4 max-h-96 overflow-y-auto">
                <div className="prose prose-slate max-w-none">
                  <ReactMarkdown>
                    {String(result[`${reportView}_template` as keyof typeof result] ?? "") || null}
                  </ReactMarkdown>
                </div>
              </div>

              {result.request_id && (
                <div className="text-xs text-slate-500">Request ID: {result.request_id}</div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
});
