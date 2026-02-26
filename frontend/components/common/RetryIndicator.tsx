/**
 * Retry Indicator Component
 *
 * Shows retry status to users with countdown timer
 */

'use client';

import React, { useEffect, useState } from 'react';
import { formatRetryMessage, type RetryState } from '@/lib/retryConfig';

interface RetryIndicatorProps {
  retryState: RetryState;
  className?: string;
}

export function RetryIndicator({ retryState, className = '' }: RetryIndicatorProps) {
  const [countdown, setCountdown] = useState(retryState.nextRetryIn || 0);

  useEffect(() => {
    if (!retryState.nextRetryIn) return;

    setCountdown(retryState.nextRetryIn);

    const interval = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1000) {
          clearInterval(interval);
          return 0;
        }
        return prev - 1000;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [retryState.nextRetryIn]);

  const seconds = Math.ceil(countdown / 1000);
  const remaining = retryState.maxRetries - retryState.attempt;

  return (
    <div className={`flex items-center gap-2 text-sm text-amber-600 dark:text-amber-400 ${className}`}>
      <div className="flex items-center gap-2">
        {/* Spinner */}
        <svg
          className="animate-spin h-4 w-4"
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

        {/* Message */}
        <span>
          Retrying... ({remaining} {remaining === 1 ? 'attempt' : 'attempts'} left
          {seconds > 0 && `, in ${seconds}s`})
        </span>
      </div>
    </div>
  );
}

/**
 * Compact retry badge for inline use
 */
export function RetryBadge({ retryState }: { retryState: RetryState }) {
  return (
    <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-md bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200">
      <svg
        className="animate-spin h-3 w-3"
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
      Retrying...
    </span>
  );
}

/**
 * Full-page retry overlay
 */
export function RetryOverlay({
  retryState,
  message = 'Network error. Retrying...',
  onCancel,
}: {
  retryState: RetryState;
  message?: string;
  onCancel?: () => void;
}) {
  const [countdown, setCountdown] = useState(retryState.nextRetryIn || 0);

  useEffect(() => {
    if (!retryState.nextRetryIn) return;

    setCountdown(retryState.nextRetryIn);

    const interval = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1000) {
          clearInterval(interval);
          return 0;
        }
        return prev - 1000;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [retryState.nextRetryIn]);

  const seconds = Math.ceil(countdown / 1000);
  const remaining = retryState.maxRetries - retryState.attempt;
  const progress = ((retryState.attempt + 1) / (retryState.maxRetries + 1)) * 100;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
      <div className="max-w-md w-full mx-4 p-6 bg-card rounded-lg shadow-lg">
        {/* Progress bar */}
        <div className="mb-4">
          <div className="flex justify-between text-sm mb-2">
            <span className="text-muted-foreground">Retry Progress</span>
            <span className="text-muted-foreground">
              {retryState.attempt} / {retryState.maxRetries}
            </span>
          </div>
          <div className="w-full bg-secondary rounded-full h-2">
            <div
              className="bg-primary h-2 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {/* Icon */}
        <div className="flex justify-center mb-4">
          <div className="relative">
            <svg
              className="animate-spin h-12 w-12 text-primary"
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
            <span className="absolute top-0 right-0 -mt-1 -mr-1 flex h-4 w-4">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75" />
              <span className="relative inline-flex rounded-full h-4 w-4 bg-primary" />
            </span>
          </div>
        </div>

        {/* Message */}
        <div className="text-center mb-4">
          <h3 className="text-lg font-semibold mb-2">{message}</h3>
          <p className="text-muted-foreground">
            Next retry in {seconds} second{seconds !== 1 ? 's' : ''} ({remaining}{' '}
            {remaining === 1 ? 'attempt' : 'attempts'} remaining)
          </p>
        </div>

        {/* Cancel button */}
        {onCancel && (
          <div className="flex justify-center">
            <button
              onClick={onCancel}
              className="px-4 py-2 text-sm font-medium text-destructive hover:text-destructive/80 transition-colors"
            >
              Cancel
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
