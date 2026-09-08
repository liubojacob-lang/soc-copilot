"use client";

import { type ReactNode } from "react";
import { cn } from "@/lib/utils";
import { Caption } from "./Typography";
import { Badge } from "./Badge";

export interface TabButtonProps {
  active?: boolean;
  onClick?: () => void;
  disabled?: boolean;
  label: string;
  icon?: ReactNode;
  className?: string;
  badge?: number;
  badgeSeverity?: "critical" | "high" | "medium" | "low" | "info" | "neutral";
}

export function TabButton({
  active = false,
  onClick,
  disabled = false,
  label,
  icon,
  className,
  badge,
  badgeSeverity = "neutral",
}: TabButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "group relative flex items-center gap-2 px-3.5 py-2.5 text-xs sm:text-sm font-medium transition-all duration-150 select-none",
        "border-b-2 -mb-px",
        active
          ? "border-accent-600 text-accent-600 dark:border-accent-400 dark:text-accent-300 font-semibold"
          : "border-transparent text-text-tertiary hover:text-text-primary hover:border-border-default",
        disabled && "opacity-40 cursor-not-allowed",
        className
      )}
    >
      {icon && <span className="inline-flex shrink-0">{icon}</span>}
      <span>{label}</span>
      {badge !== undefined && (
        <Badge severity={badgeSeverity} size="xs" variant="pill" className="ml-1">
          {badge}
        </Badge>
      )}
    </button>
  );
}

export interface TabListProps {
  children: ReactNode;
  className?: string;
}

export function TabList({ children, className }: TabListProps) {
  return (
    <nav
      className={cn("flex gap-2 border-b border-border-subtle dark:border-slate-700", className)}
    >
      {children}
    </nav>
  );
}
