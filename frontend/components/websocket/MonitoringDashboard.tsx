'use client';

import { useState, useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { loadAuthState } from '@/lib/auth';
import {
  Activity,
  MessageSquare,
  AlertTriangle,
  Zap,
  Users,
  TrendingUp,
  TrendingDown,
  Clock,
  Network,
  BarChart3,
  RefreshCw
} from 'lucide-react';

interface ConnectionMetrics {
  active_connections: number;
  total_connections: number;
  total_disconnections: number;
  total_connection_failures: number;
  avg_connection_duration_seconds: number;
}

interface MessageMetrics {
  total_messages_sent: number;
  total_messages_received: number;
  total_messages_filtered: number;
  total_messages_queued: number;
  avg_message_size_bytes: number;
  current_send_rate: number;
  current_receive_rate: number;
}

interface ErrorMetrics {
  total_errors: number;
  total_critical_errors: number;
  errors_by_type: Record<string, number>;
}

interface PerformanceMetrics {
  avg_latency_ms: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  max_latency_ms: number;
}

interface MetricsData {
  health_score: number;
  connection: ConnectionMetrics;
  message: MessageMetrics;
  error: ErrorMetrics;
  performance: PerformanceMetrics;
  timestamp: string;
}

type TimeRange = '1h' | '6h' | '24h' | '7d';

export function MonitoringDashboard() {
  const t = useTranslations('websocket.monitoring');
  const [mounted, setMounted] = useState(false);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [metrics, setMetrics] = useState<MetricsData | null>(null);
  const [timeRange, setTimeRange] = useState<TimeRange>('1h');
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchMetrics = async () => {
    try {
      const authState = loadAuthState();
      if (!authState?.isAuthenticated) return;

      setRefreshing(true);

      const response = await fetch('/api/v1/ws/monitoring/metrics', {
        headers: {
          'Authorization': `Bearer ${authState.token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setMetrics(data);
      }
    } catch (error) {
      console.error('Error fetching metrics:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
    setMounted(true);

    if (autoRefresh) {
      const interval = setInterval(fetchMetrics, 5000); // Refresh every 5 seconds
      return () => clearInterval(interval);
    }
  }, [autoRefresh, timeRange]);

  if (!mounted) return null;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex items-center gap-3 text-gray-600 dark:text-gray-400">
          <RefreshCw className="w-6 h-6 animate-spin" />
          <span>Loading metrics...</span>
        </div>
      </div>
    );
  }

  if (!metrics) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <BarChart3 className="w-12 h-12 text-gray-400 mx-auto mb-3" />
          <p className="text-gray-500 dark:text-gray-400">No metrics available</p>
        </div>
      </div>
    );
  }

  const healthStatus = metrics.health_score >= 70 ? 'healthy' : metrics.health_score >= 50 ? 'degraded' : 'critical';
  const healthColors = {
    healthy: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    degraded: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
    critical: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <BarChart3 className="w-5 h-5" />
            WebSocket Monitoring Dashboard
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Real-time WebSocket connection and message metrics
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Auto-refresh toggle */}
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded"
            />
            <span className="text-gray-600 dark:text-gray-400">Auto-refresh</span>
          </label>

          {/* Time range selector */}
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value as TimeRange)}
            className="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            <option value="1h">Last 1 hour</option>
            <option value="6h">Last 6 hours</option>
            <option value="24h">Last 24 hours</option>
            <option value="7d">Last 7 days</option>
          </select>

          {/* Refresh button */}
          <button
            onClick={fetchMetrics}
            disabled={refreshing}
            className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
          >
            <RefreshCw className={`w-5 h-5 ${refreshing ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Health Score */}
      <div className={`p-4 rounded-lg border ${healthColors[healthStatus]}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Activity className="w-8 h-8" />
            <div>
              <p className="text-sm font-medium">System Health Score</p>
              <p className="text-2xl font-bold">{metrics.health_score.toFixed(1)}%</p>
            </div>
          </div>
          <div className="text-right">
            <p className={`text-sm font-semibold uppercase`}>{healthStatus}</p>
            <p className="text-xs opacity-75">
              Last updated: {new Date(metrics.timestamp).toLocaleTimeString()}
            </p>
          </div>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Connection Metrics */}
        <MetricCard
          title="Connections"
          icon={Users}
          value={metrics.connection.active_connections}
          label="Active"
          color="blue"
          details={[
            { label: 'Total', value: metrics.connection.total_connections },
            { label: 'Failures', value: metrics.connection.total_connection_failures },
          ]}
        />

        {/* Message Metrics */}
        <MetricCard
          title="Messages"
          icon={MessageSquare}
          value={metrics.message.total_messages_sent}
          label="Sent"
          color="green"
          details={[
            { label: 'Received', value: metrics.message.total_messages_received },
            { label: 'Filtered', value: metrics.message.total_messages_filtered },
          ]}
        />

        {/* Error Metrics */}
        <MetricCard
          title="Errors"
          icon={AlertTriangle}
          value={metrics.error.total_errors}
          label="Total"
          color="red"
          details={[
            { label: 'Critical', value: metrics.error.total_critical_errors },
            { label: 'Rate', value: `${metrics.message.current_send_rate.toFixed(1)}/s` },
          ]}
          highlight={metrics.error.total_errors > 0}
        />

        {/* Performance Metrics */}
        <MetricCard
          title={t('latency')}
          icon={Zap}
          value={`${metrics.performance.avg_latency_ms.toFixed(1)}ms`}
          label={t('average')}
          color="purple"
          details={[
            { label: t('p95'), value: `${metrics.performance.p95_latency_ms.toFixed(1)}ms` },
            { label: t('p99'), value: `${metrics.performance.p99_latency_ms.toFixed(1)}ms` },
          ]}
          highlight={metrics.performance.p95_latency_ms > 500}
        />
      </div>

      {/* Detailed Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Connection Details */}
        <DetailsCard
          title={t('connectionDetails')}
          icon={Network}
          data={[
            { label: t('activeConnections'), value: metrics.connection.active_connections },
            { label: t('totalConnections'), value: metrics.connection.total_connections },
            { label: t('totalDisconnections'), value: metrics.connection.total_disconnections },
            { label: t('connectionFailures'), value: metrics.connection.total_connection_failures },
            { label: t('avgDuration'), value: `${metrics.connection.avg_connection_duration_seconds.toFixed(1)}s` },
          ]}
        />

        {/* Message Details */}
        <DetailsCard
          title={t('messageDetails')}
          icon={MessageSquare}
          data={[
            { label: t('messagesSent'), value: metrics.message.total_messages_sent },
            { label: t('messagesReceived'), value: metrics.message.total_messages_received },
            { label: t('messagesFiltered'), value: metrics.message.total_messages_filtered },
            { label: t('messagesQueued'), value: metrics.message.total_messages_queued },
            { label: t('sendRate'), value: `${metrics.message.current_send_rate.toFixed(1)}/s` },
            { label: t('receiveRate'), value: `${metrics.message.current_receive_rate.toFixed(1)}/s` },
          ]}
        />

        {/* Performance Details */}
        <DetailsCard
          title={t('performanceDetails')}
          icon={Clock}
          data={[
            { label: t('avgLatency'), value: `${metrics.performance.avg_latency_ms.toFixed(2)}ms` },
            { label: t('p50Latency'), value: `${metrics.performance.p50_latency_ms.toFixed(2)}ms` },
            { label: t('p95Latency'), value: `${metrics.performance.p95_latency_ms.toFixed(2)}ms` },
            { label: t('p99Latency'), value: `${metrics.performance.p99_latency_ms.toFixed(2)}ms` },
            { label: t('maxLatency'), value: `${metrics.performance.max_latency_ms.toFixed(2)}ms` },
          ]}
        />

        {/* Error Breakdown */}
        <DetailsCard
          title={t('errorBreakdown')}
          icon={AlertTriangle}
          data={Object.entries(metrics.error.errors_by_type).map(([type, count]) => ({
            label: type,
            value: count,
          }))}
          highlight={metrics.error.total_errors > 0}
        />
      </div>
    </div>
  );
}

interface MetricCardProps {
  title: string;
  icon: any;
  value: number | string;
  label: string;
  color: 'blue' | 'green' | 'red' | 'purple';
  details: Array<{ label: string; value: number | string }>;
  highlight?: boolean;
}

function MetricCard({ title, icon: Icon, value, label, color, details, highlight }: MetricCardProps) {
  const colorClasses = {
    blue: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
    green: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    red: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
    purple: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  };

  return (
    <div className={`p-4 rounded-lg border ${highlight ? 'border-red-300 dark:border-red-700' : 'border-gray-200 dark:border-gray-700'} bg-white dark:bg-gray-800`}>
      <div className="flex items-center gap-2 mb-3">
        <Icon className={`w-5 h-5 ${colorClasses[color].split(' ')[1]}`} />
        <h4 className="font-medium text-gray-900 dark:text-white">{title}</h4>
      </div>

      <div className="mb-3">
        <p className="text-2xl font-bold text-gray-900 dark:text-white">{value}</p>
        <p className="text-sm text-gray-500 dark:text-gray-400">{label}</p>
      </div>

      <div className="space-y-1 text-sm">
        {details.map((detail, idx) => (
          <div key={idx} className="flex justify-between text-gray-600 dark:text-gray-400">
            <span>{detail.label}</span>
            <span className="font-medium text-gray-900 dark:text-white">{detail.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

interface DetailsCardProps {
  title: string;
  icon: any;
  data: Array<{ label: string; value: number | string }>;
  highlight?: boolean;
}

function DetailsCard({ title, icon: Icon, data, highlight }: DetailsCardProps) {
  return (
    <div className={`p-4 rounded-lg border ${highlight ? 'border-red-300 dark:border-red-700' : 'border-gray-200 dark:border-gray-700'} bg-white dark:bg-gray-800`}>
      <div className="flex items-center gap-2 mb-4">
        <Icon className="w-5 h-5 text-gray-600 dark:text-gray-400" />
        <h4 className="font-medium text-gray-900 dark:text-white">{title}</h4>
      </div>

      <div className="space-y-3">
        {data.map((item, idx) => (
          <div key={idx} className="flex justify-between items-center">
            <span className="text-sm text-gray-600 dark:text-gray-400">{item.label}</span>
            <span className="font-medium text-gray-900 dark:text-white">{item.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
