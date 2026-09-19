"use client";

import { useEffect, useState } from "react";
import { Link, usePathname } from "@/i18n/navigation";
import { useLocale } from "next-intl";
import {
  ShieldCheck,
  KeyRound,
  Brain,
  Key,
  Bell,
  Settings2,
  ScrollText,
  type LucideIcon,
} from "lucide-react";
import { authFetchJSON, loadAuthState, isAdmin } from "@/lib/auth";

interface NavItem {
  href: string;
  zh: string;
  en: string;
  icon: LucideIcon;
  /** Match the path exactly instead of prefix-matching child routes. */
  exact?: boolean;
  showTwoFactorBadge?: boolean;
}

interface NavGroup {
  id: string;
  zh: string;
  en: string;
  adminOnly?: boolean;
  items: NavItem[];
}

const GROUPS: NavGroup[] = [
  {
    id: "account",
    zh: "账号安全",
    en: "Account security",
    items: [
      {
        href: "/settings",
        zh: "双因素认证",
        en: "Two-factor auth",
        icon: ShieldCheck,
        exact: true,
        showTwoFactorBadge: true,
      },
      { href: "/change-password", zh: "修改密码", en: "Password", icon: KeyRound },
    ],
  },
  {
    id: "integrations",
    zh: "系统集成",
    en: "Integrations",
    items: [
      { href: "/settings/ai-models", zh: "AI 模型与引擎", en: "AI models", icon: Brain },
      { href: "/settings/api-keys", zh: "API 密钥", en: "API keys", icon: Key },
      { href: "/settings/notifications", zh: "通知偏好", en: "Notifications", icon: Bell },
    ],
  },
  {
    id: "system",
    zh: "系统配置",
    en: "System",
    adminOnly: true,
    items: [
      { href: "/settings/system", zh: "运行时参数", en: "Runtime parameters", icon: Settings2 },
    ],
  },
  {
    id: "audit",
    zh: "审计",
    en: "Audit",
    items: [{ href: "/audit", zh: "安全审计日志", en: "Audit trail", icon: ScrollText }],
  },
];

const FOCUS_RING =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-500 focus-visible:ring-offset-1 dark:focus-visible:ring-offset-gray-900";

export function SettingsNav() {
  const pathname = usePathname();
  const locale = useLocale();
  const isZh = locale.startsWith("zh");
  const [isAdminUser, setIsAdminUser] = useState(false);
  const [totpEnabled, setTotpEnabled] = useState<boolean | null>(null);

  useEffect(() => {
    const state = loadAuthState();
    setIsAdminUser(Boolean(state && isAdmin(state.user)));
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = (await authFetchJSON("/api/v1/auth/2fa/status")) as {
          is_enabled?: boolean;
        } | null;
        if (!cancelled) setTotpEnabled(Boolean(data?.is_enabled));
      } catch {
        if (!cancelled) setTotpEnabled(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const groups = GROUPS.filter((group) => !group.adminOnly || isAdminUser);
  const flatItems = groups.flatMap((group) => group.items);

  const isActive = (item: NavItem) =>
    item.exact
      ? pathname === item.href
      : pathname === item.href || pathname.startsWith(`${item.href}/`);

  const renderBadge = (item: NavItem) => {
    if (!item.showTwoFactorBadge || totpEnabled === null) return null;
    const label = totpEnabled ? (isZh ? "已开启" : "On") : isZh ? "未开启" : "Off";
    return (
      <span
        className={
          totpEnabled
            ? "shrink-0 text-[10px] font-semibold px-1.5 py-0.5 rounded border bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800/60"
            : "shrink-0 text-[10px] font-semibold px-1.5 py-0.5 rounded border bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800/60"
        }
      >
        {label}
      </span>
    );
  };

  return (
    <>
      {/* Desktop: persistent vertical sidebar */}
      <aside className="hidden lg:block w-60 shrink-0 pl-4 sm:pl-6 lg:pl-8 pt-6">
        <nav
          aria-label={isZh ? "设置导航" : "Settings navigation"}
          className="sticky top-20 space-y-6"
        >
          {groups.map((group) => (
            <div key={group.id}>
              <p className="px-3 mb-1.5 text-[11px] font-bold uppercase tracking-wider text-text-tertiary dark:text-gray-500">
                {isZh ? group.zh : group.en}
              </p>
              <div className="space-y-0.5">
                {group.items.map((item) => {
                  const active = isActive(item);
                  const Icon = item.icon;
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      aria-current={active ? "page" : undefined}
                      className={[
                        "group flex items-center gap-2.5 h-10 px-3 rounded-lg border-l-[3px] transition-colors duration-150",
                        FOCUS_RING,
                        active
                          ? "border-accent-500 bg-accent-50 dark:bg-accent-950/30 text-accent-700 dark:text-accent-300 font-semibold"
                          : "border-transparent text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-gray-100",
                      ].join(" ")}
                    >
                      <Icon className="w-4 h-4 shrink-0" />
                      <span className="flex-1 truncate text-[13px]">
                        {isZh ? item.zh : item.en}
                      </span>
                      {renderBadge(item)}
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>
      </aside>

      {/* Mobile / tablet: horizontally scrollable pills */}
      <nav
        aria-label={isZh ? "设置导航" : "Settings navigation"}
        className="lg:hidden overflow-x-auto px-4 pt-4 pb-1"
      >
        <div className="flex items-center gap-2 min-w-max">
          {flatItems.map((item) => {
            const active = isActive(item);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={[
                  "flex items-center gap-1.5 h-9 px-3 rounded-full border text-[13px] whitespace-nowrap transition-colors duration-150",
                  FOCUS_RING,
                  active
                    ? "border-accent-500 bg-accent-50 dark:bg-accent-950/30 text-accent-700 dark:text-accent-300 font-semibold"
                    : "border-gray-200 dark:border-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800",
                ].join(" ")}
              >
                <Icon className="w-3.5 h-3.5 shrink-0" />
                {isZh ? item.zh : item.en}
                {renderBadge(item)}
              </Link>
            );
          })}
        </div>
      </nav>
    </>
  );
}
