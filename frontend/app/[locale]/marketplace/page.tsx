"use client";

import { useState, useEffect, useMemo } from "react";
import { useRouter } from "@/i18n/navigation";
import { useTranslations, useLocale } from "next-intl";
import { apiClient as api } from "@/lib/api";
import { loadAuthState } from "@/lib/auth";
import { PageHeader } from "@/components/common/PageHeader";
import { LoadingState } from "@/components/common/LoadingState";
import { useToast } from "@/components/Toast";
import {
  Star,
  Download,
  Search,
  CheckCircle,
  TrendingUp,
  Award,
  Eye,
  Shield,
  Crosshair,
  ExternalLink,
  X,
  ChevronDown,
  ChevronUp,
  Globe,
} from "lucide-react";
import { PlaybookDetailsDrawer } from "./components/PlaybookDetailsDrawer";
import { ExternalPlaybookModal } from "./components/ExternalPlaybookModal";
import { parsePlaybookSource } from "@/lib/marketplaceUtils";

interface MarketplacePlaybook {
  id: string;
  name: string;
  description: string | null;
  category: string;
  difficulty: "beginner" | "intermediate" | "advanced" | string;
  rating_average: number;
  rating_count: number;
  download_count: number;
  verified: boolean;
  author?: string;
  author_name?: string;
  tags?: string[];
}

interface MarketplaceCategory {
  id: string;
  name: string;
  count?: number;
}

interface PlaybooksResponse {
  playbooks?: MarketplacePlaybook[];
  items?: MarketplacePlaybook[];
  total?: number;
  page?: number;
  page_size?: number;
}

interface FeaturedResponse {
  featured?: MarketplacePlaybook[];
  items?: MarketplacePlaybook[];
}

interface TrendingResponse {
  trending?: Array<MarketplacePlaybook & { download_count: number }>;
  items?: Array<MarketplacePlaybook & { download_count: number }>;
}

interface CategoriesResponse {
  categories?: MarketplaceCategory[];
}

export default function MarketplacePage() {
  const router = useRouter();
  const locale = useLocale();
  const t = useTranslations("marketplace");
  const tCommon = useTranslations("common");
  const tNav = useTranslations("nav");
  const { showToast } = useToast();
  const [mounted, setMounted] = useState(false);
  const [playbooks, setPlaybooks] = useState<MarketplacePlaybook[]>([]);
  const [featured, setFeatured] = useState<MarketplacePlaybook[]>([]);
  const [trending, setTrending] = useState<Array<MarketplacePlaybook & { download_count: number }>>(
    []
  );
  const [categories, setCategories] = useState<MarketplaceCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("");
  const [selectedDifficulty, setSelectedDifficulty] = useState("all");
  const [sortBy, setSortBy] = useState<"rating" | "downloads" | "newest">("rating");
  const [verifiedOnly, setVerifiedOnly] = useState(false);
  const [showRecommendations, setShowRecommendations] = useState(false);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [selectedPlaybookId, setSelectedPlaybookId] = useState<string | null>(null);
  const [showExternalModal, setShowExternalModal] = useState(false);
  const [adaptedPlaybook, setAdaptedPlaybook] = useState<any | null>(null);

  useEffect(() => {
    setMounted(true);
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [playbooksRes, featuredRes, trendingRes, categoriesRes] = await Promise.all([
        api.get<PlaybooksResponse | MarketplacePlaybook[]>("/api/marketplace/playbooks"),
        api.get<FeaturedResponse | MarketplacePlaybook[]>("/api/marketplace/featured"),
        api.get<TrendingResponse | Array<MarketplacePlaybook & { download_count: number }>>(
          "/api/marketplace/trending"
        ),
        api.get<CategoriesResponse | MarketplaceCategory[]>("/api/marketplace/categories"),
      ]);

      const playbooksList = Array.isArray(playbooksRes)
        ? playbooksRes
        : playbooksRes?.playbooks || playbooksRes?.items || [];
      setPlaybooks(playbooksList);

      const featuredList = Array.isArray(featuredRes)
        ? featuredRes
        : featuredRes?.featured || featuredRes?.items || [];
      setFeatured(featuredList);

      const trendingList = Array.isArray(trendingRes)
        ? trendingRes
        : trendingRes?.trending || trendingRes?.items || [];
      setTrending(trendingList);

      const categoriesList = Array.isArray(categoriesRes)
        ? categoriesRes
        : categoriesRes?.categories || [];
      setCategories(categoriesList);
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Unknown error";
      console.error("Failed to load marketplace:", message);
      showToast("Failed to load marketplace: " + message, "error");
    } finally {
      setLoading(false);
    }
  };

  const downloadPlaybook = async (playbookId: string) => {
    setDownloading(playbookId);
    try {
      // If importing an in-memory adapted external playbook
      if (playbookId.startsWith("adapted-") && adaptedPlaybook) {
        const response = await api.post<{
          success: boolean;
          playbook_name?: string;
          local_definition_id?: string;
        }>("/api/marketplace/external/import", {
          playbook_data: adaptedPlaybook,
          target: "local",
        });
        if (response.success) {
          showToast(
            t("externalPlaybookImported", {
              name: response.playbook_name || adaptedPlaybook.name,
            }),
            "success"
          );
          setSelectedPlaybookId(null);
          setAdaptedPlaybook(null);
        }
        return;
      }

      const response = await api.post<{
        success: boolean;
        playbook?: { name: string };
        playbook_name?: string;
      }>(`/api/marketplace/playbooks/${playbookId}/download`);
      if (response.success) {
        const name = response.playbook?.name || response.playbook_name || "Playbook";
        showToast(t("downloadSuccess", { name, page: tNav("playbookDefinitions") }), "success");
        setPlaybooks((prev) =>
          prev.map((p) =>
            p.id === playbookId ? { ...p, download_count: (p.download_count || 0) + 1 } : p
          )
        );
        setTrending((prev) =>
          prev.map((p) =>
            p.id === playbookId ? { ...p, download_count: (p.download_count || 0) + 1 } : p
          )
        );
      }
    } catch {
      showToast(t("downloadFailed"), "error");
    } finally {
      setDownloading(null);
    }
  };

  const handleAdaptSuccess = (adapted: any) => {
    setAdaptedPlaybook(adapted);
    setSelectedPlaybookId(adapted.id);
  };

  const isFiltered = Boolean(
    searchQuery.trim() ||
    selectedCategory ||
    (selectedDifficulty && selectedDifficulty !== "all") ||
    verifiedOnly
  );

  const clearAllFilters = () => {
    setSearchQuery("");
    setSelectedCategory("");
    setSelectedDifficulty("all");
    setVerifiedOnly(false);
    setSortBy("rating");
  };

  const filteredPlaybooks = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    let result = (Array.isArray(playbooks) ? playbooks : []).filter((pb) => {
      const name = pb.name || "";
      const description = pb.description || "";
      const tagsStr = (pb.tags || []).join(" ");
      const matchesSearch =
        !query ||
        name.toLowerCase().includes(query) ||
        description.toLowerCase().includes(query) ||
        tagsStr.toLowerCase().includes(query);
      const matchesCategory = !selectedCategory || pb.category === selectedCategory;
      const matchesDifficulty =
        !selectedDifficulty || selectedDifficulty === "all" || pb.difficulty === selectedDifficulty;
      const matchesVerified = !verifiedOnly || pb.verified === true;
      return matchesSearch && matchesCategory && matchesDifficulty && matchesVerified;
    });

    return result.sort((a, b) => {
      if (sortBy === "downloads") {
        return (b.download_count || 0) - (a.download_count || 0);
      }
      if (sortBy === "newest") {
        return (b.id || "").localeCompare(a.id || "");
      }
      return (b.rating_average || 0) - (a.rating_average || 0);
    });
  }, [playbooks, searchQuery, selectedCategory, selectedDifficulty, verifiedOnly, sortBy]);

  if (!mounted) return null;

  return (
    <div className="min-h-screen bg-surface-ground pb-12">
      <PageHeader title={t("title")} subtitle={t("subtitle")} />

      <main className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Search & Filter Bar */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4 mb-6 space-y-3">
          <div className="flex flex-col lg:flex-row gap-3">
            {/* Search Input */}
            <div className="flex-1 relative">
              <Search className="absolute left-3.5 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={t("searchPlaceholder")}
                className="w-full pl-10 pr-9 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-amber-500 dark:bg-gray-700 dark:text-white text-sm"
              />
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => setSearchQuery("")}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 p-0.5 rounded-full"
                  aria-label="Clear search"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>

            {/* Selectors Group */}
            <div className="flex flex-wrap sm:flex-nowrap items-center gap-2">
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-amber-500 dark:bg-gray-700 dark:text-white text-xs sm:text-sm font-medium"
              >
                <option value="">{t("allCategories")}</option>
                {categories.map((cat) => (
                  <option key={cat.id} value={cat.id}>
                    {cat.name}
                  </option>
                ))}
              </select>

              <select
                value={selectedDifficulty}
                onChange={(e) => setSelectedDifficulty(e.target.value)}
                className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-amber-500 dark:bg-gray-700 dark:text-white text-xs sm:text-sm font-medium"
              >
                <option value="all">{t("allDifficulties")}</option>
                <option value="beginner">{t("difficulty.beginner")}</option>
                <option value="intermediate">{t("difficulty.intermediate")}</option>
                <option value="advanced">{t("difficulty.advanced")}</option>
              </select>

              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as "rating" | "downloads" | "newest")}
                className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-amber-500 dark:bg-gray-700 dark:text-white text-xs sm:text-sm font-medium"
              >
                <option value="rating">{t("sortRating")}</option>
                <option value="downloads">{t("sortDownloads")}</option>
                <option value="newest">{t("sortNewest")}</option>
              </select>

              <button
                type="button"
                onClick={() => setVerifiedOnly(!verifiedOnly)}
                className={`px-3 py-2 rounded-lg text-xs sm:text-sm font-medium flex items-center gap-1.5 transition-colors border ${
                  verifiedOnly
                    ? "bg-emerald-50 text-emerald-700 border-emerald-300 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800"
                    : "bg-gray-50 text-gray-700 border-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:border-gray-600 hover:bg-gray-100"
                }`}
              >
                <CheckCircle
                  className={`w-3.5 h-3.5 ${verifiedOnly ? "text-emerald-600" : "text-gray-400"}`}
                />
                <span>{t("verifiedOnly")}</span>
              </button>

              <button
                type="button"
                onClick={() => setShowExternalModal(true)}
                className="px-3 py-2 rounded-lg text-xs sm:text-sm font-medium flex items-center gap-1.5 transition-colors border bg-amber-50 text-amber-800 border-amber-300 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800 hover:bg-amber-100 dark:hover:bg-amber-900/60 shadow-xs"
              >
                <Globe className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
                <span>{t("externalImport")}</span>
              </button>

              <button
                type="button"
                onClick={loadData}
                className="px-3.5 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 text-xs sm:text-sm font-medium transition-colors"
              >
                {t("refresh")}
              </button>
            </div>
          </div>

          {/* Active Search & Filter Feedback Bar */}
          {isFiltered && (
            <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-gray-100 dark:border-gray-700/60 text-xs">
              <div className="flex items-center gap-2 flex-wrap text-gray-600 dark:text-gray-300">
                <span className="font-semibold text-amber-600 dark:text-amber-400">
                  {t("searchResultsCount", { count: filteredPlaybooks.length })}
                </span>
                {searchQuery && (
                  <span className="px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 font-mono">
                    "{searchQuery}"
                  </span>
                )}
                {selectedCategory && (
                  <span className="px-2 py-0.5 rounded bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300 border border-amber-200/60 dark:border-amber-800/40">
                    {categories.find((c) => c.id === selectedCategory)?.name || selectedCategory}
                  </span>
                )}
                {selectedDifficulty !== "all" && (
                  <span className="px-2 py-0.5 rounded bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300 border border-blue-200/60 dark:border-blue-800/40">
                    {t(`difficulty.${selectedDifficulty}` as any)}
                  </span>
                )}
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setShowRecommendations(!showRecommendations)}
                  className="px-2.5 py-1 text-gray-500 hover:text-gray-800 dark:hover:text-gray-200 rounded border border-gray-200 dark:border-gray-700 flex items-center gap-1 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                >
                  {showRecommendations ? (
                    <ChevronUp className="w-3.5 h-3.5" />
                  ) : (
                    <ChevronDown className="w-3.5 h-3.5" />
                  )}
                  <span>
                    {showRecommendations ? t("hideRecommendations") : t("showRecommendations")}
                  </span>
                </button>
                <button
                  type="button"
                  onClick={clearAllFilters}
                  className="px-2.5 py-1 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/40 rounded transition-colors font-medium"
                >
                  {t("clearFilters")}
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Featured & Trending (Collapsible when filtering) */}
        {(!isFiltered || showRecommendations) && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            {/* Featured */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
              <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                  <Award className="w-5 h-5 text-amber-500" />
                  {t("featured")}
                </h2>
              </div>
              <div className="p-4 space-y-3">
                {featured.length === 0 ? (
                  <p className="text-sm text-gray-500 dark:text-gray-400 py-2">
                    {t("noPlaybooks")}
                  </p>
                ) : (
                  featured.map((pb) => {
                    const meta = parsePlaybookSource(pb);
                    return (
                      <div
                        key={pb.id}
                        onClick={() => setSelectedPlaybookId(pb.id)}
                        className="cursor-pointer flex items-center justify-between gap-4 p-3.5 bg-amber-50/70 dark:bg-amber-950/20 rounded-xl hover:bg-amber-100/70 dark:hover:bg-amber-900/30 border border-amber-200/50 dark:border-amber-800/30 transition-all group"
                      >
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span
                              className={`inline-flex items-center px-1.5 py-0.2 rounded text-[11px] font-semibold border ${meta.badgeClass} ${meta.badgeBorderClass}`}
                            >
                              {meta.standardName}
                            </span>
                            <h3 className="font-semibold text-sm text-gray-900 dark:text-white truncate group-hover:text-amber-600 dark:group-hover:text-amber-400 transition-colors">
                              {pb.name}
                            </h3>
                          </div>
                          <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
                            <span className="truncate">
                              {pb.author_name || pb.author || "Community"}
                            </span>
                            <div className="flex items-center gap-1 text-amber-500 shrink-0">
                              <Star className="w-3.5 h-3.5 fill-current" />
                              <span className="font-medium">{pb.rating_average}</span>
                            </div>
                            <span className="text-gray-400 shrink-0">
                              {pb.download_count} {locale.startsWith("zh") ? "次下载" : "dl"}
                            </span>
                          </div>
                        </div>

                        <div className="flex items-center gap-2 shrink-0">
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedPlaybookId(pb.id);
                            }}
                            className="px-2.5 py-1.5 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700 rounded-lg text-xs font-medium hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center gap-1 transition-colors"
                          >
                            <Eye className="w-3.5 h-3.5" />
                            <span>{t("viewDetails")}</span>
                          </button>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              downloadPlaybook(pb.id);
                            }}
                            disabled={downloading === pb.id}
                            title={tCommon("download")}
                            aria-label={`${tCommon("download")} ${pb.name}`}
                            className="px-3 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-medium disabled:opacity-50 flex items-center gap-1.5 transition-colors shrink-0 shadow-sm"
                          >
                            {downloading === pb.id ? (
                              <>
                                <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                <span>{t("downloading")}</span>
                              </>
                            ) : (
                              <>
                                <Download className="w-3.5 h-3.5" />
                                <span>{tCommon("download")}</span>
                              </>
                            )}
                          </button>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            {/* Trending */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
              <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-green-500" />
                  {t("trending")}
                </h2>
              </div>
              <div className="p-4 space-y-3">
                {trending.length === 0 ? (
                  <p className="text-sm text-gray-500 dark:text-gray-400 py-2">
                    {t("noPlaybooks")}
                  </p>
                ) : (
                  trending.map((pb) => {
                    const meta = parsePlaybookSource(pb);
                    return (
                      <div
                        key={pb.id}
                        onClick={() => setSelectedPlaybookId(pb.id)}
                        className="cursor-pointer flex items-center justify-between gap-4 p-3.5 bg-gray-50/80 dark:bg-gray-800/50 rounded-xl hover:bg-gray-100/90 dark:hover:bg-gray-700/60 border border-gray-200/60 dark:border-gray-700/60 transition-all group"
                      >
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span
                              className={`inline-flex items-center px-1.5 py-0.2 rounded text-[11px] font-semibold border ${meta.badgeClass} ${meta.badgeBorderClass}`}
                            >
                              {meta.standardName}
                            </span>
                            <h3 className="font-semibold text-sm text-gray-900 dark:text-white truncate group-hover:text-amber-600 dark:group-hover:text-amber-400 transition-colors">
                              {pb.name}
                            </h3>
                          </div>
                          <p className="text-xs text-gray-500 dark:text-gray-400">
                            {t("downloads", { count: pb.download_count })}
                          </p>
                        </div>

                        <div className="flex items-center gap-2 shrink-0">
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedPlaybookId(pb.id);
                            }}
                            className="px-2.5 py-1.5 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700 rounded-lg text-xs font-medium hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center gap-1 transition-colors"
                          >
                            <Eye className="w-3.5 h-3.5" />
                            <span>{t("viewDetails")}</span>
                          </button>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              downloadPlaybook(pb.id);
                            }}
                            disabled={downloading === pb.id}
                            title={tCommon("download")}
                            aria-label={`${tCommon("download")} ${pb.name}`}
                            className="px-3 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-medium disabled:opacity-50 flex items-center gap-1.5 transition-colors shrink-0 shadow-sm"
                          >
                            {downloading === pb.id ? (
                              <>
                                <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                <span>{t("downloading")}</span>
                              </>
                            ) : (
                              <>
                                <Download className="w-3.5 h-3.5" />
                                <span>{tCommon("download")}</span>
                              </>
                            )}
                          </button>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          </div>
        )}

        {/* All Playbooks Grid */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              {isFiltered
                ? t("searchResultsCount", { count: filteredPlaybooks.length })
                : t("allPlaybooks", { count: filteredPlaybooks.length })}
            </h2>
          </div>
          <div className="p-5">
            <LoadingState
              isLoading={loading}
              empty={!loading && filteredPlaybooks.length === 0}
              emptyMessage={t("noPlaybooks")}
              skeletonType="card"
            >
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                {filteredPlaybooks.map((playbook) => {
                  const meta = parsePlaybookSource(playbook);
                  return (
                    <div
                      key={playbook.id}
                      onClick={() => setSelectedPlaybookId(playbook.id)}
                      className="cursor-pointer border border-gray-200 dark:border-gray-700 hover:border-amber-400 dark:hover:border-amber-500/60 rounded-xl p-5 hover:shadow-lg transition-all bg-white dark:bg-gray-800 flex flex-col justify-between group"
                    >
                      <div>
                        {/* Top Bar: Standard Badge + Verified */}
                        <div className="flex items-center justify-between gap-2 mb-3">
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold border ${meta.badgeClass} ${meta.badgeBorderClass}`}
                          >
                            <Shield className="w-3 h-3 mr-1" />
                            {meta.standardName}
                          </span>
                          {playbook.verified && (
                            <span
                              className="inline-flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-400 font-medium"
                              title={locale.startsWith("zh") ? "官方验证" : "Verified"}
                            >
                              <CheckCircle className="w-4 h-4" />
                            </span>
                          )}
                        </div>

                        {/* Title */}
                        <h3 className="font-bold text-base text-gray-900 dark:text-white mb-2 group-hover:text-amber-600 dark:group-hover:text-amber-400 transition-colors">
                          {playbook.name}
                        </h3>

                        {/* Description */}
                        <p className="text-xs text-gray-600 dark:text-gray-400 mb-4 line-clamp-2 leading-relaxed">
                          {playbook.description}
                        </p>

                        {/* Category, Difficulty & ATT&CK Tags */}
                        <div className="flex flex-wrap items-center gap-1.5 mb-4">
                          <span
                            className={`px-2 py-0.5 rounded text-xs font-medium ${
                              playbook.difficulty === "beginner"
                                ? "bg-green-100 text-green-700 dark:bg-green-950/40 dark:text-green-300"
                                : playbook.difficulty === "intermediate"
                                  ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-950/40 dark:text-yellow-300"
                                  : "bg-red-100 text-red-700 dark:bg-red-950/40 dark:text-red-300"
                            }`}
                          >
                            {playbook.difficulty === "beginner"
                              ? t("difficulty.beginner")
                              : playbook.difficulty === "intermediate"
                                ? t("difficulty.intermediate")
                                : t("difficulty.advanced")}
                          </span>

                          <span className="px-2 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded text-xs">
                            {playbook.category}
                          </span>

                          {meta.mitreTechniques.slice(0, 2).map((tech) => (
                            <span
                              key={tech}
                              className="px-1.5 py-0.5 rounded bg-amber-50 dark:bg-amber-950/30 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800/40 text-[11px] font-mono flex items-center gap-1"
                            >
                              <Crosshair className="w-2.5 h-2.5" />
                              {tech}
                            </span>
                          ))}
                        </div>
                      </div>

                      <div>
                        {/* Rating & Downloads */}
                        <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 mb-4 pt-3 border-t border-gray-100 dark:border-gray-700/60">
                          <div className="flex items-center gap-1">
                            <Star className="w-3.5 h-3.5 text-amber-500 fill-current" />
                            <span className="font-semibold text-gray-700 dark:text-gray-300">
                              {playbook.rating_average}
                            </span>
                            <span>({playbook.rating_count})</span>
                          </div>
                          <div className="flex items-center gap-1">
                            <Download className="w-3.5 h-3.5" />
                            <span>
                              {playbook.download_count} {locale.startsWith("zh") ? "次下载" : "dl"}
                            </span>
                          </div>
                        </div>

                        {/* Action Buttons: View Details + Download */}
                        <div className="grid grid-cols-2 gap-2">
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedPlaybookId(playbook.id);
                            }}
                            className="w-full py-2 bg-gray-100 dark:bg-gray-700/80 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors"
                          >
                            <Eye className="w-3.5 h-3.5" />
                            <span>{t("viewDetails")}</span>
                          </button>

                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              downloadPlaybook(playbook.id);
                            }}
                            disabled={downloading === playbook.id}
                            className="w-full py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-semibold disabled:opacity-50 flex items-center justify-center gap-1.5 transition-colors shadow-xs"
                          >
                            {downloading === playbook.id ? (
                              <>
                                <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                <span>{t("downloading")}</span>
                              </>
                            ) : (
                              <>
                                <Download className="w-3.5 h-3.5" />
                                <span>{tCommon("download")}</span>
                              </>
                            )}
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </LoadingState>
          </div>
        </div>
      </main>

      {/* Slide-in Details Drawer */}
      <PlaybookDetailsDrawer
        playbookId={selectedPlaybookId}
        playbook={
          selectedPlaybookId?.startsWith("adapted-")
            ? adaptedPlaybook
            : playbooks.find((p) => p.id === selectedPlaybookId) || null
        }
        isOpen={!!selectedPlaybookId}
        onClose={() => {
          setSelectedPlaybookId(null);
          if (selectedPlaybookId?.startsWith("adapted-")) {
            setAdaptedPlaybook(null);
          }
        }}
        onDownload={downloadPlaybook}
        isDownloading={downloading === selectedPlaybookId}
      />

      {/* External Playbook Search & AI Adapter Modal */}
      <ExternalPlaybookModal
        isOpen={showExternalModal}
        onClose={() => setShowExternalModal(false)}
        onAdaptSuccess={handleAdaptSuccess}
      />
    </div>
  );
}
