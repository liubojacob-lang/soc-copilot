"use client";

import React, { type HTMLAttributes, forwardRef } from "react";
import { cn } from "@/lib/utils";

/**
 * 统一徽章层。
 *
 * 这是全站 severity / status / AI 三种语义色的**唯一**来源。
 * 组件内部只使用 `severity-*` / `status-*` / `ai-*` 设计令牌，
 * 明暗两套取值由 globals.css 的 CSS 变量承载，因此这里不需要写任何 dark: 变体。
 *
 * 禁止在本文件之外再裸写 red/orange/amber/emerald 表示严重程度。
 */

export type Severity =
  | "critical"
  | "high"
  | "medium"
  | "low"
  | "info"
  | "neutral"
  | "success"
  | "warning"
  | "danger";

export type StatusState =
  | "active"
  | "resolved"
  | "investigating"
  | "pending"
  | "failed"
  | "success"
  | "warning"
  | "disabled"
  | "unknown"
  | "new"
  | "escalated"
  | "falsePositive"
  | "rejected"
  | "expired"
  | "running"
  | "approved";

export type AIState =
  | "analysis"
  | "suggested"
  | "confidence"
  | "running"
  | "completed"
  | "failed"
  | "approval"
  | "approved";

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  severity?: Severity;
  variant?: "pill" | "rounded";
  size?: "xs" | "sm" | "md";
  dot?: boolean;
}

interface Tone {
  bg: string;
  fg: string;
  border: string;
  dot: string;
}

/**
 * Severity 语义映射。
 * Critical 红 / High 橙 / Medium 黄 / Low 蓝 / Info 中性灰 —— 与产品规范一致。
 * success / warning / danger 是历史别名，映射到对应语义槽位而非独立色。
 */
const severityTones: Record<Severity, Tone> = {
  critical: {
    bg: "bg-severity-critical-bg",
    fg: "text-severity-critical-fg",
    border: "border-severity-critical-border",
    dot: "bg-severity-critical",
  },
  danger: {
    bg: "bg-severity-critical-bg",
    fg: "text-severity-critical-fg",
    border: "border-severity-critical-border",
    dot: "bg-severity-critical",
  },
  high: {
    bg: "bg-severity-high-bg",
    fg: "text-severity-high-fg",
    border: "border-severity-high-border",
    dot: "bg-severity-high",
  },
  medium: {
    bg: "bg-severity-medium-bg",
    fg: "text-severity-medium-fg",
    border: "border-severity-medium-border",
    dot: "bg-severity-medium",
  },
  warning: {
    bg: "bg-severity-medium-bg",
    fg: "text-severity-medium-fg",
    border: "border-severity-medium-border",
    dot: "bg-severity-medium",
  },
  low: {
    bg: "bg-severity-low-bg",
    fg: "text-severity-low-fg",
    border: "border-severity-low-border",
    dot: "bg-severity-low",
  },
  info: {
    bg: "bg-severity-info-bg",
    fg: "text-severity-info-fg",
    border: "border-severity-info-border",
    dot: "bg-severity-info",
  },
  neutral: {
    bg: "bg-severity-neutral-bg",
    fg: "text-severity-neutral-fg",
    border: "border-severity-neutral-border",
    dot: "bg-severity-neutral",
  },
  // success 是状态语义（绿），不是 severity 档位
  success: {
    bg: "bg-status-success-bg",
    fg: "text-status-success-fg",
    border: "border-status-success-border",
    dot: "bg-status-success",
  },
};

/**
 * Status 语义映射。业务上出现的额外状态（new / escalated / falsePositive
 * / rejected / expired / running / approved）复用最接近的语义槽位，避免色板膨胀。
 */
const statusTones: Record<StatusState, Tone> = {
  active: {
    bg: "bg-status-active-bg",
    fg: "text-status-active-fg",
    border: "border-status-active-border",
    dot: "bg-status-active",
  },
  resolved: {
    bg: "bg-status-resolved-bg",
    fg: "text-status-resolved-fg",
    border: "border-status-resolved-border",
    dot: "bg-status-resolved",
  },
  investigating: {
    bg: "bg-status-investigating-bg",
    fg: "text-status-investigating-fg",
    border: "border-status-investigating-border",
    dot: "bg-status-investigating",
  },
  pending: {
    bg: "bg-status-pending-bg",
    fg: "text-status-pending-fg",
    border: "border-status-pending-border",
    dot: "bg-status-pending",
  },
  failed: {
    bg: "bg-status-failed-bg",
    fg: "text-status-failed-fg",
    border: "border-status-failed-border",
    dot: "bg-status-failed",
  },
  success: {
    bg: "bg-status-success-bg",
    fg: "text-status-success-fg",
    border: "border-status-success-border",
    dot: "bg-status-success",
  },
  warning: {
    bg: "bg-status-warning-bg",
    fg: "text-status-warning-fg",
    border: "border-status-warning-border",
    dot: "bg-status-warning",
  },
  disabled: {
    bg: "bg-status-disabled-bg",
    fg: "text-status-disabled-fg",
    border: "border-status-disabled-border",
    dot: "bg-status-disabled",
  },
  unknown: {
    bg: "bg-status-unknown-bg",
    fg: "text-status-unknown-fg",
    border: "border-status-unknown-border",
    dot: "bg-status-unknown",
  },
  new: {
    bg: "bg-status-investigating-bg",
    fg: "text-status-investigating-fg",
    border: "border-status-investigating-border",
    dot: "bg-status-investigating",
  },
  running: {
    bg: "bg-status-investigating-bg",
    fg: "text-status-investigating-fg",
    border: "border-status-investigating-border",
    dot: "bg-status-investigating",
  },
  escalated: {
    bg: "bg-status-pending-bg",
    fg: "text-status-pending-fg",
    border: "border-status-pending-border",
    dot: "bg-status-pending",
  },
  approved: {
    bg: "bg-status-success-bg",
    fg: "text-status-success-fg",
    border: "border-status-success-border",
    dot: "bg-status-success",
  },
  falsePositive: {
    bg: "bg-status-disabled-bg",
    fg: "text-status-disabled-fg",
    border: "border-status-disabled-border",
    dot: "bg-status-disabled",
  },
  rejected: {
    bg: "bg-status-disabled-bg",
    fg: "text-status-disabled-fg",
    border: "border-status-disabled-border",
    dot: "bg-status-disabled",
  },
  expired: {
    bg: "bg-status-disabled-bg",
    fg: "text-status-disabled-fg",
    border: "border-status-disabled-border",
    dot: "bg-status-disabled",
  },
};

/**
 * AI 语义映射。靛紫体系，与 severity（红橙）和人工操作（accent 蓝）三方可辨。
 */
const aiTones: Record<AIState, Tone> = {
  analysis: {
    bg: "bg-ai-bg",
    fg: "text-ai-fg",
    border: "border-ai-border",
    dot: "bg-ai",
  },
  suggested: {
    bg: "bg-ai-bg",
    fg: "text-ai-fg",
    border: "border-ai-border",
    dot: "bg-ai",
  },
  confidence: {
    bg: "bg-ai-bg",
    fg: "text-ai-fg",
    border: "border-ai-border",
    dot: "bg-ai",
  },
  running: {
    bg: "bg-ai-running-bg",
    fg: "text-ai-running-fg",
    border: "border-ai-running-border",
    dot: "bg-ai-running",
  },
  completed: {
    bg: "bg-ai-completed-bg",
    fg: "text-ai-completed-fg",
    border: "border-ai-completed-border",
    dot: "bg-ai-completed",
  },
  failed: {
    bg: "bg-ai-failed-bg",
    fg: "text-ai-failed-fg",
    border: "border-ai-failed-border",
    dot: "bg-ai-failed",
  },
  approval: {
    bg: "bg-ai-approval-bg",
    fg: "text-ai-approval-fg",
    border: "border-ai-approval-border",
    dot: "bg-ai-approval",
  },
  approved: {
    bg: "bg-ai-approved-bg",
    fg: "text-ai-approved-fg",
    border: "border-ai-approved-border",
    dot: "bg-ai-approved",
  },
};

const sizeStyles = {
  xs: "text-[10px] px-1.5 py-0.5 gap-1",
  sm: "text-xs px-2 py-0.5 gap-1.5",
  md: "text-xs px-2.5 py-1 gap-1.5 font-medium",
};

const baseStyles =
  "inline-flex items-center font-medium border leading-none tracking-tight select-none transition-colors";

function renderInner(tone: Tone, dot: boolean, children: React.ReactNode) {
  return (
    <>
      {dot && <span className={cn("w-1.5 h-1.5 rounded-full shrink-0", tone.dot)} />}
      <span>{children}</span>
    </>
  );
}

const Badge = React.memo(
  forwardRef<HTMLSpanElement, BadgeProps>(
    (
      {
        severity = "neutral",
        variant = "rounded",
        size = "sm",
        dot = false,
        className,
        children,
        ...props
      },
      ref
    ) => {
      const tone = severityTones[severity] || severityTones.neutral;
      return (
        <span
          ref={ref}
          className={cn(
            baseStyles,
            variant === "pill" ? "rounded-full" : "rounded-md",
            sizeStyles[size],
            tone.bg,
            tone.fg,
            tone.border,
            className
          )}
          {...props}
        >
          {renderInner(tone, dot, children)}
        </span>
      );
    }
  )
);
Badge.displayName = "Badge";

export interface StatusBadgeProps extends Omit<HTMLAttributes<HTMLSpanElement>, "children"> {
  status: StatusState;
  /** 由调用方传入已完成 i18n 的文案，组件只负责语义色。 */
  label: React.ReactNode;
  variant?: "pill" | "rounded";
  size?: "xs" | "sm" | "md";
  dot?: boolean;
}

const StatusBadge = React.memo(
  forwardRef<HTMLSpanElement, StatusBadgeProps>(
    ({ status, label, variant = "rounded", size = "sm", dot = true, className, ...props }, ref) => {
      const tone = statusTones[status] || statusTones.unknown;
      return (
        <span
          ref={ref}
          className={cn(
            baseStyles,
            variant === "pill" ? "rounded-full" : "rounded-md",
            sizeStyles[size],
            tone.bg,
            tone.fg,
            tone.border,
            className
          )}
          {...props}
        >
          {renderInner(tone, dot, label)}
        </span>
      );
    }
  )
);
StatusBadge.displayName = "StatusBadge";

export interface AIBadgeProps extends Omit<HTMLAttributes<HTMLSpanElement>, "children"> {
  state: AIState;
  label: React.ReactNode;
  variant?: "pill" | "rounded";
  size?: "xs" | "sm" | "md";
  dot?: boolean;
}

/** AI 状态徽章，用于区分 AI 产出 / 人工操作 / 系统事件三方。 */
const AIBadge = React.memo(
  forwardRef<HTMLSpanElement, AIBadgeProps>(
    ({ state, label, variant = "rounded", size = "sm", dot = false, className, ...props }, ref) => {
      const tone = aiTones[state] || aiTones.analysis;
      return (
        <span
          ref={ref}
          className={cn(
            baseStyles,
            variant === "pill" ? "rounded-full" : "rounded-md",
            sizeStyles[size],
            tone.bg,
            tone.fg,
            tone.border,
            className
          )}
          {...props}
        >
          {renderInner(tone, dot, label)}
        </span>
      );
    }
  )
);
AIBadge.displayName = "AIBadge";

export interface ConfidenceBadgeProps extends Omit<HTMLAttributes<HTMLSpanElement>, "children"> {
  /** 0-100。null / undefined 表示后端未提供置信度，必须显式降级而不是编造数值。 */
  value?: number | null;
  /** 置信度缺失时的文案，由调用方传入已 i18n 的字符串。 */
  unavailableLabel?: string;
  showBar?: boolean;
  size?: "xs" | "sm" | "md";
}

/**
 * AI 置信度徽章。
 *
 * 硬性约束：value 缺失时渲染 unavailableLabel，**绝不回退到编造的默认百分比**。
 * 分档只表达"确定程度" —— 低置信度用中性色而非危险色，因为不确定不等于危险。
 */
const ConfidenceBadge = React.memo(
  forwardRef<HTMLSpanElement, ConfidenceBadgeProps>(
    (
      {
        value,
        unavailableLabel = "Confidence unavailable",
        showBar = false,
        size = "sm",
        className,
        ...props
      },
      ref
    ) => {
      const hasValue = typeof value === "number" && Number.isFinite(value);

      if (!hasValue) {
        return (
          <span
            ref={ref}
            className={cn(
              baseStyles,
              "rounded-md italic",
              sizeStyles[size],
              "bg-severity-neutral-bg text-severity-neutral-fg border-severity-neutral-border",
              className
            )}
            {...props}
          >
            <span>{unavailableLabel}</span>
          </span>
        );
      }

      const pct = Math.min(100, Math.max(0, Math.round(value)));
      const tone =
        pct >= 80 ? aiTones.completed : pct >= 50 ? aiTones.approval : severityTones.neutral;

      return (
        <span
          ref={ref}
          className={cn(
            baseStyles,
            "rounded-md tabular-nums",
            sizeStyles[size],
            tone.bg,
            tone.fg,
            tone.border,
            className
          )}
          {...props}
        >
          {showBar && (
            <span className="w-10 h-1 rounded-full bg-current/20 overflow-hidden shrink-0">
              <span className="block h-full rounded-full bg-current" style={{ width: `${pct}%` }} />
            </span>
          )}
          <span>{pct}%</span>
        </span>
      );
    }
  )
);
ConfidenceBadge.displayName = "ConfidenceBadge";

export { Badge, StatusBadge, AIBadge, ConfidenceBadge };
