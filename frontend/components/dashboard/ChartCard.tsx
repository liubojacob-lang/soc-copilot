"use client";

/**
 * ChartCard Component
 * 图表外层容器，统一图表视觉风格
 *
 * 使用 Card/InfoCard 作为容器基础，确保视觉一致性
 */

import React, { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { Card } from "@/components/common/Card";
import { Heading, Caption } from "@/components/ui/Typography";

interface ChartCardProps {
  /** 图表标题 */
  title?: string;
  /** 图表副标题/描述 */
  subtitle?: string;
  /** 标题右侧操作区 */
  action?: ReactNode;
  /** 图表内容 */
  children: ReactNode;
  /** 自定义类名 */
  className?: string;
}

/**
 * 图表容器卡片
 *
 * 标准卡片样式：圆角 12px（rounded-xl）、微弱阴影（shadow-sm）、1px 边框
 * 标题在顶部左对齐，使用 Typography 组件
 * 图表内边距 16px（p-4）
 */
const ChartCard = React.memo(function ChartCard({
  title,
  subtitle,
  action,
  children,
  className,
}: ChartCardProps) {
  return (
    <Card variant="default" padding="none" className={cn("rounded-xl", className)}>
      {(title || subtitle || action) && (
        <div className="flex items-center justify-between px-4 pt-4 pb-2">
          <div className="flex flex-col">
            {title && (
              <Heading level={2} color="primary" className="text-base">
                {title}
              </Heading>
            )}
            {subtitle && (
              <Caption color="tertiary" className="mt-0.5">
                {subtitle}
              </Caption>
            )}
          </div>
          {action && <div>{action}</div>}
        </div>
      )}
      <div className="p-4">{children}</div>
    </Card>
  );
});

export { ChartCard };
export type { ChartCardProps };
