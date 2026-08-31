"use client";

/**
 * Chart Theme Adapter
 * 将设计令牌映射到 Recharts 图表库配置，实现设计规范与图表库解耦
 *
 * 所有颜色引用自 designTokens.ts 或 Tailwind 语义色标准值，禁止硬编码色值
 */

import { useState, useEffect, useCallback } from "react";
import {
  coreColors,
  coreTypography,
  coreBorderRadius,
  coreShadows,
  type ThemeMode,
} from "@/styles/designTokens";

// ==================== Series Colors ====================
// 6 系列固定配色（深蓝、蓝、青、琥珀、橙、玫瑰），低饱和度
// 优先引用 designTokens.ts，缺失值使用 Tailwind 语义色标准值
export const chartSeriesColors = [
  "#1e40af", // 深蓝 — Tailwind blue-800
  coreColors.semantic.info, // 蓝 — designTokens semantic.info (#2563eb)
  "#0891b2", // 青 — Tailwind cyan-600
  coreColors.semantic.warning, // 琥珀 — designTokens semantic.warning (#d97706)
  coreColors.severity.high, // 橙 — designTokens severity.high (#ea580c)
  "#e11d48", // 玫瑰 — Tailwind rose-600
] as const;

// Severity 映射色（用于告警/严重度图表）
export const severityChartColors = {
  critical: coreColors.severity.critical,
  high: coreColors.severity.high,
  medium: coreColors.severity.medium,
  low: coreColors.severity.low,
  info: coreColors.severity.info,
} as const;

// ==================== Chart Theme Factory ====================

export interface ChartTheme {
  seriesColors: readonly string[];
  axis: {
    stroke: string;
    tick: {
      fill: string;
      fontSize: number;
      fontFamily: string;
    };
  };
  grid: {
    stroke: string;
    strokeDasharray: string;
    vertical: boolean;
  };
  tooltip: {
    contentStyle: React.CSSProperties;
    itemStyle: React.CSSProperties;
    labelStyle: React.CSSProperties;
  };
  area: {
    fillOpacity: number;
  };
  legend: {
    wrapperStyle: React.CSSProperties;
  };
  fontFamily: string;
}

export function getChartTheme(mode: ThemeMode): ChartTheme {
  const isDark = mode === "dark";

  return {
    seriesColors: chartSeriesColors,
    axis: {
      // 坐标轴颜色 slate-400
      stroke: coreColors.slate[400],
      tick: {
        // 刻度文字使用 slate-500，比轴线稍浅
        fill: coreColors.slate[500],
        fontSize: 11,
        fontFamily: coreTypography.fontFamily.sans,
      },
    },
    grid: {
      // 网格线仅保留水平极淡线
      stroke: isDark ? coreColors.slate[800] : coreColors.slate[100],
      strokeDasharray: "3 3",
      vertical: false,
    },
    tooltip: {
      // Tooltip 样式：深色背景（slate-800）、白色文字、8px 圆角、无发光边框
      contentStyle: {
        backgroundColor: coreColors.slate[800],
        color: coreColors.slate[50],
        borderRadius: coreBorderRadius.md,
        border: "none",
        boxShadow: coreShadows.sm,
        fontFamily: coreTypography.fontFamily.sans,
        fontSize: coreTypography.fontSize.small.size,
        padding: "12px",
      },
      itemStyle: {
        color: coreColors.slate[50],
      },
      labelStyle: {
        color: coreColors.slate[300],
        marginBottom: "8px",
      },
    },
    area: {
      // 面积图填充透明度 ≤ 10%
      fillOpacity: 0.08,
    },
    legend: {
      wrapperStyle: {
        paddingTop: "16px",
      },
    },
    fontFamily: coreTypography.fontFamily.sans,
  };
}

// ==================== Recharts-specific Props Helpers ====================

interface AxisProps {
  stroke: string;
  tick: { fill: string; fontSize: number; fontFamily: string };
  tickLine: boolean;
  axisLine: boolean;
  fontSize: number;
}

export function getAxisProps(mode: ThemeMode): AxisProps {
  const theme = getChartTheme(mode);
  return {
    stroke: theme.axis.stroke,
    tick: theme.axis.tick,
    tickLine: false,
    axisLine: false,
    fontSize: theme.axis.tick.fontSize,
  };
}

export function getXAxisProps(mode: ThemeMode): AxisProps {
  return getAxisProps(mode);
}

export function getYAxisProps(mode: ThemeMode): AxisProps {
  return getAxisProps(mode);
}

interface GridProps {
  strokeDasharray: string;
  stroke: string;
  vertical: boolean;
}

export function getGridProps(mode: ThemeMode): GridProps {
  const theme = getChartTheme(mode);
  return {
    strokeDasharray: theme.grid.strokeDasharray,
    stroke: theme.grid.stroke,
    vertical: theme.grid.vertical,
  };
}

interface TooltipProps {
  contentStyle: React.CSSProperties;
  itemStyle: React.CSSProperties;
  labelStyle: React.CSSProperties;
}

export function getTooltipProps(mode: ThemeMode): TooltipProps {
  const theme = getChartTheme(mode);
  return {
    contentStyle: theme.tooltip.contentStyle,
    itemStyle: theme.tooltip.itemStyle,
    labelStyle: theme.tooltip.labelStyle,
  };
}

interface LegendProps {
  wrapperStyle: React.CSSProperties;
}

export function getLegendProps(mode: ThemeMode): LegendProps {
  const theme = getChartTheme(mode);
  return {
    wrapperStyle: theme.legend.wrapperStyle,
  };
}

// ==================== Area Fill Props ====================
// 移除渐变填充，使用纯色低透明度填充
interface AreaFillProps {
  fill: string;
  fillOpacity: number;
}

export function getAreaFillProps(color: string, _mode?: ThemeMode): AreaFillProps {
  const theme = getChartTheme(_mode ?? "light");
  return {
    fill: color,
    fillOpacity: theme.area.fillOpacity,
  };
}

// ==================== Hook for Dark Mode ====================

export function useChartTheme(): ChartTheme {
  const [mode, setMode] = useState<ThemeMode>("light");

  const detectMode = useCallback((): ThemeMode => {
    return document.documentElement.classList.contains("dark") ? "dark" : "light";
  }, []);

  useEffect(() => {
    setMode(detectMode());

    const observer = new MutationObserver(() => {
      setMode(detectMode());
    });
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["class"],
    });
    return () => observer.disconnect();
  }, [detectMode]);

  return getChartTheme(mode);
}

// ==================== Re-exports for convenience ====================

export { coreColors as chartColors };
export type { ThemeMode };
