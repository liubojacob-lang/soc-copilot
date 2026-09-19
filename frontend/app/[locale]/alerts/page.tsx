"use client";

/**
 * Security Alerts List Page
 *
 * Features:
 * - Search: by title, description, IP, agent
 * - Filters: status (multi-select), severity (multi-select), source type, time range
 * - Sort: by created_at, severity, status (asc/desc)
 * - Pagination: via existing DataTable
 * - Batch operations: select rows → batch status change
 * - Loading/Empty/Error states: via LoadingState
 * - Responsive: card view on mobile, table on desktop
 */

import { useState, useEffect, useMemo, useCallback, useRef } from "react";
import { useRouter } from "@/i18n/navigation";
import { useFormatter, useLocale, useTranslations } from "next-intl";
import {
  Shield,
  Search,
  Filter,
  X,
  ChevronDown,
  ChevronUp,
  ArrowUpDown,
  Trash2,
  CheckCircle,
  MoreHorizontal,
  AlertTriangle,
  Clock,
  Server,
  RefreshCw,
  Upload,
  Download,
  Sparkles,
} from "lucide-react";
import ImportAlertModal from "./components/ImportAlertModal";
import { loadAuthState, authFetch } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/Badge";
import { PageHeader } from "@/components/common/PageHeader";
import { DataTable, type ColumnDef, type TableSeverity } from "@/components/ui/DataTable";
import { SeverityBreakdown } from "@/components/ui/SeverityBreakdown";
import { LoadingState } from "@/components/common/LoadingState";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { Button } from "@/components/common/Button";
import { useToast } from "@/components/Toast";
import { useAlerts, useBatchUpdateAlerts, useDeleteAlert, useAlertStats } from "@/hooks/useAlerts";
import type { SecurityAlertItem, AlertListFilters, AlertStatus, AlertSeverity } from "@/lib/api";

// ── Constants ──────────────────────────────────────────

const PAGE_SIZE = 20;

type SortField = "created_at" | "severity" | "status" | "title" | "source";
type SortDir = "asc" | "desc";

const SEVERITY_ORDER: Record<string, number> = {
  critical: 5,
  high: 4,
  medium: 3,
  low: 2,
  info: 1,
};

const STATUS_ORDER: Record<string, number> = {
  new: 1,
  investigating: 2,
  escalated: 3,
  resolved: 4,
  false_positive: 5,
};

// ── Helper: map severity to TableSeverity ────────────────

function mapSeverity(s: string): TableSeverity {
  const m: Record<string, TableSeverity> = {
    critical: "critical",
    high: "high",
    medium: "medium",
    low: "low",
    info: "info",
  };
  return m[s] || "neutral";
}

// ── Helper: map status to badge variant ─────────────────

function mapStatusSeverity(s: string): TableSeverity {
  const m: Record<string, TableSeverity> = {
    new: "info",
    investigating: "medium",
    resolved: "low",
    false_positive: "neutral",
    escalated: "high",
  };
  return m[s] || "neutral";
}

// ── Helper: format time ────────────────────────────────

function formatTime(ts: string | null, format: ReturnType<typeof useFormatter>): string {
  if (!ts) return "-";
  try {
    const d = new Date(ts);
    if (isNaN(d.getTime())) return "-";
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    if (diffMs < 7 * 24 * 60 * 60 * 1000) {
      return format.relativeTime(d);
    }
    return format.dateTime(d, { dateStyle: "medium" });
  } catch {
    return "-";
  }
}

// ── Sortable Header ────────────────────────────────────
//
// 之前只有"严重级别 / 状态 / 时间"三列带排序箭头，而且箭头只在**已激活**时才出现，
// 未激活的列完全看不出能不能排；"标题 / 来源"干脆没有排序入口。
// 现在所有可排序列统一：未激活显示淡色双向箭头（暗示"可排序"），
// 激活后换成明确的方向箭头并提高对比度。

function SortHeader({
  label,
  field,
  sortField,
  sortDir,
  onSort,
}: {
  label: string;
  field: SortField;
  sortField: SortField;
  sortDir: SortDir;
  onSort: (field: SortField, defaultDir: SortDir) => void;
}) {
  const active = sortField === field;
  return (
    <button
      type="button"
      onClick={() => onSort(field, field === "created_at" ? "desc" : "asc")}
      aria-sort={active ? (sortDir === "asc" ? "ascending" : "descending") : "none"}
      className={cn(
        "-mx-1 inline-flex items-center gap-1 rounded px-1 py-0.5 font-semibold transition-colors",
        active ? "text-text-primary" : "text-text-tertiary hover:text-text-primary"
      )}
    >
      {label}
      {active ? (
        sortDir === "asc" ? (
          <ChevronUp className="w-3 h-3" />
        ) : (
          <ChevronDown className="w-3 h-3" />
        )
      ) : (
        <ArrowUpDown className="w-3 h-3 opacity-50" />
      )}
    </button>
  );
}

// ── Severity Badge ─────────────────────────────────────

function SeverityTag({ severity }: { severity: string }) {
  const t = useTranslations("severity");
  const s = severity.toLowerCase();
  let label = severity;
  try {
    label = t(s as any) || severity;
  } catch {
    label = severity;
  }
  return <Badge severity={mapSeverity(severity)}>{label}</Badge>;
}

// ── Status Badge ───────────────────────────────────────

function StatusTag({ status }: { status: string }) {
  const t = useTranslations("status");
  const labels: Record<string, string> = {
    new: t("new"),
    investigating: t("investigating"),
    resolved: t("resolved"),
    false_positive: t("falsePositive"),
    escalated: t("escalated"),
  };
  return <Badge severity={mapStatusSeverity(status)}>{labels[status] || status}</Badge>;
}

// ── Filter Dropdown ────────────────────────────────────

interface FilterDropdownProps {
  label: string;
  options: { value: string; label: string }[];
  selected: string[];
  onChange: (values: string[]) => void;
}

function FilterDropdown({ label, options, selected, onChange }: FilterDropdownProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const toggle = (value: string) => {
    if (selected.includes(value)) {
      onChange(selected.filter((v) => v !== value));
    } else {
      onChange([...selected, value]);
    }
  };

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className={cn(
          // h-9 与同排的搜索框（h-9）和次级按钮（Button size=md）对齐到同一基线，
          // 此前用 py-2 + text-sm 会算出 38px，比左右邻居各高 2px。
          "flex h-9 items-center gap-2 px-3 text-xs sm:text-sm rounded-lg border transition-all duration-150",
          selected.length > 0
            ? "border-accent-500/40 bg-accent-500/10 text-accent-700 dark:text-accent-300 font-medium"
            : "border-border-subtle bg-surface-card text-text-secondary hover:border-border-default hover:text-text-primary shadow-subtle"
        )}
      >
        <Filter className="w-3.5 h-3.5 text-text-muted" />
        <span>{label}</span>
        {selected.length > 0 && (
          <span className="ml-0.5 px-1.5 py-0.2 rounded-full text-[11px] font-semibold bg-accent-600 text-white">
            {selected.length}
          </span>
        )}
        <ChevronDown className="w-3 h-3 ml-0.5 text-text-muted" />
      </button>

      {open && (
        <div className="absolute top-full left-0 mt-1.5 w-52 bg-surface-card border border-border-subtle rounded-xl shadow-elevated z-20 py-1.5 max-h-60 overflow-y-auto">
          {options.map((opt) => (
            <label
              key={opt.value}
              className="flex items-center gap-2.5 px-3 py-2 hover:bg-surface-ground active:bg-surface-ground cursor-pointer text-xs sm:text-sm text-text-primary transition-colors"
            >
              <input
                type="checkbox"
                checked={selected.includes(opt.value)}
                onChange={() => toggle(opt.value)}
                className="rounded border-border-default text-accent-600 focus:ring-accent-500/40"
              />
              <span>{opt.label}</span>
            </label>
          ))}
          {selected.length > 0 && (
            <button
              type="button"
              onClick={() => onChange([])}
              className="w-full text-left px-3 py-2 text-xs text-text-muted hover:text-text-primary hover:bg-surface-ground border-t border-border-subtle transition-colors"
            >
              Clear all
            </button>
          )}
        </div>
      )}
    </div>
  );
}

// ── Filter Chip ────────────────────────────────────────
//
// 当前生效筛选条件的可移除回显。之前界面上完全没有这个信息，
// 用户筛选后只看到"结果变少了"，不知道是哪一条条件在起作用。

function FilterChip({ label, onRemove }: { label: string; onRemove: () => void }) {
  const tCommon = useTranslations("common");
  return (
    <span className="inline-flex h-7 items-center gap-1 rounded-full border border-accent-500/40 bg-accent-500/10 pl-2.5 pr-1 text-xs font-medium text-accent-700 dark:text-accent-300">
      <span className="max-w-[12rem] truncate">{label}</span>
      <button
        type="button"
        onClick={onRemove}
        aria-label={tCommon("cancel")}
        className="flex h-5 w-5 items-center justify-center rounded-full transition-colors hover:bg-accent-500/20"
      >
        <X className="h-3 w-3" />
      </button>
    </span>
  );
}

// ── Stats Bar ───────────────────────────────────────────
//
// 之前这里直接 Object.entries(by_severity) 遍历，顺序完全取决于 API 返回的
// 对象键序，实测渲染成「中 → 信息 → 高 → 严重 → 低」这种无逻辑排列；
// 而且只有文字 + ×N，没有任何量级编码，必须逐个读数字才能建立分布印象。
// 现在与仪表盘共用 SeverityBreakdown —— 同一维度、同一排序、同一视觉语言。

function StatsBar({
  total,
  stats,
}: {
  total: number;
  stats?: { by_severity?: Record<string, number>; by_status?: Record<string, number> };
}) {
  const t = useTranslations("alerts");

  return (
    <div className="mb-4 rounded-xl border border-border-subtle bg-surface-card px-4 py-3.5">
      <div className="mb-3 flex items-baseline justify-between gap-3">
        <span className="text-sm font-medium text-text-secondary">
          {t("totalCount", { count: total })}
        </span>
      </div>
      <SeverityBreakdown counts={stats?.by_severity} layout="grid" />
    </div>
  );
}

// ── Page Component ──────────────────────────────────────

export default function AlertsPage() {
  const format = useFormatter();
  const router = useRouter();
  const locale = useLocale();
  const t = useTranslations("alerts");
  const tCommon = useTranslations("common");
  const { showToast } = useToast();

  // Auth
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    setMounted(true);
    const authState = loadAuthState();
    if (!authState?.isAuthenticated) {
      router.push("/login");
    }
  }, [router]);

  // ── Filter State ────────────────────────────────────
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string[]>([]);
  const [severityFilter, setSeverityFilter] = useState<string[]>([]);
  const [sourceFilter, setSourceFilter] = useState("");
  const [page, setPage] = useState(1);
  const [sortField, setSortField] = useState<SortField>("created_at");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [showBatchPanel, setShowBatchPanel] = useState(false);
  const [showMobileFilters, setShowMobileFilters] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);

  // Debounce search
  const debounceRef = useRef<NodeJS.Timeout>(undefined);
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setDebouncedSearch(search);
      setPage(1);
    }, 400);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [search]);

  // ── 筛选回显 ─────────────────────────────────────────
  // 当前生效条件的数量与标签。用于工具栏徽标、"清除全部"入口与条件 chip。
  const activeFilterCount =
    (debouncedSearch ? 1 : 0) +
    statusFilter.length +
    severityFilter.length +
    (sourceFilter ? 1 : 0);

  const statusFilterLabels: Record<string, string> = useMemo(
    () => ({
      new: t("statusNew"),
      investigating: t("statusInvestigating"),
      resolved: t("statusResolved"),
      false_positive: t("statusFalsePositive"),
      escalated: t("statusEscalated"),
    }),
    [t]
  );

  const severityFilterLabels: Record<string, string> = useMemo(
    () => ({
      critical: t("severityCritical"),
      high: t("severityHigh"),
      medium: t("severityMedium"),
      low: t("severityLow"),
      info: t("severityInfo"),
    }),
    [t]
  );

  const clearAllFilters = useCallback(() => {
    setSearch("");
    setStatusFilter([]);
    setSeverityFilter([]);
    setSourceFilter("");
    setPage(1);
  }, []);

  const handleSort = useCallback(
    (field: SortField, defaultDir: SortDir) => {
      if (sortField === field) {
        setSortDir(sortDir === "asc" ? "desc" : "asc");
      } else {
        setSortField(field);
        setSortDir(defaultDir);
      }
    },
    [sortField, sortDir]
  );

  // ── Build Filters ────────────────────────────────────
  const filters: AlertListFilters = useMemo(() => {
    const f: AlertListFilters = {
      page,
      page_size: PAGE_SIZE,
    };
    if (debouncedSearch) f.search = debouncedSearch;
    if (statusFilter.length === 1) {
      f.status = statusFilter[0];
    } else if (statusFilter.length > 1) {
      f.status = statusFilter.join(",");
    }
    if (severityFilter.length === 1) {
      f.severity = severityFilter[0];
    } else if (severityFilter.length > 1) {
      f.severity = severityFilter.join(",");
    }
    if (sourceFilter) f.source = sourceFilter;
    return f;
  }, [page, debouncedSearch, statusFilter, severityFilter, sourceFilter]);

  // ── Data Fetching ────────────────────────────────────
  const { data, isLoading, error, refetch } = useAlerts(filters);
  const { data: statsData } = useAlertStats();
  const batchUpdate = useBatchUpdateAlerts();
  const deleteAlert = useDeleteAlert();

  const total = data?.total ?? 0;
  const alerts: SecurityAlertItem[] = data?.alerts ?? [];

  // ── Client-side sort (when backed doesn't support full sort) ─
  const sortedAlerts = useMemo(() => {
    const sorted = [...alerts];
    sorted.sort((a, b) => {
      let cmp = 0;
      if (sortField === "created_at") {
        const aTime = a.created_at || "";
        const bTime = b.created_at || "";
        cmp = aTime.localeCompare(bTime);
      } else if (sortField === "severity") {
        cmp = (SEVERITY_ORDER[a.severity] || 0) - (SEVERITY_ORDER[b.severity] || 0);
      } else if (sortField === "status") {
        cmp = (STATUS_ORDER[a.status] || 0) - (STATUS_ORDER[b.status] || 0);
      } else if (sortField === "title") {
        cmp = (a.title || "").localeCompare(b.title || "");
      } else if (sortField === "source") {
        cmp = (a.source || "").localeCompare(b.source || "");
      }
      return sortDir === "asc" ? cmp : -cmp;
    });
    return sorted;
  }, [alerts, sortField, sortDir]);

  // ── Selection ────────────────────────────────────────
  const toggleSelect = useCallback((id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const toggleSelectAll = useCallback(() => {
    if (selectedIds.size === sortedAlerts.length && sortedAlerts.length > 0) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(sortedAlerts.map((a) => a.id)));
    }
  }, [selectedIds, sortedAlerts]);

  // ── Batch Actions ────────────────────────────────────
  const handleBatchStatus = async (status: string) => {
    if (selectedIds.size === 0) return;
    const count = selectedIds.size;
    try {
      await batchUpdate.mutateAsync({
        ids: Array.from(selectedIds),
        payload: { status },
      });
      setSelectedIds(new Set());
      setShowBatchPanel(false);
      const statusLabel =
        status === "resolved"
          ? t("statusResolved")
          : status === "false_positive"
            ? t("statusFalsePositive")
            : status === "investigating"
              ? t("statusInvestigating")
              : status;
      showToast(t("batch.updated", { count, status: statusLabel }), "success");
    } catch (err) {
      showToast(
        `${t("batch.failed")}: ${err instanceof Error ? err.message : "Unknown error"}`,
        "error"
      );
    }
  };

  const [deleteTargetId, setDeleteTargetId] = useState<number | null>(null);

  const handleDelete = (id: number) => {
    setDeleteTargetId(id);
  };

  const confirmDelete = async () => {
    if (deleteTargetId === null) return;
    try {
      await deleteAlert.mutateAsync(deleteTargetId);
      showToast(t("deleteSuccess"), "success");
    } catch {
      showToast(t("deleteFailed"), "error");
    } finally {
      setDeleteTargetId(null);
    }
  };

  const [exporting, setExporting] = useState(false);

  const handleExport = async (formatType: "csv" | "json" = "csv") => {
    setExporting(true);
    try {
      const params = new URLSearchParams();
      params.append("format", formatType);
      if (severityFilter.length === 1) params.append("severity", severityFilter[0]);
      if (statusFilter.length === 1) params.append("status", statusFilter[0]);
      const res = await authFetch(`/api/v1/export/alerts?${params.toString()}`);
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `alerts-${new Date().toISOString().split("T")[0]}.${formatType}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        showToast(t("exportSuccess") || "告警数据导出成功", "success");
      } else {
        showToast(t("exportFailed") || "导出失败", "error");
      }
    } catch (err) {
      showToast(err instanceof Error ? err.message : "导出异常", "error");
    } finally {
      setExporting(false);
    }
  };

  // Reset page on filter change
  useEffect(() => setPage(1), [debouncedSearch, statusFilter, severityFilter, sourceFilter]);

  // ── Columns ──────────────────────────────────────────

  const columns: ColumnDef<SecurityAlertItem>[] = useMemo(
    () => [
      {
        key: "select",
        header: (
          <input
            type="checkbox"
            checked={sortedAlerts.length > 0 && selectedIds.size === sortedAlerts.length}
            onChange={toggleSelectAll}
            className="rounded border-gray-300 text-accent-600 focus:ring-accent-500"
          />
        ),
        cell: (row) => (
          <input
            type="checkbox"
            checked={selectedIds.has(row.id)}
            onChange={() => toggleSelect(row.id)}
            className="rounded border-gray-300 text-accent-600 focus:ring-accent-500"
          />
        ),
        width: "40px",
        align: "center",
      },
      {
        key: "title",
        // max-w-0 + w-full 是"自适应列里做截断"的标准写法：
        // 单元格的 max-content 贡献被压成 0，于是它只吃表格的剩余宽度，
        // 不再被内容反过来撑大（实测：注入超长标题时列宽从 925 涨到 2100，
        // 整张表被推出视口）。配上单元格内的 max-w-full，长标题会在真实
        // 可用宽度处出省略号，而不是被封在 600px 里、右侧空出 300px。
        className: "w-full max-w-0",
        header: (
          <SortHeader
            label={t("list.title")}
            field="title"
            sortField={sortField}
            sortDir={sortDir}
            onSort={handleSort}
          />
        ),
        cell: (row) => (
          <div className="min-w-0">
            {/* 标题是告警队列里唯一的识别依据，被截断后相似告警无法区分，
                因此必须把完整文本挂在 title 属性上供悬停查看。
                宽度用 max-w-full 而不是具体像素：<button> 在本布局下按 max-content
                定宽，原先的 max-w-[600px] 会在 925px 的列里留下 300px 死区
                （正是审查里"标题列留出大片空白"那条）；而完全不设上限又会让
                超长标题撑破单元格。max-w-full 等于"最多占满本列"，
                省略号由 truncate 按真实可用宽度触发。 */}
            <div className="flex items-center gap-2 max-w-full">
              <button
                onClick={() => router.push(`/alerts/${row.id}`)}
                title={row.title}
                className="text-sm font-medium text-accent-600 hover:text-accent-700 dark:text-accent-400 dark:hover:text-accent-300 hover:underline truncate block text-left transition-colors"
              >
                {row.title}
              </button>
              {(row.raw_data as any)?.pipeline?.ai_triage && (
                <span
                  title={`AI 预分诊: ${(row.raw_data as any).pipeline.ai_triage.summary || ""}`}
                  className="inline-flex shrink-0 items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-purple-50 text-purple-700 dark:bg-purple-950/40 dark:text-purple-300 border border-purple-200 dark:border-purple-800/50"
                >
                  <Sparkles className="w-2.5 h-2.5" />
                  AI 已分诊
                </span>
              )}
            </div>
            {row.description && (
              <p title={row.description} className="text-xs text-text-tertiary line-clamp-1 mt-0.5">
                {row.description}
              </p>
            )}
          </div>
        ),
      },
      {
        key: "severity",
        header: (
          <SortHeader
            label={tCommon("severity")}
            field="severity"
            sortField={sortField}
            sortDir={sortDir}
            onSort={handleSort}
          />
        ),
        cell: (row) => <SeverityTag severity={row.severity} />,
        width: "120px",
      },
      {
        key: "status",
        header: (
          <SortHeader
            label={t("list.status")}
            field="status"
            sortField={sortField}
            sortDir={sortDir}
            onSort={handleSort}
          />
        ),
        cell: (row) => <StatusTag status={row.status} />,
        width: "130px",
      },
      {
        key: "source",
        // 宽度由 100px 提到 140px：`api-key-pipeline` 这类来源标识此前会被折成两行
        header: (
          <SortHeader
            label={t("list.source")}
            field="source"
            sortField={sortField}
            sortDir={sortDir}
            onSort={handleSort}
          />
        ),
        cell: (row) => (
          <span
            title={row.source || undefined}
            className="block max-w-[140px] truncate text-sm text-text-secondary"
          >
            {row.source || "-"}
          </span>
        ),
        width: "140px",
      },
      {
        key: "time",
        header: (
          <SortHeader
            label={t("list.time")}
            field="created_at"
            sortField={sortField}
            sortDir={sortDir}
            onSort={handleSort}
          />
        ),
        cell: (row) => (
          <span className="text-sm text-text-tertiary whitespace-nowrap">
            {formatTime(row.event_timestamp || row.created_at, format)}
          </span>
        ),
        width: "110px",
      },
      {
        key: "actions",
        header: "",
        cell: (row) => (
          <div className="flex items-center gap-1 justify-end">
            {/* 删除常驻但视觉极弱，既容易误点也容易被忽略 —— 已有二次确认弹窗兜底 */}
            <button
              onClick={() => handleDelete(row.id)}
              className="flex h-8 w-8 items-center justify-center text-text-muted hover:text-danger-600 dark:hover:text-danger-400 rounded-md hover:bg-danger-500/10 active:bg-danger-500/10 transition-colors"
              title={tCommon("delete")}
              aria-label={tCommon("delete")}
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        ),
        width: "56px",
        align: "right",
      },
    ],
    [
      t,
      tCommon,
      locale,
      router,
      selectedIds,
      sortedAlerts,
      toggleSelectAll,
      toggleSelect,
      sortField,
      sortDir,
      handleSort,
    ]
  );

  if (!mounted) return null;

  // ── Mobile Card Render ────────────────────────────────

  const renderMobileCard = (alert: SecurityAlertItem) => (
    <div
      key={alert.id}
      className={cn(
        "bg-surface-card rounded-xl border p-4 transition-all duration-150 shadow-subtle",
        selectedIds.has(alert.id)
          ? "border-accent-500 ring-1 ring-accent-500"
          : "border-border-subtle hover:border-border-default"
      )}
    >
      <div className="flex items-start gap-3">
        <input
          type="checkbox"
          checked={selectedIds.has(alert.id)}
          onChange={() => toggleSelect(alert.id)}
          className="mt-1 rounded border-border-default text-accent-600 focus:ring-accent-500"
        />
        <div className="flex-1 min-w-0">
          <button
            onClick={() => router.push(`/alerts/${alert.id}`)}
            className="text-sm font-semibold text-text-primary hover:text-accent-600 dark:hover:text-accent-400 text-left line-clamp-2 transition-colors"
          >
            {alert.title}
          </button>
          <div className="flex flex-wrap items-center gap-2 mt-2">
            <SeverityTag severity={alert.severity} />
            <StatusTag status={alert.status} />
            {(alert.raw_data as any)?.pipeline?.ai_triage && (
              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-purple-50 text-purple-700 dark:bg-purple-950/40 dark:text-purple-300 border border-purple-200 dark:border-purple-800/50">
                <Sparkles className="w-2.5 h-2.5" />
                AI 已分诊
              </span>
            )}
            <span className="text-xs text-text-muted">{alert.source}</span>
          </div>
          <div className="flex items-center gap-2 mt-2 text-xs text-text-muted">
            <Clock className="w-3.5 h-3.5" />
            {formatTime(alert.event_timestamp || alert.created_at, format)}
            {alert.source_ip && (
              <>
                <span className="text-border-default">·</span>
                <Server className="w-3.5 h-3.5" />
                <code className="text-xs">{alert.source_ip}</code>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );

  // ── Skeleton State ───────────────────────────────────
  const SkeletonRows = () => (
    <div className="space-y-2 p-4">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="h-16 bg-gray-100 dark:bg-gray-800 rounded-lg animate-pulse" />
      ))}
    </div>
  );

  // ── Error State ─────────────────────────────────────
  const errorState = error && (
    <LoadingState isLoading={false} error={error} onRetry={() => refetch()} />
  );

  // ── Content ──────────────────────────────────────────
  const content = (
    <>
      {/* Stats Bar */}
      {statsData && <StatsBar total={total} stats={statsData} />}

      {/* Toolbar —— 左边"查询区"、右边"数据管理区"，两组之间用分隔线隔开。
          之前"导入"是本行唯一的实心主按钮，抢走了本该属于查询的注意力，
          而且紧贴"严重级别"下拉、无任何分组间隔，读起来像筛选器的一部分。 */}
      <div className="mb-3 flex flex-col gap-3 lg:flex-row lg:items-center">
        {/* 查询区 */}
        <div className="flex flex-1 flex-col gap-2 sm:flex-row sm:items-center">
          <div className="relative w-full sm:max-w-xs">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={t("list.searchPlaceholder")}
              className="h-9 w-full pl-9 pr-8 text-sm bg-surface-input border border-border-default rounded-lg focus:outline-none focus:ring-2 focus:ring-accent-500/20 focus:border-accent-600 text-text-primary placeholder:text-text-tertiary transition-all"
            />
            {search && (
              <button
                onClick={() => setSearch("")}
                aria-label={tCommon("clear") || "清除"}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Desktop Filters */}
          <div className="hidden sm:flex items-center gap-2">
            <FilterDropdown
              label={t("list.status")}
              options={[
                { value: "new", label: t("statusNew") },
                { value: "investigating", label: t("statusInvestigating") },
                { value: "resolved", label: t("statusResolved") },
                { value: "false_positive", label: t("statusFalsePositive") },
                { value: "escalated", label: t("statusEscalated") },
              ]}
              selected={statusFilter}
              onChange={(v) => {
                setStatusFilter(v);
                setPage(1);
              }}
            />
            <FilterDropdown
              label={tCommon("severity")}
              options={[
                { value: "critical", label: t("severityCritical") },
                { value: "high", label: t("severityHigh") },
                { value: "medium", label: t("severityMedium") },
                { value: "low", label: t("severityLow") },
                { value: "info", label: t("severityInfo") },
              ]}
              selected={severityFilter}
              onChange={(v) => {
                setSeverityFilter(v);
                setPage(1);
              }}
            />
          </div>

          {/* Mobile Filter Toggle */}
          <button
            onClick={() => setShowMobileFilters(!showMobileFilters)}
            className="sm:hidden flex h-9 items-center gap-2 px-3 text-xs font-medium border border-border-subtle rounded-lg bg-surface-card text-text-secondary"
          >
            <Filter className="w-3.5 h-3.5" />
            {t("filterMobile")}
            {activeFilterCount > 0 && (
              <span className="px-1.5 py-0.2 text-[11px] bg-accent-500/20 text-accent-600 rounded-full font-semibold">
                {activeFilterCount}
              </span>
            )}
          </button>
        </div>

        {/* 数据管理区 —— 全部次级权重；"导入"不再是实心主按钮 */}
        <div className="flex items-center gap-2 lg:border-l lg:border-border-subtle lg:pl-3">
          <Button
            onClick={() => refetch()}
            variant="outline"
            size="md"
            title={tCommon("refresh")}
            aria-label={tCommon("refresh")}
            className="px-2.5"
          >
            <RefreshCw className="w-4 h-4 text-text-muted" />
          </Button>

          <Button
            onClick={() => handleExport("csv")}
            variant="outline"
            size="md"
            isLoading={exporting}
            leftIcon={<Download className="w-4 h-4 text-text-muted" />}
            title={tCommon("export") || "导出 CSV"}
          >
            <span className="hidden sm:inline">{tCommon("export") || "导出"}</span>
          </Button>

          <Button
            onClick={() => setShowImportModal(true)}
            variant="outline"
            size="md"
            leftIcon={<Upload className="w-4 h-4 text-text-muted" />}
            title={t("importAlerts")}
          >
            <span className="hidden sm:inline">{tCommon("import")}</span>
          </Button>
        </div>
      </div>

      {/* 当前筛选回显 —— 之前应用筛选后界面没有任何回显，也没有"清除全部"入口，
          用户会陷入"为什么只有 3 条结果"的困惑。 */}
      {activeFilterCount > 0 && (
        <div className="mb-4 flex flex-wrap items-center gap-2 text-xs">
          <span className="text-text-muted">{t("list.activeFilters")}</span>
          {debouncedSearch && (
            <FilterChip
              label={`${t("list.search")}: ${debouncedSearch}`}
              onRemove={() => setSearch("")}
            />
          )}
          {statusFilter.map((s) => (
            <FilterChip
              key={`st-${s}`}
              label={statusFilterLabels[s] || s}
              onRemove={() => setStatusFilter(statusFilter.filter((v) => v !== s))}
            />
          ))}
          {severityFilter.map((s) => (
            <FilterChip
              key={`sev-${s}`}
              label={severityFilterLabels[s] || s}
              onRemove={() => setSeverityFilter(severityFilter.filter((v) => v !== s))}
            />
          ))}
          {sourceFilter && <FilterChip label={sourceFilter} onRemove={() => setSourceFilter("")} />}
          <button
            type="button"
            onClick={clearAllFilters}
            className="ml-1 font-medium text-accent-600 hover:underline dark:text-accent-400"
          >
            {t("list.clearFilters")}
          </button>
        </div>
      )}

      {/* Mobile Filters Panel */}
      {showMobileFilters && (
        <div className="sm:hidden bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 mb-4 space-y-3">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">{t("status")}</h3>
          <div className="flex flex-wrap gap-2">
            {[
              { value: "new", label: t("statusNew") },
              { value: "investigating", label: t("statusInvestigating") },
              { value: "resolved", label: t("statusResolved") },
              { value: "false_positive", label: t("statusFalsePositive") },
              { value: "escalated", label: t("statusEscalated") },
            ].map((opt) => (
              <button
                key={opt.value}
                onClick={() => {
                  setStatusFilter((prev) =>
                    prev.includes(opt.value)
                      ? prev.filter((v) => v !== opt.value)
                      : [...prev, opt.value]
                  );
                  setPage(1);
                }}
                className={cn(
                  "px-2.5 py-1 text-xs rounded-full border transition-colors",
                  statusFilter.includes(opt.value)
                    ? "border-accent-500 bg-accent-50 text-accent-700 dark:border-accent-400 dark:bg-accent-900/30 dark:text-accent-300"
                    : "border-gray-200 text-gray-500 dark:border-gray-600 dark:text-gray-400"
                )}
              >
                {opt.label}
              </button>
            ))}
          </div>
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
            {tCommon("severity")}
          </h3>
          <div className="flex flex-wrap gap-2">
            {[
              { value: "critical", label: t("severityCritical") },
              { value: "high", label: t("severityHigh") },
              { value: "medium", label: t("severityMedium") },
              { value: "low", label: t("severityLow") },
              { value: "info", label: t("severityInfo") },
            ].map((opt) => (
              <button
                key={opt.value}
                onClick={() => {
                  setSeverityFilter((prev) =>
                    prev.includes(opt.value)
                      ? prev.filter((v) => v !== opt.value)
                      : [...prev, opt.value]
                  );
                  setPage(1);
                }}
                className={cn(
                  "px-2.5 py-1 text-xs rounded-full border transition-colors",
                  severityFilter.includes(opt.value)
                    ? "border-accent-500 bg-accent-50 text-accent-700 dark:border-accent-400 dark:bg-accent-900/30 dark:text-accent-300"
                    : "border-gray-200 text-gray-500 dark:border-gray-600 dark:text-gray-400"
                )}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Batch Action Bar */}
      {selectedIds.size > 0 && (
        <div className="bg-surface-card border border-accent-500/30 rounded-xl p-3 mb-4 flex items-center gap-3 flex-wrap shadow-subtle">
          <span className="text-xs font-semibold text-accent-600 dark:text-accent-400">
            {t("batch.selected", { count: selectedIds.size })}
          </span>
          <div className="flex items-center gap-2">
            <Button
              size="xs"
              variant="primary"
              onClick={() => handleBatchStatus("resolved")}
              className="bg-emerald-600 hover:bg-emerald-700 active:bg-emerald-800 text-white"
              leftIcon={<CheckCircle className="w-3.5 h-3.5" />}
            >
              {t("batch.resolve")}
            </Button>
            <Button
              size="xs"
              variant="secondary"
              onClick={() => handleBatchStatus("false_positive")}
            >
              {t("batch.falsePositive")}
            </Button>
            <Button size="xs" variant="outline" onClick={() => handleBatchStatus("investigating")}>
              {t("batch.investigate")}
            </Button>
          </div>
          <button
            onClick={() => setSelectedIds(new Set())}
            className="ml-auto p-1 text-text-muted hover:text-text-primary rounded-md transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Desktop Table */}
      <div className="hidden sm:block bg-surface-card rounded-xl border border-border-subtle overflow-hidden shadow-subtle">
        <DataTable
          data={sortedAlerts}
          columns={columns}
          currentPage={page}
          pageSize={PAGE_SIZE}
          total={total}
          onPageChange={setPage}
          emptyState={{
            title: t("list.emptyTitle"),
            description: t("list.emptyDescription"),
          }}
          showPagination={total > PAGE_SIZE}
        />
      </div>

      {/* Mobile Cards */}
      <div className="sm:hidden space-y-3">
        {sortedAlerts.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center bg-surface-card rounded-xl border border-border-subtle p-6">
            <AlertTriangle className="w-10 h-10 text-text-muted mb-2.5 opacity-60" />
            <p className="text-sm text-text-muted">{t("list.emptyTitle")}</p>
          </div>
        ) : (
          sortedAlerts.map(renderMobileCard)
        )}

        {/* Mobile Pagination */}
        {total > PAGE_SIZE && (
          <div className="flex items-center justify-between gap-2 pt-4 px-1">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
            >
              {t("pagination.prev")}
            </Button>
            <span className="text-xs font-medium text-text-muted tabular-nums">
              {page} / {Math.ceil(total / PAGE_SIZE)}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.min(Math.ceil(total / PAGE_SIZE), p + 1))}
              disabled={page >= Math.ceil(total / PAGE_SIZE)}
            >
              {t("pagination.next")}
            </Button>
          </div>
        )}
      </div>
    </>
  );

  // ── Render ──────────────────────────────────────────

  return (
    <div className="min-h-screen bg-surface-ground">
      <PageHeader
        title={t("title")}
        badge={
          total > 0 ? (
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-surface-hover text-text-secondary border border-border-subtle shadow-subtle tabular-nums">
              {total}
            </span>
          ) : undefined
        }
      />

      {/* Main Content */}
      <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Loading State */}
        {isLoading && (
          <LoadingState
            isLoading={true}
            type="skeleton"
            skeletonType="table"
            skeletonProps={{ rows: 8, columns: 6 }}
          />
        )}

        {/* Error State */}
        {errorState}

        {/* Content */}
        {!isLoading && !error && content}
      </div>

      {/* Import Alert Modal */}
      <ImportAlertModal
        open={showImportModal}
        onClose={() => setShowImportModal(false)}
        onImportSuccess={() => {
          refetch();
        }}
      />

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={deleteTargetId !== null}
        onCancel={() => setDeleteTargetId(null)}
        onConfirm={confirmDelete}
        title={t("deleteDialog.title")}
        description={t("deleteDialog.description")}
        variant="danger"
        confirmText={tCommon("delete")}
        cancelText={tCommon("cancel")}
      />
    </div>
  );
}
