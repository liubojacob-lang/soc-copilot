"use client";

import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { useRouter, usePathname } from "@/i18n/navigation";
import { loadAuthState, logout, isAdmin } from "@/lib/auth";
import { useTranslations } from "next-intl";
import { X, Shield, LogOut, ChevronRight } from "lucide-react";
import { useFocusTrap } from "@/hooks/useFocusTrap";

interface MobileDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

interface NavItem {
  label: string;
  path: string;
}

interface NavGroup {
  label: string;
  items: NavItem[];
}

export default function MobileDrawer({ isOpen, onClose }: MobileDrawerProps) {
  const router = useRouter();
  const pathname = usePathname();
  const t = useTranslations("navigation");
  const tNav = useTranslations("nav");
  const tCommon = useTranslations("common");
  const [mounted, setMounted] = useState(false);

  const drawerRef = useRef<HTMLDivElement>(null);

  // Focus trap
  useFocusTrap(isOpen, onClose, drawerRef);

  useEffect(() => {
    setMounted(true);
  }, []);

  const authState = useMemo(() => {
    if (!mounted) return null;
    return loadAuthState();
  }, [mounted]);
  const user = authState?.user;

  const [expandedGroup, setExpandedGroup] = useState<string | null>(null);

  // Navigation groups
  const navGroups: NavGroup[] = [
    {
      label: tNav("dashboard"),
      items: [
        { label: tNav("home"), path: "/" },
        { label: tNav("runs"), path: "/playbooks" },
        { label: tNav("definitions"), path: "/playbooks/definitions" },
        { label: t("approvals"), path: "/playbooks/approvals" },
      ],
    },
    {
      label: tNav("analysis"),
      items: [
        { label: tNav("ai"), path: "/ai-assistant" },
        { label: tNav("ueba"), path: "/ueba" },
        { label: tNav("threatHunting"), path: "/threat-hunting" },
      ],
    },
    {
      label: tNav("ecosystem"),
      items: [
        { label: tNav("marketplace"), path: "/marketplace" },
        { label: tNav("cloudNative"), path: "/cloud-native" },
        { label: t("triggers"), path: "/triggers" },
      ],
    },
  ];

  // Admin items
  const adminItems: NavItem[] = isAdmin(user ?? null)
    ? [
        { label: t("settings"), path: "/settings" },
        { label: t("users"), path: "/admin/users" },
        { label: tCommon("secrets"), path: "/admin/secrets" },
        { label: t("audit"), path: "/audit" },
      ]
    : [];

  const isLinkActive = (linkPath: string) => {
    if (pathname === linkPath) return true;
    if (linkPath === "/playbooks") {
      return (
        pathname?.startsWith("/playbooks/") &&
        !pathname.startsWith("/playbooks/definitions") &&
        !pathname.startsWith("/playbooks/approvals")
      );
    }
    if (linkPath !== "/" && pathname?.startsWith(linkPath + "/")) return true;
    return false;
  };

  const handleNavigate = useCallback(
    (path: string) => {
      router.push(path);
      onClose();
    },
    [router, onClose]
  );

  const handleLogout = useCallback(() => {
    logout();
    router.push("/login");
    onClose();
  }, [router, onClose]);

  // Prevent body scroll when drawer is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen]);

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

  return (
    <>
      {/* Backdrop */}
      <div
        className={`fixed inset-0 bg-black/50 z-[200] transition-opacity duration-300 ${
          isOpen ? "opacity-100" : "opacity-0 pointer-events-none"
        }`}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Drawer */}
      <div
        ref={drawerRef}
        role="dialog"
        aria-modal="true"
        aria-label="导航菜单"
        tabIndex={-1}
        className={`fixed top-0 left-0 h-full w-80 max-w-[85vw] bg-white dark:bg-gray-800 z-[201] transform transition-transform duration-300 ease-out shadow-xl ${
          isOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2">
            <Shield className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            <span className="font-bold text-lg text-gray-900 dark:text-white">SOC Copilot</span>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700"
            aria-label="关闭菜单"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* User Info */}
        {user && (
          <div className="p-4 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-blue-100 dark:bg-blue-900 flex items-center justify-center">
                <span className="text-blue-600 dark:text-blue-300 font-semibold">
                  {user.username.charAt(0).toUpperCase()}
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                  {user.username}
                </p>
                <span
                  className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${getRoleBadgeClass(
                    user.role
                  )}`}
                >
                  {user.role}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto py-2">
          {navGroups.map((group) => (
            <div key={group.label} className="mb-2">
              <button
                onClick={() => setExpandedGroup(expandedGroup === group.label ? null : group.label)}
                className="w-full px-4 py-2 flex items-center justify-between text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider hover:bg-gray-100 dark:hover:bg-gray-700"
              >
                {group.label}
                <ChevronRight
                  className={`w-4 h-4 transition-transform ${
                    expandedGroup === group.label ? "rotate-90" : ""
                  }`}
                />
              </button>
              <div
                className={`overflow-hidden transition-all duration-200 ${
                  expandedGroup === group.label ? "max-h-96" : "max-h-0"
                }`}
              >
                {group.items.map((item) => (
                  <button
                    key={item.path}
                    onClick={() => handleNavigate(item.path)}
                    className={`w-full px-4 py-3 flex items-center text-left transition-colors ${
                      isLinkActive(item.path)
                        ? "bg-blue-50 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300 border-r-2 border-blue-600"
                        : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                    }`}
                  >
                    <span className="font-medium">{item.label}</span>
                  </button>
                ))}
              </div>
            </div>
          ))}

          {/* Admin Section */}
          {adminItems.length > 0 && (
            <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
              <button
                onClick={() => setExpandedGroup(expandedGroup === "admin" ? null : "admin")}
                className="w-full px-4 py-2 flex items-center justify-between text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider hover:bg-gray-100 dark:hover:bg-gray-700"
              >
                {tCommon("admin")}
                <ChevronRight
                  className={`w-4 h-4 transition-transform ${
                    expandedGroup === "admin" ? "rotate-90" : ""
                  }`}
                />
              </button>
              <div
                className={`overflow-hidden transition-all duration-200 ${
                  expandedGroup === "admin" ? "max-h-96" : "max-h-0"
                }`}
              >
                {adminItems.map((item) => (
                  <button
                    key={item.path}
                    onClick={() => handleNavigate(item.path)}
                    className={`w-full px-4 py-3 flex items-center text-left transition-colors ${
                      isLinkActive(item.path)
                        ? "bg-purple-50 text-purple-700 dark:bg-purple-900/50 dark:text-purple-300 border-r-2 border-purple-600"
                        : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                    }`}
                  >
                    <span className="font-medium">{item.label}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={handleLogout}
            className="w-full py-2 px-4 flex items-center justify-center gap-2 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
          >
            <LogOut className="w-5 h-5" />
            <span>{t("logout")}</span>
          </button>
        </div>
      </div>
    </>
  );
}
