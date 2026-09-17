/**
 * 导航信息架构 —— 全站唯一真相源。
 *
 * 历史上这套列表在 Navigation.tsx / MobileDrawer.tsx / GlobalSearch.tsx 里各写一份，
 * 三份内容互相漂移（MobileDrawer 甚至漏掉了 alerts / assets / threat-intel）。
 * 现在 Sidebar、移动端抽屉、Command Palette 全部从这里取，改一处即可。
 *
 * 分组遵循 SOC 作业流：先看态势 → 处置 → 情报 → 自动化 → 资产 → AI → 报告 → 管理。
 * 只映射**真实存在**的路由，不凭空创建业务功能。
 */

import type { LucideIcon } from "lucide-react";
import {
  LayoutDashboard,
  Activity,
  BellRing,
  ShieldAlert,
  Network,
  Crosshair,
  Globe,
  Radar,
  Fingerprint,
  Workflow,
  FileStack,
  CheckCircle,
  Zap,
  Server,
  Cloud,
  Store,
  Sparkles,
  FileText,
  ScrollText,
  Settings,
  Users,
  Cpu,
  HeartPulse,
  Lock,
  SlidersHorizontal,
  Tv,
} from "lucide-react";

/** 路由可见性门槛。null = 所有已登录用户可见。 */
export type NavPermission = "admin" | "analystOrAdmin" | null;

export interface NavItem {
  /** i18n key，取 `navigation.*` 命名空间 */
  key: string;
  path: string;
  icon: LucideIcon;
  permission?: NavPermission;
  badge?: string;
  /** 布尔开关：隐藏该分组内的全部项目（用于"管理"整组权限） */
  children?: NavItem[];
}

export interface NavGroup {
  /** i18n key，取 `navigation.*` 命名空间 */
  key: string;
  icon: LucideIcon;
  items: NavItem[];
}

export const NAV_GROUPS: NavGroup[] = [
  {
    key: "groupOverview",
    icon: LayoutDashboard,
    items: [
      { key: "home", path: "/", icon: LayoutDashboard },
      { key: "monitor", path: "/monitor", icon: Tv },
    ],
  },
  {
    key: "groupOperations",
    icon: ShieldAlert,
    items: [
      { key: "alerts", path: "/alerts", icon: BellRing },
      { key: "incidents", path: "/cases", icon: ShieldAlert },
      { key: "correlation", path: "/correlation", icon: Network },
      { key: "threatHunting", path: "/threat-hunting", icon: Crosshair },
    ],
  },
  {
    key: "groupIntelligence",
    icon: Radar,
    items: [
      { key: "threatIntel", path: "/threat-intel", icon: Globe },
      { key: "threatIntelDashboard", path: "/threat-intel/dashboard", icon: Radar },
      { key: "ueba", path: "/ueba", icon: Fingerprint },
    ],
  },
  {
    key: "groupAutomation",
    icon: Workflow,
    items: [
      { key: "runs", path: "/playbooks", icon: Workflow },
      { key: "definitions", path: "/playbooks/definitions", icon: FileStack },
      { key: "approvals", path: "/playbooks/approvals", icon: CheckCircle },
      { key: "triggers", path: "/triggers", icon: Zap },
    ],
  },
  {
    key: "groupInfrastructure",
    icon: Server,
    items: [
      { key: "assets", path: "/assets", icon: Server },
      { key: "cloudNative", path: "/cloud-native", icon: Cloud, badge: "Beta" },
      { key: "marketplace", path: "/marketplace", icon: Store },
    ],
  },
  {
    key: "groupAI",
    icon: Sparkles,
    items: [{ key: "aiCopilot", path: "/ai-assistant", icon: Sparkles }],
  },
  {
    key: "groupReporting",
    icon: FileText,
    items: [
      { key: "reports", path: "/reports", icon: FileText },
      { key: "auditLogs", path: "/audit", icon: ScrollText, permission: "analystOrAdmin" },
    ],
  },
  {
    key: "groupAdministration",
    icon: Settings,
    items: [
      { key: "dashboard", path: "/admin/dashboard", icon: Activity, permission: "admin" },
      { key: "users", path: "/admin/users", icon: Users, permission: "admin" },
      { key: "settings", path: "/settings", icon: SlidersHorizontal, permission: "admin" },
      { key: "aiModels", path: "/settings/ai-models", icon: Cpu },
      { key: "notifications", path: "/settings/notifications", icon: BellRing },
      { key: "systemHealth", path: "/admin/health", icon: HeartPulse, permission: "admin" },
      { key: "secrets", path: "/admin/secrets", icon: Lock, permission: "admin" },
    ],
  },
];

/** 扁平化后的全部路由，用于 active 态消歧与 Command Palette。 */
export const ALL_NAV_ITEMS: NavItem[] = NAV_GROUPS.flatMap((g) => g.items);

export function isVisible(item: NavItem, isAdminUser: boolean, isAnalyst: boolean): boolean {
  if (!item.permission) return true;
  if (item.permission === "admin") return isAdminUser;
  if (item.permission === "analystOrAdmin") return isAnalyst;
  return true;
}

/**
 * 判断路由是否激活。
 *
 * 需要消歧：`/playbooks` 和 `/playbooks/definitions` 都是真实路由，
 * 访问 definitions 时不能把 playbooks 也点亮 —— 所以命中更具体的注册路由时排除父级。
 */
export function isPathActive(pathname: string | null, itemPath: string): boolean {
  if (!pathname) return false;
  if (itemPath === "/") return pathname === "/";
  if (pathname === itemPath) return true;
  if (!pathname.startsWith(`${itemPath}/`)) return false;

  const hasMoreSpecific = ALL_NAV_ITEMS.some(
    (other) =>
      other.path !== itemPath &&
      other.path.startsWith(`${itemPath}/`) &&
      (pathname === other.path || pathname.startsWith(`${other.path}/`))
  );
  return !hasMoreSpecific;
}
