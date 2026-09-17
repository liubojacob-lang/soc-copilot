"use client";

import { useEffect, useState, useMemo } from "react";
import { useRouter, Link, usePathname } from "@/i18n/navigation";
import { loadAuthState, logout, type User } from "@/lib/auth";
import { Menu, ShieldCheck, Search } from "lucide-react";
import { useTranslations } from "next-intl";
import { useDashboardStats } from "@/hooks/useDashboard";
import { useHeader } from "./providers/HeaderProvider";
import { ALL_NAV_ITEMS } from "@/lib/navigation";

import { LanguageSwitcher } from "./LanguageSwitcher";
import { ThemeToggle } from "./ThemeToggle";
import { UserMenu } from "./UserMenu";
import Breadcrumbs from "@/components/common/Breadcrumbs";

interface NavigationProps {
  /** 保留给需要展示后端连通性的页面；不传则不渲染状态点。 */
  apiStatus?: "healthy" | "checking" | "error";
  actions?: React.ReactNode;
  onOpenMobileNav?: () => void;
}

/**
 * 顶部 Header。
 *
 * 职责边界：只放全局能力（品牌 / 面包屑 / 搜索 / 状态 / 语言 / 主题 / 用户）。
 * 主导航已迁至 `components/layout/Sidebar.tsx`，这里不再内联任何导航列表。
 */
export default function Navigation({ apiStatus, actions, onOpenMobileNav }: NavigationProps) {
  const router = useRouter();
  const pathname = usePathname();
  const t = useTranslations("navigation");
  const tHome = useTranslations("home");
  const tCommon = useTranslations("common");
  const [user, setUser] = useState<User | null>(null);

  const headerCtx = useHeader();
  const headerData = headerCtx?.headerData;

  const isHome = !pathname || pathname === "/" || pathname === "";

  // 首页连通性探测（复用 React Query 缓存，零额外开销）
  const { isLoading: statsLoading, isError: statsError } = useDashboardStats({ enabled: isHome });

  const effectiveApiStatus =
    headerData?.apiStatus ??
    apiStatus ??
    (isHome ? (statsLoading ? "checking" : statsError ? "error" : "healthy") : undefined);

  // 尝试匹配注册路由作为 fallback 标题
  const registeredNav = useMemo(
    () => (pathname ? ALL_NAV_ITEMS.find((item) => item.path === pathname) : undefined),
    [pathname]
  );

  const displayTitle =
    headerData?.title ||
    (isHome ? tHome("securityOperations") : registeredNav ? t(registeredNav.key as never) : null);

  const effectiveActions = headerData?.actions || actions;

  useEffect(() => {
    setUser(loadAuthState()?.user ?? null);
  }, []);

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  const statusLabel =
    effectiveApiStatus === "healthy"
      ? "API Online"
      : effectiveApiStatus === "checking"
        ? t("checking") || "Checking..."
        : t("statusError") || "API Offline";

  const statusDotClass =
    effectiveApiStatus === "healthy"
      ? "bg-emerald-500 animate-pulse"
      : effectiveApiStatus === "checking"
        ? "bg-amber-500 animate-pulse"
        : "bg-rose-500";

  return (
    <header className="sticky top-0 z-40 h-[var(--header-h)] border-b border-border-subtle bg-surface-card">
      <div className="flex h-full items-center gap-3 px-4 sm:px-6">
        <button
          type="button"
          onClick={onOpenMobileNav}
          aria-label={tCommon("mainMenu")}
          className="-ml-1 rounded-lg p-2 text-text-secondary transition-colors hover:bg-surface-hover hover:text-text-primary lg:hidden"
        >
          <Menu className="h-5 w-5" />
        </button>

        {/* 桌面端由侧栏承载品牌，这里只保留面包屑；移动端显示品牌 */}
        <Link
          href="/"
          onClick={(e) => {
            if (isHome) {
              e.preventDefault();
              window.scrollTo({ top: 0, behavior: "smooth" });
            }
          }}
          className="flex items-center gap-2 text-text-primary transition-transform active:scale-[0.98] lg:hidden"
        >
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-accent-600 text-white">
            <ShieldCheck className="h-4 w-4" />
          </div>
          <span className="text-sm font-semibold tracking-tight">SOC Copilot</span>
        </Link>

        {/* 桌面端：优先显示当前页面标题/状态；深层嵌套页面显示面包屑 */}
        <div className="hidden min-w-0 flex-1 lg:flex items-center gap-3">
          {displayTitle ? (
            <div className="flex items-center gap-2.5 min-w-0">
              {headerData?.backButton}
              {isHome ? (
                <button
                  type="button"
                  onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
                  className="text-sm font-semibold text-text-primary tracking-tight truncate hover:opacity-80 transition-opacity cursor-pointer text-left"
                >
                  {displayTitle}
                </button>
              ) : (
                <span className="text-sm font-semibold text-text-primary tracking-tight truncate">
                  {displayTitle}
                </span>
              )}
              {headerData?.badge}
              {effectiveApiStatus && (
                <div
                  className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-surface-card border border-border-subtle shadow-subtle shrink-0"
                  title={statusLabel}
                >
                  <span
                    className={`h-2 w-2 shrink-0 rounded-full ${statusDotClass}`}
                    aria-hidden="true"
                  />
                  <span className="text-[11px] font-medium text-text-secondary">{statusLabel}</span>
                </div>
              )}
            </div>
          ) : (
            <Breadcrumbs />
          )}
        </div>
        <div className="flex-1 lg:hidden" />

        <div className="flex shrink-0 items-center gap-2">
          {effectiveActions}

          {apiStatus && !isHome && !headerData?.apiStatus && (
            <div
              className="hidden items-center gap-1.5 rounded-full border border-border-subtle bg-surface-hover px-2 py-1 sm:flex"
              title={statusLabel}
            >
              <span
                className={`h-2 w-2 shrink-0 rounded-full ${statusDotClass}`}
                aria-hidden="true"
              />
              <span className="text-[10px] font-semibold text-text-secondary">{statusLabel}</span>
            </div>
          )}

          <button
            type="button"
            onClick={() => {
              document.dispatchEvent(new KeyboardEvent("keydown", { key: "k", metaKey: true }));
            }}
            className="inline-flex h-8 items-center gap-2 rounded-lg border border-border-subtle bg-surface-hover px-2.5 text-xs text-text-secondary shadow-subtle transition-colors hover:text-text-primary"
            aria-label={tCommon("search")}
          >
            <Search className="h-3.5 w-3.5" />
            <span className="hidden xl:inline">{tCommon("search")}</span>
            <kbd className="rounded border border-border-subtle bg-surface-card px-1 py-0.5 font-mono text-[10px] leading-none text-text-tertiary">
              ⌘K
            </kbd>
          </button>

          <LanguageSwitcher />
          <ThemeToggle />

          {user && (
            <UserMenu
              user={user}
              onLogout={handleLogout}
              getRoleBadgeClass={(role: string) =>
                role === "admin"
                  ? "bg-ai-bg text-ai-fg border border-ai-border"
                  : role === "analyst"
                    ? "bg-status-investigating-bg text-status-investigating-fg border border-status-investigating-border"
                    : role === "auditor"
                      ? "bg-status-active-bg text-status-active-fg border border-status-active-border"
                      : "bg-severity-neutral-bg text-severity-neutral-fg border border-severity-neutral-border"
              }
            />
          )}
        </div>
      </div>
    </header>
  );
}
