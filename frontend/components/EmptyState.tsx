"use client";

import React, { ReactNode } from "react";
import { FileText, AlertTriangle, Search, Inbox } from "lucide-react";
import { Heading, Text } from "@/components/ui/Typography";
import { cn } from "@/lib/utils";

interface EmptyStateProps {
  icon?: "file" | "alert" | "search" | "inbox" | "custom";
  title: string;
  description?: string;
  action?: ReactNode;
  customIcon?: ReactNode;
  className?: string;
}

const ICONS = {
  file: FileText,
  alert: AlertTriangle,
  search: Search,
  inbox: Inbox,
};

const EmptyState = React.memo(function EmptyState({
  icon = "inbox",
  title,
  description,
  action,
  customIcon,
  className,
}: EmptyStateProps) {
  const iconName = icon !== "custom" ? icon : "inbox";
  const IconComponent = !customIcon ? ICONS[iconName] : null;

  return (
    <div
      className={cn("flex flex-col items-center justify-center py-12 px-4 text-center", className)}
    >
      {customIcon ? (
        <div className="mb-4 opacity-15">{customIcon}</div>
      ) : (
        IconComponent && (
          <div className="mb-4 opacity-15">
            <IconComponent
              className="w-16 h-16 text-slate-900 dark:text-slate-100"
              strokeWidth={1.5}
            />
          </div>
        )
      )}

      <Heading level={3} color="primary" className="text-base mb-1">
        {title}
      </Heading>

      {description && (
        <Text color="tertiary" className="text-sm max-w-sm mb-4">
          {description}
        </Text>
      )}

      {action && <div className="mt-2">{action}</div>}
    </div>
  );
});

export { EmptyState };
