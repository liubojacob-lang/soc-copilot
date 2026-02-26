"use client";

/**
 * SOC Copilot Home Page
 * v0.8.2: Refactored - components extracted to separate files for better maintainability
 * i18n: Added internationalization support
 */

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useTranslations, useLocale } from 'next-intl';

import { api, HistoryRecord } from "@/lib/api";
import { loadAuthState, logout, type User } from "@/lib/auth";
import { HistoryPanel } from "@/components/HistoryPanel";
import Navigation from "@/components/Navigation";

// Import refactored tab components
import { AlertAnalyzerTab } from "@/components/tabs/AlertAnalyzerTab";
import { ReportWriterTab } from "@/components/tabs/ReportWriterTab";
import { TimelineBuilderTab } from "@/components/tabs/TimelineBuilderTab";
import { AssetsTab } from "@/components/tabs/AssetsTab";

type Tab = "alert" | "report" | "timeline" | "assets";

export default function HomePage() {
  const router = useRouter();
  const t = useTranslations('home');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const [activeTab, setActiveTab] = useState<Tab>("alert");
  const [apiStatus, setApiStatus] = useState<"checking" | "healthy" | "unhealthy">("checking");
  const [mounted, setMounted] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    setMounted(true);

    // Check authentication
    const authState = loadAuthState();
    if (!authState?.isAuthenticated) {
      router.push(`/${locale}/login`);
      return;
    }
    setUser(authState.user);

    // Health check
    api.healthCheck()
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

  // Use useCallback to prevent infinite re-renders
  const handleHistoryToggle = useCallback(() => {
    setHistoryOpen(prev => !prev);
  }, []);

  const tabDefs: { key: Tab; label: string }[] = [
    { key: "alert", label: t("tabs.alertAnalyzer") },
    { key: "timeline", label: t("tabs.timelineBuilder") },
    { key: "report", label: t("tabs.reportWriter") },
    { key: "assets", label: t("tabs.assets") },
  ];

  // Early return AFTER all hooks are called (React Hooks rule)
  if (!mounted) return null;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Navigation */}
      <Navigation
        title={t("title")}
        subtitle={t("subtitle")}
        apiStatus={apiStatus === "unhealthy" ? "error" : apiStatus as "checking" | "healthy" | undefined}
      />

      {/* Main Content */}
      <main className="flex relative">
        <div className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
            <div className="border-b border-slate-200">
              <nav className="flex">
                {tabDefs.map((tab) => (
                  <button
                    key={tab.key}
                    onClick={() => {
                      setActiveTab(tab.key);
                      setHistoryOpen(false);
                    }}
                    className={`px-6 py-4 text-sm font-medium transition-colors ${
                      activeTab === tab.key
                        ? "bg-soc-50 text-soc-700 border-b-2 border-soc-600"
                        : "text-slate-500 hover:text-slate-700 hover:bg-slate-50"
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </nav>
            </div>

            <div className="p-6">
              {activeTab === "alert" && <AlertAnalyzerTab onHistoryToggle={handleHistoryToggle} />}
              {activeTab === "report" && <ReportWriterTab onHistoryToggle={handleHistoryToggle} />}
              {activeTab === "timeline" && <TimelineBuilderTab onHistoryToggle={handleHistoryToggle} />}
              {activeTab === "assets" && <AssetsTab />}
            </div>
          </div>
        </div>

        {/* History Modal */}
        {historyOpen && (
          <HistoryPanel
            module={activeTab === "alert" ? "analyzer" : activeTab === "timeline" ? "timeline" : "report"}
            onSelect={handleLoadFromHistory}
            onClose={() => setHistoryOpen(false)}
          />
        )}
      </main>
    </div>
  );
}
