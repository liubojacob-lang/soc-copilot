"use client";

import { ReactNode, ButtonHTMLAttributes, forwardRef, useState, useRef, useEffect } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface Ripple {
  id: number;
  x: number;
  y: number;
}

const buttonVariants = cva(
  "relative inline-flex items-center justify-center font-medium select-none transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-500/40 focus-visible:ring-offset-1 disabled:pointer-events-none disabled:opacity-45 active:scale-[0.98]",
  {
    variants: {
      variant: {
        primary:
          "bg-accent-600 text-white shadow-sm hover:bg-accent-700 active:bg-accent-800 shadow-accent-600/20",
        secondary:
          "bg-surface-card text-text-primary border border-border-subtle hover:bg-surface-hover hover:border-border-default active:bg-surface-active shadow-subtle",
        ghost:
          "bg-transparent text-text-secondary hover:text-text-primary hover:bg-surface-hover active:bg-surface-active",
        outline:
          "bg-transparent text-text-primary border border-border-default hover:bg-surface-hover active:bg-surface-active",
        danger:
          "bg-danger-600 text-white shadow-sm hover:bg-danger-700 active:bg-danger-800 shadow-danger-600/20",
        subtle:
          "bg-accent-50 text-accent-700 hover:bg-accent-100 dark:bg-accent-950/40 dark:text-accent-300 dark:hover:bg-accent-900/50",
      },
      size: {
        xs: "h-7 px-2.5 text-xs rounded-sm gap-1.5",
        sm: "h-8 px-3 text-xs rounded-md gap-1.5",
        md: "h-9 px-3.5 text-sm rounded-md gap-2",
        lg: "h-10 px-4 text-sm rounded-md gap-2 font-semibold",
        icon: "h-8 w-8 p-0 rounded-md",
        "icon-sm": "h-7 w-7 p-0 rounded-sm",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
    },
  }
);

type ButtonVariant = VariantProps<typeof buttonVariants>["variant"];
type ButtonSize = VariantProps<typeof buttonVariants>["size"];

interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  isLoading?: boolean;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
  disableRipple?: boolean;
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      children,
      variant,
      size,
      isLoading = false,
      leftIcon,
      rightIcon,
      className,
      disabled,
      disableRipple,
      onClick,
      type = "button",
      ...props
    },
    ref
  ) => {
    return (
      <button
        ref={ref}
        type={type}
        className={cn(buttonVariants({ variant, size }), className)}
        disabled={disabled || isLoading}
        onClick={onClick}
        {...props}
      >
        {isLoading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
        {!isLoading && leftIcon && <span className="inline-flex shrink-0">{leftIcon}</span>}
        {children && <span>{children}</span>}
        {!isLoading && rightIcon && <span className="inline-flex shrink-0">{rightIcon}</span>}
      </button>
    );
  }
);

Button.displayName = "Button";

export { Button, buttonVariants };
export type { ButtonProps, ButtonVariant, ButtonSize };
