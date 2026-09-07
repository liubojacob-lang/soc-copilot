"use client";

import { useRouter, usePathname, Link } from "@/i18n/navigation";
import { loadAuthState, logout, isAdmin, isAnalystOrAdmin } from "@/lib/auth";
import { useState, useRef, useEffect, useMemo, useCallback } from "react";
import { useLocale } from "next-intl";
import {
  Menu,
  X,
  ChevronDown,
  ShieldCheck,
  Bot,
  Globe,
  Network,
  Fingerprint,
  Crosshair,
  Store,
  Cloud,
  Server,
  Zap,
  LayoutDashboard,
  Settings,
  Cpu,
  KeyRound,
  ScrollText,
  Users,
  Search,
} from "lucide-react";
import { LanguageSwitcher } from "./LanguageSwitcher";
import { ThemeToggle } from "./ThemeToggle";
import { useTranslations } from "next-intl";

interface NavigationProps {
  title?: string;
  subtitle?: string;
  apiStatus?: "healthy" | "checking" | "error";
  actions?: React.ReactNode;
}

interface NavItem {
  label: string;
  description?: string;
  path: string;
  icon?: React.ReactNode;
  badge?: string;
}

interface NavGroup {
  label: string;
  badge?: string;
  icon?: React.ReactNode;
  items: NavItem[];
}

export default function Navigation({ title, subtitle, apiStatus, actions }: NavigationProps) {
  const router = useRouter();
  const pathname = usePathname();
  const locale = useLocale();
  const t = useTranslations("navigation");
  const tCommon = useTranslations("common");
  const [mounted, setMounted] = useState(false);
  const [authState, setAuthState] = useState<ReturnType<typeof loadAuthState>>(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [hoveredDropdown, setHoveredDropdown] = useState<string | null>(null);
  const dropdownTimeoutRef = useRef<NodeJS.Timeout | undefined>(undefined);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setMounted(true);
    setAuthState(loadAuthState());
  }, []);

  const user = authState?.user;

  // English labels are much wider than Chinese ones and would overflow the
  // fixed max-w-7xl container, so English gets tighter padding/tracking. Both
  // locales share the same 13px nav font so switching languages doesn't jump.
  const compactNav = locale !== "zh-CN";
  const navTriggerClass = compactNav
    ? "px-1.5 xl:px-2 py-1.5 xl:py-2 text-xs xl:text-[13px] tracking-tight rounded-xl whitespace-nowrap shrink-0 transition-all duration-200"
    : "px-2 xl:px-3 py-1.5 xl:py-2 text-xs xl:text-[13px] rounded-xl whitespace-nowrap shrink-0 transition-all duration-200";

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setHoveredDropdown(null);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    return () => {
      if (dropdownTimeoutRef.current) {
        clearTimeout(dropdownTimeoutRef.current);
      }
    };
  }, []);

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  const getRoleBadgeClass = useCallback((role: string) => {
    switch (role) {
      case "admin":
        return "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300";
      case "analyst":
        return "bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300";
      case "auditor":
        return "bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-300";
      default:
        return "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300";
    }
  }, []);

  const mainNavItems: NavItem[] = useMemo(
    () => [
      { label: t("home"), path: "/" },
      { label: t("monitor"), path: "/monitor" },
      { label: t("cases"), path: "/cases" },
      { label: t("alerts"), path: "/alerts" },
      { label: t("playbooks"), path: "/playbooks" },
    ],
    [t]
  );

  const analyticsGroup: NavGroup = useMemo(
    () => ({
      label: t("analytics"),
      items: [
        {
          label: t("aiCopilot"),
          path: "/ai-assistant",
          icon: <Bot className="h-4 w-4 shrink-0" />,
        },
        {
          label: t("threatIntel"),
          path: "/threat-intel",
          icon: <Globe className="h-4 w-4 shrink-0" />,
        },
        {
          label: t("correlation"),
          path: "/correlation",
          icon: <Network className="h-4 w-4 shrink-0" />,
        },
        {
          label: t("ueba"),
          path: "/ueba",
          icon: <Fingerprint className="h-4 w-4 shrink-0" />,
        },
        {
          label: t("threatHunting"),
          path: "/threat-hunting",
          icon: <Crosshair className="h-4 w-4 shrink-0" />,
        },
      ],
    }),
    [t]
  );

  const ecosystemGroup: NavGroup = useMemo(
    () => ({
      label: t("ecosystem"),
      items: [
        {
          label: t("marketplace"),
          path: "/marketplace",
          icon: <Store className="h-4 w-4 shrink-0" />,
        },
        {
          label: t("cloudNative"),
          path: "/cloud-native",
          icon: <Cloud className="h-4 w-4 shrink-0" />,
        },
        {
          label: t("assets"),
          path: "/assets",
          icon: <Server className="h-4 w-4 shrink-0" />,
        },
        {
          label: t("triggers"),
          path: "/triggers",
          icon: <Zap className="h-4 w-4 shrink-0" />,
        },
      ],
    }),
    [t]
  );

  const adminItems: NavItem[] = useMemo(
    () => [
      ...(isAdmin(user ?? null)
        ? [
            {
              label: t("dashboard"),
              path: "/admin/dashboard",
              icon: <LayoutDashboard className="h-4 w-4 shrink-0" />,
            },
            {
              label: t("settings"),
              path: "/settings",
              icon: <Settings className="h-4 w-4 shrink-0" />,
            },
          ]
        : []),
      {
        label: t("aiModels"),
        path: "/settings/ai-models",
        icon: <Cpu className="h-4 w-4 shrink-0" />,
      },
      {
        label: t("apiKeys"),
        path: "/settings/api-keys",
        icon: <KeyRound className="h-4 w-4 shrink-0" />,
      },
      ...(isAdmin(user ?? null) || isAnalystOrAdmin(user ?? null)
        ? [
            {
              label: t("audit"),
              path: "/audit",
              icon: <ScrollText className="h-4 w-4 shrink-0" />,
            },
          ]
        : []),
      ...(isAdmin(user ?? null)
        ? [
            {
              label: t("users"),
              path: "/admin/users",
              icon: <Users className="h-4 w-4 shrink-0" />,
            },
          ]
        : []),
    ],
    [t, user]
  );

  const adminGroup: NavGroup = useMemo(
    () => ({
      label: tCommon("admin"),
      items: adminItems,
    }),
    [tCommon, adminItems]
  );

  const allNavPaths = useMemo(() => {
    const paths: string[] = mainNavItems.map((item) => item.path);
    analyticsGroup.items.forEach((item) => paths.push(item.path));
    ecosystemGroup.items.forEach((item) => paths.push(item.path));
    adminItems.forEach((item) => paths.push(item.path));
    return paths;
  }, [mainNavItems, analyticsGroup, ecosystemGroup, adminItems]);

  const isLinkActive = useCallback(
    (linkPath: string) => {
      if (!pathname) return false;
      if (linkPath === "/") return pathname === "/";
      if (pathname === linkPath) return true;

      // Match nested subpaths with trailing slash (e.g. /alerts/123 -> /alerts)
      if (pathname.startsWith(`${linkPath}/`)) {
        // Disambiguate against other more specific registered nav routes
        // (e.g. /playbooks vs /playbooks/definitions, /settings vs /settings/ai-models)
        const hasMoreSpecificMatch = allNavPaths.some(
          (otherPath) =>
            otherPath !== linkPath &&
            otherPath.startsWith(`${linkPath}/`) &&
            (pathname === otherPath || pathname.startsWith(`${otherPath}/`))
        );
        return !hasMoreSpecificMatch;
      }

      return false;
    },
    [pathname, allNavPaths]
  );

  const isGroupActive = useCallback(
    (group: NavGroup) => {
      return group.items.some((item) => isLinkActive(item.path));
    },
    [isLinkActive]
  );

  const renderDropdown = (group: NavGroup, align: "center" | "left" | "right" = "center") => {
    const isActive = isGroupActive(group);
    const isHovered = hoveredDropdown === group.label;

    const handleMouseEnter = () => {
      if (dropdownTimeoutRef.current) {
        clearTimeout(dropdownTimeoutRef.current);
      }
      setHoveredDropdown(group.label);
    };

    const handleMouseLeave = () => {
      dropdownTimeoutRef.current = setTimeout(() => {
        setHoveredDropdown(null);
      }, 150);
    };

    const alignmentClass =
      align === "center" ? "left-1/2 -translate-x-1/2" : align === "right" ? "right-0" : "left-0";

    return (
      <div
        className="relative shrink-0"
        ref={isHovered ? dropdownRef : undefined}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        <button
          type="button"
          className={`flex items-center gap-1 ${navTriggerClass} ${
            isActive
              ? "bg-accent-50 text-accent-700 dark:bg-accent-950/40 dark:text-accent-300 font-semibold"
              : "text-text-secondary hover:text-text-primary hover:bg-surface-hover"
          }`}
          aria-expanded={isHovered}
        >
          {group.label}
          <ChevronDown
            className={`w-3.5 h-3.5 transition-transform duration-200 ${isHovered ? "rotate-180" : ""}`}
          />
        </button>

        {isHovered && (
          <div
            className={`absolute ${alignmentClass} top-full mt-1.5 min-w-[124px] w-max bg-surface-card border border-border-subtle rounded-xl shadow-elevated p-1 z-50 animate-fade-in overflow-hidden backdrop-blur-xl ring-1 ring-black/5 dark:ring-white/5 before:absolute before:-top-2 before:left-0 before:right-0 before:h-2 before:content-['']`}
            onMouseEnter={() => {
              if (dropdownTimeoutRef.current) {
                clearTimeout(dropdownTimeoutRef.current);
              }
            }}
            onMouseLeave={handleMouseLeave}
          >
            <div className="space-y-0.5">
              {group.items.map((item) => {
                const active = isLinkActive(item.path);
                return (
                  <Link
                    key={item.path}
                    href={item.path}
                    onClick={() => setHoveredDropdown(null)}
                    className={`flex items-center gap-2 px-2.5 py-1.5 text-xs rounded-lg transition-colors whitespace-nowrap ${
                      active
                        ? "bg-accent-50 text-accent-700 dark:bg-accent-950/40 dark:text-accent-300 font-semibold"
                        : "text-text-secondary hover:text-text-primary hover:bg-surface-hover"
                    }`}
                    aria-current={active ? "page" : undefined}
                  >
                    <span
                      className={`shrink-0 ${
                        active ? "text-accent-600 dark:text-accent-400" : "text-text-tertiary"
                      }`}
                    >
                      {item.icon}
                    </span>
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <nav className="sticky top-0 z-40 bg-surface-card/85 backdrop-blur-xl border-b border-border-subtle transition-colors">
      <div className="max-w-7xl mx-auto px-3 sm:px-4 lg:px-6">
        <div className="flex justify-between items-center h-14">
          <div className="flex items-center space-x-3 shrink-0">
            <Link
              href="/"
              className="flex items-center gap-2.5 text-text-primary font-bold text-base whitespace-nowrap transition-transform active:scale-[0.98] shrink-0"
            >
              <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-accent-600 to-accent-700 flex items-center justify-center shadow-sm shadow-accent-600/30 text-white shrink-0">
                <ShieldCheck className="w-4 h-4 text-white" />
              </div>
              <span className="hidden sm:inline tracking-tight font-semibold">SOC Copilot</span>
            </Link>
            {title && (
              <>
                <div className="hidden md:block h-5 w-px bg-border-subtle shrink-0"></div>
                <div className="hidden md:block shrink-0">
                  <h1 className="text-xs font-semibold text-text-primary truncate max-w-[8rem] xl:max-w-[14rem]">
                    {title}
                  </h1>
                  {subtitle && (
                    <p className="text-[11px] text-text-tertiary truncate max-w-[8rem] xl:max-w-[14rem]">
                      {subtitle}
                    </p>
                  )}
                </div>
              </>
            )}
          </div>

          <div className="hidden lg:flex items-center justify-between flex-1 min-w-0 ml-3 xl:ml-6">
            <div className="flex items-center space-x-1 min-w-0">
              {user && (
                <>
                  {apiStatus && (
                    <div className="flex items-center gap-1.5 px-2 py-1 rounded-full mr-1 bg-surface-hover border border-border-subtle shrink-0">
                      <span
                        className={`w-2 h-2 rounded-full shrink-0 ${
                          apiStatus === "healthy"
                            ? "bg-success-500 animate-pulse-soft"
                            : apiStatus === "checking"
                              ? "bg-warning-500 animate-pulse-soft"
                              : "bg-danger-500"
                        }`}
                      />
                      <span className="text-[10px] font-semibold text-text-secondary hidden 2xl:inline whitespace-nowrap">
                        {apiStatus === "healthy"
                          ? "API OK"
                          : apiStatus === "checking"
                            ? "..."
                            : "Err"}
                      </span>
                    </div>
                  )}

                  {mainNavItems.map((link) => (
                    <Link
                      key={link.path}
                      href={link.path}
                      className={`${navTriggerClass} ${
                        isLinkActive(link.path)
                          ? "bg-accent-50 text-accent-700 dark:bg-accent-950/40 dark:text-accent-300 font-semibold"
                          : "text-text-secondary hover:text-text-primary hover:bg-surface-hover"
                      }`}
                      aria-current={isLinkActive(link.path) ? "page" : undefined}
                    >
                      {link.label}
                    </Link>
                  ))}

                  {renderDropdown(analyticsGroup)}
                  {renderDropdown(ecosystemGroup)}

                  {adminItems.length > 0 && renderDropdown(adminGroup)}
                </>
              )}
            </div>

            <div className="flex items-center space-x-1.5 shrink-0 ml-auto pl-2">
              <button
                type="button"
                onClick={() => {
                  document.dispatchEvent(new KeyboardEvent("keydown", { key: "k", metaKey: true }));
                }}
                className="flex items-center gap-1.5 px-2 py-1 text-xs text-text-tertiary bg-surface-hover hover:text-text-primary rounded-lg border border-border-subtle hover:border-border-default transition-all duration-150 shrink-0"
                title="Search (⌘K)"
                aria-label="Global search"
              >
                <Search className="w-3.5 h-3.5" />
                <span className="hidden xl:inline text-xs">Search</span>
                <kbd className="text-[10px] font-mono px-1 py-0.5 rounded bg-surface-card border border-border-subtle">
                  ⌘K
                </kbd>
              </button>

              {actions}

              <LanguageSwitcher />
              <ThemeToggle />

              <div className="h-5 w-px bg-border-subtle mx-0.5 shrink-0"></div>

              {user && (
                <>
                  <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-surface-hover border border-border-subtle shrink-0">
                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] font-semibold shrink-0 ${getRoleBadgeClass(user.role)}`}
                    >
                      {user.role}
                    </span>
                    <span className="text-xs text-text-secondary truncate max-w-[4rem] xl:max-w-[7rem]">
                      {user.username}
                    </span>
                  </div>
                  <button
                    onClick={handleLogout}
                    className="px-2.5 py-1 text-xs text-danger-600 hover:text-danger-700 dark:text-danger-400 hover:bg-danger-50 dark:hover:bg-danger-900/20 rounded-lg transition-colors whitespace-nowrap shrink-0"
                  >
                    {t("logout")}
                  </button>
                </>
              )}
            </div>
          </div>

          <div className="lg:hidden flex items-center space-x-2">
            {user && (
              <>
                <button
                  type="button"
                  onClick={() => {
                    document.dispatchEvent(
                      new KeyboardEvent("keydown", { key: "k", metaKey: true })
                    );
                  }}
                  className="p-2 rounded-lg text-text-tertiary hover:text-text-primary hover:bg-surface-hover transition-colors"
                  aria-label="Search"
                >
                  <Search className="w-4 h-4" />
                </button>
                {apiStatus && (
                  <div className="flex items-center gap-1 px-1.5 py-1 rounded-full bg-surface-hover">
                    <span
                      className={`w-2 h-2 rounded-full ${
                        apiStatus === "healthy"
                          ? "bg-success-500"
                          : apiStatus === "checking"
                            ? "bg-warning-500"
                            : "bg-danger-500"
                      }`}
                    />
                  </div>
                )}
                <button
                  onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                  className="p-2 rounded-lg text-text-secondary hover:text-text-primary hover:bg-surface-hover transition-colors"
                >
                  {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
                </button>
              </>
            )}
          </div>
        </div>

        {mobileMenuOpen && (
          <div className="lg:hidden py-3 border-t border-border-subtle animate-fade-in max-h-[80vh] overflow-y-auto">
            <div className="space-y-1">
              {mainNavItems.map((link) => (
                <Link
                  key={link.path}
                  href={link.path}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`block w-full text-left px-3 py-2 text-xs font-medium rounded-lg transition-colors ${
                    isLinkActive(link.path)
                      ? "bg-accent-50 text-accent-700 dark:bg-accent-950/40 dark:text-accent-300 font-semibold"
                      : "text-text-secondary hover:text-text-primary hover:bg-surface-hover"
                  }`}
                  aria-current={isLinkActive(link.path) ? "page" : undefined}
                >
                  {link.label}
                </Link>
              ))}

              <div className="px-3 py-2 text-[10px] font-semibold text-text-tertiary uppercase tracking-wider mt-2">
                {t("analytics")}
              </div>
              {analyticsGroup.items.map((item) => (
                <Link
                  key={item.path}
                  href={item.path}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`flex items-center gap-2 w-full text-left px-3 py-2 text-xs rounded-lg transition-colors pl-6 ${
                    isLinkActive(item.path)
                      ? "bg-accent-50 text-accent-700 dark:bg-accent-950/40 dark:text-accent-300 font-semibold"
                      : "text-text-secondary hover:text-text-primary hover:bg-surface-hover"
                  }`}
                  aria-current={isLinkActive(item.path) ? "page" : undefined}
                >
                  <span className="text-text-tertiary">{item.icon}</span>
                  <span>{item.label}</span>
                </Link>
              ))}

              <div className="px-3 py-2 text-[10px] font-semibold text-text-tertiary uppercase tracking-wider mt-2">
                {t("ecosystem")}
              </div>
              {ecosystemGroup.items.map((item) => (
                <Link
                  key={item.path}
                  href={item.path}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`flex items-center gap-2 w-full text-left px-3 py-2 text-xs rounded-lg transition-colors pl-6 ${
                    isLinkActive(item.path)
                      ? "bg-accent-50 text-accent-700 dark:bg-accent-950/40 dark:text-accent-300 font-semibold"
                      : "text-text-secondary hover:text-text-primary hover:bg-surface-hover"
                  }`}
                  aria-current={isLinkActive(item.path) ? "page" : undefined}
                >
                  <span className="text-text-tertiary">{item.icon}</span>
                  <span>{item.label}</span>
                </Link>
              ))}

              {adminItems.length > 0 && (
                <>
                  <div className="px-3 py-2 text-[10px] font-semibold text-text-tertiary uppercase tracking-wider mt-2">
                    {tCommon("admin")}
                  </div>
                  {adminItems.map((item) => (
                    <Link
                      key={item.path}
                      href={item.path}
                      onClick={() => setMobileMenuOpen(false)}
                      className={`flex items-center gap-2 w-full text-left px-3 py-2 text-xs rounded-lg transition-colors pl-6 ${
                        isLinkActive(item.path)
                          ? "bg-accent-50 text-accent-700 dark:bg-accent-950/40 dark:text-accent-300 font-semibold"
                          : "text-text-secondary hover:text-text-primary hover:bg-surface-hover"
                      }`}
                      aria-current={isLinkActive(item.path) ? "page" : undefined}
                    >
                      <span className="text-text-tertiary">{item.icon}</span>
                      <span>{item.label}</span>
                    </Link>
                  ))}
                </>
              )}
            </div>

            <div className="border-t border-border-subtle mt-4 pt-3 space-y-3 px-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-text-secondary">{t("language")}</span>
                <div className="flex items-center gap-2">
                  <LanguageSwitcher />
                  <ThemeToggle />
                </div>
              </div>

              {user && (
                <div className="flex items-center justify-between pt-1">
                  <div className="flex items-center space-x-2">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-semibold ${getRoleBadgeClass(user?.role ?? "")}`}
                    >
                      {user?.role}
                    </span>
                    <span className="text-xs text-text-secondary">{user?.username}</span>
                  </div>
                  <button
                    onClick={handleLogout}
                    className="px-3 py-1 text-xs text-danger-600 hover:text-danger-700 dark:text-danger-400 hover:bg-danger-50 dark:hover:bg-danger-900/20 rounded-lg transition-colors"
                  >
                    Logout
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </nav>
  );
}
