import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * 安全地合并 Tailwind CSS 类名
 * 使用 clsx 处理条件类名，使用 tailwind-merge 处理 Tailwind 类冲突
 *
 * @example
 * cn('px-2 py-1', isActive && 'bg-soc-500', 'hover:bg-soc-600')
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
