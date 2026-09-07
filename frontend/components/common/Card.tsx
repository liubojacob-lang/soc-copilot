"use client";

import { ReactNode } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";
import { Heading, Text } from "@/components/ui/Typography";

/**
 * Card 组件变体配置
 * 使用设计 Token 保持一致性
 */
const cardVariants = cva("rounded-xl border shadow-subtle transition-all duration-150", {
  variants: {
    variant: {
      default: "bg-surface-card border-border-subtle",
      outlined: "bg-transparent border-border-subtle",
      elevated: "bg-surface-card border-border-subtle shadow-md dark:shadow-black/50",
      glass: "glass-surface border-border-subtle",
    },
    padding: {
      none: "",
      xs: "p-2.5",
      sm: "p-3.5",
      md: "p-5",
      lg: "p-6 sm:p-7",
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
    ? "cursor-pointer card-hover hover:border-border-default hover:bg-surface-hover/50"
    : "";

  const paddingClasses = {
    none: "",
    xs: "p-2.5",
    sm: "p-3.5",
    md: "p-5",
    lg: "p-6 sm:p-7",
  };

  const headerPaddingClasses = {
    none: "px-4 py-3",
    xs: "px-2.5 py-2",
    sm: "px-3.5 py-2.5",
    md: "px-5 py-3.5",
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
