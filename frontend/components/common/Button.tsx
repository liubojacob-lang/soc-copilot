"use client";

import { ReactNode, ButtonHTMLAttributes, forwardRef, useState, useRef, useEffect } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { patterns, transitions } from "@/styles/designTokens";

interface Ripple {
  id: number;
  x: number;
  y: number;
}

// Extract Tailwind classes from design tokens
const buttonVariants = cva(patterns.button.base, {
  variants: {
    variant: {
      primary: patterns.button.variants.primary,
      secondary: patterns.button.variants.secondary,
      ghost: patterns.button.variants.ghost,
      danger: patterns.button.variants.danger,
      outline: patterns.button.variants.outline,
    },
    size: {
      sm: patterns.button.sizes.sm,
      md: patterns.button.sizes.md,
      lg: patterns.button.sizes.lg,
    },
  },
  defaultVariants: {
    variant: "primary",
    size: "md",
  },
});

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
      disableRipple = false,
      onClick,
      ...props
    },
    ref
  ) => {
    const [ripples, setRipples] = useState<Ripple[]>([]);
    const buttonRef = useRef<HTMLButtonElement>(null);
    const nextRippleId = useRef(0);

    const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
      if (!disableRipple && buttonRef.current) {
        const rect = buttonRef.current.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        const id = nextRippleId.current++;

        setRipples((prev) => [...prev, { id, x, y }]);

        setTimeout(() => {
          setRipples((prev) => prev.filter((r) => r.id !== id));
        }, 600);
      }

      onClick?.(e);
    };

    useEffect(() => {
      if (ref) {
        if (typeof ref === "function") {
          ref(buttonRef.current);
        } else {
          ref.current = buttonRef.current;
        }
      }
    }, [ref]);

    return (
      <button
        ref={buttonRef}
        className={cn(buttonVariants({ variant, size }), className)}
        disabled={disabled || isLoading}
        onClick={handleClick}
        {...props}
      >
        {!disableRipple &&
          ripples.map((ripple) => (
            <span
              key={ripple.id}
              className="absolute rounded-full bg-white/30 pointer-events-none animate-ripple"
              style={{
                left: ripple.x,
                top: ripple.y,
                transform: "translate(-50%, -50%)",
              }}
            />
          ))}

        {isLoading && <Loader2 className="w-4 h-4 mr-2 animate-spin relative z-10" />}
        {!isLoading && leftIcon && <span className="mr-2 relative z-10">{leftIcon}</span>}
        <span className="relative z-10">{children}</span>
        {!isLoading && rightIcon && <span className="ml-2 relative z-10">{rightIcon}</span>}
      </button>
    );
  }
);

Button.displayName = "Button";

export { Button, buttonVariants };
export type { ButtonProps, ButtonVariant, ButtonSize };
