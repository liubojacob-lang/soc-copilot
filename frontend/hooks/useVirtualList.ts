/**
 * Virtual List Hook
 * 用于大列表的虚拟滚动优化
 */

import { useState, useEffect, useRef, useCallback, useMemo } from "react";

interface UseVirtualListOptions {
  itemHeight: number;
  overscan?: number;
  containerHeight?: number;
}

interface VirtualItem<T> {
  item: T;
  index: number;
  style: React.CSSProperties;
}

export function useVirtualList<T>(items: T[], options: UseVirtualListOptions) {
  const { itemHeight, overscan = 5, containerHeight: initialHeight = 400 } = options;

  const containerRef = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [containerHeight, setContainerHeight] = useState(initialHeight);

  // 监听容器大小变化
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setContainerHeight(entry.contentRect.height);
      }
    });

    resizeObserver.observe(container);
    return () => resizeObserver.disconnect();
  }, []);

  // 监听滚动
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleScroll = () => {
      setScrollTop(container.scrollTop);
    };

    container.addEventListener("scroll", handleScroll, { passive: true });
    return () => container.removeEventListener("scroll", handleScroll);
  }, []);

  // 计算可见范围
  const virtualItems = useMemo(() => {
    const totalHeight = items.length * itemHeight;
    const startIndex = Math.max(0, Math.floor(scrollTop / itemHeight) - overscan);
    const visibleCount = Math.ceil(containerHeight / itemHeight) + overscan * 2;
    const endIndex = Math.min(items.length, startIndex + visibleCount);

    const virtualItems: VirtualItem<T>[] = [];
    for (let i = startIndex; i < endIndex; i++) {
      virtualItems.push({
        item: items[i],
        index: i,
        style: {
          position: "absolute",
          top: i * itemHeight,
          left: 0,
          right: 0,
          height: itemHeight,
        },
      });
    }

    return {
      items: virtualItems,
      totalHeight,
      startIndex,
      endIndex,
    };
  }, [items, itemHeight, scrollTop, containerHeight, overscan]);

  // 滚动到指定索引
  const scrollToIndex = useCallback(
    (index: number) => {
      const container = containerRef.current;
      if (!container) return;

      container.scrollTo({
        top: index * itemHeight,
        behavior: "smooth",
      });
    },
    [itemHeight]
  );

  return {
    containerRef,
    virtualItems: virtualItems.items,
    totalHeight: virtualItems.totalHeight,
    startIndex: virtualItems.startIndex,
    endIndex: virtualItems.endIndex,
    scrollToIndex,
  };
}

// 使用示例
// const { containerRef, virtualItems, totalHeight } = useVirtualList(
//   largeArray,
//   { itemHeight: 50, overscan: 5 }
// );
//
// return (
//   <div ref={containerRef} style={{ height: '400px', overflow: 'auto' }}>
//     <div style={{ height: totalHeight, position: 'relative' }}>
//       {virtualItems.map(({ item, style }) => (
//         <div key={item.id} style={style}>
//           {item.content}
//         </div>
//       ))}
//     </div>
//   </div>
// );
