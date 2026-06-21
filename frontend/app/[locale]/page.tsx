"use client";

import { useState, useEffect, useCallback, lazy, Suspense, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useTranslations, useLocale } from "next-intl";
import { Activity, AlertTriangle, Clock, Zap, ShieldCheck } from "lucide-react";

import { api, HistoryRecord } from "@/lib/api";
import { loadAuthState, logout, type User } from "@/lib/auth";
import { HistoryPanel } from "@/components/HistoryPanel";
import Navigation from "@/components/Navigation";
import Breadcrumbs from "@/components/common/Breadcrumbs";
import { Heading, Text } from "@/components/ui/Typography";
import {
  Card,
  RippleButton,
  LoadingSpinner,
  TabTransition,
  SkeletonCard,
} from "@/components/common";
import { TabButton, TabList } from "@/components/ui/Tabs";
import { StatCard } from "@/components/dashboard/StatCard";

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
      <div className="min-h-screen bg-surface-page dark:bg-slate-900">
        <div className="flex items-center justify-center min-h-screen">
          <LoadingSpinner size="xl" color="soc" label={t("loading")} />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-surface-page dark:bg-slate-900">
      <Navigation
        title={t("title")}
        subtitle={t("subtitle")}
        apiStatus={
          apiStatus === "unhealthy" ? "error" : (apiStatus as "checking" | "healthy" | undefined)
        }
      />

      <main className="flex relative">
        <div className="flex-1 min-h-[calc(100vh-16rem)] mx-auto px-6 py-8 lg:px-12 lg:py-8 max-w-[calc(100%-4rem)] xl:max-w-7xl">
          <Breadcrumbs className="mb-6" />

          <div className="mb-8 animate-fade-in">
            <div className="flex items-start sm:items-center justify-between gap-4 mb-4">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-primary-100 dark:bg-primary-800 rounded-lg shadow-sm">
                  <ShieldCheck className="w-6 h-6 text-primary-600 dark:text-primary-400" />
                </div>
                <span className="text-sm font-semibold text-primary-600 dark:text-primary-400 uppercase tracking-wide">
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
            <Heading level={1} color="primary" className="mb-3">
              {t("title")}
            </Heading>
            <Text color="tertiary" className="max-w-2xl">
              {t("subtitle")}
            </Text>
          </div>

          <div className="grid grid-cols-1 gap-6 mb-8 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              title={tStats("totalAlerts")}
              value="1,234"
              trend="+12%"
              trendDirection="up"
              icon={<Activity className="w-6 h-6" />}
              subtitle={tStats("last24h")}
            />
            <StatCard
              title={tStats("highSeverity")}
              value="42"
              trend="-8%"
              trendDirection="down"
              icon={<AlertTriangle className="w-6 h-6" />}
              subtitle={tStats("needsAttention")}
            />
            <StatCard
              title={tStats("inProgress")}
              value="18"
              trend="+3%"
              trendDirection="neutral"
              icon={<Clock className="w-6 h-6" />}
              subtitle={tStats("investigating")}
            />
            <StatCard
              title={tStats("resolved")}
              value="328"
              trend="+24%"
              trendDirection="up"
              icon={<Zap className="w-6 h-6" />}
              subtitle={tStats("thisWeek")}
            />
          </div>

          <Card variant="default" className="animate-fade-in-up">
            <div className="px-4 pt-4 mb-6 bg-surface-hover dark:bg-slate-800/30">
              <TabList className="overflow-x-auto scrollbar-hide">
                {tabDefs.map((tab) => (
                  <TabButton
                    key={tab.key}
                    active={activeTab === tab.key}
                    onClick={() => {
                      setActiveTab(tab.key);
                      setHistoryOpen(false);
                    }}
                    label={tab.label}
                  />
                ))}
              </TabList>
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
