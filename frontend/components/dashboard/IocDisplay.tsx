"use client";

import { cn } from "@/lib/utils";

interface IocDisplayProps {
  value: string;
  className?: string;
}

/**
 * IOC 数据展示组件
 * - 等宽字体（JetBrains Mono 优先，回退系统 mono）
 * - 背景 slate-50 / slate-800
 * - 无发光、无复制按钮悬浮放大
 */
export function IocDisplay({ value, className }: IocDisplayProps) {
  return (
    <code
      className={cn(
        "inline-block",
        "font-['JetBrains_Mono',ui-monospace,SFMono-Regular,Menlo,Monaco,'Cascadia_Code',monospace]",
        "text-[13px] leading-relaxed",
        "px-2 py-1 rounded",
        "bg-slate-50 dark:bg-slate-800",
        "text-slate-900 dark:text-slate-100",
        "select-all",
        className
      )}
    >
      {value}
    </code>
  );
}
