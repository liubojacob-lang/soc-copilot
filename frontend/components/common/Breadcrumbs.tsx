"use client";

import { useRouter, usePathname } from "@/i18n/navigation";
import { useTranslations } from "next-intl";
import { Home } from "lucide-react";
import { useMemo } from "react";
import { Caption } from "@/components/ui/Typography";

interface BreadcrumbItem {
  label: string;
  path: string;
  isCurrent: boolean;
}

interface BreadcrumbsProps {
  className?: string;
  maxItems?: number;
  showHome?: boolean;
}

export default function Breadcrumbs({
  className = "",
  maxItems = 5,
  showHome = true,
}: BreadcrumbsProps) {
  const router = useRouter();
  const pathname = usePathname();
  const t = useTranslations("breadcrumbs");
  const tNav = useTranslations("nav");
  const tCommon = useTranslations("common");

  const items = useMemo(() => {
    if (!pathname) return [];

    const segments = pathname.split("/").filter(Boolean);
    const breadcrumbs: BreadcrumbItem[] = [];

    // Add home if enabled
    if (showHome) {
      breadcrumbs.push({
        label: tNav("home"),
        path: "/",
        isCurrent: segments.length === 0,
      });
    }

    // Build breadcrumb items from path segments
    let currentPath = "";
    segments.forEach((segment, index) => {
      currentPath += `/${segment}`;
      const isLast = index === segments.length - 1;

      // Get label from translations, fallback to formatted segment
      let label =
        t(segment as Parameters<typeof t>[0]) ||
        tNav(segment as Parameters<typeof tNav>[0]) ||
        tCommon(segment as Parameters<typeof tCommon>[0]);
      if (!label || label === segment) {
        // Check if it's an ID (UUID pattern or numeric)
        if (/^[a-f0-9-]{36}$/i.test(segment) || /^\d+$/.test(segment)) {
          label = `ID: ${segment.slice(0, 8)}...`;
        } else {
          // Format segment as title case
          label = segment
            .split(/-/g)
            .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
            .join(" ");
        }
      }

      breadcrumbs.push({
        label,
        path: currentPath,
        isCurrent: isLast,
      });
    });

    return breadcrumbs;
  }, [pathname, showHome]);

  // Handle truncation for long paths
  const displayItems = useMemo(() => {
    if (items.length <= maxItems) return items;

    // Keep first and last items, truncate middle
    const first = items[0];
    const last = items[items.length - 1];
    const middleCount = maxItems - 2;
    const middleStart = Math.max(1, items.length - 1 - middleCount);

    const truncated: (BreadcrumbItem | null)[] = [first];

    // Add ellipsis indicator
    if (middleStart > 1) {
      truncated.push(null); // null represents ellipsis
    }

    // Add middle items
    for (let i = middleStart; i < items.length - 1; i++) {
      truncated.push(items[i]);
    }

    truncated.push(last);

    return truncated;
  }, [items, maxItems]);

  if (items.length <= 1) return null;

  return (
    <nav aria-label="Breadcrumb" className={`flex items-center ${className}`}>
      <ol className="flex items-center flex-wrap gap-1">
        {displayItems.map((item, index) => {
          // Handle ellipsis
          if (item === null) {
            return (
              <li key={`ellipsis-${index}`} className="flex items-center">
                <Caption className="text-sm text-slate-400 dark:text-slate-500">...</Caption>
                <span className="mx-1 text-slate-400 dark:text-slate-500">/</span>
              </li>
            );
          }

          const isLast = index === displayItems.length - 1;

          return (
            <li key={item.path} className="flex items-center">
              {index > 0 && <span className="mx-1 text-slate-400 dark:text-slate-500">/</span>}
              {isLast ? (
                <Caption
                  color="primary"
                  className="text-sm font-medium dark:text-white truncate max-w-[150px]"
                  aria-current="page"
                >
                  {item.label}
                </Caption>
              ) : (
                <button
                  onClick={() => router.push(item.path)}
                  className="transition-colors truncate max-w-[100px] flex items-center gap-1"
                >
                  <Caption
                    color="tertiary"
                    className="text-sm dark:text-slate-400 flex items-center gap-1"
                  >
                    {index === 0 && showHome && <Home className="w-5 h-5 text-slate-500" />}
                    {item.label}
                  </Caption>
                </button>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
