"use client";

import { useEffect, useState } from "react";

/**
 * 对值进行防抖。用于文本类筛选条件：
 * 输入立即回显，但查询参数延迟 delay 毫秒才变化，避免逐字符触发请求。
 */
export function useDebouncedValue<T>(value: T, delay = 300): T {
  const [debounced, setDebounced] = useState<T>(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debounced;
}
