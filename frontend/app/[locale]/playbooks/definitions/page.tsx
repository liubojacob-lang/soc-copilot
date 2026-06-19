"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useTranslations, useLocale } from "next-intl";
import Navigation from "@/components/Navigation";
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
        setDefinitions(data.definitions || []);
        setPagination({
          currentPage: page,
          pageSize: pagination.pageSize,
          total: data.total || 0,
        });
      } else if (response.status === 401) {
        router.push(`/${locale}/login`);
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
      router.push(`/${locale}/login`);
      return;
    }
    loadDefinitions(1);
  }, [router, locale]);

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
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Navigation title={t("definitions.title")} subtitle={t("definitions.subtitle")} />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 mb-6 shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                {t("definitions.title")}
              </h2>
              <p className="text-gray-500 dark:text-gray-400 mt-1">{t("definitions.subtitle")}</p>
            </div>
            <button
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors shadow-sm"
              onClick={() => router.push(`/${locale}/playbooks/create`)}
            >
              <Plus className="w-4 h-4" />
              {t("definitions.createNew")}
            </button>
          </div>

          {/* Filters */}
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder={t("definitions.searchPlaceholder") || "Search definitions..."}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2 transition-colors shadow-sm"
            >
              <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} />
              {refreshing ? tCommon("loading") : tCommon("refresh")}
            </button>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
            <span className="text-red-700 dark:text-red-300">{error}</span>
          </div>
        )}

        {/* Content */}
        {loading ? (
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4">
            <SkeletonTable rows={5} columns={5} />
          </div>
        ) : filteredDefinitions.length === 0 ? (
          <div className="text-center py-16 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center">
              <BookOpen className="w-8 h-8 text-gray-400" />
            </div>
            <p className="text-gray-500 dark:text-gray-400 text-lg mb-2">
              {t("definitions.noDefinitions")}
            </p>
            <p className="text-gray-400 dark:text-gray-500 text-sm mb-4">
              {t("definitions.createFirst")}
            </p>
            <button
              onClick={() => router.push(`/${locale}/playbooks/create`)}
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <Plus className="w-4 h-4" />
              {t("definitions.createNew")}
            </button>
          </div>
        ) : (
          <div className="bg-white dark:bg-gray-800 rounded-lg overflow-hidden shadow-sm border border-gray-200 dark:border-gray-700">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 dark:bg-gray-700 border-b border-gray-200 dark:border-gray-600">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      {t("definitions.name") || "Name"}
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      {t("definitions.description") || "Description"}
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      {t("definitions.version") || "Version"}
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      {t("definitions.status") || "Status"}
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      {t("definitions.updated") || "Updated"}
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      {t("definitions.actions") || "Actions"}
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                  {filteredDefinitions.map((def) => (
                    <tr
                      key={def.id}
                      className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                    >
                      <td className="px-6 py-4">
                        <div className="font-medium text-gray-900 dark:text-white">{def.name}</div>
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
                              : def.status === "draft"
                                ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
                                : "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-400"
                          }`}
                        >
                          {def.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-300">
                        {new Date(def.updated_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            className="p-2 text-gray-500 hover:text-blue-600 dark:text-gray-400 dark:hover:text-blue-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                            title={tCommon("viewDetails")}
                            onClick={() =>
                              router.push(`/${locale}/playbooks/definitions/${def.id}`)
                            }
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                          <button
                            className="p-2 text-gray-500 hover:text-blue-600 dark:text-gray-400 dark:hover:text-blue-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                            title={tCommon("edit")}
                            onClick={() =>
                              router.push(`/${locale}/playbooks/definitions/${def.id}/edit`)
                            }
                          >
                            <Edit2 className="w-4 h-4" />
                          </button>
                          <button
                            className="p-2 text-gray-500 hover:text-red-600 dark:text-gray-400 dark:hover:text-red-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                            title={tCommon("delete")}
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 dark:border-gray-700">
                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    Showing {(pagination.currentPage - 1) * pagination.pageSize + 1} to{" "}
                    {Math.min(pagination.currentPage * pagination.pageSize, pagination.total)} of{" "}
                    {pagination.total} results
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handlePageChange(pagination.currentPage - 1)}
                      disabled={pagination.currentPage === 1}
                      className="p-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </button>
                    <span className="text-sm text-gray-600 dark:text-gray-400">
                      Page {pagination.currentPage} of {totalPages}
                    </span>
                    <button
                      onClick={() => handlePageChange(pagination.currentPage + 1)}
                      disabled={pagination.currentPage === totalPages}
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
      </main>
    </div>
  );
}
