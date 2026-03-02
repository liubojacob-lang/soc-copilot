"use client";

import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { loadAuthState, isAdmin, authFetchJSON } from "@/lib/auth";
import Navigation from "@/components/Navigation";
import { CheckCircle, XCircle, RefreshCw, Database, HardDrive, Cpu, Settings } from "lucide-react";

interface HealthState {
  dashboard: any | null;
  database: any | null;
  redis: any | null;
  resources: any | null;
  features: Record<string, boolean> | null;
}

export default function AdminHealthPage() {
  const router = useRouter();
  const locale = useLocale();
  const t = useTranslations("admin");

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<HealthState>({
    dashboard: null,
    database: null,
    redis: null,
    resources: null,
    features: null,
  });

  const loadHealth = async () => {
    setError(null);
    try {
      const [dashboard, database, redis, resources, features] = await Promise.all([
        authFetchJSON("/api/system/dashboard").catch(() => null),
        authFetchJSON("/api/system/database").catch(() => null),
        authFetchJSON("/api/system/redis").catch(() => null),
        authFetchJSON("/api/system/resources").catch(() => null),
        authFetchJSON("/api/system/features").catch(() => null),
      ]);

      setData({
        dashboard,
        database,
        redis,
        resources,
        features,
      });
    } catch (err: any) {
      setError(err?.message || "Failed to load health data");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    const authState = loadAuthState();
    if (!authState?.isAuthenticated) {
      router.push(`/${locale}/login`);
      return;
    }
    if (!isAdmin(authState.user)) {
      router.push(`/${locale}`);
      return;
    }
    loadHealth();
  }, [router, locale]);

  const refresh = async () => {
    setRefreshing(true);
    await loadHealth();
  };

  const dashboard = data.dashboard;
  const database = data.database || dashboard?.database;
  const redis = data.redis || dashboard?.redis;
  const resources = data.resources || dashboard?.system;
  const features = data.features || dashboard?.features || {};

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Navigation title={t("systemHealth", { default: "System Health" })} subtitle={t("subtitle", { default: "Runtime status and infrastructure health" })} />

      <main className="max-w-7xl mx-auto px-4 py-8">
        <div className="flex justify-end mb-6">
          <button
            onClick={refresh}
            disabled={refreshing}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            {error}
          </div>
        )}

        {loading ? (
          <div className="text-center py-12 text-gray-500">Loading...</div>
        ) : (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <StatusCard
                title="Database"
                icon={<Database className="w-5 h-5" />}
                status={database?.status || "unknown"}
                details={`Latency: ${Math.round(database?.latency_ms || 0)} ms`}
              />
              <StatusCard
                title="Redis"
                icon={<HardDrive className="w-5 h-5" />}
                status={redis?.status || "unknown"}
                details={`Latency: ${Math.round(redis?.latency_ms || 0)} ms`}
              />
              <StatusCard
                title="System"
                icon={<Cpu className="w-5 h-5" />}
                status={resources ? "ok" : "unknown"}
                details={`CPU: ${resources?.cpu_percent ?? 0}%`}
              />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
                <h3 className="font-semibold mb-3 text-gray-900 dark:text-white">{t('resources')}</h3>
                <div className="space-y-2 text-sm">
                  <Row label={t('cpu')} value={`${resources?.cpu_percent ?? 0}%`} />
                  <Row
                    label={t('memory')}
                    value={`${resources?.memory?.percent_used ?? 0}% (${resources?.memory?.used_gb ?? 0} / ${resources?.memory?.total_gb ?? 0} GB)`}
                  />
                  <Row
                    label={t('disk')}
                    value={`${resources?.disk?.percent_used ?? 0}% (${resources?.disk?.used_gb ?? 0} / ${resources?.disk?.total_gb ?? 0} GB)`}
                  />
                  <Row label={t('platform')} value={resources?.platform || "-"} />
                </div>
              </div>

              <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
                <h3 className="font-semibold mb-3 text-gray-900 dark:text-white flex items-center gap-2">
                  <Settings className="w-4 h-4" />
                  {t('features')}
                </h3>
                <div className="space-y-2 text-sm">
                  {Object.keys(features).length === 0 ? (
                    <div className="text-gray-500">{t('noFeatures')}</div>
                  ) : (
                    Object.entries(features).map(([key, enabled]) => (
                      <div key={key} className="flex items-center justify-between">
                        <span className="text-gray-600 dark:text-gray-300">{key}</span>
                        <span className={enabled ? "text-green-600" : "text-gray-500"}>
                          {enabled ? t('enabled') : t('disabled')}
                        </span>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

function StatusCard({
  title,
  icon,
  status,
  details,
}: {
  title: string;
  icon: ReactNode;
  status: string;
  details: string;
}) {
  const healthy = status === "ok";
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-sm text-gray-500 dark:text-gray-400">{title}</div>
          <div className="mt-1 text-xs text-gray-500 dark:text-gray-400">{details}</div>
        </div>
        <div className="flex items-center gap-2">
          {icon}
          {healthy ? (
            <CheckCircle className="w-5 h-5 text-green-500" />
          ) : (
            <XCircle className="w-5 h-5 text-red-500" />
          )}
        </div>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-gray-500 dark:text-gray-400">{label}</span>
      <span className="text-gray-900 dark:text-white font-medium">{value}</span>
    </div>
  );
}
