"use client";

import { type HTMLAttributes, forwardRef } from "react";
import { cn } from "@/lib/utils";

type Severity = "critical" | "high" | "medium" | "low" | "info" | "neutral";

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  severity?: Severity;
}

const severityStyles: Record<Severity, string> = {
  critical: "bg-danger-50 text-danger-800 dark:bg-danger-900 dark:text-danger-300",
  high: "bg-orange-50 text-orange-800 dark:bg-orange-900 dark:text-orange-300",
  medium: "bg-warning-50 text-warning-800 dark:bg-warning-900 dark:text-warning-300",
  low: "bg-success-50 text-success-800 dark:bg-success-900 dark:text-success-300",
  info: "bg-info-50 text-info-800 dark:bg-info-900 dark:text-info-300",
  neutral: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
};

export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ severity = "neutral", className, children, ...props }, ref) => (
    <span
      ref={ref}
      className={cn(
        "inline-flex items-center rounded-sm px-2 py-1 text-small font-medium",
        severityStyles[severity],
        className
      )}
      {...props}
    >
      {children}
    </span>
  )
);
Badge.displayName = "Badge";
