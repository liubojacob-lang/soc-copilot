"use client";

import { useState } from "react";
import { useFormatter, useTranslations } from "next-intl";
import { LoadingState } from "@/components/common/LoadingState";
import { PageHeader } from "@/components/common/PageHeader";
import { cn } from "@/lib/utils";
import { apiClient as api } from "@/lib/api";

// ── Types ──
type TIResult = {
  type: string;
  value: string;
  source: string;
  score: number;
  details: Record<string, unknown>;
  last_seen: string;
};

type SearchResponse = {
  results: TIResult[];
  total: number;
  query_time_ms: number;
};

// ── IOC type config ──
const IOC_TYPES = [
  { value: "ip", labelKey: "ip" },
  { value: "domain", labelKey: "domain" },
  { value: "url", labelKey: "url" },
  { value: "hash", labelKey: "hash" },
] as const;

const SOURCES = [
  { value: "otx", label: "AlienVault OTX" },
  { value: "virustotal", label: "VirusTotal" },
  { value: "misp", label: "MISP" },
] as const;

// ── Score color ──
function scoreColor(score: number): string {
  if (score >= 70) return "text-red-600 dark:text-red-400";
  if (score >= 40) return "text-amber-600 dark:text-amber-400";
  if (score > 0) return "text-green-600 dark:text-green-400";
  return "text-gray-400";
}

function scoreBg(score: number): string {
  if (score >= 70) return "bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800";
  if (score >= 40) return "bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800";
  if (score > 0) return "bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800";
  return "bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700";
}

// ── Main Page ──
export default function ThreatIntelPage() {
  const t = useTranslations("threatIntel");

  const format = useFormatter();
  const [query, setQuery] = useState("");
  const [iocType, setIocType] = useState("ip");
  const [results, setResults] = useState<TIResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [queryTime, setQueryTime] = useState<number | null>(null);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setIsLoading(true);
    setError(null);
    try {
      // fetch has no axios-style `params`; the query string must be explicit
      // (the previous object form silently dropped the search term).
      const params = new URLSearchParams({ q: query.trim(), type: iocType });
      const response = await api.get<SearchResponse>(`/api/ti/search?${params.toString()}`);
      setResults(response.results || []);
      setQueryTime(response.query_time_ms);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
      setResults([]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <PageHeader title={t("title")} subtitle={t("description")} />

      <main className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Search Bar */}
        <div>
          <div className="bg-white dark:bg-gray-900 shadow-sm border border-gray-200 dark:border-gray-800 rounded-2xl p-4">
            <div className="flex flex-col sm:flex-row gap-3">
              {/* IOC type selector */}
              <select
                value={iocType}
                onChange={(e) => setIocType(e.target.value)}
                className="px-3 py-2.5 text-sm rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                {IOC_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.labelKey.toUpperCase()}
                  </option>
                ))}
              </select>

              {/* Search input */}
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                placeholder={t("searchPlaceholder")}
                className="flex-1 px-4 py-2.5 text-sm rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />

              {/* Search button */}
              <button
                onClick={handleSearch}
                disabled={isLoading || !query.trim()}
                className="px-6 py-2.5 text-sm font-medium rounded-xl bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isLoading ? t("searching") : t("search")}
              </button>
            </div>

            {/* Source badges */}
            <div className="flex gap-2 mt-3 flex-wrap">
              <span className="text-xs text-gray-400 dark:text-gray-500">{t("sources")}:</span>
              {SOURCES.map((s) => (
                <span
                  key={s.value}
                  className="inline-flex items-center px-2 py-0.5 text-xs rounded-full bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400"
                >
                  {s.label}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Results */}
        <div className="px-4 sm:px-0">
          <LoadingState
            isLoading={isLoading}
            error={error}
            empty={!isLoading && !error && results.length === 0 && query !== ""}
            emptyMessage={t("noResults")}
            skeletonType="card"
            onRetry={handleSearch}
          >
            {results.length > 0 && (
              <>
                {/* Query info */}
                {queryTime !== null && (
                  <p className="text-xs text-gray-400 dark:text-gray-500 mb-3">
                    {results.length} {t("resultsFound")} · {queryTime}ms
                  </p>
                )}

                {/* Result cards */}
                <div className="grid gap-3">
                  {results.map((result, idx) => (
                    <div
                      key={`${result.source}-${idx}`}
                      className={cn(
                        "bg-white dark:bg-gray-900 border rounded-2xl p-4 shadow-sm transition-shadow hover:shadow-md",
                        scoreBg(result.score)
                      )}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1 min-w-0">
                          {/* IOC value + type */}
                          <div className="flex items-center gap-2 mb-1">
                            <span className="inline-flex items-center px-1.5 py-0.5 text-[10px] font-semibold uppercase rounded bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400">
                              {result.type}
                            </span>
                            <h3 className="text-sm font-mono font-semibold text-gray-900 dark:text-white truncate">
                              {result.value}
                            </h3>
                          </div>

                          {/* Source + last seen */}
                          <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
                            <span className="inline-flex items-center gap-1">
                              <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
                              {result.source.toUpperCase()}
                            </span>
                            {result.last_seen && (
                              <span>
                                {t("lastSeen")}:{" "}
                                {format.dateTime(new Date(result.last_seen), {
                                  dateStyle: "medium",
                                })}
                              </span>
                            )}
                          </div>

                          {/* Details */}
                          {result.details && Object.keys(result.details).length > 0 && (
                            <div className="mt-2 pt-2 border-t border-gray-100 dark:border-gray-800">
                              <dl className="grid grid-cols-2 sm:grid-cols-3 gap-x-4 gap-y-1 text-xs">
                                {Object.entries(result.details)
                                  .slice(0, 6)
                                  .map(([k, v]) => (
                                    <div key={k} className="flex gap-1">
                                      <dt className="text-gray-400 dark:text-gray-500 shrink-0">
                                        {k}:
                                      </dt>
                                      <dd className="text-gray-700 dark:text-gray-300 truncate">
                                        {typeof v === "string" ? v : JSON.stringify(v)}
                                      </dd>
                                    </div>
                                  ))}
                              </dl>
                            </div>
                          )}
                        </div>

                        {/* Score badge */}
                        <div className="shrink-0">
                          <span
                            className={cn(
                              "inline-flex items-center justify-center w-12 h-12 rounded-xl text-sm font-bold",
                              scoreColor(result.score),
                              "bg-white/80 dark:bg-gray-800/80 border",
                              scoreBg(result.score)
                            )}
                          >
                            {result.score}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </LoadingState>
        </div>
      </main>
    </div>
  );
}
