"use client";

import React, { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { Heading, Text } from "@/components/ui/Typography";

/**
 * InfoCard 变体类型
 */
type InfoCardVariant = "white" | "gray";

/**
 * InfoCard 组件属性
 * 通用信息面板，支持标题区、内容区、底部操作区
 */
interface InfoCardProps {
  /** 标题 */
  title?: string;
  /** 内容 */
  children: ReactNode;
  /** 底部操作区 */
  footer?: ReactNode;
  /** 自定义类名 */
  className?: string;
  /** 背景变体 */
  variant?: InfoCardVariant;
}

/**
 * 通用信息面板
 *
 * 纯白/纯灰背景，内边距 24px
 * 支持标题区、内容区、底部操作区
 */
const InfoCard = React.memo(function InfoCard({
  title,
  children,
  footer,
  className,
  variant = "white",
}: InfoCardProps) {
  const bgClasses: Record<InfoCardVariant, string> = {
    white: "bg-surface-card dark:bg-slate-800",
    gray: "bg-surface-hover dark:bg-slate-700",
  };

  return (
    <div
      className={cn(
        "rounded-lg border border-border-subtle dark:border-slate-700 shadow-sm p-6",
        bgClasses[variant],
        className
      )}
    >
      {title && (
        <div className="mb-4">
          <Heading level={2} color="primary">
            {title}
          </Heading>
        </div>
      )}
      <div className="flex-1">{children}</div>
      {footer && (
        <div className="mt-4 pt-4 border-t border-border-subtle dark:border-slate-700 flex items-center justify-between">
          {footer}
        </div>
      )}
    </div>
  );
});

export { InfoCard };
export type { InfoCardProps, InfoCardVariant };
