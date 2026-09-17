import { useRef } from "react";
import { useTranslations } from "next-intl";

import { getPageNumbers } from "../utils";

interface AuditPaginationProps {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
  isFetching?: boolean;
}

export function AuditPagination({
  page,
  pageSize,
  total,
  onPageChange,
  onPageSizeChange,
  isFetching = false,
}: AuditPaginationProps) {
  const t = useTranslations("auditPage");
  const containerRef = useRef<HTMLDivElement>(null);

  if (total === 0 && !isFetching) return null;

  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const pageNumbers = getPageNumbers(page, total, pageSize);

  return (
    <div
      ref={containerRef}
      className="sticky bottom-0 z-20 mt-6 flex flex-col sm:flex-row items-center justify-between gap-4 px-4 py-3 bg-white/95 dark:bg-gray-800/95 backdrop-blur-md border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg transition-all"
    >
      {/* Left: Statistics */}
      <div className="text-sm text-gray-700 dark:text-gray-300">
        {t.rich("pagination.range", {
          from: (page - 1) * pageSize + 1,
          to: Math.min(page * pageSize, total),
          total,
          strong: (chunks) => (
            <span className="font-semibold text-blue-600 dark:text-blue-400">{chunks}</span>
          ),
        })}
      </div>

      {/* Center: Page Numbers */}
      <div className="flex items-center gap-1 flex-wrap justify-center">
        {/* First Page */}
        <button
          onClick={() => onPageChange(1)}
          disabled={page === 1}
          className="w-8 h-8 flex items-center justify-center text-sm font-medium rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          title={t("pagination.first")}
        >
          «
        </button>

        {/* Previous Page */}
        <button
          onClick={() => onPageChange(Math.max(1, page - 1))}
          disabled={page === 1}
          className="w-8 h-8 flex items-center justify-center text-sm font-medium rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          title={t("pagination.prev")}
        >
          ‹
        </button>

        {/* Page Numbers */}
        {pageNumbers.map((p, i) =>
          p === "..." ? (
            <span
              key={`ellipsis-${i}`}
              className="w-8 h-8 flex items-center justify-center text-gray-500 dark:text-gray-400"
            >
              ...
            </span>
          ) : (
            <button
              key={`page-${p}`}
              onClick={() => onPageChange(p as number)}
              className={`w-8 h-8 flex items-center justify-center text-sm font-medium rounded-lg transition-colors ${
                page === p
                  ? "bg-blue-500 text-white border-blue-500 shadow-md"
                  : "border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
              }`}
            >
              {p}
            </button>
          )
        )}

        {/* Next Page */}
        <button
          onClick={() => onPageChange(Math.min(totalPages, page + 1))}
          disabled={page === totalPages}
          className="w-8 h-8 flex items-center justify-center text-sm font-medium rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          title={t("pagination.next")}
        >
          ›
        </button>

        {/* Last Page */}
        <button
          onClick={() => onPageChange(totalPages)}
          disabled={page === totalPages}
          className="w-8 h-8 flex items-center justify-center text-sm font-medium rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          title={t("pagination.last")}
        >
          »
        </button>
      </div>

      {/* Right: Page Size Selector */}
      <div className="flex items-center gap-2">
        <span className="text-sm text-gray-600 dark:text-gray-400">
          {t("pagination.perPagePrefix")}
        </span>
        <select
          value={pageSize}
          onChange={(e) => {
            const newSize = Number(e.target.value);
            onPageSizeChange(newSize);
            // Smoothly anchor the pagination container in view
            requestAnimationFrame(() => {
              containerRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
            });
          }}
          disabled={isFetching}
          className="text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-2 py-1.5 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50"
          aria-label={t("pagination.perPagePrefix")}
        >
          <option value="25">25</option>
          <option value="50">50</option>
          <option value="100">100</option>
          <option value="200">200</option>
        </select>
        <span className="text-sm text-gray-600 dark:text-gray-400">
          {t("pagination.perPageSuffix")}
        </span>
      </div>
    </div>
  );
}
