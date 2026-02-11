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

  const navLinks = [
    { label: "Home", path: "/" },
    { label: "Runs", path: "/playbooks" },
    { label: "Definitions", path: "/playbooks/definitions" },
    { label: "Dify", path: "/dify" },
    { label: "Triggers", path: "/triggers" },
    ...(isAdmin(user ?? null) ? [{ label: "Settings", path: "/settings" }] : []),
    { label: "API Keys", path: "/settings/api-keys" },
    ...(isAdmin(user ?? null) || isAnalystOrAdmin(user ?? null) ? [{ label: "Audit", path: "/audit" }] : []),
    ...(isAdmin(user ?? null) ? [{ label: "Users", path: "/admin/users" }] : []),
  ];

  const isLinkActive = (linkPath: string) => {
    if (pathname === linkPath) return true;
    if (!pathname?.startsWith(linkPath + "/")) return false;
    
    // 检查是否有子路由匹配更精确的路径
    const remainingPath = pathname.slice(linkPath.length + 1);
    const nextSegment = remainingPath.split("/")[0];
    
    // 如果存在以当前路径+下一级开头的其他导航链接，则当前链接不应高亮
    const hasChildRoute = navLinks.some(
      l => l.path !== linkPath && l.path.startsWith(linkPath + "/" + nextSegment)
    );
    
    return !hasChildRoute;
  };

  return (
    <nav className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Left: Logo and Title */}
          <div className="flex items-center space-x-4">
            <button
              onClick={() => router.push("/")}
              className="text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 font-medium whitespace-nowrap"
            >
              SOC Copilot
            </button>
            <div className="hidden sm:block h-6 w-px bg-gray-300 dark:bg-gray-600"></div>
            <div className="hidden sm:block">
              <h1 className="text-lg font-semibold text-gray-900 dark:text-white truncate max-w-md">{title}</h1>
              {subtitle && (
                <p className="text-xs text-gray-500 dark:text-gray-400">{subtitle}</p>
              )}
            </div>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden lg:flex items-center space-x-1">
            {user && (
              <>
                {/* API Status (optional) */}
                {apiStatus && (
                  <>
                    <span className="text-xs text-gray-500 dark:text-gray-400 mr-1">API:</span>
                    <span
                      className={`px-2 py-1 rounded-full text-xs font-medium mr-2 ${
                        apiStatus === "healthy"
                          ? "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300"
                          : apiStatus === "checking"
                          ? "bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300"
                          : "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300"
                      }`}
                    >
                      {apiStatus === "healthy" ? "OK" : apiStatus === "checking" ? "..." : "Err"}
                    </span>
                  </>
                )}

                {/* Navigation Links */}
                {navLinks.map((link) => (
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

                <div className="h-6 w-px bg-gray-300 dark:bg-gray-600 mx-1"></div>

                {/* User Info */}
                <span className={`px-2 py-1 rounded text-xs font-medium ${getRoleBadgeClass(user.role)}`}>
                  {user.role}
                </span>
                <span className="text-sm text-gray-600 dark:text-gray-400 truncate max-w-32">
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
              {navLinks.map((link) => (
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
            </div>
            <div className="border-t border-gray-200 dark:border-gray-700 mt-4 pt-4 flex items-center justify-between">
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
