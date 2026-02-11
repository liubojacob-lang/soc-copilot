"use client";

import { useRouter, usePathname } from "next/navigation";
import { loadAuthState, logout, isAdmin, isAnalystOrAdmin } from "@/lib/auth";
import { useState, useRef, useEffect } from "react";
import { Menu, X, ChevronDown, Brain, Shield, Cloud, Store, Target, Users } from "lucide-react";

interface NavigationProps {
  title: string;
  subtitle?: string;
  apiStatus?: "healthy" | "checking" | "error";
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

export default function Navigation({ title, subtitle, apiStatus }: NavigationProps) {
  const router = useRouter();
  const pathname = usePathname();
  const authState = loadAuthState();
  const user = authState?.user;
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setOpenDropdown(null);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  const getRoleBadgeClass = (role: string) => {
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
  };

  // Main navigation items
  const mainNavItems: NavItem[] = [
    { label: "Home", path: "/" },
    { label: "Runs", path: "/playbooks" },
    { label: "Definitions", path: "/playbooks/definitions" },
  ];

  // Analytics dropdown group
  const analyticsGroup: NavGroup = {
    label: "Analytics",
    icon: <Brain className="w-4 h-4" />,
    items: [
      { label: "AI Copilot", path: "/ai-assistant", icon: <Brain className="w-4 h-4" /> },
      { label: "UEBA", path: "/ueba", icon: <Users className="w-4 h-4" /> },
      { label: "Threat Hunting", path: "/threat-hunting", icon: <Target className="w-4 h-4" /> },
    ],
  };

  // Ecosystem dropdown group
  const ecosystemGroup: NavGroup = {
    label: "Ecosystem",
    icon: <Store className="w-4 h-4" />,
    items: [
      { label: "Marketplace", path: "/marketplace", icon: <Store className="w-4 h-4" /> },
      { label: "Cloud Native", path: "/cloud-native", icon: <Cloud className="w-4 h-4" /> },
      { label: "Dify", path: "/dify", icon: <Shield className="w-4 h-4" /> },
      { label: "Triggers", path: "/triggers" },
    ],
  };

  // Admin items
  const adminItems: NavItem[] = [
    ...(isAdmin(user ?? null) ? [{ label: "Settings", path: "/settings" }] : []),
    { label: "API Keys", path: "/settings/api-keys" },
    ...(isAdmin(user ?? null) || isAnalystOrAdmin(user ?? null) ? [{ label: "Audit", path: "/audit" }] : []),
    ...(isAdmin(user ?? null) ? [{ label: "Users", path: "/admin/users" }] : []),
  ];

  const isLinkActive = (linkPath: string) => {
    if (pathname === linkPath) return true;
    if (linkPath !== "/" && pathname?.startsWith(linkPath)) return true;
    return false;
  };

  const isGroupActive = (group: NavGroup) => {
    return group.items.some(item => isLinkActive(item.path));
  };

  const renderDropdown = (group: NavGroup) => {
    const isActive = isGroupActive(group);
    const isOpen = openDropdown === group.label;

    return (
      <div className="relative" ref={isOpen ? dropdownRef : undefined}>
        <button
          onClick={() => setOpenDropdown(isOpen ? null : group.label)}
          className={`flex items-center gap-1 px-3 py-2 text-sm rounded-md whitespace-nowrap transition-colors ${
            isActive
              ? "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300 font-medium"
              : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
          }`}
        >
          {group.icon && <span className="mr-1">{group.icon}</span>}
          {group.label}
          <ChevronDown className={`w-4 h-4 transition-transform ${isOpen ? "rotate-180" : ""}`} />
        </button>

        {isOpen && (
          <div className="absolute top-full left-0 mt-1 w-48 bg-white dark:bg-gray-800 rounded-md shadow-lg border border-gray-200 dark:border-gray-700 py-1 z-50">
            {group.items.map((item) => (
              <button
                key={item.path}
                onClick={() => {
                  router.push(item.path);
                  setOpenDropdown(null);
                }}
                className={`w-full text-left px-4 py-2 text-sm flex items-center gap-2 transition-colors ${
                  isLinkActive(item.path)
                    ? "bg-blue-50 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300 font-medium"
                    : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                }`}
              >
                {item.icon && <span>{item.icon}</span>}
                {item.label}
              </button>
            ))}
          </div>
        )}
      </div>
    );
  };

  return (
    <nav className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Left: Logo and Title */}
          <div className="flex items-center space-x-4">
            <button
              onClick={() => router.push("/")}
              className="text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 font-bold text-lg whitespace-nowrap"
            >
              SOC Copilot
            </button>
            <div className="hidden sm:block h-6 w-px bg-gray-300 dark:bg-gray-600"></div>
            <div className="hidden sm:block">
              <h1 className="text-base font-semibold text-gray-900 dark:text-white truncate max-w-xs lg:max-w-md">{title}</h1>
              {subtitle && (
                <p className="text-xs text-gray-500 dark:text-gray-400">{subtitle}</p>
              )}
            </div>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden lg:flex items-center space-x-1">
            {user && (
              <>
                {/* API Status */}
                {apiStatus && (
                  <span
                    className={`px-2 py-1 rounded-full text-xs font-medium mr-2 ${
                      apiStatus === "healthy"
                        ? "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300"
                        : apiStatus === "checking"
                        ? "bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300"
                        : "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300"
                    }`}
                  >
                    {apiStatus === "healthy" ? "API OK" : apiStatus === "checking" ? "..." : "API Err"}
                  </span>
                )}

                {/* Main Nav Items */}
                {mainNavItems.map((link) => (
                  <button
                    key={link.path}
                    onClick={() => router.push(link.path)}
                    className={`px-3 py-2 text-sm rounded-md whitespace-nowrap transition-colors ${
                      isLinkActive(link.path)
                        ? "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300 font-medium"
                        : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                    }`}
                  >
                    {link.label}
                  </button>
                ))}

                {/* Dropdown Groups */}
                {renderDropdown(analyticsGroup)}
                {renderDropdown(ecosystemGroup)}

                {/* Admin Items */}
                {adminItems.length > 0 && (
                  <div className="relative" ref={openDropdown === "Admin" ? dropdownRef : undefined}>
                    <button
                      onClick={() => setOpenDropdown(openDropdown === "Admin" ? null : "Admin")}
                      className={`flex items-center gap-1 px-3 py-2 text-sm rounded-md whitespace-nowrap transition-colors ${
                        adminItems.some(item => isLinkActive(item.path))
                          ? "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300 font-medium"
                          : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                      }`}
                    >
                      Admin
                      <ChevronDown className={`w-4 h-4 transition-transform ${openDropdown === "Admin" ? "rotate-180" : ""}`} />
                    </button>

                    {openDropdown === "Admin" && (
                      <div className="absolute top-full right-0 mt-1 w-40 bg-white dark:bg-gray-800 rounded-md shadow-lg border border-gray-200 dark:border-gray-700 py-1 z-50">
                        {adminItems.map((item) => (
                          <button
                            key={item.path}
                            onClick={() => {
                              router.push(item.path);
                              setOpenDropdown(null);
                            }}
                            className={`w-full text-left px-4 py-2 text-sm transition-colors ${
                              isLinkActive(item.path)
                                ? "bg-blue-50 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300 font-medium"
                                : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                            }`}
                          >
                            {item.label}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                <div className="h-6 w-px bg-gray-300 dark:bg-gray-600 mx-1"></div>

                {/* User Info */}
                <span className={`px-2 py-1 rounded text-xs font-medium ${getRoleBadgeClass(user.role)}`}>
                  {user.role}
                </span>
                <span className="text-sm text-gray-600 dark:text-gray-400 truncate max-w-24">
                  {user.username}
                </span>
                <button
                  onClick={handleLogout}
                  className="px-3 py-2 text-sm text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-md"
                >
                  Logout
                </button>
              </>
            )}
          </div>

          {/* Mobile Menu Button */}
          <div className="lg:hidden flex items-center space-x-2">
            {user && (
              <>
                {apiStatus && (
                  <span
                    className={`px-2 py-1 rounded-full text-xs font-medium ${
                      apiStatus === "healthy"
                        ? "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300"
                        : apiStatus === "checking"
                        ? "bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300"
                        : "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300"
                    }`}
                  >
                    {apiStatus === "healthy" ? "OK" : apiStatus === "checking" ? "..." : "Err"}
                  </span>
                )}
                <button
                  onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                  className="p-2 rounded-md text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                >
                  {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
                </button>
              </>
            )}
          </div>
        </div>

        {/* Mobile Menu */}
        {mobileMenuOpen && (
          <div className="lg:hidden py-4 border-t border-gray-200 dark:border-gray-700">
            <div className="space-y-1">
              {/* Main Items */}
              {mainNavItems.map((link) => (
                <button
                  key={link.path}
                  onClick={() => {
                    router.push(link.path);
                    setMobileMenuOpen(false);
                  }}
                  className={`block w-full text-left px-4 py-2 text-sm rounded-md transition-colors ${
                    isLinkActive(link.path)
                      ? "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300 font-medium"
                      : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                  }`}
                >
                  {link.label}
                </button>
              ))}

              {/* Analytics Group */}
              <div className="px-4 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Analytics
              </div>
              {analyticsGroup.items.map((item) => (
                <button
                  key={item.path}
                  onClick={() => {
                    router.push(item.path);
                    setMobileMenuOpen(false);
                  }}
                  className={`block w-full text-left px-4 py-2 text-sm rounded-md transition-colors pl-8 ${
                    isLinkActive(item.path)
                      ? "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300 font-medium"
                      : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                  }`}
                >
                  {item.label}
                </button>
              ))}

              {/* Ecosystem Group */}
              <div className="px-4 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Ecosystem
              </div>
              {ecosystemGroup.items.map((item) => (
                <button
                  key={item.path}
                  onClick={() => {
                    router.push(item.path);
                    setMobileMenuOpen(false);
                  }}
                  className={`block w-full text-left px-4 py-2 text-sm rounded-md transition-colors pl-8 ${
                    isLinkActive(item.path)
                      ? "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300 font-medium"
                      : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                  }`}
                >
                  {item.label}
                </button>
              ))}

              {/* Admin Items */}
              {adminItems.length > 0 && (
                <>
                  <div className="px-4 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    Admin
                  </div>
                  {adminItems.map((item) => (
                    <button
                      key={item.path}
                      onClick={() => {
                        router.push(item.path);
                        setMobileMenuOpen(false);
                      }}
                      className={`block w-full text-left px-4 py-2 text-sm rounded-md transition-colors pl-8 ${
                        isLinkActive(item.path)
                          ? "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300 font-medium"
                          : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                      }`}
                    >
                      {item.label}
                    </button>
                  ))}
                </>
              )}
            </div>

            <div className="border-t border-gray-200 dark:border-gray-700 mt-4 pt-4 flex items-center justify-between px-4">
              <div className="flex items-center space-x-2">
                <span className={`px-2 py-1 rounded text-xs font-medium ${getRoleBadgeClass(user?.role ?? "")}`}>
                  {user?.role}
                </span>
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  {user?.username}
                </span>
              </div>
              <button
                onClick={handleLogout}
                className="px-4 py-2 text-sm text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-md"
              >
                Logout
              </button>
            </div>
          </div>
        )}
      </div>
    </nav>
  );
}
