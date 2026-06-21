"use client";

import { ReactNode, useMemo, useCallback } from "react";
import { ChevronLeft, ChevronRight, Inbox } from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "./Badge";
import { Text, Heading } from "./Typography";

// ============================================================
// Types
// ============================================================

export type TableAlign = "left" | "center" | "right";

export interface ColumnDef<T> {
  /** 唯一键，用于 React key */
  key: string;
  /** 表头内容 */
  header: ReactNode;
  /** 单元格渲染函数 */
  cell: (row: T, rowIndex: number) => ReactNode;
  /** 列宽，如 "120px" / "15%" / "1fr" */
  width?: string;
  /** 对齐方式 */
  align?: TableAlign;
  /** 自定义类名 */
  className?: string;
}

export interface DataTableProps<T> {
  /** 数据数组 */
  data: T[];
  /** 列定义 */
  columns: ColumnDef<T>[];
  /** 当前页码（1-based） */
  currentPage?: number;
  /** 每页条数 */
  pageSize?: number;
  /** 总条数（不传则使用 data.length） */
  total?: number;
  /** 空状态配置 */
  emptyState?: {
    icon?: ReactNode;
    title?: string;
    description?: string;
  };
  /** 自定义类名 */
  className?: string;
  /** 页码变更回调 */
  onPageChange?: (page: number) => void;
  /** 行唯一 key 生成函数 */
  rowKey?: (row: T, index: number) => string;
  /** 是否显示分页 */
  showPagination?: boolean;
  /** 是否显示行分隔线 */
  showRowBorder?: boolean;
}

// ============================================================
// Helpers
// ============================================================

function generatePageItems(page: number, totalPages: number): (number | string)[] {
  if (totalPages <= 1) return [1];
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, i) => i + 1);
  }
  if (page <= 4) {
    return [1, 2, 3, 4, 5, "...", totalPages];
  }
  if (page >= totalPages - 3) {
    return [1, "...", totalPages - 4, totalPages - 3, totalPages - 2, totalPages - 1, totalPages];
  }
  return [1, "...", page - 1, page, page + 1, "...", totalPages];
}

function alignToClass(align?: TableAlign): string {
  switch (align) {
    case "center":
      return "text-center";
    case "right":
      return "text-right";
    default:
      return "text-left";
  }
}

// ============================================================
// Empty State
// ============================================================

interface DataTableEmptyProps {
  icon?: ReactNode;
  title?: string;
  description?: string;
}

function DataTableEmpty({ icon, title = "暂无数据", description }: DataTableEmptyProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
      {icon ? (
        <div className="mb-4 opacity-[0.15] text-text-tertiary">{icon}</div>
      ) : (
        <div className="mb-4 opacity-[0.15] text-text-tertiary">
          <Inbox className="w-16 h-16" strokeWidth={1.5} />
        </div>
      )}
      <Heading level={3} color="secondary" className="mb-1">
        {title}
      </Heading>
      {description && (
        <Text color="tertiary" className="max-w-sm">
          {description}
        </Text>
      )}
    </div>
  );
}

// ============================================================
// Pagination
// ============================================================

interface PaginationProps {
  page: number;
  pageSize: number;
  total: number;
  onChange?: (page: number) => void;
}

function Pagination({ page, pageSize, total, onChange }: PaginationProps) {
  const totalPages = useMemo(() => Math.max(1, Math.ceil(total / pageSize)), [total, pageSize]);
  const pageItems = useMemo(() => generatePageItems(page, totalPages), [page, totalPages]);

  const handlePrev = useCallback(() => {
    if (page > 1) onChange?.(page - 1);
  }, [page, onChange]);

  const handleNext = useCallback(() => {
    if (page < totalPages) onChange?.(page + 1);
  }, [page, totalPages, onChange]);

  const handlePageClick = useCallback(
    (p: number | string) => {
      if (typeof p === "number" && p !== page) {
        onChange?.(p);
      }
    },
    [page, onChange]
  );

  if (totalPages <= 1) return null;

  return (
    <div className="flex items-center justify-center gap-1 py-3">
      <button
        type="button"
        aria-label="上一页"
        onClick={handlePrev}
        disabled={page <= 1}
        className={cn(
          "inline-flex items-center justify-center w-8 h-8 rounded-sm transition-colors duration-150",
          "text-text-tertiary hover:text-text-primary hover:bg-surface-hover dark:hover:bg-slate-700",
          "disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-transparent"
        )}
      >
        <ChevronLeft className="w-4 h-4" />
      </button>

      {pageItems.map((item, idx) => {
        const isCurrent = item === page;
        const isEllipsis = item === "...";
        return (
          <button
            key={`${item}-${idx}`}
            type="button"
            aria-label={isEllipsis ? undefined : `第 ${item} 页`}
            aria-current={isCurrent ? "page" : undefined}
            disabled={isEllipsis}
            onClick={() => handlePageClick(item)}
            className={cn(
              "inline-flex items-center justify-center w-8 h-8 rounded-sm text-small transition-colors duration-150",
              isCurrent
                ? "bg-slate-900 text-white dark:bg-white dark:text-slate-900 font-medium"
                : "text-text-tertiary hover:text-text-primary hover:bg-surface-hover dark:hover:bg-slate-700",
              isEllipsis && "cursor-default opacity-60"
            )}
          >
            {item}
          </button>
        );
      })}

      <button
        type="button"
        aria-label="下一页"
        onClick={handleNext}
        disabled={page >= totalPages}
        className={cn(
          "inline-flex items-center justify-center w-8 h-8 rounded-sm transition-colors duration-150",
          "text-text-tertiary hover:text-text-primary hover:bg-surface-hover dark:hover:bg-slate-700",
          "disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-transparent"
        )}
      >
        <ChevronRight className="w-4 h-4" />
      </button>
    </div>
  );
}

// ============================================================
// Action Button
// ============================================================

export interface TableActionButtonProps {
  children: ReactNode;
  onClick?: () => void;
  variant?: "default" | "danger";
  className?: string;
  disabled?: boolean;
}

export function TableActionButton({
  children,
  onClick,
  variant = "default",
  className,
  disabled,
}: TableActionButtonProps) {
  const variantClasses = {
    default: "text-text-link hover:text-info-700 dark:hover:text-info-300",
    danger: "text-danger hover:text-danger-700 dark:hover:text-danger-300",
  };

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "inline-flex items-center gap-1 text-body font-normal transition-colors duration-150 disabled:opacity-40 disabled:cursor-not-allowed",
        variantClasses[variant],
        className
      )}
    >
      {children}
    </button>
  );
}

// ============================================================
// Severity Badge Helper
// ============================================================

export type TableSeverity = "critical" | "high" | "medium" | "low" | "info" | "neutral";

export interface SeverityBadgeCellProps {
  severity: TableSeverity;
  label?: string;
  className?: string;
}

export function SeverityBadgeCell({ severity, label, className }: SeverityBadgeCellProps) {
  const severityLabelMap: Record<TableSeverity, string> = {
    critical: "严重",
    high: "高危",
    medium: "中危",
    low: "低危",
    info: "信息",
    neutral: "一般",
  };
  return (
    <Badge severity={severity} className={className}>
      {label ?? severityLabelMap[severity]}
    </Badge>
  );
}

// ============================================================
// DataTable
// ============================================================

export function DataTable<T>({
  data,
  columns,
  currentPage = 1,
  pageSize = 10,
  total,
  emptyState,
  className,
  onPageChange,
  rowKey,
  showPagination = true,
  showRowBorder = true,
}: DataTableProps<T>) {
  const effectiveTotal = total ?? data.length;
  const isEmpty = data.length === 0;

  const tableContent = (
    <div className={cn("w-full overflow-x-auto", className)}>
      <table className="w-full border-collapse">
        <thead>
          <tr className="border-b border-border-subtle dark:border-slate-700">
            {columns.map((col) => (
              <th
                key={col.key}
                className={cn(
                  "h-12 px-4 py-3 text-left whitespace-nowrap text-body font-semibold text-text-tertiary select-none",
                  alignToClass(col.align)
                )}
                style={col.width ? { width: col.width, minWidth: col.width } : undefined}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, rowIdx) => {
            const key = rowKey ? rowKey(row, rowIdx) : `row-${rowIdx}`;
            return (
              <tr
                key={key}
                className={cn(
                  "h-[52px] transition-colors duration-150 hover:bg-surface-hover dark:hover:bg-slate-800/60",
                  showRowBorder && "border-b border-border-subtle dark:border-slate-700/60"
                )}
              >
                {columns.map((col) => (
                  <td
                    key={col.key}
                    className={cn(
                      "px-4 py-2 align-middle text-body text-text-primary",
                      alignToClass(col.align),
                      col.className
                    )}
                  >
                    {col.cell(row, rowIdx)}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );

  return (
    <div className="w-full">
      {isEmpty ? (
        <DataTableEmpty
          icon={emptyState?.icon}
          title={emptyState?.title}
          description={emptyState?.description}
        />
      ) : (
        <>
          {tableContent}
          {showPagination && effectiveTotal > 0 && (
            <>
              <div className="border-t border-border-subtle dark:border-slate-700" />
              <Pagination
                page={currentPage}
                pageSize={pageSize}
                total={effectiveTotal}
                onChange={onPageChange}
              />
            </>
          )}
        </>
      )}
    </div>
  );
}

export default DataTable;
