/**
 * ErrorDisplay - User-friendly error display component
 */

"use client";

import React from "react";
import { useRouter } from "@/i18n/navigation";
import type { AppError } from "@/lib/errorHandler";

interface ErrorDisplayProps {
  error: AppError | Error | string;
  onRetry?: () => void;
  onDismiss?: () => void;
  showRequestId?: boolean;
  className?: string;
  compact?: boolean;
}

export function ErrorDisplay({
  error,
  onRetry,
  onDismiss,
  showRequestId = true,
  className = "",
  compact = false,
}: ErrorDisplayProps) {
  const router = useRouter();

  // Normalize error
  const normalizedError = normalizeError(error);

  const handleAction = () => {
    if (normalizedError.action) {
      normalizedError.action();
    } else if (onRetry) {
      onRetry();
    } else if (normalizedError.actionLabel === "Go to Login") {
      router.push("/login");
    }
  };

  // Compact version (for inline errors)
  if (compact) {
    return (
      <div className={`flex items-center gap-2 text-red-600 dark:text-red-400 ${className}`}>
        <svg className="w-4 h-4 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
          <path
            fillRule="evenodd"
            d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
            clipRule="evenodd"
          />
        </svg>
        <span className="text-sm font-medium">{normalizedError.message}</span>
        {(normalizedError.actionLabel || onRetry) && (
          <button onClick={handleAction} className="text-xs underline hover:no-underline ml-2">
            {normalizedError.actionLabel || "Retry"}
          </button>
        )}
      </div>
    );
  }

  // Full version (for page-level errors)
  return (
    <div className={`flex flex-col items-center justify-center p-8 text-center ${className}`}>
      {/* Error Icon */}
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

      {/* Error Title */}
      <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
        {normalizedError.title}
      </h3>

      {/* Error Message */}
      <p className="text-gray-600 dark:text-gray-400 mb-2 max-w-md">{normalizedError.message}</p>

      {/* Suggestion */}
      {normalizedError.suggestion && (
        <p className="text-sm text-gray-500 dark:text-gray-500 mb-6 max-w-md">
          💡 {normalizedError.suggestion}
        </p>
      )}

      {/* Request ID */}
      {showRequestId && normalizedError.requestId && (
        <p className="text-xs text-gray-400 dark:text-gray-600 mb-6">
          Request ID: {normalizedError.requestId}
        </p>
      )}

      {/* Action Buttons */}
      <div className="flex gap-3">
        {(normalizedError.actionLabel || onRetry) && (
          <button
            onClick={handleAction}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
          >
            {normalizedError.actionLabel || "Retry"}
          </button>
        )}
        {onDismiss && (
          <button
            onClick={onDismiss}
            className="px-4 py-2 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-lg transition-colors"
          >
            Dismiss
          </button>
        )}
      </div>
    </div>
  );
}

/**
 * ErrorAlert - Inline alert banner for errors
 */
interface ErrorAlertProps {
  error: AppError | Error | string;
  onRetry?: () => void;
  onDismiss?: () => void;
  className?: string;
}

export function ErrorAlert({ error, onRetry, onDismiss, className = "" }: ErrorAlertProps) {
  const normalizedError = normalizeError(error);

  return (
    <div
      className={`bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 ${className}`}
    >
      <div className="flex items-start">
        <div className="flex-shrink-0">
          <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
              clipRule="evenodd"
            />
          </svg>
        </div>
        <div className="ml-3 flex-1">
          <h3 className="text-sm font-medium text-red-800 dark:text-red-200">
            {normalizedError.title}
          </h3>
          <div className="mt-1 text-sm text-red-700 dark:text-red-300">
            <p>{normalizedError.message}</p>
            {normalizedError.suggestion && (
              <p className="mt-1 text-xs">💡 {normalizedError.suggestion}</p>
            )}
          </div>
          {normalizedError.requestId && (
            <p className="mt-1 text-xs text-red-600 dark:text-red-400">
              Request ID: {normalizedError.requestId}
            </p>
          )}
        </div>
        {(onRetry || onDismiss) && (
          <div className="ml-auto pl-3">
            <div className="flex gap-2">
              {onRetry && (
                <button
                  onClick={onRetry}
                  className="text-sm text-red-800 dark:text-red-200 hover:text-red-600 dark:hover:text-red-400 font-medium"
                >
                  Retry
                </button>
              )}
              {onDismiss && (
                <button
                  onClick={onDismiss}
                  className="text-sm text-red-800 dark:text-red-200 hover:text-red-600 dark:hover:text-red-400"
                >
                  ✕
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * ErrorToast - Toast notification for errors
 */
interface ErrorToastProps {
  error: AppError | Error | string;
  onRetry?: () => void;
  onDismiss?: () => void;
  duration?: number;
}

export function ErrorToast({ error, onRetry, onDismiss, duration = 5000 }: ErrorToastProps) {
  const normalizedError = normalizeError(error);

  React.useEffect(() => {
    if (duration && onDismiss) {
      const timer = setTimeout(onDismiss, duration);
      return () => clearTimeout(timer);
    }
  }, [duration, onDismiss]);

  return (
    <div className="fixed bottom-4 right-4 max-w-md bg-white dark:bg-gray-800 border-l-4 border-red-500 rounded-lg shadow-lg p-4 z-50 animate-slide-up">
      <div className="flex items-start">
        <div className="flex-shrink-0">
          <svg className="h-5 w-5 text-red-500" viewBox="0 0 20 20" fill="currentColor">
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
              clipRule="evenodd"
            />
          </svg>
        </div>
        <div className="ml-3 flex-1">
          <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
            {normalizedError.title}
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{normalizedError.message}</p>
        </div>
        <div className="ml-4 flex flex-shrink-0 gap-2">
          {onRetry && (
            <button
              onClick={onRetry}
              className="text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400"
            >
              Retry
            </button>
          )}
          {onDismiss && (
            <button
              onClick={onDismiss}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            >
              ✕
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Normalize error to AppError format
 */
function normalizeError(error: AppError | Error | string): AppError {
  if (typeof error === "string") {
    return {
      code: "GENERIC_ERROR",
      title: "Error",
      message: error,
      suggestion: "Please try again.",
    };
  }

  if (error instanceof Error) {
    return {
      code: "GENERIC_ERROR",
      title: "Error",
      message: error.message,
      suggestion: "Please try again.",
      details: error.stack,
    };
  }

  return error;
}
