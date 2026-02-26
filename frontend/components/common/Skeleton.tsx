/**
 * Skeleton loading components for consistent loading states.
 */

import React from 'react';

interface SkeletonProps {
  className?: string;
  width?: string | number;
  height?: string | number;
  rounded?: 'none' | 'sm' | 'md' | 'lg' | 'full';
  animate?: boolean;
}

const roundedClasses = {
  none: 'rounded-none', sm: 'rounded-sm', md: 'rounded-md', lg: 'rounded-lg', full: 'rounded-full',
};

export function Skeleton({ className = '', width, height, rounded = 'md', animate = true }: SkeletonProps) {
  return (
    <div
      className={`bg-gray-200 dark:bg-gray-700 ${roundedClasses[rounded]} ${animate ? 'animate-pulse' : ''} ${className}`}
      style={{ width, height }}
    />
  );
}

export function SkeletonText({ lines = 3, lineHeight = '1rem', lastLineWidth = '60%', className = '' }: {
  lines?: number; lineHeight?: string; lastLineWidth?: string | number; className?: string;
}) {
  return (
    <div className={`space-y-2 ${className}`}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton key={i} height={lineHeight} width={i === lines - 1 ? lastLineWidth : '100%'} />
      ))}
    </div>
  );
}

export function SkeletonAvatar({ size = 'md', className = '' }: { size?: 'sm' | 'md' | 'lg' | 'xl'; className?: string }) {
  const sizeMap = { sm: '2rem', md: '3rem', lg: '4rem', xl: '6rem' };
  return <Skeleton width={sizeMap[size]} height={sizeMap[size]} rounded="full" className={className} />;
}

export function SkeletonCard({ hasHeader = true, hasAvatar = false, lines = 3, className = '' }: {
  hasHeader?: boolean; hasAvatar?: boolean; lines?: number; className?: string;
}) {
  return (
    <div className={`p-4 border border-gray-200 dark:border-gray-700 rounded-lg ${className}`}>
      {hasHeader && (
        <div className="flex items-center gap-3 mb-4">
          {hasAvatar && <SkeletonAvatar />}
          <div className="flex-1">
            <Skeleton height="1.25rem" width="60%" className="mb-2" />
            <Skeleton height="0.875rem" width="40%" />
          </div>
        </div>
      )}
      <SkeletonText lines={lines} />
    </div>
  );
}

export function SkeletonTable({ rows = 5, columns = 4, hasHeader = true, className = '' }: {
  rows?: number; columns?: number; hasHeader?: boolean; className?: string;
}) {
  return (
    <div className={`overflow-hidden border border-gray-200 dark:border-gray-700 rounded-lg ${className}`}>
      {hasHeader && (
        <div className="bg-gray-50 dark:bg-gray-800 p-3 flex gap-4">
          {Array.from({ length: columns }).map((_, i) => <Skeleton key={i} height="1rem" className="flex-1" />)}
        </div>
      )}
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={rowIndex} className="p-3 flex gap-4 border-t border-gray-200 dark:border-gray-700">
          {Array.from({ length: columns }).map((_, colIndex) => (
            <Skeleton key={colIndex} height="1rem" width={colIndex === 0 ? '80%' : '100%'} className="flex-1" />
          ))}
        </div>
      ))}
    </div>
  );
}

export function SkeletonList({ items = 5, hasAvatar = true, hasSecondaryText = true, className = '' }: {
  items?: number; hasAvatar?: boolean; hasSecondaryText?: boolean; className?: string;
}) {
  return (
    <div className={`space-y-3 ${className}`}>
      {Array.from({ length: items }).map((_, i) => (
        <div key={i} className="flex items-center gap-3 p-3 border border-gray-200 dark:border-gray-700 rounded-lg">
          {hasAvatar && <SkeletonAvatar size="md" />}
          <div className="flex-1">
            <Skeleton height="1rem" width="70%" className="mb-1" />
            {hasSecondaryText && <Skeleton height="0.875rem" width="50%" />}
          </div>
          <Skeleton height="2rem" width="5rem" rounded="md" />
        </div>
      ))}
    </div>
  );
}

export function SkeletonPlaybookRun({ className = '' }: { className?: string }) {
  return (
    <div className={`p-4 border border-gray-200 dark:border-gray-700 rounded-lg ${className}`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Skeleton height="1.5rem" width="10rem" />
          <Skeleton height="1.5rem" width="5rem" rounded="full" />
        </div>
        <Skeleton height="1.5rem" width="6rem" rounded="md" />
      </div>
      <SkeletonText lines={2} lineHeight="0.875rem" className="mb-3" />
      <div className="flex items-center gap-4">
        <Skeleton height="0.75rem" width="8rem" />
        <Skeleton height="0.75rem" width="6rem" />
        <Skeleton height="0.75rem" width="7rem" />
      </div>
    </div>
  );
}

export function SkeletonPage({ className = '' }: { className?: string }) {
  return (
    <div className={`p-6 ${className}`}>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <Skeleton height="2rem" width="15rem" className="mb-2" />
          <Skeleton height="1rem" width="25rem" />
        </div>
        <div className="flex gap-2">
          <Skeleton height="2.5rem" width="6rem" rounded="md" />
          <Skeleton height="2.5rem" width="8rem" rounded="md" />
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <SkeletonCard /><SkeletonCard /><SkeletonCard />
      </div>
      <SkeletonTable className="mt-6" />
    </div>
  );
}

export default Skeleton;