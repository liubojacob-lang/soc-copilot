/**
 * LoadingState - Versatile loading state component
 * Handles skeleton, spinner, and empty states
 */

"use client";

import React from "react";
import { Skeleton } from "./Skeleton";
import { InlineLoader } from "./PageLoader";

interface LoadingStateProps {
  isLoading: boolean;
  error?: Error | string | null;
  empty?: boolean;
  emptyMessage?: string;
  errorMessage?: string;
  loadingMessage?: string;
  type?: "skeleton" | "spinner" | "dots";
  children?: React.ReactNode;
  skeletonType?: "table" | "card" | "list" | "custom";
  skeletonProps?: Record<string, any>;
  onRetry?: () => void;
}

export function LoadingState({
  isLoading,
  error,
  empty = false,
  emptyMessage = "No data found",
  errorMessage = "Something went wrong",
  loadingMessage,
  type = "skeleton",
  children,
  skeletonType = "table",
  skeletonProps = {},
  onRetry,
}: LoadingStateProps) {
  // Error state
  if (error && !isLoading) {
    return (
      <div className="flex flex-col items-center justify-center p-8 text-center">
        <div className="w-16 h-16 mb-4 text-red-500">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        </div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">Error</h3>
        <p className="text-gray-600 dark:text-gray-400 mb-4">
          {typeof error === "string" ? error : error.message || errorMessage}
        </p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
          >
            Retry
          </button>
        )}
      </div>
    );
  }

  // Loading state
  if (isLoading) {
    if (type === "spinner") {
      return (
        <div className="flex items-center justify-center p-8">
          <InlineLoader message={loadingMessage} size="lg" />
        </div>
      );
    }

    if (type === "dots") {
      return (
        <div className="flex flex-col items-center justify-center p-8">
          <div className="flex gap-2 mb-3">
            <div
              className="w-3 h-3 bg-blue-600 rounded-full animate-bounce"
              style={{ animationDelay: "0ms" }}
            />
            <div
              className="w-3 h-3 bg-blue-600 rounded-full animate-bounce"
              style={{ animationDelay: "150ms" }}
            />
            <div
              className="w-3 h-3 bg-blue-600 rounded-full animate-bounce"
              style={{ animationDelay: "300ms" }}
            />
          </div>
          {loadingMessage && (
            <p className="text-sm text-gray-600 dark:text-gray-400">{loadingMessage}</p>
          )}
        </div>
      );
    }

    // Default: skeleton
    if (skeletonType === "table") {
      return <SkeletonTable {...skeletonProps} />;
    }
    if (skeletonType === "card") {
      return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 p-4">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      );
    }
    if (skeletonType === "list") {
      return <SkeletonList {...skeletonProps} />;
    }

    return <Skeleton />;
  }

  // Empty state
  if (empty && !isLoading) {
    return (
      <div className="flex flex-col items-center justify-center p-8 text-center">
        <div className="w-16 h-16 mb-4 text-gray-400">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
            />
          </svg>
        </div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">No Data</h3>
        <p className="text-gray-600 dark:text-gray-400">{emptyMessage}</p>
      </div>
    );
  }

  // Content
  return <>{children}</>;
}

// Import the components we need
function SkeletonTable({ rows = 5, columns = 4 }: { rows?: number; columns?: number }) {
  return (
    <div className="overflow-hidden border border-gray-200 dark:border-gray-700 rounded-lg">
      <div className="bg-gray-50 dark:bg-gray-800 p-3 flex gap-4">
        {Array.from({ length: columns }).map((_, i) => (
          <div key={i} className="h-4 flex-1 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div
          key={rowIndex}
          className="p-3 flex gap-4 border-t border-gray-200 dark:border-gray-700"
        >
          {Array.from({ length: columns }).map((_, colIndex) => (
            <div
              key={colIndex}
              className="h-4 flex-1 bg-gray-200 dark:bg-gray-700 rounded animate-pulse"
              style={{ width: colIndex === 0 ? "80%" : "100%" }}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg">
      <div className="h-5 bg-gray-200 dark:bg-gray-700 rounded animate-pulse mb-3 w-3/4" />
      <div className="space-y-2">
        <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
        <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded animate-pulse w-5/6" />
        <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded animate-pulse w-4/6" />
      </div>
    </div>
  );
}

function SkeletonList({ items = 5 }: { items?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: items }).map((_, i) => (
        <div
          key={i}
          className="flex items-center gap-3 p-3 border border-gray-200 dark:border-gray-700 rounded-lg"
        >
          <div className="w-12 h-12 bg-gray-200 dark:bg-gray-700 rounded-full animate-pulse" />
          <div className="flex-1 space-y-2">
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded animate-pulse w-3/4" />
            <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded animate-pulse w-1/2" />
          </div>
          <div className="h-8 w-20 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
        </div>
      ))}
    </div>
  );
}

export { SkeletonTable, SkeletonCard, SkeletonList };
