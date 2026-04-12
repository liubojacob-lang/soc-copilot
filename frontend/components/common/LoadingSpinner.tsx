"use client";

interface LoadingSpinnerProps {
  size?: "xs" | "sm" | "md" | "lg" | "xl";
  color?: "soc" | "success" | "warning" | "danger" | "gray" | "white";
  className?: string;
  label?: string;
}

const sizeClasses = {
  xs: "w-3 h-3",
  sm: "w-4 h-4",
  md: "w-6 h-6",
  lg: "w-8 h-8",
  xl: "w-12 h-12",
};

const colorClasses = {
  soc: "text-soc-500",
  success: "text-success-500",
  warning: "text-warning-500",
  danger: "text-danger-500",
  gray: "text-gray-400",
  white: "text-white",
};

export function LoadingSpinner({
  size = "md",
  color = "soc",
  className = "",
  label,
}: LoadingSpinnerProps) {
  return (
    <div
      className={`inline-flex items-center gap-2 ${className}`}
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      <svg
        className={`${sizeClasses[size]} ${colorClasses[color]} animate-spin`}
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        aria-hidden="true"
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
      {label && <span className={`text-sm ${colorClasses[color]}`}>{label}</span>}
      {!label && <span className="sr-only">加载中...</span>}
    </div>
  );
}

// 全屏加载遮罩
interface FullScreenLoaderProps {
  message?: string;
  className?: string;
}

export function FullScreenLoader({ message = "加载中...", className = "" }: FullScreenLoaderProps) {
  return (
    <div
      className={`
        fixed inset-0 z-50
        flex flex-col items-center justify-center
        bg-white/80 dark:bg-gray-900/80
        backdrop-blur-sm
        ${className}
      `}
      role="alert"
      aria-busy="true"
      aria-live="assertive"
    >
      <LoadingSpinner size="xl" color="soc" />
      {message && <p className="mt-4 text-gray-600 dark:text-gray-400 text-sm">{message}</p>}
    </div>
  );
}

// 骨架屏加载
interface SkeletonLoaderProps {
  count?: number;
  className?: string;
}

export function SkeletonLoader({ count = 3, className = "" }: SkeletonLoaderProps) {
  return (
    <div className={`space-y-3 ${className}`}>
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="
            animate-shimmer
            bg-gradient-to-r from-gray-200 via-gray-100 to-gray-200
            dark:from-gray-700 dark:via-gray-600 dark:to-gray-700
            bg-[length:200%_100%]
            rounded-xl
            h-16
          "
        />
      ))}
    </div>
  );
}
