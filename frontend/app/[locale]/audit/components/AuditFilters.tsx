"use client";

import { useTranslations } from "next-intl";
import { ChevronDown, Globe, RotateCcw, Search, Server, SlidersHorizontal, X } from "lucide-react";

import { cn } from "@/lib/utils";
import { AuditDateRangePicker } from "./AuditDateRangePicker";

interface FilterValues {
  action: string;
  path: string;
  statusCode: string;
  dateFrom: string;
  dateTo: string;
  userId: string;
  ipAddress: string;
}

interface AuditFiltersProps {
  filterAction: string;
  filterPath: string;
  filterStatusCode: string;
  filterDateFrom: string;
  filterDateTo: string;
  filterUserId: string;
  filterIpAddress: string;
  onFilterChange: (filters: FilterValues) => void;
  onReset: () => void;
}

/** 统一的输入控件样式（与告警列表工具栏同一设计语言） */
const controlClass =
  "w-full px-3 py-2 text-sm bg-surface-input border border-border-default rounded-lg focus:outline-none focus:ring-2 focus:ring-accent-500/20 focus:border-accent-600 text-text-primary placeholder:text-text-disabled transition-all";

const iconInputClass = cn(controlClass, "pl-9 pr-8");

export function AuditFilters({
  filterAction,
  filterPath,
  filterStatusCode,
  filterDateFrom,
  filterDateTo,
  filterUserId,
  filterIpAddress,
  onFilterChange,
  onReset,
}: AuditFiltersProps) {
  const t = useTranslations("auditPage");

  /** 携带局部覆盖，向上提交完整筛选对象 */
  const emit = (override: Partial<FilterValues>) =>
    onFilterChange({
      action: filterAction,
      path: filterPath,
      statusCode: filterStatusCode,
      dateFrom: filterDateFrom,
      dateTo: filterDateTo,
      userId: filterUserId,
      ipAddress: filterIpAddress,
      ...override,
    });

  const hasDate = Boolean(filterDateFrom || filterDateTo);
  const activeCount = [
    filterAction,
    filterStatusCode,
    filterPath,
    filterUserId,
    filterIpAddress,
  ].filter(Boolean).length;

  /** 已选条件 chips（可单独移除） */
  const chips: { key: string; label: string; value: string; onRemove: () => void }[] = [];
  if (filterAction)
    chips.push({
      key: "action",
      label: t("filters.action"),
      value: filterAction,
      onRemove: () => emit({ action: "" }),
    });
  if (filterStatusCode)
    chips.push({
      key: "statusCode",
      label: t("filters.statusCode"),
      value: filterStatusCode,
      onRemove: () => emit({ statusCode: "" }),
    });
  if (filterPath)
    chips.push({
      key: "path",
      label: t("filters.path"),
      value: filterPath,
      onRemove: () => emit({ path: "" }),
    });
  if (filterUserId)
    chips.push({
      key: "userId",
      label: t("filters.userId"),
      value: filterUserId,
      onRemove: () => emit({ userId: "" }),
    });
  if (filterIpAddress)
    chips.push({
      key: "ipAddress",
      label: t("filters.ipAddress"),
      value: filterIpAddress,
      onRemove: () => emit({ ipAddress: "" }),
    });

  return (
    <div className="rounded-xl border border-border-subtle bg-surface-card shadow-subtle p-4 sm:p-5">
      {/* 头部：标题 + 已选计数 + 重置 */}
      <div className="mb-4 flex items-center justify-between">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-text-primary">
          <SlidersHorizontal className="w-4 h-4 text-text-muted" />
          {t("filters.title")}
          {activeCount > 0 && (
            <span className="px-1.5 py-0.5 rounded-full text-[11px] font-semibold bg-accent-600 text-white leading-none">
              {activeCount}
            </span>
          )}
        </h3>
        {(activeCount > 0 || hasDate) && (
          <button
            type="button"
            onClick={onReset}
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-text-muted hover:text-text-primary hover:bg-surface-hover rounded-md transition-colors"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            {t("filters.reset")}
          </button>
        )}
      </div>

      {/* 筛选控件 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-12 gap-3">
        {/* 请求路径搜索 */}
        <div className="relative xl:col-span-4">
          <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
          <input
            type="text"
            value={filterPath}
            onChange={(e) => emit({ path: e.target.value })}
            placeholder={t("filters.searchPath")}
            aria-label={t("filters.path")}
            className={iconInputClass}
          />
          {filterPath && (
            <button
              type="button"
              onClick={() => emit({ path: "" })}
              aria-label={t("filters.clear")}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary transition-colors"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* 操作类型 */}
        <div className="relative xl:col-span-2">
          <select
            value={filterAction}
            onChange={(e) => emit({ action: e.target.value })}
            aria-label={t("filters.action")}
            className={cn(
              controlClass,
              "appearance-none pr-8 cursor-pointer",
              !filterAction && "text-text-muted"
            )}
          >
            <option value="">{t("filters.allActions")}</option>
            <option value="GET">GET</option>
            <option value="POST">POST</option>
            <option value="PUT">PUT</option>
            <option value="PATCH">PATCH</option>
            <option value="DELETE">DELETE</option>
            <option value="LOGIN">LOGIN</option>
            <option value="LOGOUT">LOGOUT</option>
          </select>
          <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-text-muted" />
        </div>

        {/* 状态码 */}
        <div className="relative xl:col-span-2">
          <select
            value={filterStatusCode}
            onChange={(e) => emit({ statusCode: e.target.value })}
            aria-label={t("filters.statusCode")}
            className={cn(
              controlClass,
              "appearance-none pr-8 cursor-pointer",
              !filterStatusCode && "text-text-muted"
            )}
          >
            <option value="">{t("filters.allStatuses")}</option>
            <option value="200">200 - OK</option>
            <option value="201">201 - Created</option>
            <option value="400">400 - Bad Request</option>
            <option value="401">401 - Unauthorized</option>
            <option value="403">403 - Forbidden</option>
            <option value="404">404 - Not Found</option>
            <option value="500">500 - Server Error</option>
          </select>
          <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-text-muted" />
        </div>

        {/* 日期范围 */}
        <div className="xl:col-span-4">
          <AuditDateRangePicker
            dateFrom={filterDateFrom}
            dateTo={filterDateTo}
            onChange={(from, to) => emit({ dateFrom: from, dateTo: to })}
          />
        </div>

        {/* 用户 ID */}
        <div className="relative xl:col-span-4">
          <Server className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
          <input
            type="text"
            value={filterUserId}
            onChange={(e) => emit({ userId: e.target.value })}
            placeholder={t("filters.searchUser")}
            aria-label={t("filters.userId")}
            className={iconInputClass}
          />
          {filterUserId && (
            <button
              type="button"
              onClick={() => emit({ userId: "" })}
              aria-label={t("filters.clear")}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary transition-colors"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* IP 地址 */}
        <div className="relative xl:col-span-4">
          <Globe className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
          <input
            type="text"
            value={filterIpAddress}
            onChange={(e) => emit({ ipAddress: e.target.value })}
            placeholder={t("filters.searchIp")}
            aria-label={t("filters.ipAddress")}
            className={iconInputClass}
          />
          {filterIpAddress && (
            <button
              type="button"
              onClick={() => emit({ ipAddress: "" })}
              aria-label={t("filters.clear")}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary transition-colors"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* 已选条件 chips */}
      {chips.length > 0 && (
        <div className="mt-3 pt-3 border-t border-border-subtle flex flex-wrap items-center gap-2">
          <span className="text-xs text-text-muted">{t("filters.activeFilters")}</span>
          {chips.map((chip) => (
            <span
              key={chip.key}
              className="inline-flex items-center gap-1.5 max-w-[280px] pl-2.5 pr-1 py-1 text-xs font-medium rounded-full border border-accent-500/40 bg-accent-500/10 text-accent-700 dark:text-accent-300"
            >
              <span className="text-accent-600/70 dark:text-accent-400/80">{chip.label}</span>
              <span className="truncate font-mono">{chip.value}</span>
              <button
                type="button"
                onClick={chip.onRemove}
                aria-label={`${t("filters.removeFilter")} ${chip.label}`}
                className="shrink-0 p-0.5 rounded-full hover:bg-accent-500/20 transition-colors"
              >
                <X className="w-3 h-3" />
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
