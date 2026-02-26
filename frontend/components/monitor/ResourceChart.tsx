'use client';

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { useState, useMemo, useEffect } from 'react';
import type { ResourceMetrics, HistoryPoint } from '@/lib/monitor';

interface ResourceChartProps {
  currentResources: ResourceMetrics;
  history?: HistoryPoint[];
  translations?: {
    title: string;
    cpu: string;
    memory: string;
  };
  onTimeRangeChange?: (minutes: number) => void;
}

type TimeRange = '1h' | '6h' | '24h' | 'all';

// Time range to minutes mapping
const TIME_RANGE_MINUTES: Record<TimeRange, number> = {
  '1h': 60,
  '6h': 360,
  '24h': 1440,
  'all': 1440, // Max 24 hours for 'all'
};

export function ResourceChart({ currentResources, history = [], translations, onTimeRangeChange }: ResourceChartProps) {
  // Calculate default time range based on history data span
  const getDefaultTimeRange = (): TimeRange => {
    if (history.length === 0) return '24h';
    return '24h'; // Always default to 24h for consistency
  };

  // Use 24h as default to show more historical data
  const [timeRange, setTimeRange] = useState<TimeRange>('24h');
  const [isDark, setIsDark] = useState(false);
  const [mounted, setMounted] = useState(false);

  const t = translations || { title: 'Resource Trends', cpu: 'CPU', memory: 'Memory' };

  // Update translations for 'all' option
  const rangeLabels = {
    '1h': '1h',
    '6h': '6h',
    '24h': '24h',
    'all': 'All',
  };

  // Handle time range change - fetch more data if needed
  const handleTimeRangeChange = (range: TimeRange) => {
    setTimeRange(range);
    // Notify parent to fetch more historical data if needed
    if (onTimeRangeChange) {
      onTimeRangeChange(TIME_RANGE_MINUTES[range]);
    }
  };

  // Check dark mode - only after mount to avoid hydration mismatch
  useEffect(() => {
    setMounted(true);
    const checkDarkMode = () => {
      setIsDark(document.documentElement.classList.contains('dark'));
    };
    checkDarkMode();
    // Check periodically
    const interval = setInterval(checkDarkMode, 1000);
    return () => clearInterval(interval);
  }, []);

  // Transform history data for chart
  const chartData = useMemo(() => {
    console.log('[ResourceChart] Processing history:', {
      historyLength: history.length,
      timeRange,
    });

    // Don't render anything until mounted to avoid hydration mismatch
    if (!mounted) {
      return [];
    }

    if (history.length === 0) {
      // Use current time but only on client-side
      const now = new Date();
      return [
        {
          time: `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`,
          cpu: currentResources.cpu_percent,
          memory: currentResources.memory_percent,
        },
      ];
    }

    const now = Date.now();
    const rangeMs = {
      '1h': 60 * 60 * 1000,
      '6h': 6 * 60 * 60 * 1000,
      '24h': 24 * 60 * 60 * 1000,
      'all': Infinity, // Show all data regardless of time
    }[timeRange];

    // Smart time range filtering:
    // 1. Try to show data from [now - range, now] (last N hours up to now)
    // 2. If data is old and none falls in this range, show the most recent N hours of available data
    const latestPointTime = history.length > 0
      ? Math.max(...history.map(p => new Date(p.timestamp).getTime()))
      : now;

    const dataAge = now - latestPointTime;

    // If latest data is within the selected range, use current time as reference
    // Otherwise, use latest data time as reference to show something useful
    const useCurrentTimeRef = dataAge <= rangeMs;
    const referenceTime = useCurrentTimeRef ? now : latestPointTime;

    const filtered = history.filter((point) => {
      if (timeRange === 'all') return true;

      const pointTime = new Date(point.timestamp).getTime();
      const age = referenceTime - pointTime;
      const isInRange = age >= 0 && age <= rangeMs;

      return isInRange;
    });

    // Debug: Show time range info
    if (filtered.length < 50 && history.length > 0) {
      const timestamps = history.map(h => new Date(h.timestamp).getTime());
      const oldestPoint = history.find(h => new Date(h.timestamp).getTime() === Math.min(...timestamps));
      const latestPoint = history.find(h => new Date(h.timestamp).getTime() === Math.max(...timestamps));

      console.log(`[ResourceChart] ⚠️ ${timeRange} range has only ${filtered.length} points`, {
        input: history.length,
        output: filtered.length,
        reference: useCurrentTimeRef ? 'current_time' : 'latest_history',
        referenceTime: new Date(referenceTime).toISOString(),
        dataAge: Math.round(dataAge / 60000) + 'min',
        timeRange: rangeMs / 3600000 + 'h',
        latest: latestPoint?.timestamp,
        oldest: oldestPoint?.timestamp,
        timeSpan: latestPoint && oldestPoint ?
          Math.round((new Date(latestPoint.timestamp).getTime() - new Date(oldestPoint.timestamp).getTime()) / 60000) + 'min'
          : 'N/A',
      });
    }

    console.log('[ResourceChart] Filtered result:', {
      input: history.length,
      output: filtered.length,
    });

    const mapped = filtered.map((point) => {
      const date = new Date(point.timestamp);
      return {
        // Use manual time formatting to avoid locale-dependent hydration issues
        time: `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`,
        cpu: point.resources.cpu_percent,
        memory: point.resources.memory_percent,
      };
    });

    console.log('[ResourceChart] Chart data sample:', {
      total: mapped.length,
      first: mapped[0],
      last: mapped[mapped.length - 1],
    });

    return mapped;
  }, [history, currentResources, timeRange, mounted]);

  const colors = {
    grid: isDark ? '#334155' : '#e5e7eb',
    text: isDark ? '#94a3b8' : '#6b7280',
    cpu: {
      stroke: '#3b82f6',
      fill: isDark ? 'rgba(59, 130, 246, 0.2)' : 'rgba(59, 130, 246, 0.1)',
    },
    memory: {
      stroke: '#10b981',
      fill: isDark ? 'rgba(16, 185, 129, 0.2)' : 'rgba(16, 185, 129, 0.1)',
    },
  };

  // Don't render chart until mounted to prevent hydration mismatch
  if (!mounted) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-gray-200 dark:border-slate-700 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-medium text-gray-900 dark:text-slate-100">
            {t.title}
          </h3>
          <div className="flex gap-1">
            {(['1h', '6h', '24h', 'all'] as TimeRange[]).map((range) => (
              <button
                key={range}
                disabled
                className="px-2 py-1 text-xs rounded bg-gray-100 dark:bg-slate-700 text-gray-400 dark:text-slate-500 cursor-not-allowed"
              >
                {rangeLabels[range]}
              </button>
            ))}
          </div>
        </div>
        <div className="h-64 flex items-center justify-center text-gray-400 dark:text-slate-600">
          Loading...
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-gray-200 dark:border-slate-700 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-gray-900 dark:text-slate-100">
          {t.title}
        </h3>
        <div className="flex gap-1">
          {(['1h', '6h', '24h', 'all'] as TimeRange[]).map((range) => (
            <button
              key={range}
              onClick={() => handleTimeRangeChange(range)}
              className={`px-2 py-1 text-xs rounded transition-colors ${
                timeRange === range
                  ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
                  : 'text-gray-600 dark:text-slate-400 hover:bg-gray-100 dark:hover:bg-slate-700'
              }`}
              title={range === 'all' ? 'Show all historical data' : `Show last ${range}`}
            >
              {rangeLabels[range]}
            </button>
          ))}
        </div>
      </div>

      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData}>
            <defs>
              <linearGradient id="cpuGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={colors.cpu.stroke} stopOpacity={0.3} />
                <stop offset="95%" stopColor={colors.cpu.stroke} stopOpacity={0} />
              </linearGradient>
              <linearGradient id="memoryGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={colors.memory.stroke} stopOpacity={0.3} />
                <stop offset="95%" stopColor={colors.memory.stroke} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke={colors.grid} />
            <XAxis
              dataKey="time"
              stroke={colors.text}
              tick={{ fill: colors.text, fontSize: 10 }}
              tickMargin={8}
            />
            <YAxis
              stroke={colors.text}
              tick={{ fill: colors.text, fontSize: 10 }}
              domain={[0, 100]}
              tickFormatter={(value) => `${value}%`}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: isDark ? '#1e293b' : '#ffffff',
                border: `1px solid ${isDark ? '#334155' : '#e5e7eb'}`,
                borderRadius: '8px',
                color: isDark ? '#e2e8f0' : '#1f2937',
              }}
            />
            <Area
              type="monotone"
              dataKey="cpu"
              stroke={colors.cpu.stroke}
              fill="url(#cpuGradient)"
              strokeWidth={2}
              name={t.cpu}
            />
            <Area
              type="monotone"
              dataKey="memory"
              stroke={colors.memory.stroke}
              fill="url(#memoryGradient)"
              strokeWidth={2}
              name={t.memory}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="flex items-center justify-center gap-6 mt-4">
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-blue-500" />
          <span className="text-xs text-gray-600 dark:text-slate-400">
            {t.cpu}: {currentResources.cpu_percent.toFixed(1)}%
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-green-500" />
          <span className="text-xs text-gray-600 dark:text-slate-400">
            {t.memory}: {currentResources.memory_percent.toFixed(1)}%
          </span>
        </div>
      </div>
    </div>
  );
}
