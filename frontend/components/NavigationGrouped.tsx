"use client";

import { useRouter, usePathname } from "@/i18n/routing";
import { useTranslations } from 'next-intl';
import { loadAuthState, logout, isAdmin } from "@/lib/auth";
import { useState, useRef, useEffect, useMemo, useCallback } from "react";
import { Menu, X, ChevronDown, ChevronRight, Search } from "lucide-react";
import { LanguageSwitcher } from "./LanguageSwitcher";

interface NavigationProps {
  title: string;
  subtitle?: string;
  apiStatus?: "healthy" | "checking" | "error";
  actions?: React.ReactNode;
}

interface NavGroup {
  id: string;
  label: string;
  items: NavItem[];
}

interface NavItem {
  label: string;
  path: string;
}

export default function NavigationGrouped({ title, subtitle, apiStatus, actions }: NavigationProps) {
  const router = useRouter();
  const pathname = usePathname();
  const t = useTranslations('nav');
  const tApiStatus = useTranslations('nav.apiStatus');
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const authState = useMemo(() => {
    if (!mounted) return null;
    return loadAuthState();
  }, [mounted]);
  const user = authState?.user;

  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  const toggleGroup = useCallback((groupId: string) => {
    setExpandedGroups(prev => {
      const newSet = new Set(prev);
      if (newSet.has(groupId)) {
        newSet.delete(groupId);
      } else {
        newSet.add(groupId);
      }
      return newSet;
    });
  }, []);

  const getRoleBadgeClass = useCallback((role: string) => {
    switch (role) {
      case "admin":
        return "bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300";
      case "analyst":
        return "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300";
      case "auditor":
        return "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300";
      default:
        return "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300";
    }
  }, []);

  // P3-11: Organized navigation groups
  const navGroups: NavGroup[] = useMemo(() => [
    {
      id: "dashboard",
      label: t("dashboard") || "Dashboard",
      items: [
        { label: t("home") || "Home", path: "/" },
        { label: t("monitor") || "Monitor", path: "/monitor" },
      ]
    },
    {
      id: "analysis",
      label: t("analysis") || "Analysis",
      items: [
        { label: t("alerts") || "Alerts", path: "/alerts" },
        { label: t("timeline") || "Timeline", path: "/timeline" },
        { label: t("threatIntel") || "Threat Intel", path: "/threat-intel" },
      ]
    },
    {
      id: "automation",
      label: t("automation") || "AI & Automation",
      items: [
        { label: t("ai") || "AI Assistant", path: "/ai-assistant" },
        { label: t("runs") || "Playbooks", path: "/playbooks" },
        { label: t("triggers") || "Triggers", path: "/triggers" },
        { label: t("dify") || "Dify", path: "/dify" },
      ]
    },
    {
      id: "intelligence",
      label: t("intelligence") || "Intelligence",
      items: [
        { label: t("hunting") || "Threat Hunting", path: "/threat-hunting" },
        { label: t("market") || "Marketplace", path: "/marketplace" },
        { label: t("cloud") || "Cloud Native", path: "/cloud-native" },
        { label: t("ueba") || "UEBA", path: "/ueba" },
      ]
    },
    ...(isAdmin(user ?? null) ? [{
      id: "settings",
      label: t("settings") || "Settings",
      items: [
        { label: t("settings") || "Settings", path: "/settings" },
        { label: t("users") || "Users", path: "/admin/users" },
        { label: t("audit") || "Audit Logs", path: "/audit" },
      ]
    }] : []),
  ], [t, user]);

  const isLinkActive = useCallback((linkPath: string) => {
    if (pathname === linkPath) return true;
    if (linkPath === "/playbooks") {
      if (pathname?.startsWith("/playbooks/") &&
          !pathname.startsWith("/playbooks/definitions") &&
          !pathname.startsWith("/playbooks/approvals")) {
        return true;
      }
      return false;
    }
    if (linkPath !== "/" && pathname?.startsWith(linkPath + "/")) return true;
    return false;
  }, [pathname]);

  return (
    <>
      {/* Top Navigation Bar */}
      <nav className="sticky top-0 z-50 bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-full mx-auto px-2 sm:px-4">
          <div className="flex justify-between items-center h-14">
            {/* Left: Logo, Title, Sidebar Toggle */}
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="hidden lg:block p-1.5 rounded-md text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                aria-label="Toggle sidebar"
              >
                <Menu className="w-4 h-4" />
              </button>

              <button
                onClick={() => router.push('/')}
                className="text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 font-bold text-sm whitespace-nowrap"
              >
                SOC
              </button>
              <div className="hidden sm:block h-4 w-px bg-gray-300 dark:bg-gray-600"></div>
              <div className="hidden sm:block">
                <div className="flex items-center gap-2">
                  <h1 className="text-sm font-semibold text-gray-900 dark:text-white truncate max-w-[120px] lg:max-w-md">
                    {title}
                  </h1>
                  {apiStatus && (
                    <span className={`w-2 h-2 rounded-full ${
                      apiStatus === "healthy" ? "bg-green-500" :
                      apiStatus === "checking" ? "bg-amber-500 animate-pulse" :
                      "bg-red-500"
                    }`} />
                  )}
                </div>
                {subtitle && (
                  <p className="text-[10px] text-gray-500 dark:text-gray-400">{subtitle}</p>
                )}
              </div>
            </div>

            {/* Desktop Navigation - P3-11: Grouped navigation */}
            <div className="hidden xl:flex items-center space-x-0.5">
              {user && (
                <>
                  {navGroups.slice(0, 3).map((group) => (
                    <div key={group.id} className="relative group/nav">
                      <button className="px-2 py-1.5 text-xs rounded whitespace-nowrap transition-colors text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-1">
                        {group.label}
                        <ChevronDown className="w-3 h-3 opacity-50" />
                      </button>

                      <div className="absolute top-full left-0 pt-1 w-48 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 py-1 z-50 opacity-0 invisible group-hover/nav:opacity-100 group-hover/nav:visible transition-all duration-200">
                        {group.items.map((item) => (
                          <button
                            key={item.path}
                            onClick={() => router.push(item.path)}
                            className={`w-full text-left px-4 py-2 text-sm transition-colors ${
                              isLinkActive(item.path)
                                ? "bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 font-medium"
                                : "text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
                            }`}
                          >
                            <span>{item.label}</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  ))}

                  {actions && <><div className="h-4 w-px bg-gray-300 dark:bg-gray-600 mx-1"></div>{actions}</div>}

                  <div className="h-4 w-px bg-gray-300 dark:bg-gray-600 mx-1"></div>

                  <button
                    onClick={() => setSearchOpen(true)}
                    className="p-1.5 rounded-md text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                  >
                    <Search className="w-4 h-4" />
                  </button>

                  <LanguageSwitcher />

                  <div className="h-4 w-px bg-gray-300 dark:bg-gray-600 mx-1"></div>

                  <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${getRoleBadgeClass(user.role)}`}>
                    {user.role}
                  </span>
                  <span className="text-xs text-gray-600 dark:text-gray-400 truncate max-w-[80px]">
                    {user.username}
                  </span>
                  <button
                    onClick={handleLogout}
                    className="px-2 py-1.5 text-xs text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
                  >
                    {t("exit")}
                  </button>
                </>
              )}
            </div>

            {/* Mobile Menu Button - P3-13: Enhanced mobile */}
            <div className="lg:hidden flex items-center space-x-2">
              {user && (
                <>
                  <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${getRoleBadgeClass(user.role)}`}>
                    {user.role}
                  </span>
                  <LanguageSwitcher />
                  <button
                    onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                    className="p-1.5 rounded-md text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                  >
                    {mobileMenuOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
                  </button>
                </>
              )}
            </div>
          </div>

          {/* Mobile Menu - P3-13: Grouped and collapsible */}
          {mobileMenuOpen && (
            <div className="lg:hidden py-2 border-t border-gray-200 dark:border-gray-700">
              <div className="space-y-1 max-h-[60vh] overflow-y-auto">
                {navGroups.map((group) => {
                  const Icon = group.icon;
                  const isExpanded = expandedGroups.has(group.id);
                  const hasActiveItem = group.items.some(item => isLinkActive(item.path));

                  return (
                    <div key={group.id}>
                      <button
                        onClick={() => toggleGroup(group.id)}
                        className={`w-full px-3 py-2 text-xs font-medium rounded transition-colors flex items-center justify-between ${
                          hasActiveItem
                            ? "bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300"
                            : "text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          {Icon && <Icon className="w-4 h-4" />}
                          <span>{group.label}</span>
                        </div>
                        <ChevronRight className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
                      </button>

                      {isExpanded && (
                        <div className="pl-4 space-y-1 mt-1">
                          {group.items.map((item) => (
                            <button
                              key={item.path}
                              onClick={() => {
                                router.push(item.path);
                                setMobileMenuOpen(false);
                              }}
                              className={`w-full px-3 py-2 text-xs rounded transition-colors flex items-center gap-2 ${
                                isLinkActive(item.path)
                                  ? "bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 font-medium"
                                  : "text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700"
                              }`}
                            >
                              {item.icon && <item.icon className="w-4 h-4" />}
                              <span>{item.label}</span>
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              <div className="border-t border-gray-200 dark:border-gray-700 mt-2 pt-2 flex items-center justify-between px-2">
                <span className="text-xs text-gray-600 dark:text-gray-400">{user?.username}</span>
                <button onClick={handleLogout} className="px-3 py-1.5 text-xs text-red-600 hover:text-red-700 dark:text-red-400 rounded">
                  {t("logout")}
                </button>
              </div>
            </div>
          )}
        </div>
      </nav>

      {/* Sidebar - P3-11 & P3-13 */}
      {sidebarOpen && (
        <>
          <div className="fixed inset-0 bg-black/50 z-40 lg:hidden" onClick={() => setSidebarOpen(false)} />
          <aside className={`
            fixed top-14 left-0 h-[calc(100vh-3.5rem)] w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 z-50
            transform transition-transform duration-200
            ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
            lg:relative lg:translate-x-0
          `}>
            <div className="p-4 h-full overflow-y-auto">
              <div className="mb-4">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    type="text"
                    placeholder={t("search") || "Search..."}
                    className="w-full pl-10 pr-4 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700"
                  />
                </div>
              </div>

              <nav className="space-y-6">
                {navGroups.map((group) => {
                  const Icon = group.icon;
                  const isExpanded = expandedGroups.has(group.id);
                  const hasActiveItem = group.items.some(item => isLinkActive(item.path));

                  return (
                    <div key={group.id}>
                      <button
                        onClick={() => toggleGroup(group.id)}
                        className={`w-full px-3 py-2 text-sm font-medium rounded-lg flex items-center justify-between ${
                          hasActiveItem
                            ? "bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300"
                            : "text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          {Icon && <Icon className="w-5 h-5" />}
                          <span>{group.label}</span>
                        </div>
                        <ChevronRight className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
                      </button>

                      {isExpanded && (
                        <div className="ml-4 mt-2 space-y-1">
                          {group.items.map((item) => (
                            <button
                              key={item.path}
                              onClick={() => router.push(item.path)}
                              className={`w-full px-3 py-2 text-sm rounded-lg flex items-center gap-2 ${
                                isLinkActive(item.path)
                                  ? "bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 font-medium"
                                  : "text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700"
                              }`}
                            >
                              {item.icon && <item.icon className="w-4 h-4" />}
                              <span>{item.label}</span>
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </nav>
            </div>
          </aside>
        </>
      )}

      {/* Search Modal */}
      {searchOpen && (
        <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4">
          <div className="absolute inset-0 bg-black/50" onClick={() => setSearchOpen(false)} />
          <div className="relative w-full max-w-2xl bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700">
            <div className="p-4">
              <div className="flex items-center gap-3">
                <Search className="w-5 h-5 text-gray-400" />
                <input
                  type="text"
                  placeholder={t("searchPlaceholder") || "Search for pages..."}
                  className="flex-1 text-lg bg-transparent border-0 outline-none text-gray-900 dark:text-white"
                  autoFocus
                />
                <button onClick={() => setSearchOpen(false)} className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700">
                  <X className="w-5 h-5 text-gray-400" />
                </button>
              </div>
            </div>

            <div className="border-t border-gray-200 dark:border-gray-700 max-h-96 overflow-y-auto">
              <div className="p-2">
                {navGroups.map((group) => (
                  <div key={group.id} className="mb-4">
                    <div className="px-3 py-1 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">
                      {group.label}
                    </div>
                    {group.items.map((item) => (
                      <button
                        key={item.path}
                        onClick={() => { router.push(item.path); setSearchOpen(false); }}
                        className="w-full px-3 py-2 text-sm rounded-lg flex items-center gap-2 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
                      >
                        {item.icon && <item.icon className="w-4 h-4" />}
                        <span>{item.label}</span>
                      </button>
                    ))}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
