"use client";

import { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { Card } from "@/components/common/Card";
import { Heading, Caption, Text } from "@/components/ui/Typography";

/**
 * Trend 方向类型
 */
type TrendDirection = "up" | "down" | "neutral";

/**
 * StatCard 组件属性
 * KPI 大数字卡片，用于仪表盘展示关键指标
 */
interface StatCardProps {
  /** 指标名称 */
  title: string;
  /** 数值 */
  value: string | number;
  /** 环比变化文字，如 "+12%" */
  trend?: string;
  /** 趋势方向 */
  trendDirection?: TrendDirection;
  /** 图标 */
  icon?: ReactNode;
  /** 副标题 */
  subtitle?: string;
  /** 自定义类名 */
  className?: string;
}

/**
 * KPI 统计卡片
 *
 * 顶部指标名称（12px 辅助色）
 * 中部大字号数据（32px / 600 字重）
 * 底部环比变化（绿色/红色小字 + 箭头图标）
 */
function StatCard({
  title,
  value,
  trend,
  trendDirection = "neutral",
  icon,
  subtitle,
  className,
}: StatCardProps) {
  const trendColorClasses: Record<TrendDirection, string> = {
    up: "text-success-600 dark:text-success-400",
    down: "text-danger-600 dark:text-danger-400",
    neutral: "text-text-tertiary dark:text-slate-400",
  };

  const trendArrow: Record<TrendDirection, string> = {
    up: "↑",
    down: "↓",
    neutral: "−",
  };

  return (
    <Card
      variant="default"
      padding="lg"
      className={cn("flex items-start justify-between", className)}
    >
      <div className="flex-1 min-w-0">
        <Caption color="tertiary">{title}</Caption>
        <Heading level="display" color="primary" className="mt-1 font-semibold">
          {value}
        </Heading>
        {subtitle && (
          <Text color="tertiary" className="mt-1 text-sm">
            {subtitle}
          </Text>
        )}
        {trend && (
          <div className="mt-2 flex items-center gap-1.5">
            <span className={cn("text-sm font-medium", trendColorClasses[trendDirection])}>
              {trendArrow[trendDirection]} {trend}
            </span>
          </div>
        )}
      </div>
      {icon && (
        <div className="p-3 rounded-lg bg-surface-hover dark:bg-slate-700 text-text-secondary dark:text-slate-300 shrink-0 ml-4">
          {icon}
        </div>
      )}
    </Card>
  );
}

export { StatCard };
export type { StatCardProps, TrendDirection };
