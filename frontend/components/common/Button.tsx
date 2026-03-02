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
  "inline-flex items-center justify-center font-medium rounded-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed touch-manipulation relative overflow-hidden",
  {
    variants: {
      variant: {
        primary:
          "bg-soc-600 text-white hover:bg-soc-700 shadow-sm focus:outline-none focus:ring-2 focus:ring-soc-500 focus:ring-offset-2 active:bg-soc-800",
        secondary:
          "bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white hover:bg-gray-200 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2",
        ghost:
          "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2",
        danger:
          "bg-danger-600 text-white hover:bg-danger-700 focus:outline-none focus:ring-2 focus:ring-danger-500 focus:ring-offset-2 active:bg-danger-800",
        outline:
          "border border-gray-300 dark:border-gray-600 bg-transparent text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2",
      },
      size: {
        sm: "px-3 py-1.5 text-sm",
        md: "px-4 py-2.5 text-sm",
        lg: "px-6 py-3 text-base",
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
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
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
        
        setRipples(prev => [...prev, { id, x, y }]);
        
        setTimeout(() => {
          setRipples(prev => prev.filter(r => r.id !== id));
        }, 600);
      }
      
      onClick?.(e);
    };

    useEffect(() => {
      if (ref) {
        if (typeof ref === 'function') {
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
        {!disableRipple && ripples.map(ripple => (
          <span
            key={ripple.id}
            className="absolute rounded-full bg-white/30 pointer-events-none animate-ripple"
            style={{
              left: ripple.x,
              top: ripple.y,
              transform: 'translate(-50%, -50%)',
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
