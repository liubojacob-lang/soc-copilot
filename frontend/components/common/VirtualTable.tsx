"use client";

import { memo, useCallback, useMemo, useState, useRef, useEffect } from "react";

interface VirtualTableProps<T> {
  data: T[];
  columns: {
    key: string;
    header: string;
    width?: string;
    render: (item: T, index: number) => React.ReactNode;
  }[];
  rowHeight?: number;
  containerHeight?: number;
  overscan?: number;
  onRowClick?: (item: T, index: number) => void;
  emptyMessage?: string;
  loading?: boolean;
  loadingComponent?: React.ReactNode;
  className?: string;
}

function VirtualTableInner<T>({
  data,
  columns,
  rowHeight = 56,
  containerHeight = 600,
  overscan = 5,
  onRowClick,
  emptyMessage = "No data available",
  loading = false,
  loadingComponent,
  className = "",
}: VirtualTableProps<T>) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);

  const { startIndex, endIndex, totalHeight } = useMemo(() => {
    const totalHeight = data.length * rowHeight;
    const visibleCount = Math.ceil(containerHeight / rowHeight);
    const startIndex = Math.max(0, Math.floor(scrollTop / rowHeight) - overscan);
    const endIndex = Math.min(data.length - 1, startIndex + visibleCount + overscan * 2);

    return { startIndex, endIndex, totalHeight };
  }, [data.length, rowHeight, containerHeight, scrollTop, overscan]);

  const visibleData = useMemo(() => {
    return data.slice(startIndex, endIndex + 1);
  }, [data, startIndex, endIndex]);

  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    setScrollTop(e.currentTarget.scrollTop);
  }, []);

  if (loading) {
    return (
      <div className={`bg-white dark:bg-gray-800 rounded-lg shadow ${className}`}>
        {loadingComponent || (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        )}
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className={`bg-white dark:bg-gray-800 rounded-lg shadow ${className}`}>
        <div className="p-8 text-center text-gray-500 dark:text-gray-400">{emptyMessage}</div>
      </div>
    );
  }

  return (
    <div className={`bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden ${className}`}>
      <div className="overflow-x-auto">
        <table className="min-w-full" style={{ display: "block" }}>
          <thead className="bg-gray-50 dark:bg-gray-700 sticky top-0 z-10">
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider"
                  style={{ width: col.width }}
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
        </table>
      </div>
      <div
        ref={containerRef}
        onScroll={handleScroll}
        style={{
          height: containerHeight,
          overflow: "auto",
          position: "relative",
        }}
      >
        <div style={{ height: totalHeight, position: "relative" }}>
          <table className="min-w-full">
            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
              {visibleData.map((item, idx) => {
                const actualIndex = startIndex + idx;
                return (
                  <tr
                    key={actualIndex}
                    onClick={() => onRowClick?.(item, actualIndex)}
                    className={`hover:bg-gray-50 dark:hover:bg-gray-750 ${
                      onRowClick ? "cursor-pointer" : ""
                    }`}
                    style={{
                      position: "absolute",
                      top: actualIndex * rowHeight,
                      left: 0,
                      right: 0,
                      height: rowHeight,
                      display: "flex",
                      width: "100%",
                    }}
                  >
                    {columns.map((col) => (
                      <td
                        key={col.key}
                        className="px-4 py-3 text-sm flex-shrink-0"
                        style={{ width: col.width }}
                      >
                        {col.render(item, actualIndex)}
                      </td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export const VirtualTable = memo(VirtualTableInner) as typeof VirtualTableInner;

export function useVirtualTable<T>(
  data: T[],
  containerHeight: number = 600,
  rowHeight: number = 56
) {
  const [scrollTop, setScrollTop] = useState(0);

  const visibleRange = useMemo(() => {
    const startIndex = Math.floor(scrollTop / rowHeight);
    const visibleCount = Math.ceil(containerHeight / rowHeight);
    const endIndex = Math.min(data.length - 1, startIndex + visibleCount);

    return { startIndex, endIndex };
  }, [scrollTop, rowHeight, containerHeight, data.length]);

  return {
    scrollTop,
    setScrollTop,
    visibleRange,
    totalHeight: data.length * rowHeight,
  };
}

export default VirtualTable;
