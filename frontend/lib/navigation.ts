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
  Users,
  Cpu,
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
  /**
   * 分组**没有**图标，这是刻意的。
   *
   * 此前每个分组都带一个图标，而它和该组第一个子项的图标往往是同一个
   * （概览↔首页同为 LayoutDashboard、情报↔情报看板同为 Radar、自动化↔执行记录同为 Workflow、
   * 基础设施↔资产同为 Server、AI↔助手同为 Sparkles、报表↔报告同为 FileText，
   * 运营↔事件同为 ShieldAlert —— 8 组中 7 组重复）。
   * 同一个图形在相邻两行出现，等于告诉用户"这两个是同一个东西"。
   *
   * 分组是**容器**、子项是**内容**，两者不该共用一套视觉语汇。
   * 因此分组改用纯排版层级表达（小字号 + 字距 + 次级色），
   * 把图标语汇完整让给子项。
   */
  items: NavItem[];
}

export const NAV_GROUPS: NavGroup[] = [
  {
    key: "groupOverview",
    items: [
      { key: "home", path: "/", icon: LayoutDashboard },
      { key: "monitor", path: "/monitor", icon: Tv },
    ],
  },
  {
    key: "groupOperations",
    items: [
      { key: "alerts", path: "/alerts", icon: BellRing },
      { key: "incidents", path: "/cases", icon: ShieldAlert },
      { key: "correlation", path: "/correlation", icon: Network },
      { key: "threatHunting", path: "/threat-hunting", icon: Crosshair },
    ],
  },
  {
    key: "groupIntelligence",
    items: [
      { key: "threatIntel", path: "/threat-intel", icon: Globe },
      { key: "threatIntelDashboard", path: "/threat-intel/dashboard", icon: Radar },
      { key: "ueba", path: "/ueba", icon: Fingerprint },
    ],
  },
  {
    key: "groupAutomation",
    items: [
      { key: "runs", path: "/playbooks", icon: Workflow },
      { key: "definitions", path: "/playbooks/definitions", icon: FileStack },
      { key: "approvals", path: "/playbooks/approvals", icon: CheckCircle },
      { key: "triggers", path: "/triggers", icon: Zap },
    ],
  },
  {
    key: "groupInfrastructure",
    items: [
      { key: "assets", path: "/assets", icon: Server },
      { key: "cloudNative", path: "/cloud-native", icon: Cloud, badge: "Demo" },
      { key: "marketplace", path: "/marketplace", icon: Store },
    ],
  },
  {
    key: "groupAI",
    items: [{ key: "aiCopilot", path: "/ai-assistant", icon: Sparkles }],
  },
  {
    key: "groupReporting",
    items: [
      { key: "reports", path: "/reports", icon: FileText },
      { key: "auditLogs", path: "/audit", icon: ScrollText, permission: "analystOrAdmin" },
    ],
  },
  {
    key: "groupAdministration",
    items: [
      { key: "dashboard", path: "/admin/dashboard", icon: Activity, permission: "admin" },
      { key: "users", path: "/admin/users", icon: Users, permission: "admin" },
      { key: "settings", path: "/settings", icon: SlidersHorizontal, permission: "admin" },
      { key: "aiModels", path: "/settings/ai-models", icon: Cpu },
      { key: "notifications", path: "/settings/notifications", icon: BellRing },
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
