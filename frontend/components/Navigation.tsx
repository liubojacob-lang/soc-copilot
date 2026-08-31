"use client";

import { useRouter, usePathname } from "@/i18n/navigation";
import { loadAuthState, logout, isAdmin, isAnalystOrAdmin } from "@/lib/auth";
import { useState, useRef, useEffect, useMemo, useCallback } from "react";
import { Menu, X, ChevronDown, ShieldCheck } from "lucide-react";
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
  path: string;
  icon?: React.ReactNode;
}

interface NavGroup {
  label: string;
  icon?: React.ReactNode;
  items: NavItem[];
}

export default function Navigation({ title, subtitle, apiStatus, actions }: NavigationProps) {
  const router = useRouter();
  const pathname = usePathname();
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
      { label: t("runs"), path: "/playbooks" },
      { label: t("definitions"), path: "/playbooks/definitions" },
    ],
    [t]
  );

  const analyticsGroup: NavGroup = useMemo(
    () => ({
      label: t("analytics"),
      items: [
        { label: t("aiCopilot"), path: "/ai-assistant" },
        { label: t("threatIntel"), path: "/threat-intel" },
        { label: t("correlation"), path: "/correlation" },
        { label: t("ueba"), path: "/ueba" },
        { label: t("threatHunting"), path: "/threat-hunting" },
      ],
    }),
    [t]
  );

  const ecosystemGroup: NavGroup = useMemo(
    () => ({
      label: t("ecosystem"),
      items: [
        { label: t("marketplace"), path: "/marketplace" },
        { label: t("cloudNative"), path: "/cloud-native" },
        { label: t("assets"), path: "/assets" },
        { label: t("triggers"), path: "/triggers" },
      ],
    }),
    [t]
  );

  const adminItems: NavItem[] = useMemo(
    () => [
      ...(isAdmin(user ?? null)
        ? [
            { label: t("dashboard"), path: "/admin/dashboard" },
            { label: t("settings"), path: "/settings" },
          ]
        : []),
      { label: t("aiModels"), path: "/settings/ai-models" },
      { label: t("apiKeys"), path: "/settings/api-keys" },
      ...(isAdmin(user ?? null) || isAnalystOrAdmin(user ?? null)
        ? [{ label: t("audit"), path: "/audit" }]
        : []),
      ...(isAdmin(user ?? null) ? [{ label: t("users"), path: "/admin/users" }] : []),
    ],
    [t, user]
  );

  const isLinkActive = useCallback(
    (linkPath: string) => {
      if (pathname === linkPath) return true;
      if (linkPath !== "/" && pathname?.startsWith(linkPath)) return true;
      return false;
    },
    [pathname]
  );

  const isGroupActive = useCallback(
    (group: NavGroup) => {
      return group.items.some((item) => isLinkActive(item.path));
    },
    [isLinkActive]
  );

  const renderDropdown = (group: NavGroup, alignRight = false) => {
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

    return (
      <div
        className="relative"
        ref={isHovered ? dropdownRef : undefined}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        <button
          className={`flex items-center gap-1 px-3 py-2.5 text-sm rounded-xl whitespace-nowrap transition-all duration-300 ${
            isActive
              ? "bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300 font-semibold"
              : "text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700/50"
          }`}
        >
          {group.label}
          <ChevronDown
            className={`w-3.5 h-3.5 transition-transform duration-200 ${isHovered ? "rotate-180" : ""}`}
          />
        </button>

        {isHovered && (
          <div
            className={`absolute ${alignRight ? "right-0" : "left-0"} top-full w-52 bg-white dark:bg-gray-800 rounded-2xl shadow-elevated border border-gray-200 dark:border-gray-700 py-1 z-50 animate-fade-in overflow-hidden`}
            onMouseEnter={() => {
              if (dropdownTimeoutRef.current) {
                clearTimeout(dropdownTimeoutRef.current);
              }
            }}
            onMouseLeave={handleMouseLeave}
          >
            {group.items.map((item) => (
              <button
                key={item.path}
                onClick={() => {
                  router.push(item.path);
                  setHoveredDropdown(null);
                }}
                className={`w-full text-left px-3 py-1.5 text-sm transition-all duration-200 ${
                  isLinkActive(item.path)
                    ? "bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300 font-semibold"
                    : "text-gray-700 dark:text-gray-300 hover:bg-gray-75 dark:hover:bg-gray-700/50"
                }`}
                aria-current={
                  adminItems.some((adminItem) => isLinkActive(adminItem.path)) ? "page" : undefined
                }
              >
                {item.label}
              </button>
            ))}
          </div>
        )}
      </div>
    );
  };

  return (
    <nav className="sticky top-0 z-50 bg-white/85 dark:bg-gray-800/85 backdrop-blur-xl shadow-sm border-b border-gray-200/70 dark:border-gray-700/70">
      <div className="max-w-7xl mx-auto px-3 sm:px-4 lg:px-6">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => router.push("/")}
              className="flex items-center gap-2.5 text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300 font-bold text-base whitespace-nowrap transition-colors"
            >
              <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center shadow-lg shadow-primary-500/25">
                <ShieldCheck className="w-4.5 h-4.5 text-white" />
              </div>
              <span className="hidden sm:inline tracking-tight">SOC Copilot</span>
            </button>
            {title && (
              <>
                <div className="hidden md:block h-6 w-px bg-gray-200 dark:bg-gray-700"></div>
                <div className="hidden md:block">
                  <h1 className="text-sm font-semibold text-gray-900 dark:text-white truncate max-w-[10rem] lg:max-w-[15rem]">
                    {title}
                  </h1>
                  {subtitle && (
                    <p className="text-xs text-gray-500 dark:text-gray-400">{subtitle}</p>
                  )}
                </div>
              </>
            )}
          </div>

          <div className="hidden lg:flex items-center justify-between flex-1">
            <div className="flex items-center space-x-1.5 ml-6">
              {user && (
                <>
                  {apiStatus && (
                    <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full mr-2 bg-gray-75 dark:bg-gray-700/50">
                      <span
                        className={`w-2.5 h-2.5 rounded-full ${
                          apiStatus === "healthy"
                            ? "bg-success-500 animate-pulse-soft"
                            : apiStatus === "checking"
                              ? "bg-warning-500 animate-pulse-soft"
                              : "bg-danger-500"
                        }`}
                      />
                      <span className="text-[11px] font-semibold text-gray-600 dark:text-gray-300 hidden xl:inline">
                        {apiStatus === "healthy"
                          ? "API OK"
                          : apiStatus === "checking"
                            ? "..."
                            : "Err"}
                      </span>
                    </div>
                  )}

                  {mainNavItems.map((link) => (
                    <button
                      key={link.path}
                      onClick={() => router.push(link.path)}
                      className={`px-3 py-2.5 text-sm rounded-xl whitespace-nowrap transition-all duration-300 ${
                        isLinkActive(link.path)
                          ? "bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300 font-semibold"
                          : "text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700/50"
                      }`}
                      aria-current={isLinkActive(link.path) ? "page" : undefined}
                    >
                      {link.label}
                    </button>
                  ))}

                  {renderDropdown(analyticsGroup)}
                  {renderDropdown(ecosystemGroup)}

                  {adminItems.length > 0 && (
                    <div
                      className="relative"
                      ref={hoveredDropdown === "adminGroup" ? dropdownRef : undefined}
                      onMouseEnter={() => {
                        if (dropdownTimeoutRef.current) {
                          clearTimeout(dropdownTimeoutRef.current);
                        }
                        setHoveredDropdown("adminGroup");
                      }}
                      onMouseLeave={() => {
                        dropdownTimeoutRef.current = setTimeout(() => {
                          setHoveredDropdown(null);
                        }, 150);
                      }}
                    >
                      <button
                        className={`flex items-center gap-1 px-3 py-2.5 text-sm rounded-xl whitespace-nowrap transition-all duration-300 ${
                          adminItems.some((item) => isLinkActive(item.path))
                            ? "bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300 font-semibold"
                            : "text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700/50"
                        }`}
                        aria-current={
                          adminItems.some((adminItem) => isLinkActive(adminItem.path))
                            ? "page"
                            : undefined
                        }
                      >
                        {tCommon("admin")}
                        <ChevronDown
                          className={`w-3.5 h-3.5 transition-transform duration-200 ${hoveredDropdown === "adminGroup" ? "rotate-180" : ""}`}
                        />
                      </button>

                      {hoveredDropdown === "adminGroup" && (
                        <div
                          className="absolute right-0 top-full w-52 bg-white dark:bg-gray-800 rounded-2xl shadow-elevated border border-gray-200 dark:border-gray-700 py-1 z-50 animate-fade-in overflow-hidden"
                          onMouseEnter={() => {
                            if (dropdownTimeoutRef.current) {
                              clearTimeout(dropdownTimeoutRef.current);
                            }
                          }}
                          onMouseLeave={() => {
                            dropdownTimeoutRef.current = setTimeout(() => {
                              setHoveredDropdown(null);
                            }, 150);
                          }}
                        >
                          {adminItems.map((item) => (
                            <button
                              key={item.path}
                              onClick={() => {
                                router.push(item.path);
                                setHoveredDropdown(null);
                              }}
                              className={`w-full text-left px-3 py-1.5 text-sm transition-all duration-200 ${
                                isLinkActive(item.path)
                                  ? "bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300 font-semibold"
                                  : "text-gray-700 dark:text-gray-300 hover:bg-gray-75 dark:hover:bg-gray-700/50"
                              }`}
                              aria-current={
                                adminItems.some((adminItem) => isLinkActive(adminItem.path))
                                  ? "page"
                                  : undefined
                              }
                            >
                              {item.label}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </>
              )}
            </div>

            <div className="flex items-center space-x-2">
              {actions}

              <ThemeToggle />
              <LanguageSwitcher />

              <div className="h-6 w-px bg-gray-200 dark:bg-gray-700 mx-0.5"></div>

              {user && (
                <>
                  <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-gray-75 dark:bg-gray-700/50">
                    <span
                      className={`px-2.5 py-0.5 rounded-lg text-[11px] font-semibold ${getRoleBadgeClass(user.role)}`}
                    >
                      {user.role}
                    </span>
                    <span className="text-sm text-gray-600 dark:text-gray-300 truncate max-w-[5rem] xl:max-w-[8rem]">
                      {user.username}
                    </span>
                  </div>
                  <button
                    onClick={handleLogout}
                    className="px-3 py-2 text-sm text-danger-600 hover:text-danger-700 dark:text-danger-400 dark:hover:text-danger-300 hover:bg-danger-50 dark:hover:bg-danger-900/20 rounded-xl transition-all duration-300"
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
                {apiStatus && (
                  <div className="flex items-center gap-1 px-2 py-1 rounded-full">
                    <span
                      className={`w-2.5 h-2.5 rounded-full ${
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
                  className="p-2.5 rounded-xl text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700/50 transition-all duration-300"
                >
                  {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
                </button>
              </>
            )}
          </div>
        </div>

        {mobileMenuOpen && (
          <div className="lg:hidden py-4 border-t border-gray-200 dark:border-gray-700 animate-fade-in-up">
            <div className="space-y-1">
              {mainNavItems.map((link) => (
                <button
                  key={link.path}
                  onClick={() => {
                    router.push(link.path);
                    setMobileMenuOpen(false);
                  }}
                  className={`block w-full text-left px-4 py-3 text-sm rounded-xl transition-all duration-300 ${
                    isLinkActive(link.path)
                      ? "bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300 font-semibold"
                      : "text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700/50"
                  }`}
                  aria-current={isLinkActive(link.path) ? "page" : undefined}
                >
                  {link.label}
                </button>
              ))}

              <div className="px-4 py-2.5 text-[11px] font-semibold text-gray-400 uppercase tracking-wider mt-2">
                {t("analytics")}
              </div>
              {analyticsGroup.items.map((item) => (
                <button
                  key={item.path}
                  onClick={() => {
                    router.push(item.path);
                    setMobileMenuOpen(false);
                  }}
                  className={`block w-full text-left px-4 py-3 text-sm rounded-xl transition-all duration-300 pl-8 ${
                    isLinkActive(item.path)
                      ? "bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300 font-semibold"
                      : "text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700/50"
                  }`}
                  aria-current={
                    adminItems.some((adminItem) => isLinkActive(adminItem.path))
                      ? "page"
                      : undefined
                  }
                >
                  {item.label}
                </button>
              ))}

              <div className="px-4 py-2.5 text-[11px] font-semibold text-gray-400 uppercase tracking-wider mt-2">
                {t("ecosystem")}
              </div>
              {ecosystemGroup.items.map((item) => (
                <button
                  key={item.path}
                  onClick={() => {
                    router.push(item.path);
                    setMobileMenuOpen(false);
                  }}
                  className={`block w-full text-left px-4 py-3 text-sm rounded-xl transition-all duration-300 pl-8 ${
                    isLinkActive(item.path)
                      ? "bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300 font-semibold"
                      : "text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700/50"
                  }`}
                  aria-current={
                    adminItems.some((adminItem) => isLinkActive(adminItem.path))
                      ? "page"
                      : undefined
                  }
                >
                  {item.label}
                </button>
              ))}

              {adminItems.length > 0 && (
                <>
                  <div className="px-4 py-2.5 text-[11px] font-semibold text-gray-400 uppercase tracking-wider mt-2">
                    {tCommon("admin")}
                  </div>
                  {adminItems.map((item) => (
                    <button
                      key={item.path}
                      onClick={() => {
                        router.push(item.path);
                        setMobileMenuOpen(false);
                      }}
                      className={`block w-full text-left px-4 py-3 text-sm rounded-xl transition-all duration-300 pl-8 ${
                        isLinkActive(item.path)
                          ? "bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300 font-semibold"
                          : "text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700/50"
                      }`}
                      aria-current={
                        adminItems.some((adminItem) => isLinkActive(adminItem.path))
                          ? "page"
                          : undefined
                      }
                    >
                      {item.label}
                    </button>
                  ))}
                </>
              )}
            </div>

            <div className="border-t border-gray-200 dark:border-gray-700 mt-5 pt-5 space-y-4 px-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                  Language
                </span>
                <ThemeToggle />
                <LanguageSwitcher />
              </div>

              {user && (
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span
                      className={`px-2.5 py-0.5 rounded-lg text-[11px] font-semibold ${getRoleBadgeClass(user?.role ?? "")}`}
                    >
                      {user?.role}
                    </span>
                    <span className="text-sm text-gray-600 dark:text-gray-300">
                      {user?.username}
                    </span>
                  </div>
                  <button
                    onClick={handleLogout}
                    className="px-4 py-2.5 text-sm text-danger-600 hover:text-danger-700 dark:text-danger-400 dark:hover:text-danger-300 hover:bg-danger-50 dark:hover:bg-danger-900/20 rounded-xl transition-all duration-300"
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
