"use client";

/**
 * Virtual List Component for efficient rendering of large lists.
 *
 * Features:
 * - Only renders visible items
 * - Variable item height support
 * - Smooth scrolling
 * - Resize observer for responsive containers
 */

import React, { useState, useRef, useEffect, useCallback, useMemo, memo } from "react";

interface VirtualListProps<T> {
  items: T[];
  itemHeight: number | ((index: number) => number);
  containerHeight: number;
  renderItem: (item: T, index: number) => React.ReactNode;
  overscan?: number;
  className?: string;
  onScroll?: (scrollTop: number) => void;
  onLoadMore?: () => void;
  hasMore?: boolean;
  loadingMore?: boolean;
  loadingComponent?: React.ReactNode;
  emptyComponent?: React.ReactNode;
}

interface ItemPosition {
  index: number;
  offset: number;
  height: number;
}

function VirtualListComponent<T>({
  items,
  itemHeight,
  containerHeight,
  renderItem,
  overscan = 3,
  className = "",
  onScroll,
  onLoadMore,
  hasMore = false,
  loadingMore = false,
  loadingComponent,
  emptyComponent,
}: VirtualListProps<T>) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [measuredHeights, setMeasuredHeights] = useState<Map<number, number>>(new Map());

  // Calculate item positions
  const itemPositions = useMemo<ItemPosition[]>(() => {
    const positions: ItemPosition[] = [];
    let offset = 0;

    for (let i = 0; i < items.length; i++) {
      let height: number;

      if (measuredHeights.has(i)) {
        height = measuredHeights.get(i)!;
      } else if (typeof itemHeight === "function") {
        height = itemHeight(i);
      } else {
        height = itemHeight;
      }

      positions.push({ index: i, offset, height });
      offset += height;
    }

    return positions;
  }, [items, itemHeight, measuredHeights]);

  // Calculate total height
  const totalHeight = useMemo(() => {
    if (itemPositions.length === 0) return 0;
    const last = itemPositions[itemPositions.length - 1];
    return last.offset + last.height;
  }, [itemPositions]);

  // Find visible range
  const visibleRange = useMemo(() => {
    if (itemPositions.length === 0) {
      return { startIndex: 0, endIndex: 0 };
    }

    let startIndex = 0;
    let endIndex = itemPositions.length - 1;

    // Binary search for start index
    let low = 0;
    let high = itemPositions.length - 1;
    while (low <= high) {
      const mid = Math.floor((low + high) / 2);
      const pos = itemPositions[mid];

      if (pos.offset + pos.height < scrollTop) {
        low = mid + 1;
      } else {
        high = mid - 1;
      }
    }
    startIndex = Math.max(0, low - overscan);

    // Binary search for end index
    low = 0;
    high = itemPositions.length - 1;
    while (low <= high) {
      const mid = Math.floor((low + high) / 2);
      const pos = itemPositions[mid];

      if (pos.offset <= scrollTop + containerHeight) {
        low = mid + 1;
      } else {
        high = mid - 1;
      }
    }
    endIndex = Math.min(itemPositions.length - 1, low + overscan);

    return { startIndex, endIndex };
  }, [itemPositions, scrollTop, containerHeight, overscan]);

  // Handle scroll
  const handleScroll = useCallback(
    (e: React.UIEvent<HTMLDivElement>) => {
      const newScrollTop = e.currentTarget.scrollTop;
      setScrollTop(newScrollTop);
      onScroll?.(newScrollTop);

      // Check if we need to load more
      if (onLoadMore && hasMore && !loadingMore) {
        const scrollBottom = newScrollTop + containerHeight;
        const threshold = totalHeight - containerHeight * 0.2; // Load when 20% from bottom

        if (scrollBottom >= threshold) {
          onLoadMore();
        }
      }
    },
    [onScroll, onLoadMore, hasMore, loadingMore, containerHeight, totalHeight]
  );

  // Measure item heights after render
  useEffect(() => {
    if (typeof itemHeight !== "function" || !containerRef.current) return;

    const container = containerRef.current;
    const items = container.querySelectorAll("[data-index]");
    const newHeights = new Map<number, number>();

    items.forEach((item) => {
      const index = parseInt(item.getAttribute("data-index") || "", 10);
      if (!isNaN(index)) {
        const height = item.getBoundingClientRect().height;
        if (height > 0) {
          newHeights.set(index, height);
        }
      }
    });

    if (newHeights.size > 0) {
      setMeasuredHeights((prev) => {
        const merged = new Map(prev);
        newHeights.forEach((height, index) => {
          if (!prev.has(index) || prev.get(index) !== height) {
            merged.set(index, height);
          }
        });
        return merged;
      });
    }
  }, [visibleRange, itemHeight]);

  // Render empty state
  if (items.length === 0 && emptyComponent) {
    return (
      <div className={className} style={{ height: containerHeight }}>
        {emptyComponent}
      </div>
    );
  }

  // Get visible items
  const visibleItems = itemPositions.slice(visibleRange.startIndex, visibleRange.endIndex + 1);

  return (
    <div
      ref={containerRef}
      className={className}
      style={{
        height: containerHeight,
        overflow: "auto",
        position: "relative",
      }}
      onScroll={handleScroll}
    >
      <div
        style={{
          height: totalHeight,
          position: "relative",
        }}
      >
        {visibleItems.map((pos) => (
          <div
            key={pos.index}
            data-index={pos.index}
            style={{
              position: "absolute",
              top: pos.offset,
              left: 0,
              right: 0,
              height: pos.height,
            }}
          >
            {renderItem(items[pos.index], pos.index)}
          </div>
        ))}
      </div>

      {/* Loading indicator */}
      {loadingMore && (
        <div
          style={{
            position: "absolute",
            bottom: 0,
            left: 0,
            right: 0,
            padding: "16px",
            textAlign: "center",
          }}
        >
          {loadingComponent || <div className="text-text-tertiary">Loading more...</div>}
        </div>
      )}
    </div>
  );
}

// Export with memo for performance
export const VirtualList = memo(VirtualListComponent) as typeof VirtualListComponent;

// Hook for infinite scroll
export function useInfiniteScroll<T>(
  fetchMore: (page: number) => Promise<T[]>,
  initialItems: T[] = [],
  pageSize: number = 20
) {
  const [items, setItems] = useState<T[]>(initialItems);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const loadMore = useCallback(async () => {
    if (loading || !hasMore) return;

    setLoading(true);
    setError(null);

    try {
      const newItems = await fetchMore(page + 1);

      if (newItems.length < pageSize) {
        setHasMore(false);
      }

      setItems((prev) => [...prev, ...newItems]);
      setPage((prev) => prev + 1);
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setLoading(false);
    }
  }, [fetchMore, page, pageSize, loading, hasMore]);

  const reset = useCallback(() => {
    setItems(initialItems);
    setPage(1);
    setHasMore(true);
    setLoading(false);
    setError(null);
  }, [initialItems]);

  return {
    items,
    hasMore,
    loading,
    error,
    loadMore,
    reset,
  };
}

export default VirtualList;
