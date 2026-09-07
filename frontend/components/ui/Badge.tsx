"use client";

import React, { type HTMLAttributes, forwardRef } from "react";
import { cn } from "@/lib/utils";

export type Severity =
  | "critical"
  | "high"
  | "medium"
  | "low"
  | "info"
  | "neutral"
  | "success"
  | "warning"
  | "danger";

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  severity?: Severity;
  variant?: "pill" | "rounded";
  size?: "xs" | "sm" | "md";
  dot?: boolean;
}

const severityStyles: Record<Severity, { bg: string; dot: string }> = {
  critical: {
    bg: "bg-red-50 text-red-700 border-red-200/80 dark:bg-red-500/10 dark:text-red-400 dark:border-red-500/25",
    dot: "bg-red-500",
  },
  danger: {
    bg: "bg-red-50 text-red-700 border-red-200/80 dark:bg-red-500/10 dark:text-red-400 dark:border-red-500/25",
    dot: "bg-red-500",
  },
  high: {
    bg: "bg-orange-50 text-orange-700 border-orange-200/80 dark:bg-orange-500/10 dark:text-orange-400 dark:border-orange-500/25",
    dot: "bg-orange-500",
  },
  warning: {
    bg: "bg-amber-50 text-amber-700 border-amber-200/80 dark:bg-amber-500/10 dark:text-amber-400 dark:border-amber-500/25",
    dot: "bg-amber-500",
  },
  medium: {
    bg: "bg-amber-50 text-amber-700 border-amber-200/80 dark:bg-amber-500/10 dark:text-amber-400 dark:border-amber-500/25",
    dot: "bg-amber-500",
  },
  low: {
    bg: "bg-emerald-50 text-emerald-700 border-emerald-200/80 dark:bg-emerald-500/10 dark:text-emerald-400 dark:border-emerald-500/25",
    dot: "bg-emerald-500",
  },
  success: {
    bg: "bg-emerald-50 text-emerald-700 border-emerald-200/80 dark:bg-emerald-500/10 dark:text-emerald-400 dark:border-emerald-500/25",
    dot: "bg-emerald-500",
  },
  info: {
    bg: "bg-sky-50 text-sky-700 border-sky-200/80 dark:bg-sky-500/10 dark:text-sky-400 dark:border-sky-500/25",
    dot: "bg-sky-500",
  },
  neutral: {
    bg: "bg-slate-100 text-slate-700 border-slate-200/80 dark:bg-slate-800/60 dark:text-slate-300 dark:border-slate-700/60",
    dot: "bg-slate-400",
  },
};

const sizeStyles = {
  xs: "text-[10px] px-1.5 py-0.5 gap-1",
  sm: "text-xs px-2 py-0.5 gap-1.5",
  md: "text-xs px-2.5 py-1 gap-1.5 font-medium",
};

const Badge = React.memo(
  forwardRef<HTMLSpanElement, BadgeProps>(
    (
      {
        severity = "neutral",
        variant = "rounded",
        size = "sm",
        dot = false,
        className,
        children,
        ...props
      },
      ref
    ) => {
      const config = severityStyles[severity] || severityStyles.neutral;
      return (
        <span
          ref={ref}
          className={cn(
            "inline-flex items-center font-medium border leading-none tracking-tight select-none transition-colors",
            variant === "pill" ? "rounded-full" : "rounded-md",
            sizeStyles[size],
            config.bg,
            className
          )}
          {...props}
        >
          {dot && <span className={cn("w-1.5 h-1.5 rounded-full shrink-0", config.dot)} />}
          <span>{children}</span>
        </span>
      );
    }
  )
);
Badge.displayName = "Badge";

export { Badge };
