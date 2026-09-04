"use client";

import { useState, useEffect } from "react";
import { useRouter } from "@/i18n/navigation";
import { useTranslations, useLocale } from "next-intl";
import { apiClient as api } from "@/lib/api";
import { loadAuthState } from "@/lib/auth";
import { PageHeader } from "@/components/common/PageHeader";
import { LoadingState } from "@/components/common/LoadingState";
import { Star, Download, Search, CheckCircle, TrendingUp, Award } from "lucide-react";

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
  const [downloading, setDownloading] = useState<string | null>(null);

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
      alert("Failed to load marketplace: " + message);
    } finally {
      setLoading(false);
    }
  };

  const downloadPlaybook = async (playbookId: string) => {
    setDownloading(playbookId);
    try {
      const response = await api.post<{
        success: boolean;
        playbook?: { name: string };
        playbook_name?: string;
      }>(`/api/marketplace/playbooks/${playbookId}/download`);
      if (response.success) {
        const name = response.playbook?.name || response.playbook_name || "Playbook";
        alert(t("downloadSuccess", { name, page: tNav("playbookDefinitions") }));
      }
    } catch {
      alert(t("downloadFailed"));
    } finally {
      setDownloading(null);
    }
  };

  const filteredPlaybooks = (Array.isArray(playbooks) ? playbooks : []).filter((pb) => {
    const name = pb.name || "";
    const description = pb.description || "";
    const matchesSearch =
      !searchQuery ||
      name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      description.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = !selectedCategory || pb.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  if (!mounted) return null;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <PageHeader title={t("title")} subtitle={t("subtitle")} />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Debug Info */}
        {!loading && playbooks.length > 0 && (
          <div className="mb-4 p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
            <p className="text-sm text-green-800 dark:text-green-200">
              ✅ {t("loaded", { count: playbooks.length })}
            </p>
          </div>
        )}

        {/* Search & Filter */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4 mb-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={t("searchPlaceholder")}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-amber-500 dark:bg-gray-700 dark:text-white"
              />
            </div>
            <div className="flex gap-2">
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-amber-500 dark:bg-gray-700 dark:text-white"
              >
                <option value="">{t("allCategories")}</option>
                {categories.map((cat) => (
                  <option key={cat.id} value={cat.id}>
                    {cat.name}
                  </option>
                ))}
              </select>
              <button
                onClick={loadData}
                className="px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 text-sm"
              >
                {t("refresh")}
              </button>
            </div>
          </div>
        </div>

        {/* Featured & Trending */}
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
              {featured.map((pb) => (
                <div
                  key={pb.id}
                  className="flex items-center gap-4 p-3 bg-amber-50 dark:bg-amber-900/20 rounded-lg"
                >
                  <div className="flex-1">
                    <h3 className="font-medium text-gray-900 dark:text-white">{pb.name}</h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      {pb.author_name || pb.author || "Community"}
                    </p>
                  </div>
                  <div className="flex items-center gap-1">
                    <Star className="w-4 h-4 text-yellow-500 fill-current" />
                    <span className="text-sm font-medium">{pb.rating_average}</span>
                  </div>
                </div>
              ))}
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
              {trending.map((pb) => (
                <div
                  key={pb.id}
                  className="flex items-center gap-4 p-3 bg-gray-50 dark:bg-gray-700 rounded-lg"
                >
                  <div className="flex-1">
                    <h3 className="font-medium text-gray-900 dark:text-white">{pb.name}</h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      {pb.download_count} downloads
                    </p>
                  </div>
                  <div className="flex items-center gap-1">
                    <Download className="w-4 h-4 text-gray-400" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* All Playbooks */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="p-4 border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              {t("allPlaybooks", { count: filteredPlaybooks.length })}
            </h2>
          </div>
          <div className="p-4">
            <LoadingState
              isLoading={loading}
              empty={!loading && filteredPlaybooks.length === 0}
              emptyMessage={t("noPlaybooks")}
              skeletonType="card"
            >
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {filteredPlaybooks.map((playbook) => (
                  <div
                    key={playbook.id}
                    className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:shadow-lg transition-shadow"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <h3 className="font-semibold text-gray-900 dark:text-white">
                        {playbook.name}
                      </h3>
                      {playbook.verified && <CheckCircle className="w-5 h-5 text-green-500" />}
                    </div>

                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-3 line-clamp-2">
                      {playbook.description}
                    </p>

                    <div className="flex items-center gap-2 mb-3">
                      <span
                        className={`px-2 py-1 rounded text-xs font-medium ${
                          playbook.difficulty === "beginner"
                            ? "bg-green-100 text-green-600"
                            : playbook.difficulty === "intermediate"
                              ? "bg-yellow-100 text-yellow-600"
                              : "bg-red-100 text-red-600"
                        }`}
                      >
                        {playbook.difficulty === "beginner"
                          ? t("difficulty.beginner")
                          : playbook.difficulty === "intermediate"
                            ? t("difficulty.intermediate")
                            : t("difficulty.advanced")}
                      </span>
                      <span className="px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded text-xs">
                        {playbook.category}
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-sm text-gray-500 mb-3">
                      <div className="flex items-center gap-1">
                        <Star className="w-4 h-4 text-yellow-500" />
                        <span>{playbook.rating_average}</span>
                        <span>({playbook.rating_count})</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Download className="w-4 h-4" />
                        <span>{playbook.download_count}</span>
                      </div>
                    </div>

                    <button
                      onClick={() => downloadPlaybook(playbook.id)}
                      disabled={downloading === playbook.id}
                      className="w-full py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 disabled:opacity-50 flex items-center justify-center gap-2"
                    >
                      {downloading === playbook.id ? (
                        <>{t("downloading")}</>
                      ) : (
                        <>
                          <Download className="w-4 h-4" />
                          {tCommon("download")}
                        </>
                      )}
                    </button>
                  </div>
                ))}
              </div>
            </LoadingState>
          </div>
        </div>
      </main>
    </div>
  );
}
