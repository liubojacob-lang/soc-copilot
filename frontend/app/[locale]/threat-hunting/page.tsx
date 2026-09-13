"use client";

import { useState, useEffect } from "react";
import { useRouter } from "@/i18n/navigation";
import { useFormatter, useTranslations, useLocale } from "next-intl";
import { api } from "@/lib/api";
import { loadAuthState } from "@/lib/auth";
import { PageHeader } from "@/components/common/PageHeader";
import { ErrorDisplay } from "@/components/common/ErrorDisplay";
import { LogTimelineAnalyzer } from "@/components/timeline/LogTimelineAnalyzer";
import { useToast } from "@/components/Toast";
import {
  Target,
  Play,
  Shield,
  Clock,
  CheckCircle,
  AlertTriangle,
  TrendingUp,
  Code,
  Search,
  Database,
  Filter,
  ChevronDown,
  ChevronRight,
  Zap,
} from "lucide-react";

/* ── Type Definitions ── */

interface ThreatHypothesis {
  id: string;
  name: string;
  description: string;
  status: string;
  priority: string;
  severity: string;
  verified: boolean;
  mitre_techniques: string[];
  data_sources: string[];
  created_at: string;
}

interface ThreatResult {
  id: string;
  hypothesis_id: string;
  hunt_name: string;
  status: string;
  findings: string;
  findings_count: number;
  started_at: string;
  created_at: string;
}

interface ThreatDashboard {
  total_hypotheses: number;
  active_hypotheses: number;
  confirmed_threats: number;
  top_mitre_techniques: Array<{ technique: string; name: string; count: number }>;
  summary: {
    total_hunts_executed: number;
    total_findings: number;
    critical_findings: number;
  };
  hunt_effectiveness: {
    success_rate: string;
  };
}

/* ── Sigma Types ── */

interface SigmaRuleSummary {
  id: string;
  title: string;
  level: string;
  category: string;
  status: string;
  mitre_techniques: string[];
  description: string;
}

interface SigmaRuleDetail {
  id: string;
  title: string;
  description: string;
  status: string;
  level: string;
  author: string;
  category: string;
  tags: string[];
  mitre_techniques: string[];
  logsource: Record<string, string>;
  false_positives: string[];
  references: string[];
  generated_sql: string;
}

interface SigmaSearchResult {
  rule_id: string;
  rule_title: string;
  rule_level: string;
  sql_query: string;
  searched_hours: number;
  total_matches: number;
  matches: Array<Record<string, any>>;
  timestamp: string;
}

const CATEGORY_LABELS: Record<string, string> = {
  windows: "Windows",
  linux: "Linux",
  cloud: "Cloud",
  kubernetes: "Kubernetes",
};

const CATEGORY_ICONS: Record<string, string> = {
  windows: "🪟",
  linux: "🐧",
  cloud: "☁️",
  kubernetes: "☸️",
};

export default function ThreatHuntingPage() {
  const router = useRouter();
  const locale = useLocale();
  const t = useTranslations("threatHunting");
  const format = useFormatter();
  const tCommon = useTranslations("common");
  const { showToast } = useToast();
  const [mounted, setMounted] = useState(false);

  /* ── Existing state ── */
  const [hypotheses, setHypotheses] = useState<ThreatHypothesis[]>([]);
  const [results, setResults] = useState<ThreatResult[]>([]);
  const [dashboard, setDashboard] = useState<ThreatDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [executing, setExecuting] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<Error | null>(null);

  /* ── Sigma state ── */
  const [sigmaRules, setSigmaRules] = useState<SigmaRuleSummary[]>([]);
  const [sigmaCategories, setSigmaCategories] = useState<string[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [selectedRule, setSelectedRule] = useState<SigmaRuleDetail | null>(null);
  const [selectedRuleId, setSelectedRuleId] = useState<string | null>(null);
  const [sigmaSearchResult, setSigmaSearchResult] = useState<SigmaSearchResult | null>(null);
  const [searching, setSearching] = useState(false);
  const [activeTab, setActiveTab] = useState<"hypotheses" | "sigma" | "timeline">("hypotheses");

  useEffect(() => {
    setMounted(true);
    loadData();
  }, []);

  const loadData = async () => {
    setLoadError(null);
    try {
      const [hypRes, resultRes, dashRes] = await Promise.all([
        api.get("/api/threat-hunting/hypotheses"),
        api.get("/api/threat-hunting/results?limit=10"),
        api.get("/api/threat-hunting/dashboard"),
      ]);
      setHypotheses(hypRes as ThreatHypothesis[]);
      setResults(resultRes as ThreatResult[]);
      setDashboard(dashRes as ThreatDashboard);
    } catch (e) {
      console.error("Failed to load threat hunting data:", e);
      setLoadError(e instanceof Error ? e : new Error(String(e)));
    }

    // Load Sigma data
    try {
      const [rulesRes, catRes] = await Promise.all([
        api.get("/api/threat-hunting/sigma/rules"),
        api.get("/api/threat-hunting/sigma/rules/categories"),
      ]);
      setSigmaRules(rulesRes as SigmaRuleSummary[]);
      setSigmaCategories((catRes as any)?.categories ?? []);
    } catch (e) {
      console.error("Failed to load Sigma rules:", e);
    }

    setLoading(false);
  };

  const executeHunt = async (hypothesisId: string) => {
    setExecuting(hypothesisId);
    try {
      await api.post("/api/threat-hunting/execute", {
        hypothesis_id: hypothesisId,
        time_range_hours: 24,
      });
      const resultRes = await api.get("/api/threat-hunting/results?limit=10");
      setResults(resultRes as ThreatResult[]);
    } catch (e) {
      console.error("Failed to execute hunt:", e);
    } finally {
      setExecuting(null);
    }
  };

  /* ── Sigma: Load rule detail ── */
  const loadRuleDetail = async (ruleId: string) => {
    if (selectedRuleId === ruleId) {
      setSelectedRuleId(null);
      setSelectedRule(null);
      return;
    }
    setSelectedRuleId(ruleId);
    setSelectedRule(null);
    setSigmaSearchResult(null);
    try {
      const detail = await api.get(`/api/threat-hunting/sigma/rules/${ruleId}`);
      setSelectedRule(detail as SigmaRuleDetail);
    } catch (e) {
      console.error("Failed to load rule detail:", e);
    }
  };

  /* ── Sigma: Execute search ── */
  const executeSigmaSearch = async (ruleId: string) => {
    setSearching(true);
    setSigmaSearchResult(null);
    try {
      const result = await api.post("/api/threat-hunting/sigma/search", {
        rule_id: ruleId,
        hours: 24,
      });
      setSigmaSearchResult(result as SigmaSearchResult);
    } catch (e) {
      console.error("Sigma search failed:", e);
    } finally {
      setSearching(false);
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "critical":
        return "text-red-600 bg-red-50 dark:bg-red-900/30";
      case "high":
        return "text-orange-600 bg-orange-50 dark:bg-orange-900/30";
      case "medium":
        return "text-yellow-600 bg-yellow-50 dark:bg-yellow-900/30";
      default:
        return "text-blue-600 bg-blue-50 dark:bg-blue-900/30";
    }
  };

  const filteredRules =
    selectedCategory === "all"
      ? sigmaRules
      : sigmaRules.filter((r) => r.category === selectedCategory);

  if (!mounted) return null;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <PageHeader title={t("title")} subtitle={t("subtitle")} />

      <main className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {loadError && <ErrorDisplay error={loadError} onRetry={loadData} compact />}

        {/* Stats */}
        {dashboard && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
              <p className="text-sm text-gray-600 dark:text-gray-400">{t("totalHunts")}</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {dashboard.summary.total_hunts_executed}
              </p>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
              <p className="text-sm text-gray-600 dark:text-gray-400">{t("findings")}</p>
              <p className="text-2xl font-bold text-green-600">
                {dashboard.summary.total_findings}
              </p>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
              <p className="text-sm text-gray-600 dark:text-gray-400">{t("critical")}</p>
              <p className="text-2xl font-bold text-red-600">
                {dashboard.summary.critical_findings}
              </p>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
              <p className="text-sm text-gray-600 dark:text-gray-400">{t("successRate")}</p>
              <p className="text-2xl font-bold text-blue-600">
                {dashboard.hunt_effectiveness.success_rate}
              </p>
            </div>
          </div>
        )}

        {/* Tab Navigation */}
        <div className="flex gap-2 mb-6 border-b border-gray-200 dark:border-gray-700">
          {(["hypotheses", "sigma", "timeline"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab
                  ? "border-green-500 text-green-600 dark:text-green-400"
                  : "border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
              }`}
            >
              {tab === "hypotheses"
                ? t("huntHypotheses")
                : tab === "sigma"
                  ? t("sigmaRules")
                  : t("timelineAnalysis")}
            </button>
          ))}
        </div>

        {activeTab === "timeline" ? (
          <LogTimelineAnalyzer />
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* ── MAIN COLUMN ── */}
            <div className="lg:col-span-2">
              {/* ── HYPOTHESES TAB ── */}
              {activeTab === "hypotheses" && (
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
                  <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                    <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                      <Shield className="w-5 h-5 text-green-500" />
                      {t("huntHypotheses")}
                    </h2>
                  </div>
                  <div className="p-4">
                    {loading ? (
                      <div className="text-center py-8 text-gray-500">{tCommon("loading")}</div>
                    ) : (
                      <div className="space-y-4">
                        {hypotheses.map((hypothesis) => (
                          <div
                            key={hypothesis.id}
                            className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:shadow-md transition-shadow"
                          >
                            <div className="flex items-start justify-between">
                              <div className="flex-1">
                                <div className="flex items-center gap-2 mb-2">
                                  <h3 className="font-semibold text-gray-900 dark:text-white">
                                    {hypothesis.name}
                                  </h3>
                                  <span
                                    className={`px-2 py-0.5 rounded text-xs font-medium ${getSeverityColor(hypothesis.severity)}`}
                                  >
                                    {hypothesis.severity === "critical"
                                      ? t("severity.critical")
                                      : hypothesis.severity === "high"
                                        ? t("severity.high")
                                        : hypothesis.severity === "medium"
                                          ? t("severity.medium")
                                          : t("severity.low")}
                                  </span>
                                  {hypothesis.verified && (
                                    <CheckCircle className="w-4 h-4 text-green-500" />
                                  )}
                                </div>
                                <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                                  {hypothesis.description}
                                </p>
                                <div className="flex items-center gap-4 text-xs text-gray-500">
                                  <span>
                                    {t("mitre")}: {hypothesis.mitre_techniques.join(", ")}
                                  </span>
                                  <span>
                                    {t("dataSources")}: {hypothesis.data_sources.join(", ")}
                                  </span>
                                </div>
                              </div>
                              <button
                                onClick={() => executeHunt(hypothesis.id)}
                                disabled={executing === hypothesis.id}
                                className="ml-4 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 flex items-center gap-2"
                              >
                                {executing === hypothesis.id ? (
                                  <>
                                    <Clock className="w-4 h-4 animate-spin" />
                                    {t("running")}
                                  </>
                                ) : (
                                  <>
                                    <Play className="w-4 h-4" />
                                    {t("run")}
                                  </>
                                )}
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* ── SIGMA RULES TAB ── */}
              {activeTab === "sigma" && (
                <div className="space-y-4">
                  {/* Category Filter */}
                  <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Filter className="w-4 h-4 text-gray-400" />
                      <button
                        onClick={() => setSelectedCategory("all")}
                        className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                          selectedCategory === "all"
                            ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300"
                            : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 active:bg-gray-100 dark:hover:bg-gray-700 active:bg-gray-700"
                        }`}
                      >
                        {t("all")} ({sigmaRules.length})
                      </button>
                      {sigmaCategories.map((cat) => (
                        <button
                          key={cat}
                          onClick={() => setSelectedCategory(cat)}
                          className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                            selectedCategory === cat
                              ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300"
                              : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 active:bg-gray-100 dark:hover:bg-gray-700 active:bg-gray-700"
                          }`}
                        >
                          {CATEGORY_ICONS[cat] || ""} {CATEGORY_LABELS[cat] || cat} (
                          {sigmaRules.filter((r) => r.category === cat).length})
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Rules List */}
                  <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
                    <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                      <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                        <Code className="w-5 h-5 text-green-500" />
                        {t("sigmaRulesList")} ({filteredRules.length})
                      </h2>
                    </div>
                    <div className="divide-y divide-gray-100 dark:divide-gray-700">
                      {filteredRules.map((rule) => (
                        <div key={rule.id}>
                          <button
                            onClick={() => loadRuleDetail(rule.id)}
                            className="w-full p-4 text-left hover:bg-gray-50 active:bg-gray-50 dark:hover:bg-gray-750 active:bg-gray-750 transition-colors flex items-start justify-between"
                          >
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-1">
                                <span className="text-sm">
                                  {selectedRuleId === rule.id ? (
                                    <ChevronDown className="w-4 h-4 text-green-500" />
                                  ) : (
                                    <ChevronRight className="w-4 h-4 text-gray-400" />
                                  )}
                                </span>
                                <h3 className="font-medium text-gray-900 dark:text-white text-sm">
                                  {rule.title}
                                </h3>
                                <span
                                  className={`px-2 py-0.5 rounded text-xs font-medium ${getSeverityColor(rule.level)}`}
                                >
                                  {rule.level}
                                </span>
                                <span className="text-xs text-gray-400 font-mono">{rule.id}</span>
                              </div>
                              <p className="text-xs text-gray-500 dark:text-gray-400 ml-6 line-clamp-2">
                                {rule.description}
                              </p>
                              <div className="flex items-center gap-3 ml-6 mt-1">
                                <span className="text-xs text-gray-400">
                                  {CATEGORY_ICONS[rule.category] || ""}{" "}
                                  {CATEGORY_LABELS[rule.category] || rule.category}
                                </span>
                                {rule.mitre_techniques.length > 0 && (
                                  <span className="text-xs px-1.5 py-0.5 bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 rounded font-mono">
                                    {rule.mitre_techniques[0]}
                                  </span>
                                )}
                              </div>
                            </div>
                          </button>

                          {/* Expanded Rule Detail */}
                          {selectedRuleId === rule.id && selectedRule && (
                            <div className="px-4 pb-4 border-t border-gray-100 dark:border-gray-700">
                              <div className="grid grid-cols-1 gap-3 mt-3">
                                {/* Meta info */}
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                                  <div className="p-2 bg-gray-50 dark:bg-gray-700 rounded">
                                    <span className="text-gray-400">{t("status")}</span>
                                    <p className="font-medium text-gray-700 dark:text-gray-300">
                                      {selectedRule.status}
                                    </p>
                                  </div>
                                  <div className="p-2 bg-gray-50 dark:bg-gray-700 rounded">
                                    <span className="text-gray-400">{t("author")}</span>
                                    <p className="font-medium text-gray-700 dark:text-gray-300">
                                      {selectedRule.author}
                                    </p>
                                  </div>
                                  <div className="p-2 bg-gray-50 dark:bg-gray-700 rounded">
                                    <span className="text-gray-400">{t("logsource")}</span>
                                    <p className="font-medium text-gray-700 dark:text-gray-300">
                                      {selectedRule.logsource.product} /{" "}
                                      {selectedRule.logsource.service}
                                    </p>
                                  </div>
                                  <div className="p-2 bg-gray-50 dark:bg-gray-700 rounded">
                                    <span className="text-gray-400">MITRE</span>
                                    <p className="font-medium text-gray-700 dark:text-gray-300">
                                      {selectedRule.mitre_techniques.join(", ") || "—"}
                                    </p>
                                  </div>
                                </div>

                                {/* Tags */}
                                {selectedRule.tags.length > 0 && (
                                  <div className="flex flex-wrap gap-1">
                                    {selectedRule.tags.map((tag, i) => (
                                      <span
                                        key={i}
                                        className="px-2 py-0.5 bg-purple-50 dark:bg-purple-900/20 text-purple-600 dark:text-purple-400 rounded text-xs"
                                      >
                                        {tag}
                                      </span>
                                    ))}
                                  </div>
                                )}

                                {/* SQL Preview */}
                                <div>
                                  <div className="flex items-center justify-between mb-1">
                                    <span className="text-xs font-medium text-gray-500 dark:text-gray-400 flex items-center gap-1">
                                      <Database className="w-3 h-3" />
                                      {t("generatedSQL")}
                                    </span>
                                  </div>
                                  <pre className="p-3 bg-gray-900 text-green-400 rounded-lg text-xs overflow-x-auto font-mono max-h-40">
                                    {selectedRule.generated_sql}
                                  </pre>
                                </div>

                                {/* Execute Button */}
                                <div className="flex gap-2">
                                  <button
                                    onClick={() => executeSigmaSearch(rule.id)}
                                    disabled={searching}
                                    className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 flex items-center gap-2 text-sm font-medium"
                                  >
                                    {searching ? (
                                      <>
                                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                        {t("searching")}
                                      </>
                                    ) : (
                                      <>
                                        <Search className="w-4 h-4" />
                                        {t("executeSearch")}
                                      </>
                                    )}
                                  </button>
                                </div>

                                {/* Search Results */}
                                {sigmaSearchResult && sigmaSearchResult.rule_id === rule.id && (
                                  <div className="space-y-2">
                                    <div className="flex items-center gap-3">
                                      <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                                        {t("matchCount")}:{" "}
                                        <span className="text-green-600 font-bold">
                                          {sigmaSearchResult.total_matches}
                                        </span>
                                      </span>
                                      {sigmaSearchResult.total_matches > 0 && (
                                        <span className="px-2 py-0.5 bg-red-100 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded text-xs font-medium">
                                          {t("matchesFound")}
                                        </span>
                                      )}
                                    </div>
                                    {sigmaSearchResult.matches.length > 0 && (
                                      <div className="overflow-x-auto">
                                        <table className="w-full text-xs border border-gray-200 dark:border-gray-700 rounded-lg">
                                          <thead>
                                            <tr className="bg-gray-50 dark:bg-gray-700">
                                              {Object.keys(sigmaSearchResult.matches[0]).map(
                                                (key) => (
                                                  <th
                                                    key={key}
                                                    className="px-3 py-2 text-left font-medium text-gray-600 dark:text-gray-300 whitespace-nowrap"
                                                  >
                                                    {key}
                                                  </th>
                                                )
                                              )}
                                            </tr>
                                          </thead>
                                          <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                                            {sigmaSearchResult.matches.map((match, idx) => (
                                              <tr
                                                key={idx}
                                                className="hover:bg-gray-50 active:bg-gray-50 dark:hover:bg-gray-750 active:bg-gray-750"
                                              >
                                                {Object.values(match).map((val: any, i) => (
                                                  <td
                                                    key={i}
                                                    className="px-3 py-2 text-gray-700 dark:text-gray-300 max-w-xs truncate"
                                                  >
                                                    {String(val ?? "—")}
                                                  </td>
                                                ))}
                                              </tr>
                                            ))}
                                          </tbody>
                                        </table>
                                      </div>
                                    )}
                                  </div>
                                )}
                              </div>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                    {filteredRules.length === 0 && (
                      <div className="p-8 text-center text-gray-400">
                        <Code className="w-8 h-8 mx-auto mb-2 opacity-50" />
                        {t("noSigmaRules")}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* ── SIDEBAR ── */}
            <div className="space-y-6">
              {/* Recent Results */}
              <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
                <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                  <h3 className="font-semibold text-gray-900 dark:text-white">
                    {t("recentResults")}
                  </h3>
                </div>
                <div className="p-4">
                  {results.slice(0, 5).map((result, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between py-3 border-b border-gray-100 dark:border-gray-700 last:border-0"
                    >
                      <div>
                        <p className="font-medium text-gray-900 dark:text-white text-sm">
                          {result.hunt_name}
                        </p>
                        <p className="text-xs text-gray-500">
                          {format.dateTime(new Date(result.started_at), {
                            dateStyle: "medium",
                            timeStyle: "medium",
                          })}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        {result.findings_count > 0 ? (
                          <span className="px-2 py-1 bg-red-100 text-red-600 rounded text-xs">
                            {t("findingsCount", { count: result.findings_count })}
                          </span>
                        ) : (
                          <span className="px-2 py-1 bg-green-100 text-green-600 rounded text-xs">
                            {t("clean")}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Top MITRE Techniques */}
              {dashboard && (
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4">
                  <h3 className="font-semibold text-gray-900 dark:text-white mb-4">
                    {t("topTechniques")}
                  </h3>
                  <div className="space-y-3">
                    {dashboard.top_mitre_techniques.map((tech, index) => (
                      <div key={index} className="flex items-center justify-between">
                        <div>
                          <p className="text-sm font-medium text-gray-900 dark:text-white">
                            {tech.technique}
                          </p>
                          <p className="text-xs text-gray-500">{tech.name}</p>
                        </div>
                        <span className="text-sm text-gray-600">
                          {tech.count} {t("times")}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Sigma Quick Stats */}
              {sigmaRules.length > 0 && (
                <div className="bg-gradient-to-br from-green-50 to-teal-50 dark:from-green-900/20 dark:to-teal-900/20 rounded-xl p-4 border border-green-200 dark:border-green-800">
                  <h4 className="font-medium text-green-900 dark:text-green-100 mb-3 flex items-center gap-2">
                    <Zap className="w-4 h-4" />
                    {t("sigmaQuickStats")}
                  </h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between text-green-800 dark:text-green-200">
                      <span>{t("totalRules")}</span>
                      <span className="font-bold">{sigmaRules.length}</span>
                    </div>
                    {sigmaCategories.map((cat) => (
                      <div
                        key={cat}
                        className="flex justify-between text-green-800 dark:text-green-200"
                      >
                        <span>{CATEGORY_LABELS[cat] || cat}</span>
                        <span className="font-bold">
                          {sigmaRules.filter((r) => r.category === cat).length}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* IOC Hunt */}
              <div className="bg-gradient-to-br from-green-50 to-teal-50 dark:from-green-900/20 dark:to-teal-900/20 rounded-xl p-4 border border-green-200 dark:border-green-800">
                <h4 className="font-medium text-green-900 dark:text-green-100 mb-2 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4" />
                  {t("iocHunt.title")}
                </h4>
                <p className="text-sm text-green-800 dark:text-green-200 mb-3">
                  {t("iocHunt.description")}
                </p>
                <button
                  onClick={() => showToast(t("iocHunt.comingSoon"), "info")}
                  className="w-full py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm"
                >
                  {t("iocHunt.button")}
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
