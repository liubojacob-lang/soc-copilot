"use client";

import { cn } from "@/lib/utils";
import { Caption } from "@/components/ui/Typography";

interface TimeDisplayProps {
  value: string | Date | number;
  className?: string;
}

/**
 * 将输入值格式化为 YYYY-MM-DD HH:mm
 */
function formatTimestamp(value: string | Date | number): string {
  const date = typeof value === "string" ? new Date(value) : new Date(value);
  if (Number.isNaN(date.getTime())) return "--";

  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  const hour = String(date.getHours()).padStart(2, "0");
  const minute = String(date.getMinutes()).padStart(2, "0");

  return `${year}-${month}-${day} ${hour}:${minute}`;
}

export function TimeDisplay({ value, className }: TimeDisplayProps) {
  return (
    <Caption color="tertiary" className={cn("text-xs text-slate-400", className)}>
      {formatTimestamp(value)}
    </Caption>
  );
}
