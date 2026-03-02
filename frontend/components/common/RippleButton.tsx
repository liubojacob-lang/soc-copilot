"use client";

import { useState, useRef, ReactNode } from "react";

interface Ripple {
  x: number;
  y: number;
  id: number;
}

interface RippleButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  rippleColor?: string;
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  isLoading?: boolean;
}

export function RippleButton({
  children,
  className = "",
  rippleColor,
  variant = "primary",
  size = "md",
  isLoading = false,
  disabled,
  ...props
}: RippleButtonProps) {
  const [ripples, setRipples] = useState<Ripple[]>([]);
  const buttonRef = useRef<HTMLButtonElement>(null);

  const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
    const button = buttonRef.current;
    if (!button || disabled || isLoading) return;

    const rect = button.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const id = Date.now();

    setRipples((prev) => [...prev, { x, y, id }]);

    setTimeout(() => {
      setRipples((prev) => prev.filter((ripple) => ripple.id !== id));
    }, 600);

    props.onClick?.(e);
  };

  // 变体样式
  const variantClasses = {
    primary: "bg-gradient-to-r from-soc-500 to-soc-600 text-white shadow-lg shadow-soc-500/25 hover:shadow-xl hover:shadow-soc-500/35",
    secondary: "bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700",
    ghost: "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800",
    danger: "bg-gradient-to-r from-danger-500 to-danger-600 text-white shadow-lg shadow-danger-500/25 hover:shadow-xl hover:shadow-danger-500/35",
  };

  // 尺寸样式
  const sizeClasses = {
    sm: "px-3 py-1.5 text-xs",
    md: "px-5 py-2.5 text-sm",
    lg: "px-6 py-3 text-base",
  };

  // 默认涟漪颜色
  const defaultRippleColor = variant === "primary" || variant === "danger" 
    ? "rgba(255, 255, 255, 0.3)" 
    : "rgba(14, 165, 233, 0.2)";

  return (
    <button
      ref={buttonRef}
      className={`
        relative overflow-hidden
        font-semibold rounded-xl
        transition-all duration-300
        focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-soc-500 focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-soc-500
        active:scale-95
        disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100
        ${variantClasses[variant]}
        ${sizeClasses[size]}
        ${className}
      `}
      onClick={handleClick}
      disabled={disabled || isLoading}
      aria-busy={isLoading}
      aria-disabled={disabled || isLoading}
      {...props}
    >
      {isLoading && (
        <span className="absolute left-3 top-1/2 -translate-y-1/2" aria-hidden="true">
          <svg
            className="animate-spin w-4 h-4"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        </span>
      )}
      
      <span className={isLoading ? "ml-5" : ""}>{children}</span>
      
      {ripples.map((ripple) => (
        <span
          key={ripple.id}
          className="absolute rounded-full animate-ripple pointer-events-none"
          style={{
            left: ripple.x,
            top: ripple.y,
            backgroundColor: rippleColor || defaultRippleColor,
          }}
          aria-hidden="true"
        />
      ))}
    </button>
  );
}
