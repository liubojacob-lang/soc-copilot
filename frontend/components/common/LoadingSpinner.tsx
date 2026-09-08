"use client";

import React from "react";
import { useTranslations } from "next-intl";

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
  soc: "text-primary-500",
  success: "text-success-500",
  warning: "text-warning-500",
  danger: "text-danger-500",
  gray: "text-gray-400",
  white: "text-white",
};

const LoadingSpinner = React.memo(function LoadingSpinner({
  size = "md",
  color = "soc",
  className = "",
  label,
}: LoadingSpinnerProps) {
  const t = useTranslations("common");
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
      {!label && <span className="sr-only">{t("loading")}</span>}
    </div>
  );
});

// 全屏加载遮罩
interface FullScreenLoaderProps {
  message?: string;
  className?: string;
}

const FullScreenLoader = React.memo(function FullScreenLoader({
  message,
  className = "",
}: FullScreenLoaderProps) {
  const t = useTranslations("common");
  const messageText = message ?? t("loading");
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
      {messageText && (
        <p className="mt-4 text-gray-600 dark:text-gray-400 text-sm">{messageText}</p>
      )}
    </div>
  );
});

// 骨架屏加载
interface SkeletonLoaderProps {
  count?: number;
  className?: string;
}

const SkeletonLoader = React.memo(function SkeletonLoader({
  count = 3,
  className = "",
}: SkeletonLoaderProps) {
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
});

export { LoadingSpinner, FullScreenLoader, SkeletonLoader };
