'use client';

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useLocale } from 'next-intl';
import { loadAuthState, isAdmin } from "@/lib/auth";
import Navigation from "@/components/Navigation";
import { WazuhAlertStream } from "@/components/wazuh/WazuhAlertStream";
import { AlertTriangle } from "lucide-react";

export default function WazuhPage() {
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
        title="Wazuh"
        subtitle="Real-time Alert Stream - WebSocket"
      />

      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-orange-100 dark:bg-orange-900/30 rounded-lg">
              <AlertTriangle className="w-6 h-6 text-orange-600 dark:text-orange-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                Wazuh Real-time Alert Stream
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Week 2 - WebSocket Real-time Push
              </p>
            </div>
          </div>
        </div>

        {/* Alert Stream Component with WebSocket */}
        <WazuhAlertStream
          maxAlerts={100}
          autoScroll={true}
          showFilters={true}
        />

        {/* Info Box */}
        <div className="mt-6 bg-blue-50 dark:bg-blue-900/20 border border border-blue-200 dark:border-blue-800 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-blue-900 dark:text-blue-100 mb-2">
            ℹ️ WebSocket 实时告警流
          </h3>
          <ul className="text-sm text-blue-800 dark:text-blue-200 space-y-1">
            <li>✅ 自动连接到 WebSocket 服务器</li>
            <li>✅ 实时接收新告警（无需手动刷新）</li>
            <li>✅ 自动统计更新</li>
            <li>✅ 连接状态指示器（绿色=已连接，红色=断开）</li>
            <li>✅ 断线自动重连</li>
          </ul>
        </div>
      </main>
    </div>
  );
}
