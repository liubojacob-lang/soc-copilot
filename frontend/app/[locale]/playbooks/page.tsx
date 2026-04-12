"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useTranslations, useLocale } from "next-intl";
import { api } from "@/lib/api";
import { loadAuthState } from "@/lib/auth";
import Navigation from "@/components/Navigation";
import { SkeletonTable } from "@/components/common/LoadingState";
import { STATUS_COLORS, MODE_COLORS } from "./constants";
import { usePlaybooks } from "./hooks/usePlaybooks";
import { useKeyboardShortcuts } from "@/hooks/useKeyboardShortcuts";
import {
  Search,
  RefreshCw,
  Play,
  BookOpen,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  Eye,
  Edit2,
  Trash2,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

export default function PlaybooksPage() {
  const router = useRouter();
  const locale = useLocale();
  const t = useTranslations("playbooks");
  const tCommon = useTranslations("common");
  const [activeTab, setActiveTab] = useState<"runs" | "definitions" | "create">("runs");
  const [mounted, setMounted] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [refreshing, setRefreshing] = useState(false);

  const {
    runs,
    playbooks,
    definitions,
    queueStats,
    loading,
    error,
    runsPagination,
    definitionsPagination,
    filters,
    setFilters,
    loadData,
    loadDefinitions,
  } = usePlaybooks();

  useEffect(() => {
    setMounted(true);
    if (activeTab === "definitions") {
      loadDefinitions(1);
    }
  }, [activeTab]);

  const [autoRefresh, setAutoRefresh] = useState(true);
  const [autoRefreshInterval, setAutoRefreshInterval] = useState<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (autoRefresh && !refreshing) {
      const interval = setInterval(() => {
        loadData();
      }, 10000); // Auto refresh every 10 seconds
      setAutoRefreshInterval(interval);
      return () => clearInterval(interval);
    }
  }, [autoRefresh, refreshing, loadData]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadData(runsPagination.currentPage);
    setRefreshing(false);
  };

  const handlePageChange = (newPage: number) => {
    loadData(newPage);
  };

  const totalRunsPages = Math.ceil(runsPagination.total / runsPagination.pageSize);

  const filteredRuns = runs.filter((run) => {
    if (!searchQuery) return true;
    const search = searchQuery.toLowerCase();
    return (
      run.playbook_name.toLowerCase().includes(search) || run.id.toLowerCase().includes(search)
    );
  });

  // Keyboard shortcuts
  useKeyboardShortcuts(
    {
      r: () => {
        setRefreshing(true);
        loadData(runsPagination.currentPage).finally(() => setRefreshing(false));
      },
      "/": () => {
        document.querySelector<HTMLInputElement>('input[type="text"]')?.focus();
      },
      "1": () => setActiveTab("runs"),
      "2": () => setActiveTab("definitions"),
    },
    { enabled: mounted && !loading }
  );

  if (!mounted) return null;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Navigation title={t("title")} subtitle={t("subtitle")} />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Tabs */}
        <div className="mb-6">
          <div className="border-b border-gray-200 dark:border-gray-700">
            <nav className="-mb-px flex space-x-8">
              <button
                onClick={() => setActiveTab("runs")}
                className={`${activeTab === "runs" ? "border-blue-600 text-blue-600" : "border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"} py-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2 transition-colors`}
              >
                <Play className="w-4 h-4" />
                {t("tabs.runs")}
              </button>
              <button
                onClick={() => setActiveTab("definitions")}
                className={`${activeTab === "definitions" ? "border-blue-600 text-blue-600" : "border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"} py-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2 transition-colors`}
              >
                <BookOpen className="w-4 h-4" />
                {t("tabs.definitions")}
              </button>
            </nav>
          </div>
        </div>

        {/* Runs Tab */}
        {activeTab === "runs" && (
          <>
            {/* Queue Stats */}
            {queueStats && (
              <div className="mb-6 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-lg border border-blue-100 dark:border-blue-800">
                <div className="flex items-center gap-6">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
                    <span className="text-sm text-gray-600 dark:text-gray-400">
                      {t("queue.running")}:
                    </span>
                    <span className="font-semibold text-gray-900 dark:text-white">
                      {queueStats.running}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Clock className="w-4 h-4 text-amber-500" />
                    <span className="text-sm text-gray-600 dark:text-gray-400">
                      {t("queue.queued")}:
                    </span>
                    <span className="font-semibold text-gray-900 dark:text-white">
                      {queueStats.queued}
                    </span>
                  </div>
                  <div className="ml-auto text-xs text-gray-500 dark:text-gray-400">
                    Max concurrent: {queueStats.max_concurrent}
                  </div>
                </div>
              </div>
            )}

            {/* Filters */}
            <div className="bg-white dark:bg-gray-800 rounded-lg p-4 mb-6 shadow-sm border border-gray-200 dark:border-gray-700">
              <div className="flex flex-col sm:flex-row gap-4">
                <div className="flex-1 relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    type="text"
                    placeholder={t("searchPlaceholder")}
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
                <select
                  value={filters.playbook}
                  onChange={(e) => setFilters({ ...filters, playbook: e.target.value })}
                  className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">{t("allPlaybooks")}</option>
                  {Object.entries(playbooks).map(([key, pb]) => (
                    <option key={key} value={key}>
                      {pb.name}
                    </option>
                  ))}
                </select>
                <select
                  value={filters.status}
                  onChange={(e) => setFilters({ ...filters, status: e.target.value })}
                  className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">{t("allStatuses")}</option>
                  <option value="running">{t("statuses.running")}</option>
                  <option value="success">{t("statuses.success")}</option>
                  <option value="failed">{t("statuses.failed")}</option>
                </select>
                <button
                  onClick={handleRefresh}
                  disabled={refreshing}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2 transition-colors shadow-sm"
                >
                  <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} />
                  {refreshing ? tCommon("loading") : tCommon("refresh")}
                </button>
                <button
                  onClick={() => setAutoRefresh(!autoRefresh)}
                  className={`px-3 py-2 border rounded-lg flex items-center gap-2 transition-colors ${
                    autoRefresh
                      ? "bg-green-50 border-green-300 text-green-700 dark:bg-green-900/20 dark:border-green-700 dark:text-green-400"
                      : "border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700"
                  }`}
                  title={autoRefresh ? "Auto-refresh ON (10s)" : "Auto-refresh OFF"}
                >
                  <div
                    className={`w-2 h-2 rounded-full ${autoRefresh ? "bg-green-500 animate-pulse" : "bg-gray-400"}`}
                  />
                  <span className="text-sm">{autoRefresh ? "Live" : "Paused"}</span>
                </button>
              </div>
            </div>

            {error && (
              <div className="mb-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-center gap-2">
                <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
                <span className="text-red-700 dark:text-red-300">{error}</span>
              </div>
            )}

            {loading ? (
              <div className="bg-white dark:bg-gray-800 rounded-lg p-4">
                <SkeletonTable rows={5} columns={5} />
              </div>
            ) : filteredRuns.length === 0 ? (
              <div className="text-center py-16 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center">
                  <Play className="w-8 h-8 text-gray-400" />
                </div>
                <p className="text-gray-500 dark:text-gray-400 text-lg mb-2">
                  {t("noPlaybookRuns")}
                </p>
                <p className="text-gray-400 dark:text-gray-500 text-sm">{t("runPlaybookHint")}</p>
              </div>
            ) : (
              <div className="bg-white dark:bg-gray-800 rounded-lg overflow-hidden shadow-sm border border-gray-200 dark:border-gray-700">
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-50 dark:bg-gray-700 border-b border-gray-200 dark:border-gray-600">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                          {t("playbook")}
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                          {t("status")}
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                          {t("mode")}
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                          {t("started")}
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                          {t("duration")}
                        </th>
                        <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                          {tCommon("actions")}
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                      {filteredRuns.map((run) => {
                        const duration = run.finished_at
                          ? Math.round(
                              (new Date(run.finished_at).getTime() -
                                new Date(run.started_at).getTime()) /
                                1000
                            )
                          : null;
                        return (
                          <tr
                            key={run.id}
                            className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                          >
                            <td className="px-6 py-4">
                              <div className="font-medium text-gray-900 dark:text-white">
                                {playbooks[run.playbook_name]?.name || run.playbook_name}
                              </div>
                              <div className="text-xs text-gray-500 dark:text-gray-400 font-mono">
                                {run.id.slice(0, 8)}...
                              </div>
                            </td>
                            <td className="px-6 py-4">
                              <span
                                className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${STATUS_COLORS[run.status]}`}
                              >
                                {run.status === "success" && <CheckCircle className="w-3 h-3" />}
                                {run.status === "failed" && <XCircle className="w-3 h-3" />}
                                {run.status === "running" && (
                                  <div className="w-2 h-2 bg-current rounded-full animate-pulse" />
                                )}
                                {t(`statuses.${run.status}`)}
                              </span>
                            </td>
                            <td className="px-6 py-4">
                              <span
                                className={`px-2.5 py-1 rounded-full text-xs font-medium ${MODE_COLORS[run.mode]}`}
                              >
                                {run.mode}
                              </span>
                            </td>
                            <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-300">
                              {new Date(run.started_at).toLocaleDateString()}
                              <div className="text-xs text-gray-400">
                                {new Date(run.started_at).toLocaleTimeString()}
                              </div>
                            </td>
                            <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-300">
                              {duration !== null ? (
                                <span className="font-mono">{duration}s</span>
                              ) : (
                                <span className="text-gray-400">-</span>
                              )}
                            </td>
                            <td className="px-6 py-4 text-right">
                              <a
                                href={`/${locale}/playbooks/${run.id}`}
                                className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 text-sm font-medium"
                              >
                                <Eye className="w-4 h-4" />
                                {tCommon("viewDetails")}
                              </a>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>

                  {/* Pagination */}
                  {totalRunsPages > 1 && (
                    <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 dark:border-gray-700">
                      <div className="text-sm text-gray-500 dark:text-gray-400">
                        Showing {(runsPagination.currentPage - 1) * runsPagination.pageSize + 1} to{" "}
                        {Math.min(
                          runsPagination.currentPage * runsPagination.pageSize,
                          runsPagination.total
                        )}{" "}
                        of {runsPagination.total} results
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handlePageChange(runsPagination.currentPage - 1)}
                          disabled={runsPagination.currentPage === 1}
                          className="p-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          <ChevronLeft className="w-4 h-4" />
                        </button>
                        <span className="text-sm text-gray-600 dark:text-gray-400">
                          Page {runsPagination.currentPage} of {totalRunsPages}
                        </span>
                        <button
                          onClick={() => handlePageChange(runsPagination.currentPage + 1)}
                          disabled={runsPagination.currentPage === totalRunsPages}
                          className="p-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          <ChevronRight className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </>
        )}

        {/* Definitions Tab */}
        {activeTab === "definitions" && (
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                  {t("definitions.title")}
                </h2>
                <p className="text-gray-500 dark:text-gray-400 mt-1">{t("definitions.subtitle")}</p>
              </div>
            </div>
            {definitions.length === 0 ? (
              <div className="text-center py-16">
                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center">
                  <BookOpen className="w-8 h-8 text-gray-400" />
                </div>
                <p className="text-gray-500 dark:text-gray-400 text-lg">
                  {t("definitions.noDefinitions")}
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 dark:bg-gray-700 border-b border-gray-200 dark:border-gray-600">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                        {t("definitions.name")}
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                        {t("definitions.description")}
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                        {t("definitions.version")}
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                        {t("definitions.status")}
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                        {t("definitions.actions")}
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                    {definitions.map((def) => (
                      <tr
                        key={def.id}
                        className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                      >
                        <td className="px-6 py-4 font-medium text-gray-900 dark:text-white">
                          {def.name}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-300 max-w-xs truncate">
                          {def.description || "-"}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-300 font-mono">
                          v{def.version}
                        </td>
                        <td className="px-6 py-4">
                          <span
                            className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${
                              def.status === "published"
                                ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                                : "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
                            }`}
                          >
                            {def.status}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <button className="p-2 text-gray-500 hover:text-blue-600 dark:text-gray-400 dark:hover:text-blue-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors">
                              <Eye className="w-4 h-4" />
                            </button>
                            <button className="p-2 text-gray-500 hover:text-blue-600 dark:text-gray-400 dark:hover:text-blue-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors">
                              <Edit2 className="w-4 h-4" />
                            </button>
                            <button className="p-2 text-gray-500 hover:text-red-600 dark:text-gray-400 dark:hover:text-red-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors">
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
