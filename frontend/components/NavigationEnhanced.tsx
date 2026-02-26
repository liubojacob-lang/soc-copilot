"use client";

import { useRouter, usePathname } from "next/navigation";
import { loadAuthState, logout, isAdmin, isAnalystOrAdmin } from "@/lib/auth";
import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import {
  Menu,
  X,
  Search,
  ChevronDown,
} from "lucide-react";
import Breadcrumbs from "./common/Breadcrumbs";
import MobileDrawer from "./common/MobileDrawer";
import { useResponsive } from "./common/ResponsiveLayout";

interface NavigationProps {
  title: string;
  subtitle?: string;
  apiStatus?: "healthy" | "checking" | "error";
}

// Navigation group configuration
interface NavItem {
  label: string;
  path: string;
  badge?: string;
  children?: NavItem[];
}

interface NavGroup {
  label: string;
  items: NavItem[];
}

export default function NavigationEnhanced({ title, subtitle, apiStatus }: NavigationProps) {
  const router = useRouter();
  const pathname = usePathname();
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
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeDropdown, setActiveDropdown] = useState<string | null>(null);
  const [keyboardNavIndex, setKeyboardNavIndex] = useState(-1);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const dropdownRefs = useRef<Record<string, HTMLDivElement>>({});

  // Navigation groups configuration
  const navGroups: NavGroup[] = [
    {
      label: "Core",
      items: [
        { label: "Home", path: "/" },
        { label: "Runs", path: "/playbooks" },
        { label: "Definitions", path: "/playbooks/definitions" },
        { label: "Approvals", path: "/playbooks/approvals" },
      ],
    },
    {
      label: "Analysis",
      items: [
        { label: "AI", path: "/ai-assistant" },
        { label: "UEBA", path: "/ueba" },
        { label: "Hunting", path: "/threat-hunting" },
      ],
    },
    {
      label: "Integrations",
      items: [
        { label: "Market", path: "/marketplace" },
        { label: "Cloud", path: "/cloud-native" },
        { label: "Dify", path: "/dify" },
        { label: "Triggers", path: "/triggers" },
      ],
    },
  ];

  // Admin navigation items
  const adminItems: NavItem[] = isAdmin(user ?? null)
    ? [
        { label: "Settings", path: "/settings" },
        { label: "Users", path: "/admin/users" },
        { label: "Secrets", path: "/admin/secrets" },
        { label: "Audit", path: "/audit" },
      ]
    : [];

  // Flatten all items for search
  const allNavItems = [
    ...navGroups.flatMap((g) => g.items),
    ...adminItems,
  ];

  // Filter items based on search
  const filteredItems = searchQuery
    ? allNavItems.filter((item) =>
        item.label.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : allNavItems;

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

  const isLinkActive = (linkPath: string) => {
    if (pathname === linkPath) return true;
    if (linkPath === "/playbooks") {
      if (
        pathname?.startsWith("/playbooks/") &&
        !pathname.startsWith("/playbooks/definitions") &&
        !pathname.startsWith("/playbooks/approvals")
      ) {
        return true;
      }
      return false;
    }
    if (linkPath !== "/" && pathname?.startsWith(linkPath + "/")) return true;
    return false;
  };

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Global shortcuts
      if (e.key === "/" && !searchOpen && !e.ctrlKey && !e.metaKey) {
        e.preventDefault();
        setSearchOpen(true);
        setTimeout(() => searchInputRef.current?.focus(), 0);
      }

      if (e.key === "Escape") {
        if (searchOpen) {
          setSearchOpen(false);
          setSearchQuery("");
        }
        if (activeDropdown) {
          setActiveDropdown(null);
        }
        if (mobileMenuOpen) {
          setMobileMenuOpen(false);
        }
      }

      // Navigation within search results
      if (searchOpen && filteredItems.length > 0) {
        if (e.key === "ArrowDown") {
          e.preventDefault();
          setKeyboardNavIndex((prev) =>
            prev < filteredItems.length - 1 ? prev + 1 : 0
          );
        } else if (e.key === "ArrowUp") {
          e.preventDefault();
          setKeyboardNavIndex((prev) =>
            prev > 0 ? prev - 1 : filteredItems.length - 1
          );
        } else if (e.key === "Enter" && keyboardNavIndex >= 0) {
          e.preventDefault();
          router.push(filteredItems[keyboardNavIndex].path);
          setSearchOpen(false);
          setSearchQuery("");
          setKeyboardNavIndex(-1);
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [searchOpen, filteredItems, keyboardNavIndex, router, activeDropdown, mobileMenuOpen]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      // Check if click is outside all dropdown refs
      const isOutside = Object.values(dropdownRefs.current).every(
        (ref) => !ref || !ref.contains(e.target as Node)
      );
      if (isOutside) {
        setActiveDropdown(null);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Navigate to page
  const navigateTo = useCallback(
    (path: string) => {
      router.push(path);
      setMobileMenuOpen(false);
      setSearchOpen(false);
      setSearchQuery("");
      setActiveDropdown(null);
      setKeyboardNavIndex(-1);
    },
    [router]
  );

  return (
    <>
      <nav className="sticky top-0 z-50 bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-2 sm:px-4">
          <div className="flex justify-between items-center h-14">
            {/* Left: Logo and Title */}
            <div className="flex items-center space-x-2">
              <button
                onClick={() => navigateTo("/")}
                className="text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 font-bold text-sm whitespace-nowrap flex items-center gap-1"
              >
                <Shield className="w-4 h-4" />
                SOC
              </button>
              <div className="hidden sm:block h-4 w-px bg-gray-300 dark:bg-gray-600"></div>
              <div className="hidden sm:block">
                <h1 className="text-sm font-semibold text-gray-900 dark:text-white truncate max-w-[120px] lg:max-w-md">
                  {title}
                </h1>
                {subtitle && (
                  <p className="text-[10px] text-gray-500 dark:text-gray-400">
                    {subtitle}
                  </p>
                )}
              </div>
            </div>

            {/* Desktop Navigation - Grouped Dropdowns */}
            <div className="hidden xl:flex items-center space-x-1">
              {user && (
                <>
                  {/* API Status */}
                  {apiStatus && (
                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] font-medium mr-2 ${
                        apiStatus === "healthy"
                          ? "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300"
                          : apiStatus === "checking"
                          ? "bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300"
                          : "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300"
                      }`}
                    >
                      {apiStatus === "healthy"
                        ? "OK"
                        : apiStatus === "checking"
                        ? "..."
                        : "Err"}
                    </span>
                  )}

                  {/* Navigation Groups as Dropdowns */}
                  {navGroups.map((group) => (
                    <div
                      key={group.label}
                      className="relative"
                      ref={(el) => {
                        if (el) dropdownRefs.current[group.label] = el;
                      }}
                    >
                      <button
                        onClick={() =>
                          setActiveDropdown(
                            activeDropdown === group.label ? null : group.label
                          )
                        }
                        className={`px-2 py-1.5 text-xs rounded flex items-center gap-1 transition-colors ${
                          group.items.some((item) => isLinkActive(item.path))
                            ? "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300 font-medium"
                            : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                        }`}
                      >
                        {group.label}
                        <ChevronDown
                          className={`w-3 h-3 transition-transform ${
                            activeDropdown === group.label ? "rotate-180" : ""
                          }`}
                        />
                      </button>

                      {activeDropdown === group.label && (
                        <div className="absolute top-full left-0 pt-1 w-48 bg-white dark:bg-gray-800 rounded-md shadow-lg border border-gray-200 dark:border-gray-700 py-1 z-50">
                          {group.items.map((item) => (
                            <button
                              key={item.path}
                              onClick={() => navigateTo(item.path)}
                              className={`w-full px-4 py-2 text-sm text-left transition-colors ${
                                isLinkActive(item.path)
                                  ? "bg-blue-50 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300"
                                  : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                              }`}
                            >
                              {item.label}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}

                  {/* Admin Dropdown */}
                  {adminItems.length > 0 && (
                    <div
                      className="relative"
                      ref={(el) => {
                        if (el) dropdownRefs.current["admin"] = el;
                      }}
                    >
                      <button
                        onClick={() =>
                          setActiveDropdown(
                            activeDropdown === "admin" ? null : "admin"
                          )
                        }
                        className={`px-2 py-1.5 text-xs rounded flex items-center gap-1 transition-colors ${
                          adminItems.some((item) => isLinkActive(item.path))
                            ? "bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300 font-medium"
                            : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                        }`}
                      >
                        Admin
                        <ChevronDown
                          className={`w-3 h-3 transition-transform ${
                            activeDropdown === "admin" ? "rotate-180" : ""
                          }`}
                        />
                      </button>

                      {activeDropdown === "admin" && (
                        <div className="absolute top-full right-0 pt-1 w-48 bg-white dark:bg-gray-800 rounded-md shadow-lg border border-gray-200 dark:border-gray-700 py-1 z-50">
                          {adminItems.map((item) => (
                            <button
                              key={item.path}
                              onClick={() => navigateTo(item.path)}
                              className={`w-full px-4 py-2 text-sm text-left transition-colors ${
                                isLinkActive(item.path)
                                  ? "bg-purple-50 text-purple-700 dark:bg-purple-900/50 dark:text-purple-300"
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

                  <div className="h-4 w-px bg-gray-300 dark:bg-gray-600 mx-1"></div>

                  {/* Search Button */}
                  <button
                    onClick={() => {
                      setSearchOpen(true);
                      setTimeout(() => searchInputRef.current?.focus(), 0);
                    }}
                    className="p-1.5 rounded text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700"
                    title="Search (Press /)"
                  >
                    <Search className="w-4 h-4" />
                  </button>

                  {/* User Info */}
                  <span
                    className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${getRoleBadgeClass(
                      user.role
                    )}`}
                  >
                    {user.role}
                  </span>
                  <span className="text-xs text-gray-600 dark:text-gray-400 truncate max-w-[80px]">
                    {user.username}
                  </span>
                  <button
                    onClick={handleLogout}
                    className="p-1.5 text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
                    title="Logout"
                  >
                    <LogOut className="w-4 h-4" />
                  </button>
                </>
              )}
            </div>

            {/* Tablet Navigation - Compact */}
            <div className="hidden lg:flex xl:hidden items-center space-x-0.5">
              {user && (
                <>
                  {allNavItems.slice(0, 6).map((link) => (
                    <button
                      key={link.path}
                      onClick={() => navigateTo(link.path)}
                      className={`px-2 py-1.5 text-xs rounded whitespace-nowrap transition-colors ${
                        isLinkActive(link.path)
                          ? "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300 font-medium"
                          : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                      }`}
                    >
                      {link.label}
                    </button>
                  ))}
                  <button
                    onClick={() => {
                      setSearchOpen(true);
                      setTimeout(() => searchInputRef.current?.focus(), 0);
                    }}
                    className="p-1.5 rounded text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700"
                  >
                    <Search className="w-4 h-4" />
                  </button>
                  <span
                    className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${getRoleBadgeClass(
                      user.role
                    )}`}
                  >
                    {user.role}
                  </span>
                  <button
                    onClick={handleLogout}
                    className="p-1.5 text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
                  >
                    <LogOut className="w-4 h-4" />
                  </button>
                </>
              )}
            </div>

            {/* Mobile Menu Button */}
            <div className="lg:hidden flex items-center space-x-2">
              {user && (
                <>
                  <button
                    onClick={() => {
                      setSearchOpen(true);
                      setTimeout(() => searchInputRef.current?.focus(), 0);
                    }}
                    className="p-1.5 rounded text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700"
                  >
                    <Search className="w-4 h-4" />
                  </button>
                  <span
                    className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${getRoleBadgeClass(
                      user.role
                    )}`}
                  >
                    {user.role}
                  </span>
                  <button
                    onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                    className="p-1.5 rounded-md text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                  >
                    {mobileMenuOpen ? (
                      <X className="w-4 h-4" />
                    ) : (
                      <Menu className="w-4 h-4" />
                    )}
                  </button>
                </>
              )}
            </div>
          </div>

          {/* Breadcrumbs Row */}
          <div className="hidden sm:block pb-2">
            <Breadcrumbs />
          </div>
        </div>

        {/* Mobile Menu */}
        {mobileMenuOpen && (
          <div className="lg:hidden border-t border-gray-200 dark:border-gray-700">
            <div className="max-h-[70vh] overflow-y-auto">
              {navGroups.map((group) => (
                <div key={group.label} className="py-2">
                  <div className="px-4 py-1 text-[10px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider">
                    {group.label}
                  </div>
                  <div className="grid grid-cols-2 gap-1 px-2">
                    {group.items.map((link) => (
                      <button
                        key={link.path}
                        onClick={() => navigateTo(link.path)}
                        className={`px-3 py-2 text-xs rounded transition-colors ${
                          isLinkActive(link.path)
                            ? "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300 font-medium"
                            : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                        }`}
                      >
                        {link.label}
                      </button>
                    ))}
                  </div>
                </div>
              ))}

              {/* Admin Section */}
              {adminItems.length > 0 && (
                <div className="py-2 border-t border-gray-200 dark:border-gray-700">
                  <div className="px-4 py-1 text-[10px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider">
                    Admin
                  </div>
                  <div className="grid grid-cols-2 gap-1 px-2">
                    {adminItems.map((link) => (
                      <button
                        key={link.path}
                        onClick={() => navigateTo(link.path)}
                        className={`px-3 py-2 text-xs rounded transition-colors ${
                          isLinkActive(link.path)
                            ? "bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300 font-medium"
                            : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                        }`}
                      >
                        {link.label}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* User Section */}
              <div className="border-t border-gray-200 dark:border-gray-700 py-2 px-4 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span
                    className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${getRoleBadgeClass(
                      user?.role || ""
                    )}`}
                  >
                    {user?.role}
                  </span>
                  <span className="text-xs text-gray-600 dark:text-gray-400">
                    {user?.username}
                  </span>
                </div>
                <button
                  onClick={handleLogout}
                  className="px-3 py-1.5 text-xs text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 hover:bg-red-50 dark:hover:bg-red-900/20 rounded flex items-center gap-1"
                >
                  <LogOut className="w-3 h-3" />
                  Logout
                </button>
              </div>
            </div>
          </div>
        )}
      </nav>

      {/* Search Modal */}
      {searchOpen && (
        <div className="fixed inset-0 z-[100] bg-black/50 flex items-start justify-center pt-20">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-lg mx-4 overflow-hidden">
            <div className="p-4 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-2">
                <Search className="w-5 h-5 text-gray-400" />
                <input
                  ref={searchInputRef}
                  type="text"
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value);
                    setKeyboardNavIndex(-1);
                  }}
                  placeholder="Search navigation... (Press / to focus)"
                  className="flex-1 bg-transparent border-none outline-none text-gray-900 dark:text-white placeholder-gray-400"
                />
                <kbd className="hidden sm:inline-flex items-center px-2 py-1 text-xs text-gray-400 bg-gray-100 dark:bg-gray-700 rounded">
                  ESC
                </kbd>
              </div>
            </div>

            <div className="max-h-80 overflow-y-auto">
              {filteredItems.length > 0 ? (
                <div className="py-2">
                  {filteredItems.map((item, index) => (
                    <button
                      key={item.path}
                      onClick={() => navigateTo(item.path)}
                      className={`w-full px-4 py-2 text-left flex items-center gap-3 transition-colors ${
                        index === keyboardNavIndex
                          ? "bg-blue-50 dark:bg-blue-900/50"
                          : "hover:bg-gray-100 dark:hover:bg-gray-700"
                      }`}
                    >
                      <span className="text-sm text-gray-900 dark:text-white">
                        {item.label}
                      </span>
                      <span className="text-xs text-gray-400 ml-auto">
                        {item.path}
                      </span>
                    </button>
                  ))}
                </div>
              ) : (
                <div className="py-8 text-center text-gray-500 dark:text-gray-400">
                  <Search className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">No results found</p>
                </div>
              )}
            </div>

            <div className="p-2 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between text-xs text-gray-400">
              <div className="flex items-center gap-2">
                <kbd className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 rounded">
                  ↑↓
                </kbd>
                <span>Navigate</span>
              </div>
              <div className="flex items-center gap-2">
                <kbd className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 rounded">
                  Enter
                </kbd>
                <span>Select</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Keyboard Shortcuts Help */}
      <div className="fixed bottom-4 right-4 hidden lg:block">
        <button
          onClick={() => {
            setSearchOpen(true);
            setTimeout(() => searchInputRef.current?.focus(), 0);
          }}
          className="flex items-center gap-2 px-3 py-2 bg-white dark:bg-gray-800 rounded-lg shadow-md border border-gray-200 dark:border-gray-700 text-xs text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700"
        >
          <Keyboard className="w-4 h-4" />
          <span>Press</span>
          <kbd className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 rounded font-mono">
            /
          </kbd>
          <span>to search</span>
        </button>
      </div>

      {/* Mobile Drawer - Only render on mobile/tablet */}
      <div className="lg:hidden">
        <MobileDrawer
          isOpen={mobileMenuOpen}
          onClose={() => setMobileMenuOpen(false)}
        />
      </div>
    </>
  );
}
