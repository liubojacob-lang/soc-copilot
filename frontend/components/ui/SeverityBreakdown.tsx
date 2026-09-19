"use client";

/**
 * 严重度分布 —— 全站唯一实现。
 *
 * 为什么要有这个组件：
 * 同一份数据（alerts_by_severity）此前在仪表盘与告警列表页各有各的画法 ——
 * 仪表盘是"圆点 + 条形"，列表页是"文字 + ×N"，而且列表页的顺序直接来自
 * API 返回的对象键序，实测会渲染成「中 → 信息 → 高 → 严重 → 低」这种无逻辑排列。
 * 同一维度、同一产品、两套语言，读者无法在两个页面之间建立共同的分布印象。
 *
 * 现在两处共用本组件：
 *   - 排序固定为严重度降序（critical → info），与数据到达顺序无关
 *   - 每级同时给出绝对数与百分比（`11 · 6.2%`），读者不必心算
 *   - 长度严格线性映射占比，无最小宽度下限
 *   - 配色一律取 severity-* 的 DEFAULT 槽位，不混用 fg 槽位
 */

import { useTranslations } from "next-intl";

import { Badge, type Severity } from "@/components/ui/Badge";
import { cn } from "@/lib/utils";

/** 严重度降序 —— 全站唯一排序依据，不依赖数据源的对象键序 */
export const SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"] as const;
export type SeverityLevel = (typeof SEVERITY_ORDER)[number];

/**
 * 等级 → 视觉 token。
 * 必须是静态字面量：Tailwind 的 JIT 在构建期扫地识别类名，
 * 拼接出来的 `bg-severity-${level}` 不会生成任何 CSS；
 * 项目的 check-design-tokens.mjs 也会把它判为"死类名"。
 */
const SEVERITY_TOKENS: Record<SeverityLevel, { dot: string; bar: string; badge: Severity }> = {
  critical: { dot: "bg-severity-critical", bar: "bg-severity-critical", badge: "critical" },
  high: { dot: "bg-severity-high", bar: "bg-severity-high", badge: "high" },
  medium: { dot: "bg-severity-medium", bar: "bg-severity-medium", badge: "medium" },
  low: { dot: "bg-severity-low", bar: "bg-severity-low", badge: "low" },
  info: { dot: "bg-severity-info", bar: "bg-severity-info", badge: "info" },
};

/** i18n 键名 → severity 命名空间 */
const SEVERITY_I18N_KEY: Record<SeverityLevel, string> = {
  critical: "critical",
  high: "high",
  medium: "medium",
  low: "low",
  info: "info",
};

export interface SeverityBreakdownProps {
  /**
   * 各级别告警数。用 Partial<Record<SeverityLevel, number>> 而不是
   * Record<string, number>：前者对 `SeverityDistribution` 这类具名接口
   * （有 5 个必填键、无索引签名）可直接赋值，后者会因缺少索引签名而报错。
   * 仍然接受 `Record<string, number>`（列表页的 by_severity 就是这种），
   * 因为索引签名天然覆盖全部键。
   */
  counts?: Partial<Record<SeverityLevel, number>> | undefined;
  /**
   * 容器排布。条目本身的视觉完全一致，只有外框不同：
   *   list —— 竖向单列，用于窄卡片（仪表盘）
   *   grid —— 2/5 列自适应，用于整页宽度的页头（告警列表）
   */
  layout?: "list" | "grid";
  showBadge?: boolean;
  className?: string;
}

export function SeverityBreakdown({
  counts,
  layout = "list",
  showBadge = false,
  className,
}: SeverityBreakdownProps) {
  const tSeverity = useTranslations("severity");

  if (!counts) return null;

  const total = SEVERITY_ORDER.reduce((acc, level) => acc + (counts[level] || 0), 0);

  return (
    <ul
      className={cn(
        layout === "list" ? "space-y-3" : "grid grid-cols-2 gap-x-5 gap-y-3 sm:grid-cols-5",
        className
      )}
    >
      {SEVERITY_ORDER.map((level) => {
        const count = counts[level] || 0;
        const pct = total > 0 ? (count / total) * 100 : 0;
        const token = SEVERITY_TOKENS[level];
        const label = tSeverity(SEVERITY_I18N_KEY[level] as never);

        return (
          <li key={level} className="min-w-0 space-y-1.5">
            <div className="flex items-baseline justify-between gap-2">
              <span className="flex min-w-0 items-center gap-1.5 text-xs font-medium text-text-secondary">
                <span className={cn("h-2 w-2 shrink-0 rounded-full", token.dot)} aria-hidden />
                {showBadge ? (
                  <Badge severity={token.badge} size="xs">
                    {label}
                  </Badge>
                ) : (
                  <span className="truncate">{label}</span>
                )}
              </span>
              <span className="flex shrink-0 items-baseline gap-1 tabular-nums">
                <span className="text-sm font-semibold text-text-primary">{count}</span>
                <span className="text-[11px] font-normal text-text-muted">{pct.toFixed(1)}%</span>
              </span>
            </div>
            {/* 长度严格 = 占比；0 值不渲染可见条（不设最小宽度下限） */}
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-hover">
              <div
                className={cn("h-full rounded-full transition-[width] duration-300", token.bar)}
                style={{ width: `${pct}%` }}
              />
            </div>
          </li>
        );
      })}
    </ul>
  );
}
