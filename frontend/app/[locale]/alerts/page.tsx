'use client';

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useLocale } from 'next-intl';
import { loadAuthState, isAdmin } from "@/lib/auth";
import Navigation from "@/components/Navigation";
import { RealTimeAlertStream } from "@/components/alerts/RealTimeAlertStream";
import { Shield, AlertTriangle } from "lucide-react";

export default function AlertsPage() {
  const router = useRouter();
  const locale = useLocale();
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
        title="安全告警中心"
        subtitle="Real-time Alert Stream - Loki"
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
                安全告警中心
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                实时告警流 - 由 Grafana + Loki 提供支持
              </p>
            </div>
          </div>
        </div>

        {/* Alert Stream Component */}
        <RealTimeAlertStream
          maxAlerts={100}
          autoScroll={true}
          showFilters={true}
        />

        {/* Info Box */}
        <div className="mt-6 bg-blue-50 dark:bg-blue-900/20 border border border-blue-200 dark:border-blue-800 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-blue-900 dark:text-blue-100 mb-2 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" />
            ℹ️ 实时告警流
          </h3>
          <ul className="text-sm text-blue-800 dark:text-blue-200 space-y-1">
            <li>✅ 自动连接到 Loki 数据源</li>
            <li>✅ 实时接收新告警（无需手动刷新）</li>
            <li>✅ 自动统计更新</li>
            <li>✅ 连接状态指示器</li>
            <li>✅ 断线自动重连</li>
            <li>✅ 支持过滤和导出</li>
          </ul>
        </div>

        {/* Link to Grafana */}
        <div className="mt-4 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-2">
            📊 Grafana 仪表板
          </h3>
          <a
            href="http://localhost:3001/d/soc-copilot-full/9a7be4f"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm"
          >
            打开 Grafana Dashboard →
          </a>
        </div>
      </main>
    </div>
  );
}
