"use client";

import { useEffect, useMemo, useState } from "react";
import { usePathname, Link } from "@/i18n/navigation";
import { useTranslations } from "next-intl";
import { ChevronDown, PanelLeftClose, PanelLeftOpen, ShieldCheck, X } from "lucide-react";

import { NAV_GROUPS, isVisible, isPathActive, type NavItem } from "@/lib/navigation";
import { isAdmin, isAnalystOrAdmin, loadAuthState, type User } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { useFocusTrap } from "@/hooks/useFocusTrap";
import { useRef } from "react";

const SIDEBAR_STORAGE_KEY = "sidebar-collapsed";
const GROUP_COLLAPSE_STORAGE_KEY = "sidebar-collapsed-groups";

function readCollapsed(): boolean {
  try {
    return localStorage.getItem(SIDEBAR_STORAGE_KEY) === "true";
  } catch {
    return false;
  }
}

function readCollapsedGroups(): Set<string> {
  try {
    const raw = localStorage.getItem(GROUP_COLLAPSE_STORAGE_KEY);
    if (!raw) return new Set<string>();
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) {
      return new Set<string>(parsed);
    }
  } catch {
    /* 隐私模式下静默降级 */
  }
  return new Set<string>();
}

function saveCollapsedGroups(groups: Set<string>) {
  try {
    const arr = Array.from(groups);
    localStorage.setItem(GROUP_COLLAPSE_STORAGE_KEY, JSON.stringify(arr));
    document.cookie = `sidebar_collapsed_groups=${encodeURIComponent(JSON.stringify(arr))}; path=/; max-age=2592000; SameSite=Lax`;
  } catch {
    /* 隐私模式下静默降级 */
  }
}

/** 折叠状态写回 localStorage + <html> 属性 + cookie，CSS 变量驱动宽度，避免 hydration 抖动。 */
export function setSidebarCollapsed(collapsed: boolean) {
  try {
    localStorage.setItem(SIDEBAR_STORAGE_KEY, String(collapsed));
    document.cookie = `sidebar_collapsed=${collapsed ? "true" : "false"}; path=/; max-age=2592000; SameSite=Lax`;
  } catch {
    /* 隐私模式下 localStorage 不可用时静默降级 */
  }
  document.documentElement.setAttribute("data-sidebar-collapsed", String(collapsed));
}

interface NavContentProps {
  onNavigate?: () => void;
  /** 折叠态下用图标居中布局 */
  collapsed: boolean;
  initialRole?: string | null;
  initialCollapsedGroups?: string[];
  isMounted?: boolean;
}

function useAuthFlags(initialRole?: string | null) {
  const [role, setRole] = useState<string | null>(initialRole ?? null);
  useEffect(() => {
    const user = loadAuthState()?.user;
    if (user?.role) {
      setRole(user.role);
      document.cookie = `user_role=${encodeURIComponent(user.role)}; path=/; max-age=2592000; SameSite=Lax`;
    } else if (!user) {
      setRole(null);
    }
  }, []);
  const userObj = role ? ({ role } as User) : null;
  return {
    admin: isAdmin(userObj),
    analyst: isAdmin(userObj) || isAnalystOrAdmin(userObj),
  };
}

function SidebarLink({
  item,
  label,
  active,
  collapsed,
  onNavigate,
}: {
  item: NavItem;
  label: string;
  active: boolean;
  collapsed: boolean;
  onNavigate?: () => void;
}) {
  const Icon = item.icon;
  const handleClick = (e: React.MouseEvent<HTMLAnchorElement>) => {
    if (active && (item.path === "/" || item.path === "")) {
      e.preventDefault();
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
    onNavigate?.();
  };

  return (
    <Link
      href={item.path}
      onClick={handleClick}
      aria-current={active ? "page" : undefined}
      title={label}
      className={cn(
        "group relative flex items-center gap-2.5 rounded-lg text-[13px] transition-colors duration-150",
        collapsed ? "justify-center h-9 w-9 mx-auto" : "h-9 px-2.5",
        active
          ? "bg-accent-50 text-accent-700 dark:bg-accent-950/40 dark:text-accent-300 font-semibold"
          : "text-text-secondary hover:text-text-primary hover:bg-surface-hover"
      )}
    >
      {active && (
        <span
          aria-hidden="true"
          className="absolute left-0 top-1/2 -translate-y-1/2 h-4 w-0.5 rounded-r bg-accent-600 dark:bg-accent-400"
        />
      )}
      <Icon
        className={cn(
          "h-4 w-4 shrink-0",
          active ? "text-accent-600 dark:text-accent-400" : "text-text-tertiary"
        )}
      />
      <span className="sidebar-label truncate flex-1 min-w-0">{label}</span>
      {!collapsed && item.badge && (
        <span className="sidebar-label shrink-0 ml-auto px-1.5 py-0.2 text-[10px] font-semibold tracking-wider uppercase rounded bg-severity-medium-bg text-severity-medium-fg border border-severity-medium-border">
          {item.badge}
        </span>
      )}
    </Link>
  );
}

function NavContent({
  onNavigate,
  collapsed,
  initialRole,
  initialCollapsedGroups = [],
  isMounted = true,
}: NavContentProps) {
  const pathname = usePathname();
  const t = useTranslations("navigation");
  const { admin, analyst } = useAuthFlags(initialRole);
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(
    () => new Set(initialCollapsedGroups)
  );

  // 初始化从 localStorage 载入用户折叠偏好
  useEffect(() => {
    const stored = readCollapsedGroups();
    if (stored.size > 0 || initialCollapsedGroups.length > 0) {
      setCollapsedGroups(stored);
    }
  }, []);

  const groups = useMemo(
    () =>
      NAV_GROUPS.map((group) => ({
        ...group,
        label: t(group.key as never),
        items: group.items.filter((item) => isVisible(item, admin, analyst)),
      })).filter((group) => group.items.length > 0),
    [t, admin, analyst]
  );

  // 路由跳转时，自动展开当前活跃页面所在的分组，防止用户在折叠菜单中迷失
  useEffect(() => {
    const activeGroup = groups.find((g) =>
      g.items.some((item) => isPathActive(pathname, item.path))
    );
    if (activeGroup) {
      setCollapsedGroups((prev) => {
        if (!prev.has(activeGroup.key)) return prev;
        const next = new Set(prev);
        next.delete(activeGroup.key);
        saveCollapsedGroups(next);
        return next;
      });
    }
  }, [pathname, groups]);

  const toggleGroup = (groupKey: string) => {
    setCollapsedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(groupKey)) {
        next.delete(groupKey);
      } else {
        next.add(groupKey);
      }
      saveCollapsedGroups(next);
      return next;
    });
  };

  return (
    <nav
      aria-label={t("mainNavigation")}
      className="sidebar-scrollbar flex-1 overflow-y-auto overflow-x-hidden px-2 py-3 space-y-2.5"
    >
      {groups.map((group) => {
        const isGroupCollapsed = !collapsed && collapsedGroups.has(group.key);
        const hasActiveItem = group.items.some((item) => isPathActive(pathname, item.path));

        return (
          <div key={group.key}>
            {!collapsed && (
              <button
                type="button"
                onClick={() => toggleGroup(group.key)}
                aria-expanded={!isGroupCollapsed}
                aria-controls={`sidebar-group-${group.key}`}
                title={group.label}
                className={cn(
                  "group/btn flex w-full items-center justify-between rounded-lg px-2.5 py-1.5 transition-colors duration-150 cursor-pointer select-none",
                  hasActiveItem && isGroupCollapsed
                    ? "bg-accent-50/80 dark:bg-accent-950/40"
                    : "hover:bg-surface-hover"
                )}
              >
                {/* 分组标题用排版层级区分，不再配图标：
                    小一档字号 + 字距 + 次级色，明确表达"这是一段的分隔"，
                    与 13px 的子项拉开层级；图标语汇完整留给子项。 */}
                <span
                  className={cn(
                    "sidebar-group-label truncate text-[11px] font-semibold uppercase tracking-[0.07em] transition-colors",
                    hasActiveItem && isGroupCollapsed
                      ? "text-accent-700 dark:text-accent-300"
                      : "text-text-tertiary group-hover/btn:text-text-secondary"
                  )}
                >
                  {group.label}
                </span>
                <ChevronDown
                  className={cn(
                    "ml-2 h-3.5 w-3.5 shrink-0 text-text-tertiary transition-transform duration-200 group-hover/btn:text-text-primary",
                    isGroupCollapsed && "-rotate-90"
                  )}
                  aria-hidden="true"
                />
              </button>
            )}
            {collapsed && <div className="mx-2 mb-2 h-px bg-border-subtle" aria-hidden="true" />}
            <div
              id={`sidebar-group-${group.key}`}
              className={cn(
                "grid",
                isMounted && "transition-all duration-200 ease-in-out",
                isGroupCollapsed ? "grid-rows-[0fr] opacity-0" : "grid-rows-[1fr] opacity-100"
              )}
            >
              <div
                className={cn(
                  "overflow-hidden space-y-0.5 pt-0.5",
                  !collapsed && "ml-3 pl-2 border-l border-border-subtle/80"
                )}
              >
                {group.items.map((item) => (
                  <SidebarLink
                    key={item.path}
                    item={item}
                    label={t(item.key as never)}
                    active={isPathActive(pathname, item.path)}
                    collapsed={collapsed}
                    onNavigate={onNavigate}
                  />
                ))}
              </div>
            </div>
          </div>
        );
      })}
    </nav>
  );
}

function SidebarBrand({
  collapsed,
  onToggle,
  isMounted = true,
}: {
  collapsed: boolean;
  onToggle: () => void;
  isMounted?: boolean;
}) {
  const tCommon = useTranslations("common");
  const collapseTitle = `${tCommon("collapse") || "收起侧边栏"} (⌘B)`;
  const expandTitle = `${tCommon("expand") || "展开侧边栏"} (⌘B)`;

  return (
    <div
      className={cn(
        "relative flex h-[var(--header-h)] shrink-0 items-center border-b border-border-subtle",
        isMounted && "transition-all duration-200",
        collapsed ? "justify-center px-2" : "justify-between px-3"
      )}
    >
      {collapsed ? (
        // 折叠态：居中品牌按钮，点击展开，Hover 时徽标变动为展开图标
        <button
          type="button"
          onClick={onToggle}
          aria-expanded={false}
          aria-label={tCommon("expand") || "展开侧边栏"}
          title={expandTitle}
          className="group relative flex h-9 w-9 items-center justify-center rounded-lg transition-colors hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-500/40 cursor-pointer"
        >
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-accent-600 text-white shadow-subtle transition-all duration-150 group-hover:scale-95 group-hover:opacity-0">
            <ShieldCheck className="h-4 w-4" />
          </div>
          <PanelLeftOpen className="absolute h-4 w-4 text-accent-600 dark:text-accent-400 opacity-0 transition-all duration-150 group-hover:opacity-100 group-hover:scale-110" />
        </button>
      ) : (
        // 展开态：左侧品牌 Logo + 标题，右侧优雅放置折叠按钮（主流大众规范）
        <>
          <Link
            href="/"
            onClick={(e) => {
              if (window.location.pathname === "/zh-CN" || window.location.pathname === "/en") {
                e.preventDefault();
                window.scrollTo({ top: 0, behavior: "smooth" });
              }
            }}
            className="flex items-center gap-2.5 min-w-0 transition-opacity hover:opacity-85"
          >
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-accent-600 text-white shadow-subtle">
              <ShieldCheck className="h-4 w-4" />
            </div>
            <span className="sidebar-label truncate text-sm font-semibold tracking-tight text-text-primary">
              SOC Copilot
            </span>
          </Link>

          <button
            type="button"
            onClick={onToggle}
            aria-expanded={true}
            aria-label={tCommon("collapse") || "收起侧边栏"}
            title={collapseTitle}
            className="sidebar-label flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-text-muted transition-colors hover:bg-surface-hover hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-500/40 cursor-pointer"
          >
            <PanelLeftClose className="h-4 w-4" />
          </button>
        </>
      )}
    </div>
  );
}

interface SidebarProps {
  initialRole?: string | null;
  initialCollapsed?: boolean;
  initialCollapsedGroups?: string[];
}

/** 桌面端固定侧栏。宽度由 --sidebar-w 驱动，折叠只留图标。 */
export function Sidebar({
  initialRole = null,
  initialCollapsed = false,
  initialCollapsedGroups = [],
}: SidebarProps) {
  const [collapsed, setCollapsed] = useState(initialCollapsed);
  const [isMounted, setIsMounted] = useState(false);

  // 首屏由 layout.tsx 的内联脚本设置属性，这里同步一次以对齐按钮图标状态。
  useEffect(() => {
    setIsMounted(true);
    const stored = readCollapsed();
    if (stored !== collapsed) {
      setCollapsed(stored);
    }
  }, []);

  const toggle = () => {
    const next = !collapsed;
    setCollapsed(next);
    setSidebarCollapsed(next);
  };

  // 全局快捷键 ⌘B / Ctrl+B 切换侧边栏展开与折叠
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && (e.key === "b" || e.key === "B")) {
        const target = e.target as HTMLElement | null;
        if (
          target?.tagName === "INPUT" ||
          target?.tagName === "TEXTAREA" ||
          target?.isContentEditable
        ) {
          return;
        }
        e.preventDefault();
        const next = !collapsed;
        setCollapsed(next);
        setSidebarCollapsed(next);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [collapsed]);

  return (
    <aside
      className={cn(
        "group/sidebar fixed inset-y-0 left-0 z-30 hidden w-[var(--sidebar-w)] flex-col border-r border-border-subtle bg-surface-card lg:flex",
        isMounted && "transition-[width] duration-200"
      )}
      style={{ height: "100dvh" }}
    >
      <SidebarBrand collapsed={collapsed} onToggle={toggle} isMounted={isMounted} />
      <NavContent
        collapsed={collapsed}
        initialRole={initialRole}
        initialCollapsedGroups={initialCollapsedGroups}
        isMounted={isMounted}
      />
    </aside>
  );
}

interface MobileNavDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  initialRole?: string | null;
  initialCollapsedGroups?: string[];
}

/** 移动端抽屉。与桌面侧栏共用 NAV_GROUPS，不再维护第二份列表。 */
export function MobileNavDrawer({
  isOpen,
  onClose,
  initialRole = null,
  initialCollapsedGroups = [],
}: MobileNavDrawerProps) {
  const drawerRef = useRef<HTMLDivElement>(null);
  useFocusTrap(isOpen, onClose, drawerRef);
  const tCommon = useTranslations("common");

  useEffect(() => {
    if (!isOpen) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, [isOpen]);

  return (
    <>
      <div
        className={cn(
          "fixed inset-0 z-[200] bg-black/50 transition-opacity duration-200",
          isOpen ? "opacity-100" : "pointer-events-none opacity-0"
        )}
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        ref={drawerRef}
        role="dialog"
        aria-modal="true"
        aria-label={tCommon("mainMenu")}
        tabIndex={-1}
        className={cn(
          "group/sidebar fixed inset-y-0 left-0 z-[201] flex w-[260px] max-w-[85vw] flex-col border-r border-border-subtle bg-surface-card transition-transform duration-200 ease-out lg:hidden",
          isOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex h-[var(--header-h)] shrink-0 items-center justify-between border-b border-border-subtle px-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-accent-600 text-white">
              <ShieldCheck className="h-4 w-4" />
            </div>
            <span className="text-sm font-semibold tracking-tight text-text-primary">
              SOC Copilot
            </span>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label={tCommon("close")}
            className="rounded-lg p-2 text-text-tertiary transition-colors hover:bg-surface-hover hover:text-text-primary"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <NavContent
          collapsed={false}
          onNavigate={onClose}
          initialRole={initialRole}
          initialCollapsedGroups={initialCollapsedGroups}
          isMounted={true}
        />
      </div>
    </>
  );
}
