"use client";

import { useState, useEffect, useCallback, lazy, Suspense, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useTranslations, useLocale } from "next-intl";
import { Activity, AlertTriangle, Clock, Zap, ShieldCheck } from "lucide-react";

import { api, HistoryRecord } from "@/lib/api";
import { loadAuthState, logout, type User } from "@/lib/auth";
import { HistoryPanel } from "@/components/HistoryPanel";
import Navigation from "@/components/Navigation";
import {
  Card,
  StatCard,
  RippleButton,
  LoadingSpinner,
  TabTransition,
  SkeletonCard,
} from "@/components/common";

const AlertAnalyzerTab = lazy(() =>
  import("@/components/tabs/AlertAnalyzerTab").then((mod) => ({ default: mod.AlertAnalyzerTab }))
);
const ReportWriterTab = lazy(() =>
  import("@/components/tabs/ReportWriterTab").then((mod) => ({ default: mod.ReportWriterTab }))
);
const TimelineBuilderTab = lazy(() =>
  import("@/components/tabs/TimelineBuilderTab").then((mod) => ({
    default: mod.TimelineBuilderTab,
  }))
);
const AssetsTab = lazy(() =>
  import("@/components/tabs/AssetsTab").then((mod) => ({ default: mod.AssetsTab }))
);

type Tab = "alert" | "report" | "timeline" | "assets";

export default function HomePage() {
  const router = useRouter();
  const t = useTranslations("home");
  const tStats = useTranslations("stats");
  const locale = useLocale();
  const [activeTab, setActiveTab] = useState<Tab>("alert");
  const [apiStatus, setApiStatus] = useState<"checking" | "healthy" | "unhealthy">("checking");
  const [mounted, setMounted] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  useEffect(() => {
    setMounted(true);

    const authState = loadAuthState();
    if (!authState?.isAuthenticated) {
      router.push(`/${locale}/login`);
      return;
    }
    setUser(authState.user);

    api
      .healthCheck()
      .then(() => setApiStatus("healthy"))
      .catch(() => setApiStatus("unhealthy"));
  }, [router, locale]);

  const handleLogout = () => {
    logout();
    router.push(`/${locale}/login`);
  };

  const handleLoadFromHistory = (record: HistoryRecord) => {
    setHistoryOpen(false);
  };

  const handleHistoryToggle = useCallback(() => {
    setHistoryOpen((prev) => !prev);
  }, []);

  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true);
    // 模拟数据刷新
    await new Promise((resolve) => setTimeout(resolve, 1500));
    setIsRefreshing(false);
  }, []);

  const tabDefs: { key: Tab; label: string }[] = useMemo(
    () => [
      { key: "alert", label: t("tabs.alertAnalyzer") },
      { key: "timeline", label: t("tabs.timelineBuilder") },
      { key: "report", label: t("tabs.reportWriter") },
      { key: "assets", label: t("tabs.assets") },
    ],
    [t]
  );

  const tabContents = useMemo(
    () => [
      {
        key: "alert",
        content: (
          <Suspense fallback={<SkeletonCard />}>
            <AlertAnalyzerTab onHistoryToggle={handleHistoryToggle} />
          </Suspense>
        ),
      },
      {
        key: "report",
        content: (
          <Suspense fallback={<SkeletonCard />}>
            <ReportWriterTab onHistoryToggle={handleHistoryToggle} />
          </Suspense>
        ),
      },
      {
        key: "timeline",
        content: (
          <Suspense fallback={<SkeletonCard />}>
            <TimelineBuilderTab onHistoryToggle={handleHistoryToggle} />
          </Suspense>
        ),
      },
      {
        key: "assets",
        content: (
          <Suspense fallback={<SkeletonCard />}>
            <AssetsTab />
          </Suspense>
        ),
      },
    ],
    [handleHistoryToggle]
  );

  if (!mounted) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 via-soc-50/30 to-gray-50 dark:from-gray-900 dark:via-soc-950/20 dark:to-gray-900 bg-dots">
        <div className="flex items-center justify-center min-h-screen">
          <LoadingSpinner size="xl" color="soc" label={t("loading")} />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-soc-50/30 to-gray-50 dark:from-gray-900 dark:via-soc-950/20 dark:to-gray-900 bg-dots">
      <Navigation
        title={t("title")}
        subtitle={t("subtitle")}
        apiStatus={
          apiStatus === "unhealthy" ? "error" : (apiStatus as "checking" | "healthy" | undefined)
        }
      />

      <main className="flex relative">
        <div className="flex-1 min-h-[calc(100vh-16rem)] mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12 lg:py-16 max-w-[calc(100%-4rem)] xl:max-w-7xl">
          <div className="mb-10 sm:mb-12 animate-fade-in">
            <div className="flex items-start sm:items-center justify-between gap-4 mb-4">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-gradient-to-br from-soc-100 to-soc-50 dark:from-soc-900/40 dark:to-soc-800/30 rounded-xl shadow-sm">
                  <ShieldCheck className="w-6 h-6 text-soc-600 dark:text-soc-400" />
                </div>
                <span className="text-sm font-semibold text-soc-600 dark:text-soc-400 uppercase tracking-wide">
                  {t("securityOperations")}
                </span>
              </div>
              <RippleButton
                variant="secondary"
                size="sm"
                onClick={handleRefresh}
                isLoading={isRefreshing}
                className="hidden sm:flex shrink-0"
              >
                {t("refreshData")}
              </RippleButton>
            </div>
            <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-gray-900 dark:text-white mb-3 tracking-tight leading-tight">
              <span className="text-gradient">{t("title")}</span>
            </h1>
            <p className="text-base sm:text-lg text-gray-600 dark:text-gray-400 max-w-2xl leading-relaxed">
              {t("subtitle")}
            </p>
          </div>

          <div className="grid grid-cols-1 gap-6 mb-8 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              title={tStats("totalAlerts")}
              value="1,234"
              trend="+12%"
              trendDirection="up"
              icon={<Activity className="w-6 h-6" />}
              colorScheme="soc"
              subtitle={tStats("last24h")}
              delay={0}
            />
            <StatCard
              title={tStats("highSeverity")}
              value="42"
              trend="-8%"
              trendDirection="down"
              icon={<AlertTriangle className="w-6 h-6" />}
              colorScheme="danger"
              subtitle={tStats("needsAttention")}
              delay={1}
            />
            <StatCard
              title={tStats("inProgress")}
              value="18"
              trend="+3%"
              trendDirection="neutral"
              icon={<Clock className="w-6 h-6" />}
              colorScheme="warning"
              subtitle={tStats("investigating")}
              delay={2}
            />
            <StatCard
              title={tStats("resolved")}
              value="328"
              trend="+24%"
              trendDirection="up"
              icon={<Zap className="w-6 h-6" />}
              colorScheme="success"
              subtitle={tStats("thisWeek")}
              delay={3}
            />
          </div>

          <Card variant="glass" className="animate-fade-in-up">
            <div className="border-b border-gray-200 dark:border-gray-700/50 px-4 pt-4 mb-6 bg-gradient-to-r from-gray-50/30 to-transparent dark:from-gray-800/20">
              <nav className="flex gap-3 overflow-x-auto pb-2 scrollbar-hide">
                {tabDefs.map((tab, index) => (
                  <button
                    key={tab.key}
                    onClick={() => {
                      setActiveTab(tab.key);
                      setHistoryOpen(false);
                    }}
                    className={`px-4 py-2 text-sm font-semibold rounded-lg transition-all duration-300 whitespace-nowrap ${
                      activeTab === tab.key
                        ? "bg-gradient-to-r from-soc-500 to-soc-600 text-white shadow-lg shadow-soc-500/25"
                        : "text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700/50"
                    }`}
                    style={{ animationDelay: `${index * 50}ms` }}
                  >
                    {tab.label}
                  </button>
                ))}
              </nav>
            </div>

            <TabTransition activeKey={activeTab} children={tabContents} />
          </Card>
        </div>

        {historyOpen && (
          <HistoryPanel
            module={
              activeTab === "alert" ? "analyzer" : activeTab === "timeline" ? "timeline" : "report"
            }
            onSelect={handleLoadFromHistory}
            onClose={() => setHistoryOpen(false)}
          />
        )}
      </main>
    </div>
  );
}
