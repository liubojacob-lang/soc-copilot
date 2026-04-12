/**
 * PageLoader - Full-page loading overlay with spinner
 * Use for initial page loads or major operations
 */

"use client";

import React from "react";

interface PageLoaderProps {
  message?: string;
  size?: "sm" | "md" | "lg";
}

export function PageLoader({ message, size = "md" }: PageLoaderProps) {
  const sizeClasses = {
    sm: "w-8 h-8",
    md: "w-12 h-12",
    lg: "w-16 h-16",
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-white dark:bg-gray-900 bg-opacity-90 dark:bg-opacity-90">
      <div className="flex flex-col items-center gap-4">
        <div
          className={`${sizeClasses[size]} border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin`}
        />
        {message && (
          <p className="text-sm text-gray-600 dark:text-gray-400 animate-pulse">{message}</p>
        )}
      </div>
    </div>
  );
}

/**
 * InlineLoader - Compact loading spinner for inline use
 */
interface InlineLoaderProps {
  message?: string;
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function InlineLoader({ message, size = "sm", className = "" }: InlineLoaderProps) {
  const sizeClasses = {
    sm: "w-4 h-4",
    md: "w-6 h-6",
    lg: "w-8 h-8",
  };

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div
        className={`${sizeClasses[size]} border-2 border-blue-200 border-t-blue-600 rounded-full animate-spin`}
      />
      {message && <span className="text-sm text-gray-600 dark:text-gray-400">{message}</span>}
    </div>
  );
}

/**
 * LoadingOverlay - Overlay for specific content areas
 */
interface LoadingOverlayProps {
  isLoading: boolean;
  message?: string;
  children: React.ReactNode;
}

export function LoadingOverlay({ isLoading, message, children }: LoadingOverlayProps) {
  return (
    <div className="relative">
      {children}
      {isLoading && (
        <div className="absolute inset-0 z-10 flex items-center justify-center bg-white dark:bg-gray-900 bg-opacity-75 dark:bg-opacity-75 rounded-lg">
          <InlineLoader message={message} size="md" />
        </div>
      )}
    </div>
  );
}
