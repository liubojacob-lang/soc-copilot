"use client";

import { ReactNode } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";
import { Heading, Text } from "@/components/ui/Typography";

/**
 * Card 组件变体配置
 * 使用设计 Token 保持一致性
 */
const cardVariants = cva("rounded-lg border shadow-sm transition-colors duration-200", {
  variants: {
    variant: {
      default: "bg-surface-card dark:bg-slate-800 border-border-subtle dark:border-slate-700",
      outlined: "bg-transparent dark:bg-transparent border-border-subtle dark:border-slate-700",
      elevated:
        "bg-surface-card dark:bg-slate-800 border-border-subtle dark:border-slate-700 shadow-md",
    },
    padding: {
      none: "",
      sm: "p-3",
      md: "p-4",
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
  const hoverClasses = onClick
    ? "cursor-pointer hover:bg-surface-hover dark:hover:bg-slate-700"
    : "";

  const paddingClasses = {
    none: "",
    sm: "p-3",
    md: "p-4",
    lg: "p-6",
  };

  const headerPaddingClasses = {
    none: "px-4 py-3",
    sm: "px-3 py-3",
    md: "px-4 py-3",
    lg: "px-6 py-4",
  };

  return (
    <div
      className={cn(cardVariants({ variant, padding: undefined }), hoverClasses, className)}
      onClick={onClick}
    >
      {(title || subtitle || icon || action) && (
        <div
          className={cn(
            "flex items-start justify-between border-b border-border-subtle dark:border-slate-700",
            headerPaddingClasses[padding || "md"]
          )}
        >
          <div className="flex items-center gap-3">
            {icon && (
              <div className="p-2.5 rounded-lg bg-surface-hover dark:bg-slate-700 text-text-secondary dark:text-slate-300">
                {icon}
              </div>
            )}
            <div>
              {title && (
                <Heading level={3} color="primary" className="text-base font-semibold">
                  {title}
                </Heading>
              )}
              {subtitle && (
                <Text color="tertiary" className="mt-0.5 text-sm">
                  {subtitle}
                </Text>
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

export { Card, cardVariants };
export type { CardProps, CardVariant, CardPadding };
