"use client";

import { useMemo } from "react";
import { usePathname, Link } from "@/i18n/navigation";
import { useTranslations } from "next-intl";
import { Home, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

import { ALL_NAV_ITEMS } from "@/lib/navigation";

interface BreadcrumbItem {
  label: string;
  path: string;
  isCurrent: boolean;
}

interface BreadcrumbsProps {
  className?: string;
  showHome?: boolean;
  /**
   * 仅在深层嵌套页面（详情页/编辑页/子路由）展示面包屑。
   * 默认 true：主菜单直达页面（如 /monitor, /alerts, /cases 等）自动隐藏，避免与侧栏和主标题三重重复。
   */
  onlyOnNested?: boolean;
}

const ID_SEGMENT = /^[a-f0-9-]{36}$|^\d+$/i;

/**
 * 面包屑。
 *
 * 标签优先从 `lib/navigation.ts` 的注册路由取（复用侧栏同一份 i18n key），
 * 取不到才降级为路径片段格式化 —— 避免出现 "Threat Intel" 与 "Threat intel" 两种写法。
 */
export default function Breadcrumbs({
  className,
  showHome = true,
  onlyOnNested = true,
}: BreadcrumbsProps) {
  const pathname = usePathname();
  const t = useTranslations("navigation");
  const tCommon = useTranslations("common");

  // 判断是否为侧边栏直达的一级/主菜单路由
  const isPrimaryNavPage = useMemo(() => {
    if (!pathname || pathname === "/") return true;
    return ALL_NAV_ITEMS.some((item) => item.path === pathname);
  }, [pathname]);

  const items = useMemo<BreadcrumbItem[]>(() => {
    if (!pathname) return [];

    // 若开启 onlyOnNested 模式，主菜单直达路由不显示面包屑，保持顶栏通透极简
    if (onlyOnNested && isPrimaryNavPage) return [];

    const segments = pathname.split("/").filter(Boolean);
    // 至少需要 2 个路径段（如 /alerts/123 或 /playbooks/definitions/create）才构成具有回溯价值的面包屑
    if (onlyOnNested && segments.length < 2) return [];
    if (segments.length === 0) return [];

    const result: BreadcrumbItem[] = [];
    if (showHome) {
      result.push({ label: t("home"), path: "/", isCurrent: false });
    }

    let currentPath = "";
    segments.forEach((segment, index) => {
      currentPath += `/${segment}`;
      const isLast = index === segments.length - 1;

      if (ID_SEGMENT.test(segment)) {
        // 详情页：用短 ID 代替不可读的 UUID，避免撑破布局
        result.push({ label: `#${segment.slice(0, 8)}`, path: currentPath, isCurrent: isLast });
        return;
      }

      const registered = ALL_NAV_ITEMS.find((item) => item.path === currentPath);
      if (registered) {
        result.push({ label: t(registered.key as never), path: currentPath, isCurrent: isLast });
        return;
      }

      result.push({
        label: segment
          .split("-")
          .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
          .join(" "),
        path: currentPath,
        isCurrent: isLast,
      });
    });

    return result;
  }, [pathname, showHome, onlyOnNested, isPrimaryNavPage, t]);

  if (items.length === 0) return null;

  return (
    <nav aria-label={tCommon("breadcrumb")} className={cn("min-w-0", className)}>
      <ol className="flex min-w-0 items-center gap-1 text-xs">
        {items.map((item, index) => {
          const isLast = index === items.length - 1;
          return (
            <li key={item.path} className="flex min-w-0 items-center gap-1">
              {index > 0 && (
                <ChevronRight
                  className="h-3.5 w-3.5 shrink-0 text-text-disabled"
                  aria-hidden="true"
                />
              )}
              {isLast ? (
                <span
                  aria-current="page"
                  className="truncate font-medium text-text-primary"
                  title={item.label}
                >
                  {item.label}
                </span>
              ) : (
                <Link
                  href={item.path}
                  className="flex min-w-0 items-center gap-1 rounded px-1 py-0.5 text-text-tertiary transition-colors hover:bg-surface-hover hover:text-text-primary"
                >
                  {index === 0 && showHome && <Home className="h-3.5 w-3.5 shrink-0" />}
                  <span className="truncate">{item.label}</span>
                </Link>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
