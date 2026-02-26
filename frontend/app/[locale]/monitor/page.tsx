'use client';

export const dynamic = 'force-dynamic';

import { useMonitor } from '@/hooks/useMonitor';
import { ResourceChart } from '@/components/monitor/ResourceChart';
import Navigation from '@/components/Navigation';
import { Maximize2, Minimize2, RefreshCw, Activity, Database, HardDrive, Cpu, ListTodo, Wifi } from 'lucide-react';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { loadAuthState } from '@/lib/auth';
import { useTranslations } from 'next-intl';

interface ServiceStatus {
  status: string;
  latency_ms: number | null;
  message: string | null;
  pending_count: number | null;
}

interface ResourceMetrics {
  cpu_percent: number;
  memory_percent: number;
  memory_used_gb: number;
  memory_total_gb: number;
  disk_percent: number;
  disk_used_gb: number;
  disk_total_gb: number;
  error: string | null;
}

interface MonitorData {
  timestamp: string;
  services: {
    database: ServiceStatus;
    redis: ServiceStatus;
    ai: ServiceStatus;
    queue: ServiceStatus;
  };
  resources: ResourceMetrics;
  activities: Array<{
    type: string;
    id: string;
    name: string;
    status: string;
    timestamp: string | null;
  }>;
  metrics: {
    requests_per_minute: number;
    error_rate: number;
    avg_response_time_ms: number;
  };
}

const serviceIcons = {
  database: Database,
  redis: HardDrive,
  ai: Cpu,
  queue: ListTodo,
};

const serviceKeys = ['database', 'redis', 'ai', 'queue'] as const;

export default function MonitorPage() {
  const router = useRouter();
  const t = useTranslations('monitor');
  const { data, history, connected, error, reconnect, connectionType, fetchHistory } = useMonitor();
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [mounted, setMounted] = useState(false);

  // Wait for client-side mount to avoid hydration mismatch
  useEffect(() => {
    // Mark as mounted on client-side only
    setMounted(true);
    // Set isFullscreen initial state on client only to avoid SSR mismatch
    try {
      setIsFullscreen(typeof document !== 'undefined' && !!document.fullscreenElement);
    } catch {
      setIsFullscreen(false);
    }
  }, []);

  // Check admin access (TEMPORARILY DISABLED for SSE testing)
  // useEffect(() => {
  //   const auth = loadAuthState();
  //   if (!auth?.user || auth.user.role !== 'admin') {
  //     router.push('/');
  //   }
  // }, [router]);

  // Sync fullscreen state with browser
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
    };
  }, []);

  const toggleFullscreen = () => {
    // Ensure document is available (client-side only)
    if (typeof window === 'undefined' || !document) return;

    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'ok':
        return 'bg-green-500';
      case 'error':
        return 'bg-red-500';
      case 'degraded':
        return 'bg-yellow-500';
      case 'disabled':
        return 'bg-gray-400';
      case 'initializing':
        return 'bg-blue-400 animate-pulse';
      default:
        return 'bg-gray-400';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'ok':
        return t('status.ok');
      case 'error':
        return t('status.error');
      case 'degraded':
        return t('status.degraded');
      case 'disabled':
        return t('status.disabled');
      case 'initializing':
        return t('status.initializing');
      default:
        return status;
    }
  };

  const getServiceName = (key: string) => {
    switch (key) {
      case 'database':
        return t('services.database');
      case 'redis':
        return t('services.redis');
      case 'ai':
        return t('services.ai');
      case 'queue':
        return t('services.queue');
      default:
        return key;
    }
  };

  // Don't render interactive elements until mounted to prevent hydration mismatch
  if (!mounted) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-950">
        <Navigation
          title={t('title')}
          subtitle={t('subtitle')}
          apiStatus="checking"
          actions={<div className="flex items-center gap-2" />}
        />
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="space-y-6">
            <section>
              <h2 className="text-sm font-medium text-gray-700 dark:text-slate-300 mb-4">
                {t('services.title')}
              </h2>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                {[1, 2, 3, 4].map((i) => (
                  <div
                    key={i}
                    className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-gray-200 dark:border-slate-700 shadow-sm animate-pulse"
                  >
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-lg bg-gray-200 dark:bg-slate-700">
                        <div className="w-5 h-5 rounded" />
                      </div>
                      <div className="flex-1">
                        <div className="h-4 bg-gray-200 dark:bg-slate-700 rounded w-20 mb-2" />
                        <div className="h-3 bg-gray-200 dark:bg-slate-700 rounded w-16" />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-950">
      {/* Unified Navigation with Monitor Actions */}
      <Navigation
        title={t('title')}
        subtitle={t('subtitle')}
        apiStatus={connected ? "healthy" : "error"}
        actions={
          <div className="flex items-center gap-2">
            {/* Connection Status Badge */}
            <div className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-gray-100 dark:bg-slate-700">
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  connected ? 'bg-green-500 animate-pulse' : 'bg-red-500'
                }`}
              />
              <span className="text-[10px] text-gray-600 dark:text-slate-400">
                {connected ? t('live') : t('offline')}
              </span>
              {connectionType === 'sse' && (
                <span title={t('sseConnected')}>
                  <Wifi className="w-3 h-3 text-blue-500" />
                </span>
              )}
              {connectionType === 'polling' && (
                <span title={t('pollingMode')}>
                  <RefreshCw className="w-3 h-3 text-amber-500 animate-spin-slow" />
                </span>
              )}
            </div>

            {/* Reconnect Button */}
            <button
              onClick={reconnect}
              className="p-1 text-gray-600 dark:text-slate-400 hover:bg-gray-100 dark:hover:bg-slate-700 rounded transition-colors"
              title={t('actions.refresh')}
            >
              <RefreshCw className="w-4 h-4" />
            </button>

            {/* Fullscreen Toggle */}
            <button
              onClick={toggleFullscreen}
              className="p-1 text-gray-600 dark:text-slate-400 hover:bg-gray-100 dark:hover:bg-slate-700 rounded transition-colors"
              title={isFullscreen ? t('actions.exitFullscreen') : t('actions.fullscreen')}
            >
              {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
            </button>
          </div>
        }
      />

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {error && (
          <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <p className="text-sm text-red-800 dark:text-red-200">
              {t('errors.connectionFailed')}: {error}
            </p>
          </div>
        )}

        {data && (
          <div className="space-y-6">
            {/* Service Cards */}
            <section>
              <h2 className="text-sm font-medium text-gray-700 dark:text-slate-300 mb-4">
                {t('services.title')}
              </h2>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                {Object.entries(data.services).map(([key, service]) => {
                  const Icon = serviceIcons[key as keyof typeof serviceIcons] || Activity;
                  return (
                    <div
                      key={key}
                      className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-gray-200 dark:border-slate-700 shadow-sm"
                    >
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/30">
                          <Icon className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                        </div>
                        <div>
                          <h3 className="text-sm font-medium text-gray-900 dark:text-slate-100">
                            {getServiceName(key)}
                          </h3>
                          <div className="flex items-center gap-2 mt-1">
                            <span className={`w-2 h-2 rounded-full ${getStatusColor(service.status)}`} />
                            <span className="text-xs text-gray-600 dark:text-slate-400">
                              {getStatusText(service.status)}
                            </span>
                          </div>
                        </div>
                      </div>
                      {service.latency_ms !== null && (
                        <div className="mt-3 pt-3 border-t border-gray-100 dark:border-slate-700">
                          <div className="flex justify-between text-xs">
                            <span className="text-gray-500 dark:text-slate-500">{t('latency')}</span>
                            <span className="font-mono text-gray-700 dark:text-slate-300">
                              {service.latency_ms.toFixed(0)}ms
                            </span>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </section>

            {/* Charts and Activities */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2">
                <ResourceChart
                  currentResources={data.resources}
                  history={history}
                  translations={{
                    title: t('chart.title'),
                    cpu: t('chart.cpu'),
                    memory: t('chart.memory'),
                  }}
                  onTimeRangeChange={fetchHistory}
                />
              </div>
              <div>
                {/* Activities */}
                <div className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-gray-200 dark:border-slate-700 shadow-sm">
                  <h3 className="text-sm font-medium text-gray-700 dark:text-slate-300 mb-4">
                    {t('activities.title')}
                  </h3>
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {data.activities.length === 0 ? (
                      <div className="text-center py-4 text-gray-500 dark:text-slate-500">
                        {t('activities.empty')}
                      </div>
                    ) : (
                      data.activities.map((activity) => (
                        <div
                          key={activity.id}
                          className="flex items-center justify-between p-2 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700/50"
                        >
                          <div className="flex items-center gap-3">
                            <Activity className="w-4 h-4 text-gray-400" />
                            <span className="text-sm text-gray-900 dark:text-slate-100">{activity.name}</span>
                          </div>
                          <span className="text-xs text-gray-500 dark:text-slate-500 capitalize">
                            {activity.status}
                          </span>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Resource Details */}
            <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-gray-200 dark:border-slate-700">
                <h3 className="text-sm font-medium text-gray-700 dark:text-slate-300 mb-2">
                  {t('resources.cpu')}
                </h3>
                <div className="flex items-end gap-2">
                  <span className="text-3xl font-bold text-gray-900 dark:text-slate-100">
                    {data.resources.cpu_percent.toFixed(1)}%
                  </span>
                </div>
                <div className="mt-2 h-2 bg-gray-200 dark:bg-slate-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-500 transition-all duration-300"
                    style={{ width: `${data.resources.cpu_percent}%` }}
                  />
                </div>
              </div>

              <div className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-gray-200 dark:border-slate-700">
                <h3 className="text-sm font-medium text-gray-700 dark:text-slate-300 mb-2">
                  {t('resources.memory')}
                </h3>
                <div className="flex items-end gap-2">
                  <span className="text-3xl font-bold text-gray-900 dark:text-slate-100">
                    {data.resources.memory_percent.toFixed(1)}%
                  </span>
                  <span className="text-sm text-gray-500 dark:text-slate-500 mb-1">
                    ({data.resources.memory_used_gb.toFixed(1)} / {data.resources.memory_total_gb.toFixed(1)} GB)
                  </span>
                </div>
                <div className="mt-2 h-2 bg-gray-200 dark:bg-slate-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-green-500 transition-all duration-300"
                    style={{ width: `${data.resources.memory_percent}%` }}
                  />
                </div>
              </div>

              <div className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-gray-200 dark:border-slate-700">
                <h3 className="text-sm font-medium text-gray-700 dark:text-slate-300 mb-2">
                  {t('resources.disk')}
                </h3>
                <div className="flex items-end gap-2">
                  <span className="text-3xl font-bold text-gray-900 dark:text-slate-100">
                    {data.resources.disk_percent.toFixed(1)}%
                  </span>
                  <span className="text-sm text-gray-500 dark:text-slate-500 mb-1">
                    ({data.resources.disk_used_gb.toFixed(1)} / {data.resources.disk_total_gb.toFixed(1)} GB)
                  </span>
                </div>
                <div className="mt-2 h-2 bg-gray-200 dark:bg-slate-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-purple-500 transition-all duration-300"
                    style={{ width: `${data.resources.disk_percent}%` }}
                  />
                </div>
              </div>
            </section>
          </div>
        )}

        {!data && !error && (
          <div className="space-y-6">
            {/* Service Cards Skeleton */}
            <section>
              <h2 className="text-sm font-medium text-gray-700 dark:text-slate-300 mb-4">
                {t('services.title')}
              </h2>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                {[1, 2, 3, 4].map((i) => (
                  <div
                    key={i}
                    className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-gray-200 dark:border-slate-700 shadow-sm animate-pulse"
                  >
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-lg bg-gray-200 dark:bg-slate-700">
                        <div className="w-5 h-5 rounded" />
                      </div>
                      <div className="flex-1">
                        <div className="h-4 bg-gray-200 dark:bg-slate-700 rounded w-20 mb-2" />
                        <div className="h-3 bg-gray-200 dark:bg-slate-700 rounded w-16" />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            {/* Charts and Activities Skeleton */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2">
                <div className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-gray-200 dark:border-slate-700 shadow-sm h-64 animate-pulse" />
              </div>
              <div>
                <div className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-gray-200 dark:border-slate-700 shadow-sm h-64 animate-pulse" />
              </div>
            </div>

            {/* Resource Details Skeleton */}
            <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-gray-200 dark:border-slate-700 animate-pulse"
                >
                  <div className="h-4 bg-gray-200 dark:bg-slate-700 rounded w-24 mb-3" />
                  <div className="h-8 bg-gray-200 dark:bg-slate-700 rounded w-16 mb-2" />
                  <div className="h-2 bg-gray-200 dark:bg-slate-700 rounded w-full" />
                </div>
              ))}
            </section>
          </div>
        )}
      </main>
    </div>
  );
}
