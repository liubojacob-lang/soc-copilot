"use client";

import type { ReactNode } from "react";

interface PageHeaderProps {
  title?: string;
  subtitle?: string;
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
  className = "",
}: PageHeaderProps) {
  if (!title && !subtitle && !apiStatus && !actions) {
    return null;
  }

  return (
    <div className={`max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6 pb-2 ${className}`}>
      <div className="flex items-start justify-between gap-4 mb-4">
        <div className="min-w-0">
          <div className="flex items-center gap-3">
            {title && (
              <h1 className="text-xl font-semibold text-gray-900 dark:text-white truncate">
                {title}
              </h1>
            )}
            {apiStatus && (
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-gray-100 dark:bg-gray-700/50">
                <span
                  className={`w-2 h-2 rounded-full ${
                    apiStatus === "healthy"
                      ? "bg-success-500 animate-pulse-soft"
                      : apiStatus === "checking"
                        ? "bg-warning-500 animate-pulse-soft"
                        : "bg-danger-500"
                  }`}
                />
                <span className="text-[11px] font-semibold text-gray-600 dark:text-gray-300">
                  {apiStatus === "healthy" ? "API OK" : apiStatus === "checking" ? "..." : "Err"}
                </span>
              </div>
            )}
          </div>
          {subtitle && (
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{subtitle}</p>
          )}
        </div>
        {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
      </div>
    </div>
  );
}
