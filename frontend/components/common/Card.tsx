"use client";

import { ReactNode } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

/**
 * Card 组件变体配置
 */
const cardVariants = cva("rounded-2xl border transition-all duration-300 overflow-hidden", {
  variants: {
    variant: {
      default:
        "bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 shadow-card hover:shadow-elevated",
      outlined: "bg-transparent border-gray-300 dark:border-gray-600 shadow-sm hover:shadow-card",
      elevated:
        "bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 shadow-elevated hover:shadow-[0_20px_25px_-5px_rgb(0_0_0/0.1),0_8px_10px_-6px_rgb(0_0_0/0.1)]",
      glass:
        "bg-white/75 dark:bg-gray-800/75 backdrop-blur-glass border-white/50 dark:border-gray-700/50 shadow-glass hover:bg-white/85 dark:hover:bg-gray-800/85",
      neumorphic:
        "bg-gray-75 dark:bg-gray-800 border-gray-100 dark:border-gray-700 shadow-neumorphic dark:shadow-neumorphic-dark",
    },
    padding: {
      none: "",
      sm: "p-3",
      md: "p-5",
      lg: "p-6",
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
    sm: "p-3",
    md: "p-5",
    lg: "p-6",
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
 */
const statCardColorClasses = {
  soc: {
    bg: "bg-soc-50 dark:bg-soc-900/20",
    text: "text-soc-600 dark:text-soc-400",
    iconBg: "bg-soc-100 dark:bg-soc-900/30",
    border: "border-soc-200 dark:border-soc-800/50",
    glow: "hover:shadow-glow",
    gradient: "from-soc-500 to-soc-700",
  },
  success: {
    bg: "bg-success-50 dark:bg-success-900/20",
    text: "text-success-600 dark:text-success-400",
    iconBg: "bg-success-100 dark:bg-success-900/30",
    border: "border-success-200 dark:border-success-800/50",
    glow: "hover:shadow-glow-success",
    gradient: "from-success-500 to-success-700",
  },
  warning: {
    bg: "bg-warning-50 dark:bg-warning-900/20",
    text: "text-warning-600 dark:text-warning-400",
    iconBg: "bg-warning-100 dark:bg-warning-900/30",
    border: "border-warning-200 dark:border-warning-800/50",
    glow: "",
    gradient: "from-warning-500 to-warning-700",
  },
  danger: {
    bg: "bg-danger-50 dark:bg-danger-900/20",
    text: "text-danger-600 dark:text-danger-400",
    iconBg: "bg-danger-100 dark:bg-danger-900/30",
    border: "border-danger-200 dark:border-danger-800/50",
    glow: "hover:shadow-glow-danger",
    gradient: "from-danger-500 to-danger-700",
  },
  info: {
    bg: "bg-info-50 dark:bg-info-900/20",
    text: "text-info-600 dark:text-info-400",
    iconBg: "bg-info-100 dark:bg-info-900/30",
    border: "border-info-200 dark:border-info-800/50",
    glow: "",
    gradient: "from-info-500 to-info-700",
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
  const colors = statCardColorClasses[colorScheme];
  const delayClasses = [
    "animate-fade-in-up-stagger-1",
    "animate-fade-in-up-stagger-2",
    "animate-fade-in-up-stagger-3",
    "animate-fade-in-up-stagger-4",
  ];
  const delayClass = delayClasses[delay] || "animate-fade-in-up";

  const trendIcon =
    trendDirection === "up" ? (
      <span className="text-success-600 dark:text-success-400">↑</span>
    ) : trendDirection === "down" ? (
      <span className="text-danger-600 dark:text-danger-400">↓</span>
    ) : null;

  const gradientTextClass = `bg-gradient-to-r ${colors.gradient}`;

  return (
    <Card
      variant="elevated"
      className={cn(
        delayClass,
        colors.glow,
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
                    ? "text-success-600 dark:text-success-400"
                    : trendDirection === "down"
                      ? "text-danger-600 dark:text-danger-400"
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
              colors.iconBg,
              colors.text,
              colors.border,
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
