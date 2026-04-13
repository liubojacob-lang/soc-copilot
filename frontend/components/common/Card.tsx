"use client";

import { ReactNode } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";
import { patterns, borderRadius, shadows, colors } from "@/styles/designTokens";

/**
 * Card 组件变体配置
 * 使用设计 Token 保持一致性
 */
const cardVariants = cva(`${borderRadius.xl} border transition-all duration-300 overflow-hidden`, {
  variants: {
    variant: {
      default: `${patterns.card.base} ${patterns.card.shadow} ${patterns.card.hover}`,
      outlined: `bg-transparent ${patterns.card.border} shadow-sm ${patterns.card.hover}`,
      elevated: `${patterns.card.base} ${shadows.lg} hover:shadow-xl`,
      glass:
        "bg-white/75 dark:bg-gray-800/75 backdrop-blur-glass border-white/50 dark:border-gray-700/50 shadow-glass hover:bg-white/85 dark:hover:bg-gray-800/85",
      neumorphic:
        "bg-gray-75 dark:bg-gray-800 border-gray-100 dark:border-gray-700 shadow-neumorphic dark:shadow-neumorphic-dark",
    },
    padding: {
      none: "",
      sm: patterns.card.padding.sm,
      md: patterns.card.padding.md,
      lg: patterns.card.padding.lg,
    },
  },
  defaultVariants: {
    variant: "default",
    padding: "md",
  },
});

type CardVariant = VariantProps<typeof cardVariants>["variant"];
type CardPadding = VariantProps<typeof cardVariants>["padding"];

interface CardProps extends VariantProps<typeof cardVariants> {
  title?: string;
  subtitle?: string;
  icon?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  onClick?: () => void;
}

function Card({
  title,
  subtitle,
  icon,
  action,
  children,
  variant,
  padding,
  className,
  onClick,
}: CardProps) {
  const hoverClasses = onClick ? "cursor-pointer hover:-translate-y-1 active:translate-y-0" : "";

  const paddingClasses = {
    none: "",
    sm: patterns.card.padding.sm,
    md: patterns.card.padding.md,
    lg: patterns.card.padding.lg,
  };

  const headerPaddingClasses = {
    none: "px-5 py-4",
    sm: "px-3 py-3",
    md: "px-5 py-4",
    lg: "px-5 py-4",
  };

  return (
    <div
      className={cn(cardVariants({ variant, padding: undefined }), hoverClasses, className)}
      onClick={onClick}
    >
      {(title || subtitle || icon || action) && (
        <div
          className={cn(
            "flex items-start justify-between border-b border-gray-100 dark:border-gray-700/50",
            headerPaddingClasses[padding || "md"]
          )}
        >
          <div className="flex items-center gap-3">
            {icon && (
              <div className="p-2.5 rounded-xl bg-gray-75 dark:bg-gray-700/50 text-gray-600 dark:text-gray-300">
                {icon}
              </div>
            )}
            <div>
              {title && (
                <h3 className="font-semibold text-gray-900 dark:text-white text-base">{title}</h3>
              )}
              {subtitle && (
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{subtitle}</p>
              )}
            </div>
          </div>
          {action && <div>{action}</div>}
        </div>
      )}
      <div className={paddingClasses[padding || "md"]}>{children}</div>
    </div>
  );
}

/**
 * StatCard 颜色配置
 * 使用 severity 颜色系统保持一致性
 */
const statCardColorClasses = {
  soc: {
    bg: "bg-blue-50 dark:bg-blue-900/20",
    text: "text-blue-600 dark:text-blue-400",
    iconBg: "bg-blue-100 dark:bg-blue-900/30",
    border: "border-blue-200 dark:border-blue-800/50",
    glow: "hover:shadow-[0_0_20px_rgba(37,99,235,0.3)]",
    gradient: "from-blue-500 to-blue-700",
  },
  success: {
    bg: "bg-green-50 dark:bg-green-900/20",
    text: "text-green-600 dark:text-green-400",
    iconBg: "bg-green-100 dark:bg-green-900/30",
    border: "border-green-200 dark:border-green-800/50",
    glow: "hover:shadow-[0_0_20px_rgba(16,185,129,0.3)]",
    gradient: "from-green-500 to-green-700",
  },
  warning: {
    bg: "bg-yellow-50 dark:bg-yellow-900/20",
    text: "text-yellow-600 dark:text-yellow-400",
    iconBg: "bg-yellow-100 dark:bg-yellow-900/30",
    border: "border-yellow-200 dark:border-yellow-800/50",
    glow: "",
    gradient: "from-yellow-500 to-yellow-700",
  },
  danger: {
    bg: "bg-red-50 dark:bg-red-900/20",
    text: "text-red-600 dark:text-red-400",
    iconBg: "bg-red-100 dark:bg-red-900/30",
    border: "border-red-200 dark:border-red-800/50",
    glow: "hover:shadow-[0_0_20px_rgba(239,68,68,0.3)]",
    gradient: "from-red-500 to-red-700",
  },
  info: {
    bg: "bg-gray-50 dark:bg-gray-800/50",
    text: "text-gray-600 dark:text-gray-400",
    iconBg: "bg-gray-100 dark:bg-gray-700/30",
    border: "border-gray-200 dark:border-gray-700/50",
    glow: "",
    gradient: "from-gray-500 to-gray-700",
  },
};

type StatCardColorScheme = keyof typeof statCardColorClasses;

interface StatCardProps {
  title: string;
  value: string | number;
  trend?: string;
  trendDirection?: "up" | "down" | "neutral";
  icon?: ReactNode;
  colorScheme?: StatCardColorScheme;
  subtitle?: string;
  className?: string;
  delay?: number;
}

function StatCard({
  title,
  value,
  trend,
  trendDirection = "neutral",
  icon,
  colorScheme = "soc",
  subtitle,
  className,
  delay = 0,
}: StatCardProps) {
  const colorClasses = statCardColorClasses[colorScheme];
  const delayClasses = [
    "animate-fade-in-up-stagger-1",
    "animate-fade-in-up-stagger-2",
    "animate-fade-in-up-stagger-3",
    "animate-fade-in-up-stagger-4",
  ];
  const delayClass = delayClasses[delay] || "animate-fade-in-up";

  const trendIcon =
    trendDirection === "up" ? (
      <span className="text-green-600 dark:text-green-400">↑</span>
    ) : trendDirection === "down" ? (
      <span className="text-red-600 dark:text-red-400">↓</span>
    ) : null;

  const gradientTextClass = `bg-gradient-to-r ${colorClasses.gradient}`;

  return (
    <Card
      variant="elevated"
      className={cn(
        delayClass,
        colorClasses.glow,
        "group",
        "hover:-translate-y-1",
        "transition-all duration-300",
        className
      )}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400 transition-colors group-hover:text-gray-700 dark:group-hover:text-gray-200">
            {title}
          </p>
          <p
            className={cn(
              "mt-2 text-3xl font-bold tracking-tight",
              "bg-clip-text text-transparent",
              gradientTextClass,
              "-webkit-background-clip text"
            )}
          >
            {value}
          </p>
          {subtitle && (
            <p className="mt-1.5 text-sm text-gray-500 dark:text-gray-400">{subtitle}</p>
          )}
          {trend && (
            <div className="mt-2.5 flex items-center gap-1.5">
              {trendIcon}
              <span
                className={cn(
                  "text-sm font-semibold",
                  trendDirection === "up"
                    ? "text-green-600 dark:text-green-400"
                    : trendDirection === "down"
                      ? "text-red-600 dark:text-red-400"
                      : "text-gray-500 dark:text-gray-400"
                )}
              >
                {trend}
              </span>
            </div>
          )}
        </div>
        {icon && (
          <div
            className={cn(
              "p-3.5 rounded-2xl",
              colorClasses.iconBg,
              colorClasses.text,
              colorClasses.border,
              "group-hover:scale-110 group-hover:rotate-5 transition-all duration-300"
            )}
          >
            {icon}
          </div>
        )}
      </div>
    </Card>
  );
}

export { Card, StatCard, cardVariants, statCardColorClasses };
export type { CardProps, CardVariant, CardPadding, StatCardProps, StatCardColorScheme };
