"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { useState, useMemo, useEffect } from "react";
import { cn } from "@/lib/utils";
import { ChartCard } from "@/components/dashboard/ChartCard";
import {
  chartSeriesColors,
  getAxisProps,
  getGridProps,
  getTooltipProps,
} from "@/lib/chartThemeAdapter";
import type { ResourceMetrics, HistoryPoint } from "@/lib/monitor";

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

type TimeRange = "1h" | "6h" | "24h" | "all";

// Time range to minutes mapping
const TIME_RANGE_MINUTES: Record<TimeRange, number> = {
  "1h": 60,
  "6h": 360,
  "24h": 1440,
  all: 1440, // Max 24 hours for 'all'
};

export function ResourceChart({
  currentResources,
  history = [],
  translations,
  onTimeRangeChange,
}: ResourceChartProps) {
  const [timeRange, setTimeRange] = useState<TimeRange>("24h");
  const [isDark, setIsDark] = useState(false);
  const [mounted, setMounted] = useState(false);

  const t = translations || { title: "Resource Trends", cpu: "CPU", memory: "Memory" };

  const rangeLabels = {
    "1h": "1h",
    "6h": "6h",
    "24h": "24h",
    all: "All",
  };

  const handleTimeRangeChange = (range: TimeRange) => {
    setTimeRange(range);
    if (onTimeRangeChange) {
      onTimeRangeChange(TIME_RANGE_MINUTES[range]);
    }
  };

  // Check dark mode using MutationObserver (no polling)
  useEffect(() => {
    setMounted(true);
    setIsDark(document.documentElement.classList.contains("dark"));

    const observer = new MutationObserver(() => {
      setIsDark(document.documentElement.classList.contains("dark"));
    });
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["class"],
    });
    return () => observer.disconnect();
  }, []);

  // Transform history data for chart
  const chartData = useMemo(() => {
    if (!mounted) {
      return [];
    }

    if (history.length === 0) {
      const now = new Date();
      return [
        {
          time: `${now.getHours().toString().padStart(2, "0")}:${now.getMinutes().toString().padStart(2, "0")}`,
          cpu: currentResources.cpu_percent,
          memory: currentResources.memory_percent,
        },
      ];
    }

    const now = Date.now();
    const rangeMs = {
      "1h": 60 * 60 * 1000,
      "6h": 6 * 60 * 60 * 1000,
      "24h": 24 * 60 * 60 * 1000,
      all: Infinity,
    }[timeRange];

    const latestPointTime =
      history.length > 0 ? Math.max(...history.map((p) => new Date(p.timestamp).getTime())) : now;
    const dataAge = now - latestPointTime;
    const useCurrentTimeRef = dataAge <= rangeMs;
    const referenceTime = useCurrentTimeRef ? now : latestPointTime;

    const filtered = history.filter((point) => {
      if (timeRange === "all") return true;
      const pointTime = new Date(point.timestamp).getTime();
      const age = referenceTime - pointTime;
      return age >= 0 && age <= rangeMs;
    });

    return filtered.map((point) => {
      const date = new Date(point.timestamp);
      return {
        time: `${date.getHours().toString().padStart(2, "0")}:${date.getMinutes().toString().padStart(2, "0")}`,
        cpu: point.resources.cpu_percent,
        memory: point.resources.memory_percent,
      };
    });
  }, [history, currentResources, timeRange, mounted]);

  const mode = isDark ? ("dark" as const) : ("light" as const);
  const themeAxis = getAxisProps(mode);
  const themeGrid = getGridProps(mode);
  const themeTooltip = getTooltipProps(mode);

  // Time range action buttons
  const timeRangeAction = (
    <div className="flex gap-1">
      {(["1h", "6h", "24h", "all"] as TimeRange[]).map((range) => (
        <button
          key={range}
          onClick={() => handleTimeRangeChange(range)}
          disabled={!mounted}
          className={cn(
            "px-2 py-1 text-xs rounded transition-colors",
            timeRange === range
              ? "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300"
              : "text-gray-600 dark:text-slate-400 hover:bg-gray-100 dark:hover:bg-slate-700"
          )}
          title={range === "all" ? "Show all historical data" : `Show last ${range}`}
        >
          {rangeLabels[range]}
        </button>
      ))}
    </div>
  );

  // Don't render chart until mounted to prevent hydration mismatch
  if (!mounted) {
    return (
      <ChartCard title={t.title} action={timeRangeAction}>
        <div className="h-64 flex items-center justify-center text-gray-400 dark:text-slate-600">
          Loading...
        </div>
      </ChartCard>
    );
  }

  return (
    <ChartCard title={t.title} action={timeRangeAction}>
      <div className="w-full min-w-0 h-64">
        <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
          <AreaChart data={chartData}>
            <CartesianGrid {...themeGrid} />
            <XAxis dataKey="time" {...themeAxis} tickMargin={8} />
            <YAxis {...themeAxis} domain={[0, 100]} tickFormatter={(value) => `${value}%`} />
            <Tooltip {...themeTooltip} />
            <Area
              type="monotone"
              dataKey="cpu"
              stroke={chartSeriesColors[0]}
              fill={chartSeriesColors[0]}
              fillOpacity={0.08}
              strokeWidth={2}
              name={t.cpu}
            />
            <Area
              type="monotone"
              dataKey="memory"
              stroke={chartSeriesColors[1]}
              fill={chartSeriesColors[1]}
              fillOpacity={0.08}
              strokeWidth={2}
              name={t.memory}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="flex items-center justify-center gap-6 mt-4">
        <div className="flex items-center gap-2">
          <span
            className="w-3 h-3 rounded-full"
            style={{ backgroundColor: chartSeriesColors[0] }}
          />
          <span className="text-xs text-gray-600 dark:text-slate-400">
            {t.cpu}: {currentResources.cpu_percent.toFixed(1)}%
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span
            className="w-3 h-3 rounded-full"
            style={{ backgroundColor: chartSeriesColors[1] }}
          />
          <span className="text-xs text-gray-600 dark:text-slate-400">
            {t.memory}: {currentResources.memory_percent.toFixed(1)}%
          </span>
        </div>
      </div>
    </ChartCard>
  );
}
