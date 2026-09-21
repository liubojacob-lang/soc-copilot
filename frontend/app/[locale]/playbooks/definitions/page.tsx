"use client";

import { useState, useEffect } from "react";
import { useRouter } from "@/i18n/navigation";
import { useFormatter, useTranslations, useLocale } from "next-intl";
import { PageHeader } from "@/components/common/PageHeader";
import { SkeletonTable } from "@/components/common/LoadingState";
import { loadAuthState, authFetch } from "@/lib/auth";
import { useKeyboardShortcuts } from "@/hooks/useKeyboardShortcuts";
import {
  Search,
  RefreshCw,
  BookOpen,
  Eye,
  Edit2,
  Trash2,
  ChevronLeft,
  ChevronRight,
  Plus,
  AlertCircle,
} from "lucide-react";

interface PlaybookDefinition {
  id: string;
  name: string;
  description: string | null;
  version: number;
  status: "draft" | "published" | "archived";
  created_at: string;
  updated_at: string;
  created_by: string;
}

interface PaginationState {
  currentPage: number;
  pageSize: number;
  total: number;
}

export default function PlaybookDefinitionsPage() {
  const router = useRouter();
  const locale = useLocale();
  const t = useTranslations("playbooks");
  const format = useFormatter();
  const tCommon = useTranslations("common");

  const [mounted, setMounted] = useState(false);
  const [definitions, setDefinitions] = useState<PlaybookDefinition[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [refreshing, setRefreshing] = useState(false);

  const [pagination, setPagination] = useState<PaginationState>({
    currentPage: 1,
    pageSize: 10,
    total: 0,
  });

  const loadDefinitions = async (page: number = 1) => {
    setLoading(true);
    setError(null);
    try {
      const response = await authFetch(
        `/api/playbook-definitions?page=${page}&page_size=${pagination.pageSize}`
      );

      if (response.ok) {
        const data = await response.json();
        const rawItems = (data.definitions || data.items || []) as Record<string, unknown>[];
        const normalized: PlaybookDefinition[] = rawItems.map((d) => ({
          id: String(d.id),
          name: String(d.name || ""),
          description: (d.description as string) || null,
          version: typeof d.version === "number" ? d.version : 1,
          status:
            (d.status as "draft" | "published" | "archived") ||
            (d.is_active ? "published" : "draft"),
          created_at: String(d.created_at || ""),
          updated_at: String(d.updated_at || ""),
          created_by: String(d.created_by || d.created_by_user_id || ""),
        }));
        setDefinitions(normalized);
        setPagination({
          currentPage: page,
          pageSize: pagination.pageSize,
          total: (data.total as number) || normalized.length,
        });
      } else if (response.status === 401) {
        router.push("/login");
        return;
      } else {
        setError(`Failed to load definitions: ${response.statusText}`);
      }
    } catch (e) {
      console.error("Failed to load definitions:", e);
      setError((e as Error)?.message ?? "Error loading definitions");
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadDefinitions(pagination.currentPage);
    setRefreshing(false);
  };

  const handlePageChange = (newPage: number) => {
    loadDefinitions(newPage);
  };

  useEffect(() => {
    setMounted(true);
    const authState = loadAuthState();
    if (!authState?.isAuthenticated) {
      router.push("/login");
      return;
    }
    loadDefinitions(1);
  }, [router]);

  // Keyboard shortcuts
  useKeyboardShortcuts(
    {
      r: () => {
        setRefreshing(true);
        loadDefinitions(pagination.currentPage).finally(() => setRefreshing(false));
      },
      "/": () => {
        document.querySelector<HTMLInputElement>('input[type="text"]')?.focus();
      },
    },
    { enabled: mounted && !loading }
  );

  if (!mounted) return null;

  const totalPages = Math.ceil(pagination.total / pagination.pageSize);

  const filteredDefinitions = definitions.filter((def) => {
    if (!searchQuery) return true;
    const search = searchQuery.toLowerCase();
    return (
      def.name.toLowerCase().includes(search) ||
      (def.description?.toLowerCase().includes(search) ?? false)
    );
  });

  return (
    <div className="min-h-screen bg-surface-page transition-colors">
      <PageHeader
        title={t("definitions.title")}
        subtitle={t("definitions.subtitle")}
        actions={
          <button
            className="inline-flex items-center gap-2 px-3.5 py-2 bg-accent-600 hover:bg-accent-700 text-white rounded-lg text-sm font-medium transition-colors shadow-subtle"
            onClick={() => router.push("/playbooks/create")}
          >
            <Plus className="w-4 h-4" />
            <span>{t("definitions.createNew")}</span>
          </button>
        }
      />

      <main className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-5">
        {/* Toolbar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3.5">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
            <input
              type="text"
              placeholder={t("definitions.searchPlaceholder") || "Search definitions..."}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-sm border border-border-default rounded-lg bg-surface-input text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent-500/20 focus:border-accent-600 transition-colors h-9"
            />
          </div>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="h-9 px-3 bg-accent-600 hover:bg-accent-700 text-white rounded-lg disabled:opacity-50 flex items-center gap-1.5 transition-colors text-sm font-medium shadow-subtle self-start sm:self-auto"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} />
            {refreshing ? tCommon("loading") : tCommon("refresh")}
          </button>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-3.5 p-3.5 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-center gap-2 text-sm">
            <AlertCircle className="w-4 h-4 text-red-600 dark:text-red-400 shrink-0" />
            <span className="text-red-700 dark:text-red-300">{error}</span>
          </div>
        )}

        {/* Content */}
        {loading ? (
          <div className="bg-surface-card rounded-xl p-4 border border-border-subtle">
            <SkeletonTable rows={5} columns={5} />
          </div>
        ) : filteredDefinitions.length === 0 ? (
          <div className="text-center py-12 bg-surface-card rounded-xl border border-border-subtle">
            <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-surface-hover flex items-center justify-center">
              <BookOpen className="w-6 h-6 text-text-muted" />
            </div>
            <p className="text-text-primary font-medium text-base mb-1">
              {t("definitions.noDefinitions")}
            </p>
            <p className="text-text-muted text-xs mb-3">{t("definitions.createFirst")}</p>
            <button
              onClick={() => router.push("/playbooks/create")}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-accent-600 text-white rounded-lg hover:bg-accent-700 active:bg-accent-700 transition-colors text-sm font-medium shadow-subtle"
            >
              <Plus className="w-3.5 h-3.5" />
              {t("definitions.createNew")}
            </button>
          </div>
        ) : (
          <div className="bg-surface-card rounded-xl shadow-subtle border border-border-subtle overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-surface-hover/50 border-b border-border-subtle text-xs uppercase text-text-muted">
                  <tr>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold text-text-muted uppercase tracking-wider">
                      {t("definitions.name")}
                    </th>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold text-text-muted uppercase tracking-wider">
                      {t("definitions.version")}
                    </th>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold text-text-muted uppercase tracking-wider">
                      {t("definitions.status")}
                    </th>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold text-text-muted uppercase tracking-wider">
                      {t("definitions.updated")}
                    </th>
                    <th className="px-4 py-2.5 text-right text-xs font-semibold text-text-muted uppercase tracking-wider">
                      {t("definitions.actions")}
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-subtle">
                  {filteredDefinitions.map((def) => (
                    <tr key={def.id} className="hover:bg-surface-hover/50 transition-colors">
                      <td className="px-4 py-2.5">
                        <div className="flex items-center gap-2.5">
                          <BookOpen className="w-4 h-4 text-text-muted shrink-0" />
                          <div>
                            <button
                              type="button"
                              onClick={() => router.push(`/playbooks/definitions/${def.id}`)}
                              className="font-semibold text-accent-600 hover:text-accent-700 dark:text-accent-400 dark:hover:text-accent-300 hover:underline text-left block text-sm transition-colors"
                            >
                              {def.name}
                            </button>
                            {def.description && (
                              <div className="text-xs text-text-muted mt-0.5 max-w-sm truncate">
                                {def.description}
                              </div>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-2.5 text-sm text-text-secondary font-mono">
                        v{def.version}
                      </td>
                      <td className="px-4 py-2.5">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                            def.status === "published"
                              ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                              : "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
                          }`}
                        >
                          {def.status}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 text-sm text-text-secondary">
                        {format.dateTime(new Date(def.updated_at), { dateStyle: "medium" })}
                      </td>
                      <td className="px-4 py-2.5 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            className="p-1.5 text-text-muted hover:text-accent-600 hover:bg-surface-hover rounded-lg transition-colors"
                            title={tCommon("edit")}
                            onClick={() => router.push(`/playbooks/definitions/${def.id}/edit`)}
                          >
                            <Edit2 className="w-3.5 h-3.5" />
                          </button>
                          <button
                            className="p-1.5 text-text-muted hover:text-red-600 hover:bg-surface-hover rounded-lg transition-colors"
                            title={tCommon("delete")}
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between px-4 py-2.5 border-t border-border-subtle">
                  <div className="text-xs text-text-muted">
                    Showing {(pagination.currentPage - 1) * pagination.pageSize + 1} to{" "}
                    {Math.min(pagination.currentPage * pagination.pageSize, pagination.total)} of{" "}
                    {pagination.total} results
                  </div>
                  <div className="flex items-center gap-1.5">
                    <button
                      onClick={() => handlePageChange(pagination.currentPage - 1)}
                      disabled={pagination.currentPage === 1}
                      className="p-1.5 border border-border-default rounded-lg hover:bg-surface-hover active:bg-surface-active text-text-secondary disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </button>
                    <span className="text-xs text-text-secondary px-1">
                      Page {pagination.currentPage} of {totalPages}
                    </span>
                    <button
                      onClick={() => handlePageChange(pagination.currentPage + 1)}
                      disabled={pagination.currentPage === totalPages}
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
