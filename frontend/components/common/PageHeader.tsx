"use client";

import type { ReactNode } from "react";

interface PageHeaderProps {
  title?: string;
  subtitle?: string;
  /** Optional back button rendered to the left of the title */
  backButton?: ReactNode;
  /** Optional health chip: "healthy" | "checking" | "error" */
  apiStatus?: "healthy" | "checking" | "error";
  /** Right-aligned slot for page-level actions */
  actions?: ReactNode;
  className?: string;
}

/**
 * Page-level heading rendered below the global navigation bar.
 *
 * Replaces the per-page `<Navigation title=... />` pattern: the nav bar is
 * mounted once in ClientLayout, and each page renders its own title here.
 * Renders nothing when no content is provided.
 */
export function PageHeader({
  title,
  subtitle,
  apiStatus,
  actions,
  backButton,
  className = "",
}: PageHeaderProps) {
  if (!title && !subtitle && !apiStatus && !actions && !backButton) {
    return null;
  }

  return (
    <div className={`max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6 pb-2 ${className}`}>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
        <div className="min-w-0">
          <div className="flex items-center gap-3">
            {backButton}
            {title && (
              <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-text-primary truncate">
                {title}
              </h1>
            )}
            {apiStatus && (
              <div className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-surface-card border border-border-subtle shadow-xs">
                <span
                  className={`w-2 h-2 rounded-full ${
                    apiStatus === "healthy"
                      ? "bg-emerald-500 animate-pulse"
                      : apiStatus === "checking"
                        ? "bg-amber-500 animate-pulse"
                        : "bg-rose-500"
                  }`}
                />
                <span className="text-[11px] font-medium text-text-secondary">
                  {apiStatus === "healthy"
                    ? "API Online"
                    : apiStatus === "checking"
                      ? "Checking..."
                      : "API Offline"}
                </span>
              </div>
            )}
          </div>
          {subtitle && (
            <p className="text-xs sm:text-sm text-text-secondary mt-1 max-w-2xl leading-relaxed">
              {subtitle}
            </p>
          )}
        </div>
        {actions && <div className="flex items-center gap-2.5 shrink-0">{actions}</div>}
      </div>
    </div>
  );
}
