"use client";

import { useState, useEffect } from "react";
import { useRouter, Link } from "@/i18n/navigation";
import { useFormatter, useTranslations, useLocale } from "next-intl";
import { api } from "@/lib/api";
import { loadAuthState, authFetch } from "@/lib/auth";
import { PageHeader } from "@/components/common/PageHeader";
import { SkeletonTable } from "@/components/common/LoadingState";
import { STATUS_COLORS, MODE_COLORS } from "./constants";
import { usePlaybooks } from "./hooks/usePlaybooks";
import { useKeyboardShortcuts } from "@/hooks/useKeyboardShortcuts";
import {
  Search,
  RefreshCw,
  Play,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  Eye,
  ChevronLeft,
  ChevronRight,
  Download,
  FileStack,
  ArrowRight,
} from "lucide-react";

export default function PlaybooksPage() {
  const router = useRouter();
  const locale = useLocale();
  const t = useTranslations("playbooks");
  const format = useFormatter();
  const tCommon = useTranslations("common");
  const [mounted, setMounted] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [refreshing, setRefreshing] = useState(false);

  const {
    runs,
    playbooks,
    queueStats,
    loading,
    error,
    runsPagination,
    filters,
    setFilters,
    loadData,
  } = usePlaybooks();

  useEffect(() => {
    setMounted(true);
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const tabParam = params.get("tab");
      if (tabParam === "definitions") {
        router.replace("/playbooks/definitions");
      }
    }
  }, [router]);

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

  const [exporting, setExporting] = useState(false);

  const handleExport = async (formatType: "csv" | "json" = "csv") => {
    try {
      setExporting(true);
      const params = new URLSearchParams();
      params.append("format", formatType);
      if (filters.playbook) params.append("playbook_name", filters.playbook);
      if (filters.status) params.append("status", filters.status);

      const res = await authFetch(`/api/v1/export/playbook-runs?${params.toString()}`);
      if (!res.ok) throw new Error("Export failed");

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `playbook_runs_${new Date().toISOString().slice(0, 10)}.${formatType}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error("Export error:", err);
      alert(t("exportFailed"));
    } finally {
      setExporting(false);
    }
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
    },
    { enabled: mounted && !loading }
  );

  if (!mounted) return null;

  return (
    <div className="min-h-screen bg-surface-page transition-colors">
      <PageHeader title={t("title")} subtitle={t("subtitle")} />

      <main className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-5">
        {/* Header bar: Queue Stats & Quick Link */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-3.5">
          {queueStats ? (
            <div className="inline-flex items-center gap-3 px-3 py-1.5 bg-surface-card rounded-lg border border-border-subtle text-xs shadow-xs self-start sm:self-auto">
              <div className="flex items-center gap-1.5">
                <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse"></div>
                <span className="text-text-secondary">{t("queue.running")}:</span>
                <span className="font-semibold text-text-primary">{queueStats.running}</span>
              </div>
              <div className="w-px h-3 bg-border-subtle" />
              <div className="flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-amber-500" />
                <span className="text-text-secondary">{t("queue.queued")}:</span>
                <span className="font-semibold text-text-primary">{queueStats.queued}</span>
              </div>
              <div className="w-px h-3 bg-border-subtle" />
              <span className="text-text-muted">Max: {queueStats.max_concurrent}</span>
            </div>
          ) : (
            <div />
          )}

          <Link
            href="/playbooks/definitions"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border-default bg-surface-card hover:bg-surface-hover text-text-secondary hover:text-accent-600 dark:hover:text-accent-400 text-xs font-medium transition-colors shadow-xs self-end sm:self-auto"
          >
            <FileStack className="w-3.5 h-3.5 text-accent-600 dark:text-accent-400" />
            <span>{t("goToDefinitions")}</span>
            <ArrowRight className="w-3 h-3 text-text-muted" />
          </Link>
        </div>
        {/* Filters & Actions Toolbar */}
        <div className="flex flex-col md:flex-row items-stretch md:items-center gap-2.5 mb-3.5">
          <div className="flex-1 relative min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
            <input
              type="text"
              placeholder={t("searchPlaceholder")}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-sm border border-border-default rounded-lg bg-surface-input text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent-500/20 focus:border-accent-600 transition-colors h-9"
            />
          </div>
          <select
            value={filters.playbook}
            onChange={(e) => setFilters({ ...filters, playbook: e.target.value })}
            className="px-3 py-1.5 text-sm border border-border-default rounded-lg bg-surface-input text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-500/20 focus:border-accent-600 transition-colors h-9"
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
            className="px-3 py-1.5 text-sm border border-border-default rounded-lg bg-surface-input text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-500/20 focus:border-accent-600 transition-colors h-9"
          >
            <option value="">{t("allStatuses")}</option>
            <option value="running">{t("statuses.running")}</option>
            <option value="success">{t("statuses.success")}</option>
            <option value="failed">{t("statuses.failed")}</option>
          </select>
          <div className="flex items-center gap-2">
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="h-9 px-3 bg-accent-600 hover:bg-accent-700 text-white rounded-lg disabled:opacity-50 flex items-center gap-1.5 transition-colors text-sm font-medium shadow-subtle"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} />
              {refreshing ? tCommon("loading") : tCommon("refresh")}
            </button>
            <button
              onClick={() => handleExport("csv")}
              disabled={exporting}
              className="h-9 px-3 border border-border-default rounded-lg hover:bg-surface-hover active:bg-surface-active flex items-center gap-1.5 transition-colors text-sm text-text-secondary disabled:opacity-50 bg-surface-card"
              title={t("exportCsv")}
            >
              <Download className={`w-3.5 h-3.5 ${exporting ? "animate-bounce" : ""}`} />
              {exporting ? t("exporting") : tCommon("export")}
            </button>
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`h-9 px-2.5 border rounded-lg flex items-center gap-1.5 transition-colors text-xs ${
                autoRefresh
                  ? "bg-success-500/15 border-success-500/30 text-success-700 dark:text-success-300"
                  : "border-border-default hover:bg-surface-hover active:bg-surface-active text-text-secondary bg-surface-card"
              }`}
              title={autoRefresh ? "Auto-refresh ON (10s)" : "Auto-refresh OFF"}
            >
              <div
                className={`w-2 h-2 rounded-full ${autoRefresh ? "bg-success-500 animate-pulse" : "bg-text-tertiary"}`}
              />
              <span className="font-medium">{autoRefresh ? "Live" : "Paused"}</span>
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-3.5 p-3.5 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-center gap-2 text-sm">
            <AlertCircle className="w-4 h-4 text-red-600 dark:text-red-400 shrink-0" />
            <span className="text-red-700 dark:text-red-300">{error}</span>
          </div>
        )}

        {loading ? (
          <div className="bg-surface-card rounded-xl p-4 border border-border-subtle">
            <SkeletonTable rows={5} columns={5} />
          </div>
        ) : filteredRuns.length === 0 ? (
          <div className="text-center py-12 bg-surface-card rounded-xl border border-border-subtle">
            <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-surface-hover flex items-center justify-center">
              <Play className="w-6 h-6 text-text-muted" />
            </div>
            <p className="text-text-primary font-medium text-base mb-1">{t("noPlaybookRuns")}</p>
            <p className="text-text-muted text-xs">{t("runPlaybookHint")}</p>
          </div>
        ) : (
          <div className="bg-surface-card rounded-xl overflow-hidden shadow-subtle border border-border-subtle">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-surface-hover/50 border-b border-border-subtle text-xs uppercase text-text-muted">
                  <tr>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold text-text-muted uppercase tracking-wider">
                      {t("playbook")}
                    </th>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold text-text-muted uppercase tracking-wider">
                      {t("status")}
                    </th>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold text-text-muted uppercase tracking-wider">
                      {t("mode")}
                    </th>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold text-text-muted uppercase tracking-wider">
                      {t("started")}
                    </th>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold text-text-muted uppercase tracking-wider">
                      {t("duration")}
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-subtle">
                  {filteredRuns.map((run) => {
                    const duration = run.finished_at
                      ? Math.round(
                          (new Date(run.finished_at).getTime() -
                            new Date(run.started_at).getTime()) /
                            1000
                        )
                      : null;
                    return (
                      <tr key={run.id} className="hover:bg-surface-hover/50 transition-colors">
                        <td className="px-4 py-2.5">
                          <button
                            type="button"
                            onClick={() => router.push(`/playbooks/${run.id}`)}
                            className="font-semibold text-accent-600 hover:text-accent-700 dark:text-accent-400 dark:hover:text-accent-300 hover:underline text-left block text-sm transition-colors"
                          >
                            {playbooks[run.playbook_name]?.name || run.playbook_name}
                          </button>
                          <div className="text-xs text-text-muted font-mono mt-0.5">
                            {run.id.slice(0, 8)}...
                          </div>
                        </td>
                        <td className="px-4 py-2.5">
                          <span
                            className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[run.status]}`}
                          >
                            {run.status === "success" && <CheckCircle className="w-3 h-3" />}
                            {run.status === "failed" && <XCircle className="w-3 h-3" />}
                            {run.status === "running" && (
                              <div className="w-2 h-2 bg-current rounded-full animate-pulse" />
                            )}
                            {t(`statuses.${run.status}`)}
                          </span>
                        </td>
                        <td className="px-4 py-2.5">
                          <span
                            className={`px-2 py-0.5 rounded-full text-xs font-medium ${MODE_COLORS[run.mode]}`}
                          >
                            {run.mode}
                          </span>
                        </td>
                        <td className="px-4 py-2.5 text-sm text-text-secondary">
                          {format.dateTime(new Date(run.started_at), { dateStyle: "medium" })}
                          <div className="text-xs text-text-muted mt-0.5">
                            {format.dateTime(new Date(run.started_at), { timeStyle: "medium" })}
                          </div>
                        </td>
                        <td className="px-4 py-2.5 text-sm text-text-secondary font-mono">
                          {duration !== null ? (
                            <span>{duration}s</span>
                          ) : (
                            <span className="text-text-tertiary">-</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>

              {/* Pagination */}
              {totalRunsPages > 1 && (
                <div className="flex items-center justify-between px-4 py-2.5 border-t border-border-subtle">
                  <div className="text-xs text-text-muted">
                    Showing {(runsPagination.currentPage - 1) * runsPagination.pageSize + 1} to{" "}
                    {Math.min(
                      runsPagination.currentPage * runsPagination.pageSize,
                      runsPagination.total
                    )}{" "}
                    of {runsPagination.total} results
                  </div>
                  <div className="flex items-center gap-1.5">
                    <button
                      onClick={() => handlePageChange(runsPagination.currentPage - 1)}
                      disabled={runsPagination.currentPage === 1}
                      className="p-1.5 border border-border-default rounded-lg hover:bg-surface-hover active:bg-surface-active text-text-secondary disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </button>
                    <span className="text-xs text-text-secondary px-1">
                      Page {runsPagination.currentPage} of {totalRunsPages}
                    </span>
                    <button
                      onClick={() => handlePageChange(runsPagination.currentPage + 1)}
                      disabled={runsPagination.currentPage === totalRunsPages}
                      className="p-1.5 border border-border-default rounded-lg hover:bg-surface-hover active:bg-surface-active text-text-secondary disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
