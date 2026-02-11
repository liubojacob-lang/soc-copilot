"use client";

import { useRouter, usePathname } from "next/navigation";
import { loadAuthState, logout, isAdmin, isAnalystOrAdmin } from "@/lib/auth";
import { useState } from "react";
import { Menu, X } from "lucide-react";

interface NavigationProps {
  title: string;
  subtitle?: string;
  apiStatus?: "healthy" | "checking" | "error";
}

export default function Navigation({ title, subtitle, apiStatus }: NavigationProps) {
  const router = useRouter();
  const pathname = usePathname();
  const authState = loadAuthState();
  const user = authState?.user;
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

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

  // All navigation items in flat structure for easy debugging
  const navItems = [
    { label: "Home", path: "/" },
    { label: "Runs", path: "/playbooks" },
    { label: "Definitions", path: "/playbooks/definitions" },
    { label: "AI", path: "/ai-assistant" },
    { label: "UEBA", path: "/ueba" },
    { label: "Hunting", path: "/threat-hunting" },
    { label: "Market", path: "/marketplace" },
    { label: "Cloud", path: "/cloud-native" },
    { label: "Dify", path: "/dify" },
    { label: "Triggers", path: "/triggers" },
    ...(isAdmin(user ?? null) ? [{ label: "Settings", path: "/settings" }] : []),
    ...(isAdmin(user ?? null) ? [{ label: "Users", path: "/admin/users" }] : []),
  ];

  const isLinkActive = (linkPath: string) => {
    if (pathname === linkPath) return true;
    if (linkPath !== "/" && pathname?.startsWith(linkPath)) return true;
    return false;
  };

  return (
    <nav className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
      <div className="max-w-7xl mx-auto px-2 sm:px-4">
        <div className="flex justify-between items-center h-14">
          {/* Left: Logo and Title */}
          <div className="flex items-center space-x-2">
            <button
              onClick={() => router.push("/")}
              className="text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 font-bold text-sm whitespace-nowrap"
            >
              SOC
            </button>
            <div className="hidden sm:block h-4 w-px bg-gray-300 dark:bg-gray-600"></div>
            <div className="hidden sm:block">
              <h1 className="text-sm font-semibold text-gray-900 dark:text-white truncate max-w-[120px] lg:max-w-md">{title}</h1>
              {subtitle && (
                <p className="text-[10px] text-gray-500 dark:text-gray-400">{subtitle}</p>
              )}
            </div>
          </div>

          {/* Desktop Navigation - Compact */}
          <div className="hidden xl:flex items-center space-x-0.5">
            {user && (
              <>
                {/* API Status */}
                {apiStatus && (
                  <span
                    className={`px-1.5 py-0.5 rounded text-[10px] font-medium mr-1 ${
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

                {/* Nav Links - Compact */}
                {navItems.map((link) => (
                  <button
                    key={link.path}
                    onClick={() => router.push(link.path)}
                    className={`px-2 py-1.5 text-xs rounded whitespace-nowrap transition-colors ${
                      isLinkActive(link.path)
                        ? "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300 font-medium"
                        : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                    }`}
                  >
                    {link.label}
                  </button>
                ))}

                <div className="h-4 w-px bg-gray-300 dark:bg-gray-600 mx-1"></div>

                {/* User Info - Compact */}
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
                  Exit
                </button>
              </>
            )}
          </div>

          {/* Tablet Navigation - Show fewer items */}
          <div className="hidden lg:flex xl:hidden items-center space-x-0.5">
            {user && (
              <>
                {navItems.slice(0, 8).map((link) => (
                  <button
                    key={link.path}
                    onClick={() => router.push(link.path)}
                    className={`px-2 py-1.5 text-xs rounded whitespace-nowrap transition-colors ${
                      isLinkActive(link.path)
                        ? "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300 font-medium"
                        : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                    }`}
                  >
                    {link.label}
                  </button>
                ))}
                <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${getRoleBadgeClass(user.role)}`}>
                  {user.role}
                </span>
                <button
                  onClick={handleLogout}
                  className="px-2 py-1.5 text-xs text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
                >
                  Exit
                </button>
              </>
            )}
          </div>

          {/* Mobile Menu Button */}
          <div className="lg:hidden flex items-center space-x-2">
            {user && (
              <>
                <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${getRoleBadgeClass(user.role)}`}>
                  {user.role}
                </span>
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

        {/* Mobile Menu */}
        {mobileMenuOpen && (
          <div className="lg:hidden py-2 border-t border-gray-200 dark:border-gray-700">
            <div className="grid grid-cols-3 gap-1">
              {navItems.map((link) => (
                <button
                  key={link.path}
                  onClick={() => {
                    router.push(link.path);
                    setMobileMenuOpen(false);
                  }}
                  className={`px-2 py-2 text-xs rounded transition-colors text-center ${
                    isLinkActive(link.path)
                      ? "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300 font-medium"
                      : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                  }`}
                >
                  {link.label}
                </button>
              ))}
            </div>
            <div className="border-t border-gray-200 dark:border-gray-700 mt-2 pt-2 flex items-center justify-between px-2">
              <span className="text-xs text-gray-600 dark:text-gray-400">
                {user?.username}
              </span>
              <button
                onClick={handleLogout}
                className="px-3 py-1.5 text-xs text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
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
