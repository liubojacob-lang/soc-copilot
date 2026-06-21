"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { TabButton, TabList } from "@/components/ui/Tabs";
import {
  api,
  Platform,
  TimeRange,
  GeneratePlaybookQueriesResponse,
  GenerateRemediationActionsResponse,
} from "@/lib/api";

const RISK_COLORS: Record<string, string> = {
  low: "bg-green-100 text-green-800 border-green-300",
  medium: "bg-amber-100 text-amber-800 border-amber-300",
  high: "bg-orange-100 text-orange-800 border-orange-300",
  critical: "bg-red-100 text-red-800 border-red-300",
};

const CATEGORY_COLORS: Record<string, string> = {
  containment: "bg-red-50 text-red-700",
  eradication: "bg-purple-50 text-purple-700",
  recovery: "bg-blue-50 text-blue-700",
};

interface PlaybookPanelProps {
  historyId?: string;
  iocs?: { ips: string[]; domains: string[]; urls: string[]; hashes: string[] };
  module?: string;
}

export function PlaybookPanel({ historyId, iocs, module = "analyzer" }: PlaybookPanelProps) {
  const t = useTranslations("playbookPanel");
  const tCommon = useTranslations("common");
  const [tab, setTab] = useState<"queries" | "actions">("queries");
  const [platform, setPlatform] = useState<Platform>("splunk");
  const [timeRange, setTimeRange] = useState<TimeRange>("last_24h");
  const [policy, setPolicy] = useState<string>("safe");

  const [queriesResponse, setQueriesResponse] = useState<GeneratePlaybookQueriesResponse | null>(
    null
  );
  const [actionsResponse, setActionsResponse] = useState<GenerateRemediationActionsResponse | null>(
    null
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const hasIOCs =
    iocs &&
    ((iocs.ips?.length ?? 0) > 0 ||
      (iocs.domains?.length ?? 0) > 0 ||
      (iocs.urls?.length ?? 0) > 0 ||
      (iocs.hashes?.length ?? 0) > 0);

  const handleGenerateQueries = async () => {
    if (!hasIOCs && !historyId) {
      setError(t("errors.noIOCs"));
      return;
    }

    setLoading(true);
    setError(null);
    setQueriesResponse(null);

    try {
      const response = await api.generatePlaybookQueries(
        module,
        historyId,
        iocs,
        [platform],
        [timeRange]
      );
      setQueriesResponse(response);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t("errors.generateQueriesFailed"));
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateActions = async () => {
    if (!historyId) {
      setError(t("errors.noHistoryId"));
      return;
    }

    setLoading(true);
    setError(null);
    setActionsResponse(null);

    try {
      const response = await api.generateRemediationActions(historyId, policy, true);
      setActionsResponse(response);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t("errors.generateActionsFailed"));
    } finally {
      setLoading(false);
    }
  };

  const copyQuery = (query: string) => {
    navigator.clipboard.writeText(query);
  };

  const copyActionAsMarkdown = (action: {
    title: string;
    risk: string;
    category: string;
    priority: number;
    rationale: string;
    steps: Array<{ action: string; method: string; command?: string }>;
    verification: string[];
    rollback: string[];
  }) => {
    const markdown = `## ${action.title}

**Risk:** ${action.risk.toUpperCase()} | **Category:** ${action.category} | **Priority:** ${action.priority}

**Rationale:** ${action.rationale}

### Steps
${action.steps.map((s, i: number) => `${i + 1}. **${s.action}** (${s.method})\n   \`\`\`\n   ${s.command || "N/A"}\n   \`\`\``).join("\n")}

### Verification
${action.verification.map((v: string, i: number) => `${i + 1}. ${v}`).join("\n")}

### Rollback
${action.rollback.map((r: string, i: number) => `${i + 1}. ${r}`).join("\n")}
`;
    navigator.clipboard.writeText(markdown);
  };

  return (
    <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
      <h3 className="text-sm font-semibold text-slate-700 mb-3">{t("title")}</h3>

      {/* Tabs */}
      <TabList className="mb-4">
        <TabButton
          active={tab === "queries"}
          onClick={() => setTab("queries")}
          label={t("tabs.queries")}
        />
        <TabButton
          active={tab === "actions"}
          onClick={() => setTab("actions")}
          label={t("tabs.actions")}
          disabled={!historyId}
        />
      </TabList>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-800 text-sm">{error}</p>
        </div>
      )}

      {tab === "queries" && (
        <div className="space-y-4">
          {/* Query Controls */}
          <div className="flex gap-4 items-end">
            <div className="flex-1">
              <label className="block text-xs font-medium text-slate-600 mb-1">
                {t("queries.platform")}
              </label>
              <select
                value={platform}
                onChange={(e) => setPlatform(e.target.value as Platform)}
                className="w-full p-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-soc-500"
              >
                <option value="splunk">{t("queries.platforms.splunk")}</option>
                <option value="elastic_kql">{t("queries.platforms.elastic_kql")}</option>
                <option value="sentinel_kql">{t("queries.platforms.sentinel_kql")}</option>
              </select>
            </div>
            <div className="flex-1">
              <label className="block text-xs font-medium text-slate-600 mb-1">
                {t("queries.timeRange")}
              </label>
              <select
                value={timeRange}
                onChange={(e) => setTimeRange(e.target.value as TimeRange)}
                className="w-full p-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-soc-500"
              >
                <option value="last_1h">{t("queries.timeRanges.last_1h")}</option>
                <option value="last_24h">{t("queries.timeRanges.last_24h")}</option>
                <option value="last_7d">{t("queries.timeRanges.last_7d")}</option>
              </select>
            </div>
            <button
              onClick={handleGenerateQueries}
              disabled={loading || (!hasIOCs && !historyId)}
              className="px-4 py-2 bg-soc-600 text-white font-medium rounded-lg hover:bg-soc-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? t("queries.generating") : t("queries.generate")}
            </button>
          </div>

          {/* Query Results */}
          {queriesResponse && queriesResponse.results.length > 0 && (
            <div className="space-y-3">
              {queriesResponse.results[0].queries.map((query, idx) => (
                <div key={idx} className="bg-white border border-slate-200 rounded-lg p-3">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <h4 className="text-sm font-semibold text-slate-700">{query.name}</h4>
                      <p className="text-xs text-slate-500">{query.description}</p>
                      <div className="flex gap-2 mt-1">
                        <span className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded text-xs">
                          {query.time_range}
                        </span>
                        <span className="px-2 py-0.5 bg-slate-100 text-slate-600 rounded text-xs">
                          {query.fields_expected.length} {t("queries.fields")}
                        </span>
                      </div>
                    </div>
                    <button
                      onClick={() => copyQuery(query.query)}
                      className="px-3 py-1 text-sm bg-slate-100 hover:bg-slate-200 rounded transition-colors"
                    >
                      {tCommon("copy")}
                    </button>
                  </div>
                  <div className="bg-slate-900 text-green-400 p-3 rounded-lg font-mono text-xs overflow-x-auto">
                    <pre>{query.query}</pre>
                  </div>
                  <p className="text-xs text-slate-500 mt-2">
                    <strong>{t("queries.prerequisite")}</strong> {query.prerequisite}
                  </p>
                  <p className="text-xs text-slate-500">
                    <strong>{t("queries.expectedFields")}</strong>{" "}
                    {query.fields_expected.join(", ")}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === "actions" && (
        <div className="space-y-4">
          {/* Action Controls */}
          <div className="flex gap-4 items-end">
            <div className="flex-1">
              <label className="block text-xs font-medium text-slate-600 mb-1">
                {t("actions.policy")}
              </label>
              <select
                value={policy}
                onChange={(e) => setPolicy(e.target.value)}
                className="w-full p-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-soc-500"
              >
                <option value="safe">{t("actions.policies.safe")}</option>
                <option value="moderate">{t("actions.policies.moderate")}</option>
                <option value="aggressive">{t("actions.policies.aggressive")}</option>
              </select>
            </div>
            <button
              onClick={handleGenerateActions}
              disabled={loading || !historyId}
              className="px-4 py-2 bg-soc-600 text-white font-medium rounded-lg hover:bg-soc-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? t("actions.generating") : t("actions.generate")}
            </button>
          </div>

          {/* Action Results */}
          {actionsResponse && actionsResponse.actions.length > 0 && (
            <div className="space-y-3">
              {actionsResponse.actions.map((action, idx) => (
                <div key={idx} className="bg-white border border-slate-200 rounded-lg p-3">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <h4 className="text-sm font-semibold text-slate-700">{action.title}</h4>
                      <p className="text-xs text-slate-500 mt-1">{action.rationale}</p>
                    </div>
                    <button
                      onClick={() => copyActionAsMarkdown(action)}
                      className="px-3 py-1 text-sm bg-slate-100 hover:bg-slate-200 rounded transition-colors"
                    >
                      {t("actions.copyMD")}
                    </button>
                  </div>
                  <div className="flex gap-2 flex-wrap mb-3">
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-medium border ${RISK_COLORS[action.risk]}`}
                    >
                      {action.risk.toUpperCase()} {t("actions.risk")}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded text-xs ${CATEGORY_COLORS[action.category]}`}
                    >
                      {action.category}
                    </span>
                    <span className="px-2 py-0.5 bg-slate-100 text-slate-600 rounded text-xs">
                      {t("actions.priority")} {action.priority}
                    </span>
                  </div>

                  <div className="space-y-3 text-sm">
                    <div>
                      <h5 className="text-xs font-semibold text-slate-600 uppercase">
                        {t("actions.steps")}
                      </h5>
                      <ol className="mt-1 space-y-2">
                        {action.steps.map((step, stepIdx) => (
                          <li key={stepIdx} className="bg-slate-50 p-2 rounded">
                            <div className="font-medium text-slate-700">{step.action}</div>
                            <div className="text-xs text-slate-500">{step.method}</div>
                            {step.command && (
                              <div className="bg-slate-900 text-green-400 p-2 rounded mt-1 font-mono text-xs">
                                <pre>{step.command}</pre>
                              </div>
                            )}
                          </li>
                        ))}
                      </ol>
                    </div>

                    <div>
                      <h5 className="text-xs font-semibold text-green-600 uppercase">
                        {t("actions.verification")}
                      </h5>
                      <ul className="mt-1 space-y-1">
                        {action.verification.map((v, vIdx) => (
                          <li key={vIdx} className="text-xs text-slate-600 flex items-start">
                            <span className="mr-2">✓</span>
                            {v}
                          </li>
                        ))}
                      </ul>
                    </div>

                    <div>
                      <h5 className="text-xs font-semibold text-amber-600 uppercase">
                        {t("actions.rollback")}
                      </h5>
                      <ul className="mt-1 space-y-1">
                        {action.rollback.map((r, rIdx) => (
                          <li key={rIdx} className="text-xs text-slate-600 flex items-start">
                            <span className="mr-2">↩</span>
                            {r}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
