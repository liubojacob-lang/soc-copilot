'use client';

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from 'next-intl';
import { loadAuthState, isAdmin } from "@/lib/auth";
import Navigation from "@/components/Navigation";
import { WazuhAlertStream } from "@/components/alerts/RealTimeAlertStream";
import { Shield, AlertTriangle } from "lucide-react";

export default function AlertsPage() {
  const router = useRouter();
  const locale = useLocale();
  const t = useTranslations('alertsPage');
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);

    const authState = loadAuthState();
    if (!authState?.isAuthenticated) {
      router.push(`/${locale}/login`);
      return;
    }
    if (!isAdmin(authState.user)) {
      router.push(`/${locale}`);
      return;
    }
  }, [router, locale]);

  if (!mounted) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Navigation
        title={t('title')}
        subtitle={t('subtitle')}
      />

      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
              <Shield className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                {t('title')}
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {t('subtitle')}
              </p>
            </div>
          </div>
        </div>

        {/* Alert Stream Component */}
        <WazuhAlertStream
          maxAlerts={100}
          autoScroll={true}
          showFilters={true}
        />

        {/* Info Box */}
        <div className="mt-6 bg-blue-50 dark:bg-blue-900/20 border border border-blue-200 dark:border-blue-800 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-blue-900 dark:text-blue-100 mb-2 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" />
            {t('info')}
          </h3>
          <ul className="text-sm text-blue-800 dark:text-blue-200 space-y-1">
            <li>{t('realtimeFeature1')}</li>
            <li>{t('realtimeFeature2')}</li>
            <li>{t('realtimeFeature3')}</li>
            <li>{t('realtimeFeature4')}</li>
          </ul>
        </div>

        {/* Link to Grafana */}
        <div className="mt-4 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-2">
            {t('grafanaDashboard')}
          </h3>
          <a
            href="http://localhost:3001/d/soc-copilot-full/9a7be4f"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm"
          >
            {t('openDashboard')}
          </a>
        </div>
      </main>
    </div>
  );
}
