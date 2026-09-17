"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import {
  ChevronDown,
  ChevronRight,
  LogOut,
  Settings,
  Lock,
  Users,
  ScrollText,
  ShieldCheck,
  ShieldAlert,
  Keyboard,
} from "lucide-react";
import type { User } from "@/lib/types";
import { isAdmin, isAnalystOrAdmin } from "@/lib/auth";

interface UserMenuProps {
  user: User;
  onLogout: () => void;
  getRoleBadgeClass?: (role: string) => string;
}

export function UserMenu({ user, onLogout, getRoleBadgeClass }: UserMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const locale = useLocale();
  const isZh = locale.startsWith("zh");
  const tNav = useTranslations("navigation");

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      document.addEventListener("keydown", handleKeyDown);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  const defaultBadgeClass = useCallback((role: string) => {
    switch (role) {
      case "admin":
        return "bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300 border border-purple-300/40 dark:border-purple-700/40";
      case "analyst":
        return "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300 border border-blue-300/40 dark:border-blue-700/40";
      case "auditor":
        return "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300 border border-emerald-300/40 dark:border-emerald-700/40";
      default:
        return "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300 border border-gray-300/40 dark:border-gray-600/40";
    }
  }, []);

  const badgeClass = getRoleBadgeClass
    ? getRoleBadgeClass(user.role)
    : defaultBadgeClass(user.role);

  const initial = (user.username || "U").charAt(0).toUpperCase();
  const is2FA = Boolean(user.is_totp_enabled);
  const totpPolicy = user.totp_policy || "sudo";

  const closeMenu = () => setIsOpen(false);

  return (
    <div className="relative shrink-0" ref={menuRef}>
      {/* Navbar trigger button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={`h-8 inline-flex items-center gap-2 p-1 pr-2.5 rounded-xl border transition-all duration-150 select-none shadow-subtle shrink-0 whitespace-nowrap focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-500 cursor-pointer ${
          isOpen
            ? "border-accent-500/80 bg-accent-50/70 dark:bg-accent-950/50 text-accent-700 dark:text-accent-300 ring-2 ring-accent-500/20"
            : "bg-gray-100/90 dark:bg-gray-800/90 border-gray-200/80 dark:border-gray-700/80 hover:bg-gray-200/70 dark:hover:bg-gray-750 text-gray-700 dark:text-gray-200"
        }`}
        aria-expanded={isOpen}
        aria-haspopup="menu"
        aria-label="User account menu"
      >
        {/* Avatar with gradient & online indicator */}
        <div className="relative shrink-0">
          <div className="w-6 h-6 rounded-lg bg-gradient-to-tr from-accent-600 via-indigo-600 to-purple-600 text-white font-bold text-[10px] flex items-center justify-center shadow-subtle">
            {initial}
          </div>
          <span
            className="absolute -bottom-0.5 -right-0.5 w-2 h-2 rounded-full bg-emerald-500 ring-1.5 ring-white dark:ring-gray-900"
            title={tNav("online")}
          />
        </div>

        {/* Username */}
        <span className="text-xs font-semibold max-w-[5rem] xl:max-w-[7.5rem] truncate leading-none">
          {user.username}
        </span>

        {/* Role tag */}
        <span
          className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider ${badgeClass} hidden sm:inline-block leading-none`}
        >
          {user.role}
        </span>

        {/* Caret icon */}
        <ChevronDown
          className={`w-3 h-3 text-gray-400 dark:text-gray-500 transition-transform duration-200 ${
            isOpen ? "rotate-180 text-accent-600 dark:text-accent-400" : ""
          }`}
        />
      </button>

      {/* SOC Security Cockpit Menu Popover */}
      {isOpen && (
        <div
          role="menu"
          className="absolute right-0 top-full mt-2 w-[284px] rounded-2xl bg-white dark:bg-gray-900 border border-gray-200/90 dark:border-gray-800 shadow-2xl shadow-slate-900/15 dark:shadow-black/60 p-2.5 z-50 animate-in fade-in-0 zoom-in-95 duration-150"
        >
          {/* 1. Identity & Security Posture Header Card */}
          <div className="p-3 rounded-xl bg-gray-50/80 dark:bg-gray-800/40 border border-gray-100 dark:border-gray-800 space-y-2.5">
            {/* User Details */}
            <div className="flex items-center gap-3">
              <div className="relative shrink-0">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-accent-600 via-indigo-600 to-purple-600 text-white text-sm font-bold flex items-center justify-center shadow-subtle ring-1 ring-black/5 dark:ring-white/10">
                  {initial}
                </div>
                <span
                  className="absolute -bottom-0.5 -right-0.5 flex h-3 w-3 items-center justify-center"
                  title={isZh ? "在线状态：正常" : "Status: Online"}
                >
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-60" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500 ring-2 ring-white dark:ring-gray-800" />
                </span>
              </div>

              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-1.5">
                  <span className="text-sm font-bold text-gray-900 dark:text-white truncate leading-tight">
                    {user.username}
                  </span>
                  <span
                    className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider ${badgeClass} shrink-0 leading-none`}
                  >
                    {user.role}
                  </span>
                </div>
                <div
                  className="text-xs text-gray-500 dark:text-gray-400 truncate mt-0.5"
                  title={user.email || `${user.username}@soc.local`}
                >
                  {user.email || `${user.username}@soc.local`}
                </div>
              </div>
            </div>

            {/* Account Security Posture Badge */}
            <Link
              href="/settings"
              onClick={closeMenu}
              className={`group flex items-center justify-between p-2 rounded-lg border transition-all text-xs select-none ${
                is2FA
                  ? "bg-emerald-50/70 hover:bg-emerald-100/70 dark:bg-emerald-950/25 dark:hover:bg-emerald-900/40 border-emerald-200/70 dark:border-emerald-800/40 text-emerald-800 dark:text-emerald-300"
                  : "bg-amber-50/70 hover:bg-amber-100/70 dark:bg-amber-950/25 dark:hover:bg-amber-900/40 border-amber-200/70 dark:border-amber-800/40 text-amber-800 dark:text-amber-300"
              }`}
            >
              <div className="flex items-center gap-2 min-w-0">
                <div
                  className={`w-5 h-5 rounded-md flex items-center justify-center shrink-0 ${
                    is2FA
                      ? "bg-emerald-100 text-emerald-600 dark:bg-emerald-900/60 dark:text-emerald-400"
                      : "bg-amber-100 text-amber-600 dark:bg-amber-900/60 dark:text-amber-400"
                  }`}
                >
                  {is2FA ? (
                    <ShieldCheck className="w-3.5 h-3.5" />
                  ) : (
                    <ShieldAlert className="w-3.5 h-3.5" />
                  )}
                </div>
                <span className="font-semibold text-xs truncate">
                  {is2FA
                    ? isZh
                      ? "2FA 保护已启用"
                      : "2FA Protected"
                    : isZh
                      ? "2FA 双因素未启用"
                      : "2FA Inactive"}
                </span>
              </div>
              <span
                className={`px-1.5 py-0.5 rounded text-[10px] font-semibold shrink-0 transition-transform group-hover:translate-x-0.5 flex items-center gap-0.5 ${
                  is2FA
                    ? "bg-emerald-200/80 text-emerald-900 dark:bg-emerald-900/80 dark:text-emerald-200"
                    : "bg-amber-200/80 text-amber-900 dark:bg-amber-900/80 dark:text-amber-200"
                }`}
              >
                <span>
                  {is2FA
                    ? totpPolicy === "login"
                      ? isZh
                        ? "登录保护"
                        : "Login"
                      : isZh
                        ? "Sudo 模式"
                        : "Sudo"
                    : isZh
                      ? "立即配置"
                      : "Setup"}
                </span>
                <ChevronRight className="w-3 h-3 opacity-70" />
              </span>
            </Link>
          </div>

          {/* 2. Group: 个人中心 / Personal */}
          <div className="pt-2 pb-1">
            <div className="px-3 pb-1.5 text-[10px] font-bold uppercase tracking-wider text-gray-400 dark:text-gray-500">
              {isZh ? "个人中心" : "Personal"}
            </div>
            <div className="space-y-0.5">
              <Link
                href="/settings"
                onClick={closeMenu}
                className="flex items-center justify-between px-3 py-2 text-xs font-medium text-gray-700 dark:text-gray-200 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100/90 dark:hover:bg-gray-800/90 rounded-xl transition-all group cursor-pointer"
              >
                <div className="flex items-center gap-2.5">
                  <Settings className="w-4 h-4 text-gray-400 dark:text-gray-500 group-hover:text-accent-600 dark:group-hover:text-accent-400 transition-colors shrink-0" />
                  <span>{isZh ? "偏好与系统设置" : tNav("settings")}</span>
                </div>
                <ChevronRight className="w-3.5 h-3.5 text-gray-400 opacity-0 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all" />
              </Link>

              <Link
                href="/change-password"
                onClick={closeMenu}
                className="flex items-center justify-between px-3 py-2 text-xs font-medium text-gray-700 dark:text-gray-200 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100/90 dark:hover:bg-gray-800/90 rounded-xl transition-all group cursor-pointer"
              >
                <div className="flex items-center gap-2.5">
                  <Lock className="w-4 h-4 text-gray-400 dark:text-gray-500 group-hover:text-accent-600 dark:group-hover:text-accent-400 transition-colors shrink-0" />
                  <span>{tNav("changePassword")}</span>
                </div>
                <ChevronRight className="w-3.5 h-3.5 text-gray-400 opacity-0 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all" />
              </Link>
            </div>
          </div>

          {/* 3. Group: 平台管理 / Administration (Only for Admin/Analyst) */}
          {(isAdmin(user) || isAnalystOrAdmin(user)) && (
            <div className="pt-2 pb-1 border-t border-gray-100 dark:border-gray-800/80 mt-1">
              <div className="px-3 pb-1.5 text-[10px] font-bold uppercase tracking-wider text-gray-400 dark:text-gray-500">
                {isZh ? "平台管理" : "Administration"}
              </div>
              <div className="space-y-0.5">
                {isAdmin(user) && (
                  <Link
                    href="/admin/users"
                    onClick={closeMenu}
                    className="flex items-center justify-between px-3 py-2 text-xs font-medium text-gray-700 dark:text-gray-200 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100/90 dark:hover:bg-gray-800/90 rounded-xl transition-all group cursor-pointer"
                  >
                    <div className="flex items-center gap-2.5">
                      <Users className="w-4 h-4 text-gray-400 dark:text-gray-500 group-hover:text-accent-600 dark:group-hover:text-accent-400 transition-colors shrink-0" />
                      <span>{isZh ? "团队与权限" : tNav("users")}</span>
                    </div>
                    <span className="px-1.5 py-0.5 rounded text-[9px] font-mono font-medium bg-purple-50 dark:bg-purple-950/40 text-purple-600 dark:text-purple-400 border border-purple-200/50 dark:border-purple-800/50">
                      RBAC
                    </span>
                  </Link>
                )}

                <Link
                  href="/audit"
                  onClick={closeMenu}
                  className="flex items-center justify-between px-3 py-2 text-xs font-medium text-gray-700 dark:text-gray-200 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100/90 dark:hover:bg-gray-800/90 rounded-xl transition-all group cursor-pointer"
                >
                  <div className="flex items-center gap-2.5">
                    <ScrollText className="w-4 h-4 text-gray-400 dark:text-gray-500 group-hover:text-accent-600 dark:group-hover:text-accent-400 transition-colors shrink-0" />
                    <span>{isZh ? "操作审计合规" : tNav("audit")}</span>
                  </div>
                  <ChevronRight className="w-3.5 h-3.5 text-gray-400 opacity-0 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all" />
                </Link>
              </div>
            </div>
          )}

          <div className="border-t border-gray-100 dark:border-gray-800/80 my-1" />

          {/* 4. Footer Actions (Keyboard Shortcut Help & Logout) */}
          <div className="space-y-0.5 pt-0.5">
            <button
              type="button"
              onClick={() => {
                closeMenu();
                document.dispatchEvent(new KeyboardEvent("keydown", { key: "?" }));
              }}
              className="w-full flex items-center justify-between px-3 py-2 text-xs font-medium text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100/90 dark:hover:bg-gray-800/90 rounded-xl transition-all group cursor-pointer"
            >
              <div className="flex items-center gap-2.5">
                <Keyboard className="w-4 h-4 text-gray-400 dark:text-gray-500 group-hover:text-accent-600 dark:group-hover:text-accent-400 transition-colors shrink-0" />
                <span>{isZh ? "键盘快捷键帮助" : "Keyboard Shortcuts"}</span>
              </div>
              <kbd className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 border border-gray-200 dark:border-gray-700 shadow-subtle leading-none">
                ?
              </kbd>
            </button>

            <button
              type="button"
              onClick={() => {
                closeMenu();
                onLogout();
              }}
              className="w-full flex items-center justify-between px-3 py-2 text-xs font-medium text-red-600 dark:text-red-400 hover:bg-red-50/80 dark:hover:bg-red-950/30 rounded-xl transition-all group cursor-pointer"
            >
              <div className="flex items-center gap-2.5">
                <LogOut className="w-4 h-4 text-red-500 dark:text-red-400 group-hover:translate-x-0.5 transition-transform shrink-0" />
                <span>{tNav("logout")}</span>
              </div>
              <span className="text-[10px] text-red-400/80 dark:text-red-400/60 font-mono opacity-0 group-hover:opacity-100 transition-opacity">
                Sign out
              </span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
