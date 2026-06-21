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
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "group relative flex items-center gap-2 px-4 py-2 transition-colors duration-200",
        "border-b-2",
        active ? "border-slate-900 dark:border-white" : "border-transparent",
        disabled && "opacity-50 cursor-not-allowed",
        className
      )}
    >
      {icon}
      <Caption
        className={cn(
          "font-medium",
          active
            ? "text-text-primary dark:text-white"
            : "text-text-tertiary group-hover:text-text-secondary dark:text-slate-400 dark:group-hover:text-slate-200"
        )}
      >
        {label}
      </Caption>
      {badge !== undefined && (
        <Badge severity={badgeSeverity} className="ml-1">
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
