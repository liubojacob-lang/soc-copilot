"use client";

import { useCallback } from "react";
import { useRouter } from "@/i18n/navigation";
import { useTranslations } from "next-intl";
import { ArrowLeft } from "lucide-react";
import { cn } from "@/lib/utils";

export interface BackButtonProps {
  /**
   * Fallback URL when there is no browser history within the app.
   * e.g. "/alerts", "/playbooks?tab=runs", "/playbooks?tab=definitions"
   */
  fallbackUrl: string;
  /**
   * Optional custom button label. Defaults to localized "返回" / "Back".
   */
  label?: string;
  /**
   * Additional custom CSS classes.
   */
  className?: string;
  /**
   * Visual style variant:
   * - "pill": rounded card button with icon + text (default across all detail pages)
   * - "icon": icon-only button with tooltip
   * - "ghost": minimal transparent button with icon + text
   */
  variant?: "pill" | "icon" | "ghost";
  /**
   * Button size: "sm" (default, matching page headers) | "md"
   */
  size?: "sm" | "md";
  /**
   * Optional callback to execute before navigating back.
   */
  onClick?: () => void;
}

/**
 * Standardized Back Navigation Button for all Detail Views (Alerts, Playbooks, Cases, etc.)
 *
 * Provides:
 * 1. Consistent visual hierarchy (pill button, subtle border, smooth hover micro-interaction)
 * 2. Intelligent routing:
 *    - Uses `router.back()` if internal page history exists (preserves filters, search, pagination & tabs)
 *    - Safely falls back to `fallbackUrl` if opened in a fresh tab, refreshed, or from external referrer
 * 3. Complete i18n support & WCAG-compliant accessibility (keyboard focus, aria-label)
 */
export function BackButton({
  fallbackUrl,
  label,
  className,
  variant = "pill",
  size = "sm",
  onClick,
}: BackButtonProps) {
  const router = useRouter();
  const tCommon = useTranslations("common");

  const handleBack = useCallback(
    (e?: React.MouseEvent) => {
      e?.preventDefault();
      if (onClick) {
        onClick();
      }

      if (typeof window !== "undefined") {
        const hasInternalReferrer =
          Boolean(document.referrer) && document.referrer.startsWith(window.location.origin);
        const hasHistory = window.history.length > 1;

        if (hasInternalReferrer || hasHistory) {
          router.back();
          return;
        }
      }

      router.push(fallbackUrl);
    },
    [router, fallbackUrl, onClick]
  );

  const buttonText = label ?? tCommon("back");

  if (variant === "icon") {
    return (
      <button
        type="button"
        onClick={handleBack}
        className={cn(
          "group inline-flex items-center justify-center p-2 rounded-xl border border-border-subtle bg-surface-card hover:bg-surface-hover hover:border-border-default active:bg-surface-active text-text-secondary hover:text-text-primary shadow-subtle transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-500/40 select-none",
          className
        )}
        title={buttonText}
        aria-label={buttonText}
      >
        <ArrowLeft className="w-4 h-4 transition-transform duration-150 group-hover:-translate-x-0.5" />
      </button>
    );
  }

  if (variant === "ghost") {
    return (
      <button
        type="button"
        onClick={handleBack}
        className={cn(
          "group inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-text-secondary hover:text-text-primary hover:bg-surface-hover active:bg-surface-active text-xs font-medium transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-500/40 select-none",
          size === "md" && "px-3 py-2 text-sm",
          className
        )}
        title={buttonText}
        aria-label={buttonText}
      >
        <ArrowLeft className="w-3.5 h-3.5 shrink-0 transition-transform duration-150 group-hover:-translate-x-0.5" />
        <span>{buttonText}</span>
      </button>
    );
  }

  return (
    <button
      type="button"
      onClick={handleBack}
      className={cn(
        "group inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-border-subtle bg-surface-card hover:bg-surface-hover hover:border-border-default active:bg-surface-active text-text-secondary hover:text-text-primary text-xs font-medium shadow-subtle transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-500/40 select-none",
        size === "md" && "px-3.5 py-2 text-sm",
        className
      )}
      title={buttonText}
      aria-label={buttonText}
    >
      <ArrowLeft className="w-3.5 h-3.5 shrink-0 transition-transform duration-150 group-hover:-translate-x-0.5" />
      <span>{buttonText}</span>
    </button>
  );
}
