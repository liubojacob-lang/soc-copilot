"use client";

import { useEffect, type ReactNode } from "react";
import { useHeader } from "@/components/providers/HeaderProvider";

export interface PageHeaderProps {
  title?: ReactNode;
  subtitle?: ReactNode;
  /** Optional badge or pill counter rendered next to the title */
  badge?: ReactNode;
  /** Optional back button rendered to the left of the title */
  backButton?: ReactNode;
  /** Optional health chip: "healthy" | "checking" | "error" */
  apiStatus?: "healthy" | "checking" | "error";
  /** Right-aligned slot for page-level actions */
  actions?: ReactNode;
  className?: string;
  /** Force rendering inside page content instead of elevating to top navbar */
  inline?: boolean;
}

/**
 * Page-level heading component.
 *
 * By default, PageHeader elevates the title, badge, apiStatus, actions and backButton
 * directly into the top global navigation header (via HeaderProvider), eliminating
 * double-headers and saving ~90px of vertical space across all pages.
 *
 * To force rendering inline in the page content, pass `inline={true}`.
 */
export function PageHeader({
  title,
  subtitle,
  badge,
  apiStatus,
  actions,
  backButton,
  className = "",
  inline = false,
}: PageHeaderProps) {
  const headerCtx = useHeader();
  const setHeaderData = headerCtx?.setHeaderData;
  const resetHeaderData = headerCtx?.resetHeaderData;

  useEffect(() => {
    if (inline || !setHeaderData) return;

    setHeaderData({
      title,
      subtitle,
      badge,
      apiStatus,
      actions,
      backButton,
    });
  }, [title, subtitle, badge, apiStatus, actions, backButton, inline, setHeaderData]);

  // Reset header data ONLY when unmounting
  useEffect(() => {
    if (inline || !resetHeaderData) return;
    return () => {
      resetHeaderData();
    };
  }, [inline, resetHeaderData]);

  if (!inline) {
    return null;
  }

  if (!title && !subtitle && !apiStatus && !actions && !backButton && !badge) {
    return null;
  }

  return (
    <div className={`max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 pt-6 pb-2 ${className}`}>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2.5">
            {backButton}
            {title && (
              <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-text-primary truncate">
                {title}
              </h1>
            )}
            {badge}
            {apiStatus && (
              <div className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-surface-card border border-border-subtle shadow-subtle">
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
