'use client';

/**
 * System Dashboard Page
 * 系统仪表盘 - 显示系统整体健康状态、资源使用情况、功能开关等
 */

import { useEffect, useState } from 'react';
import Navigation from '@/components/Navigation';
import {
  Activity,
  Database,
  HardDrive,
  Cpu,
  MemoryStick,
  Server,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Zap,
  Clock,
  RefreshCw
} from 'lucide-react';

// Types
interface DatabaseStatus {
  status: string;
  latency_ms: number;
  pool?: {
    size: number;
    checked_in: number;
    checked_out: number;
    overflow: number;
    invalid: number;
  };
  version?: string;
  database_size?: string;
  active_connections?: number;
}

interface RedisStatus {
  status: string;
  latency_ms?: number;
  version?: string;
  connected_clients?: number;
  used_memory?: string;
  uptime_seconds?: number;
  pool_connections?: number;
}

interface AIModelStatus {
  id: string;
  name: string;
  provider: string;
  is_active: boolean;
  last_used?: string;
  total_requests: number;
}

interface SystemStats {
  cpu_percent: number;
  memory: {
    total_gb: number;
    available_gb: number;
    used_gb: number;
    percent_used: number;
  };
  disk: {
    total_gb: number;
    used_gb: number;
    free_gb: number;
    percent_used: number;
  };
  uptime_seconds: number;
  platform: string;
  python_version: string;
}

interface SystemDashboard {
  timestamp: string;
  version: string;
  environment: string;
  database: DatabaseStatus;
  redis: RedisStatus;
  ai_models: AIModelStatus[];
  system: SystemStats;
  features: Record<string, boolean>;
}

export default function SystemDashboardPage() {
  const [dashboard, setDashboard] = useState<SystemDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchDashboard = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch('/api/system/dashboard', {
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      setDashboard(data);
    } catch (err) {
      console.error('Failed to fetch dashboard:', err);
      setError(err instanceof Error ? err.message : 'Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboard();

    if (autoRefresh) {
      const interval = setInterval(fetchDashboard, 30000);
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'ok':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'error':
        return <XCircle className="w-5 h-5 text-red-500" />;
      case 'degraded':
      case 'disabled':
        return <AlertTriangle className="w-5 h-5 text-yellow-500" />;
      default:
        return <Activity className="w-5 h-5 text-gray-400" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'ok':
        return 'text-green-600 bg-green-50 dark:bg-green-900/20 dark:text-green-400';
      case 'error':
        return 'text-red-600 bg-red-50 dark:bg-red-900/20 dark:text-red-400';
      case 'degraded':
      case 'disabled':
        return 'text-yellow-600 bg-yellow-50 dark:bg-yellow-900/20 dark:text-yellow-400';
      default:
        return 'text-gray-600 bg-gray-50 dark:bg-gray-900/20 dark:text-gray-400';
    }
  };

  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);

    if (days > 0) {
      return `${days}d ${hours}h ${minutes}m`;
    } else if (hours > 0) {
      return `${hours}h ${minutes}m`;
    } else {
      return `${minutes}m`;
    }
  };

  if (loading && !dashboard) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (error && !dashboard) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen space-y-4">
        <XCircle className="w-16 h-16 text-red-500" />
        <div className="text-center">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            Failed to load dashboard
          </h2>
          <p className="text-gray-600 dark:text-gray-400 mt-2">{error}</p>
        </div>
        <button
          onClick={fetchDashboard}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!dashboard) return null;

  return (
    <>
      <Navigation title="System Dashboard" />
      <div className="space-y-6 p-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
              System Dashboard
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mt-1">
              System health monitoring and resource usage
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <div className="text-sm text-gray-500 dark:text-gray-400">
            v{dashboard.version} • {dashboard.environment}
          </div>
          {/* Auto-refresh toggle switch */}
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-600 dark:text-gray-400">Auto-refresh</span>
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
                autoRefresh ? 'bg-blue-600' : 'bg-gray-300 dark:bg-gray-600'
              }`}
              role="switch"
              aria-checked={autoRefresh}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  autoRefresh ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>
          <button
            onClick={fetchDashboard}
            disabled={loading}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Database Status */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-2">
              <Database className="w-5 h-5 text-blue-500" />
              <h3 className="font-semibold text-gray-900 dark:text-white">Database</h3>
            </div>
            {getStatusIcon(dashboard.database.status)}
          </div>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Status</span>
              <span className={`font-medium ${getStatusColor(dashboard.database.status)}`}>
                {dashboard.database.status.toUpperCase()}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Latency</span>
              <span className="font-medium text-gray-900 dark:text-white">
                {dashboard.database.latency_ms.toFixed(2)} ms
              </span>
            </div>
            {dashboard.database.version && (
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Version</span>
                <span className="font-medium text-gray-900 dark:text-white">
                  {dashboard.database.version}
                </span>
              </div>
            )}
            {dashboard.database.database_size && (
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Size</span>
                <span className="font-medium text-gray-900 dark:text-white">
                  {dashboard.database.database_size}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Redis Status */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-2">
              <Server className="w-5 h-5 text-red-500" />
              <h3 className="font-semibold text-gray-900 dark:text-white">Redis</h3>
            </div>
            {getStatusIcon(dashboard.redis.status)}
          </div>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Status</span>
              <span className={`font-medium ${getStatusColor(dashboard.redis.status)}`}>
                {dashboard.redis.status.toUpperCase()}
              </span>
            </div>
            {dashboard.redis.latency_ms && (
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Latency</span>
                <span className="font-medium text-gray-900 dark:text-white">
                  {dashboard.redis.latency_ms.toFixed(2)} ms
                </span>
              </div>
            )}
            {dashboard.redis.used_memory && (
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Memory</span>
                <span className="font-medium text-gray-900 dark:text-white">
                  {dashboard.redis.used_memory}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* CPU Usage */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-2">
              <Cpu className="w-5 h-5 text-purple-500" />
              <h3 className="font-semibold text-gray-900 dark:text-white">CPU</h3>
            </div>
            {dashboard.system.cpu_percent > 80 ? (
              <AlertTriangle className="w-5 h-5 text-yellow-500" />
            ) : (
              <CheckCircle className="w-5 h-5 text-green-500" />
            )}
          </div>
          <div className="space-y-2">
            <div className="flex items-end justify-between">
              <span className="text-sm text-gray-600 dark:text-gray-400">Usage</span>
              <span className="text-2xl font-bold text-gray-900 dark:text-white">
                {dashboard.system.cpu_percent.toFixed(1)}%
              </span>
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
              <div
                className={`h-2 rounded-full transition-colors ${
                  dashboard.system.cpu_percent > 80
                    ? 'bg-red-500'
                    : dashboard.system.cpu_percent > 60
                    ? 'bg-yellow-500'
                    : 'bg-green-500'
                }`}
                style={{ width: `${Math.min(dashboard.system.cpu_percent, 100)}%` }}
              />
            </div>
          </div>
        </div>

        {/* Memory Usage */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-2">
              <MemoryStick className="w-5 h-5 text-green-500" />
              <h3 className="font-semibold text-gray-900 dark:text-white">Memory</h3>
            </div>
            {dashboard.system.memory.percent_used > 80 ? (
              <AlertTriangle className="w-5 h-5 text-yellow-500" />
            ) : (
              <CheckCircle className="w-5 h-5 text-green-500" />
            )}
          </div>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Used</span>
              <span className="font-medium text-gray-900 dark:text-white">
                {dashboard.system.memory.used_gb.toFixed(2)} GB
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Total</span>
              <span className="font-medium text-gray-900 dark:text-white">
                {dashboard.system.memory.total_gb.toFixed(2)} GB
              </span>
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
              <div
                className={`h-2 rounded-full transition-colors ${
                  dashboard.system.memory.percent_used > 80
                    ? 'bg-red-500'
                    : dashboard.system.memory.percent_used > 60
                    ? 'bg-yellow-500'
                    : 'bg-green-500'
                }`}
                style={{ width: `${Math.min(dashboard.system.memory.percent_used, 100)}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Detailed Sections */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Database Details */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
            <Database className="w-5 h-5 mr-2 text-blue-500" />
            Database Details
          </h2>
          {dashboard.database.pool ? (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div className="bg-gray-50 dark:bg-gray-900/50 p-3 rounded-md">
                  <div className="text-gray-600 dark:text-gray-400">Pool Size</div>
                  <div className="text-lg font-semibold text-gray-900 dark:text-white">
                    {dashboard.database.pool.size}
                  </div>
                </div>
                <div className="bg-gray-50 dark:bg-gray-900/50 p-3 rounded-md">
                  <div className="text-gray-600 dark:text-gray-400">Checked In</div>
                  <div className="text-lg font-semibold text-gray-900 dark:text-white">
                    {dashboard.database.pool.checked_in}
                  </div>
                </div>
                <div className="bg-gray-50 dark:bg-gray-900/50 p-3 rounded-md">
                  <div className="text-gray-600 dark:text-gray-400">Checked Out</div>
                  <div className="text-lg font-semibold text-gray-900 dark:text-white">
                    {dashboard.database.pool.checked_out}
                  </div>
                </div>
                <div className="bg-gray-50 dark:bg-gray-900/50 p-3 rounded-md">
                  <div className="text-gray-600 dark:text-gray-400">Overflow</div>
                  <div className="text-lg font-semibold text-gray-900 dark:text-white">
                    {dashboard.database.pool.overflow}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <p className="text-gray-500 dark:text-gray-400 text-sm">
              Connection pool information not available
            </p>
          )}
        </div>

        {/* Disk Usage */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
            <HardDrive className="w-5 h-5 mr-2 text-orange-500" />
            Disk Usage
          </h2>
          <div className="space-y-4">
            <div className="flex items-end justify-between">
              <span className="text-sm text-gray-600 dark:text-gray-400">Used Space</span>
              <span className="text-2xl font-bold text-gray-900 dark:text-white">
                {dashboard.system.disk.used_gb.toFixed(2)} GB
              </span>
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Total</span>
                <span className="font-medium text-gray-900 dark:text-white">
                  {dashboard.system.disk.total_gb.toFixed(2)} GB
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Free</span>
                <span className="font-medium text-gray-900 dark:text-white">
                  {dashboard.system.disk.free_gb.toFixed(2)} GB
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Usage</span>
                <span className="font-medium text-gray-900 dark:text-white">
                  {dashboard.system.disk.percent_used.toFixed(1)}%
                </span>
              </div>
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3">
              <div
                className={`h-3 rounded-full transition-colors ${
                  dashboard.system.disk.percent_used > 80
                    ? 'bg-red-500'
                    : dashboard.system.disk.percent_used > 60
                    ? 'bg-yellow-500'
                    : 'bg-green-500'
                }`}
                style={{ width: `${Math.min(dashboard.system.disk.percent_used, 100)}%` }}
              />
            </div>
          </div>
        </div>

        {/* AI Models */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
            <Zap className="w-5 h-5 mr-2 text-yellow-500" />
            AI Models
          </h2>
          <div className="space-y-3">
            {dashboard.ai_models.length > 0 ? (
              dashboard.ai_models.map((model) => (
                <div
                  key={model.id}
                  className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-900/50 rounded-md"
                >
                  <div className="flex-1">
                    <div className="flex items-center space-x-2">
                      <span className="font-medium text-gray-900 dark:text-white">
                        {model.name}
                      </span>
                      {model.is_active ? (
                        <span className="px-2 py-0.5 text-xs bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400 rounded-full">
                          Active
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 text-xs bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400 rounded-full">
                          Inactive
                        </span>
                      )}
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                      {model.provider} • {model.total_requests} requests
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-gray-500 dark:text-gray-400 text-sm">
                No AI models configured
              </p>
            )}
          </div>
        </div>

        {/* System Info */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
            <Server className="w-5 h-5 mr-2 text-gray-500" />
            System Information
          </h2>
          <div className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Platform</span>
              <span className="font-medium text-gray-900 dark:text-white">
                {dashboard.system.platform}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Python</span>
              <span className="font-medium text-gray-900 dark:text-white">
                {dashboard.system.python_version}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600 dark:text-gray-400 flex items-center">
                <Clock className="w-4 h-4 mr-1" />
                Uptime
              </span>
              <span className="font-medium text-gray-900 dark:text-white">
                {formatUptime(dashboard.system.uptime_seconds)}
              </span>
            </div>
            <div className="border-t border-gray-200 dark:border-gray-700 pt-3 mt-3">
              <div className="text-xs text-gray-500 dark:text-gray-400 mb-2">Features</div>
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(dashboard.features).map(([key, value]) => (
                  <div key={key} className="flex items-center space-x-2">
                    {value ? (
                      <CheckCircle className="w-4 h-4 text-green-500" />
                    ) : (
                      <XCircle className="w-4 h-4 text-gray-400" />
                    )}
                    <span className="text-gray-700 dark:text-gray-300 capitalize">
                      {key.replace(/_/g, ' ')}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Last Updated */}
      <div className="text-center text-sm text-gray-500 dark:text-gray-400">
        Last updated: {new Date(dashboard.timestamp).toLocaleString()}
      </div>
    </div>
    </>
  );
}
