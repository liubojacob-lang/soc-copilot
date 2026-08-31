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
  Eye,
  MoreHorizontal,
  AlertTriangle,
  Clock,
  Server,
  RefreshCw,
  Upload,
} from "lucide-react";
import ImportAlertModal from "./components/ImportAlertModal";
import { loadAuthState } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/Badge";
import { DataTable, type ColumnDef, type TableSeverity } from "@/components/ui/DataTable";
import { LoadingState } from "@/components/common/LoadingState";
import { useToast } from "@/components/Toast";
import { useAlerts, useBatchUpdateAlerts, useDeleteAlert, useAlertStats } from "@/hooks/useAlerts";
import type { SecurityAlertItem, AlertListFilters, AlertStatus, AlertSeverity } from "@/lib/api";

// ── Constants ──────────────────────────────────────────

const PAGE_SIZE = 20;

type SortField = "created_at" | "severity" | "status";
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
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 1) return "just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHrs = Math.floor(diffMins / 60);
    if (diffHrs < 24) return `${diffHrs}h ago`;
    const diffDays = Math.floor(diffHrs / 24);
    if (diffDays < 7) return `${diffDays}d ago`;
    return format.dateTime(d, { dateStyle: "medium" });
  } catch {
    return "-";
  }
}

// ── Severity Badge ─────────────────────────────────────

function SeverityTag({ severity }: { severity: string }) {
  const t = useTranslations("severity");
  const labels: Record<string, string> = {
    critical: t("critical"),
    high: t("high"),
    medium: t("medium"),
    low: t("low"),
    info: "Info",
  };
  return <Badge severity={mapSeverity(severity)}>{labels[severity] || severity}</Badge>;
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
          "flex items-center gap-2 px-3 py-2 text-sm rounded-lg focus-visible:ring-2 focus-visible:ring-primary-600/50 border transition-colors",
          selected.length > 0
            ? "border-blue-300 bg-blue-50 text-blue-700 dark:border-blue-600 dark:bg-blue-900/20 dark:text-blue-300"
            : "border-gray-200 bg-white text-gray-600 hover:border-gray-300 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400"
        )}
      >
        <Filter className="w-3.5 h-3.5" />
        <span>{label}</span>
        {selected.length > 0 && (
          <span className="ml-1 px-1.5 py-0.5 text-xs bg-blue-200 dark:bg-blue-800 rounded-full">
            {selected.length}
          </span>
        )}
        <ChevronDown className="w-3 h-3 ml-1" />
      </button>

      {open && (
        <div className="absolute top-full left-0 mt-1 w-48 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-20 py-1 max-h-60 overflow-y-auto">
          {options.map((opt) => (
            <label
              key={opt.value}
              className="flex items-center gap-2 px-3 py-2 hover:bg-gray-50 active:bg-gray-50 dark:hover:bg-gray-700 active:bg-gray-700 cursor-pointer text-sm"
            >
              <input
                type="checkbox"
                checked={selected.includes(opt.value)}
                onChange={() => toggle(opt.value)}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-gray-700 dark:text-gray-300">{opt.label}</span>
            </label>
          ))}
          {selected.length > 0 && (
            <button
              type="button"
              onClick={() => onChange([])}
              className="w-full text-left px-3 py-2 text-xs text-gray-500 hover:bg-gray-50 active:bg-gray-50 dark:hover:bg-gray-700 active:bg-gray-700 border-t border-gray-100 dark:border-gray-700"
            >
              Clear all
            </button>
          )}
        </div>
      )}
    </div>
  );
}

// ── Stats Bar ───────────────────────────────────────────

function StatsBar({
  total,
  stats,
}: {
  total: number;
  stats?: { by_severity?: Record<string, number>; by_status?: Record<string, number> };
}) {
  const t = useTranslations("common");
  if (!stats) return null;

  return (
    <div className="flex flex-wrap items-center gap-2 mb-4">
      <span className="text-sm text-gray-500 dark:text-gray-400 mr-2">{total} alerts</span>
      {stats.by_severity &&
        Object.entries(stats.by_severity).map(([sev, count]) => (
          <span key={sev} className="text-xs text-gray-400 dark:text-gray-500">
            <Badge severity={mapSeverity(sev)}>{sev}</Badge> ×{count}
          </span>
        ))}
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
      router.push(`/${locale}/login`);
    }
  }, [router, locale]);

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
    try {
      await batchUpdate.mutateAsync({
        ids: Array.from(selectedIds),
        payload: { status },
      });
      setSelectedIds(new Set());
      setShowBatchPanel(false);
      showToast(`Updated ${selectedIds.size} alerts to "${status}"`, "success");
    } catch (err) {
      showToast(
        `Batch update failed: ${err instanceof Error ? err.message : "Unknown error"}`,
        "error"
      );
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this alert permanently?")) return;
    try {
      await deleteAlert.mutateAsync(id);
      showToast("Alert deleted", "success");
    } catch (err) {
      showToast("Delete failed", "error");
    }
  };

  // Reset page on filter change
  useEffect(() => setPage(1), [debouncedSearch, statusFilter, severityFilter, sourceFilter]);

  if (!mounted) return null;

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
            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
        ),
        cell: (row) => (
          <input
            type="checkbox"
            checked={selectedIds.has(row.id)}
            onChange={() => toggleSelect(row.id)}
            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
        ),
        width: "40px",
        align: "center",
      },
      {
        key: "title",
        header: t("list.title"),
        cell: (row) => (
          <div className="min-w-0">
            <button
              onClick={() => router.push(`/${locale}/alerts/${row.id}`)}
              className="text-sm font-medium text-gray-900 dark:text-white hover:text-blue-600 dark:hover:text-blue-400 truncate block max-w-[320px] text-left transition-colors"
            >
              {row.title}
            </button>
            {row.description && (
              <p className="text-xs text-gray-500 dark:text-gray-400 truncate max-w-[320px] mt-0.5">
                {row.description}
              </p>
            )}
          </div>
        ),
      },
      {
        key: "severity",
        header: (
          <button
            type="button"
            onClick={() => {
              if (sortField === "severity") setSortDir((d) => (d === "asc" ? "desc" : "asc"));
              else {
                setSortField("severity");
                setSortDir("desc");
              }
            }}
            className="flex items-center gap-1 text-body font-semibold text-text-tertiary select-none"
          >
            {tCommon("severity")}
            {sortField === "severity" &&
              (sortDir === "asc" ? (
                <ChevronUp className="w-3 h-3" />
              ) : (
                <ChevronDown className="w-3 h-3" />
              ))}
          </button>
        ),
        cell: (row) => <SeverityTag severity={row.severity} />,
        width: "100px",
      },
      {
        key: "status",
        header: (
          <button
            type="button"
            onClick={() => {
              if (sortField === "status") setSortDir((d) => (d === "asc" ? "desc" : "asc"));
              else {
                setSortField("status");
                setSortDir("asc");
              }
            }}
            className="flex items-center gap-1 text-body font-semibold text-text-tertiary select-none"
          >
            {t("list.status")}
            {sortField === "status" &&
              (sortDir === "asc" ? (
                <ChevronUp className="w-3 h-3" />
              ) : (
                <ChevronDown className="w-3 h-3" />
              ))}
          </button>
        ),
        cell: (row) => <StatusTag status={row.status} />,
        width: "120px",
      },
      {
        key: "source",
        header: t("list.source"),
        cell: (row) => (
          <span className="text-sm text-gray-600 dark:text-gray-400">{row.source || "-"}</span>
        ),
        width: "100px",
      },
      {
        key: "time",
        header: (
          <button
            type="button"
            onClick={() => {
              if (sortField === "created_at") setSortDir((d) => (d === "asc" ? "desc" : "asc"));
              else {
                setSortField("created_at");
                setSortDir("desc");
              }
            }}
            className="flex items-center gap-1 text-body font-semibold text-text-tertiary select-none"
          >
            {t("list.time")}
            {sortField === "created_at" &&
              (sortDir === "asc" ? (
                <ChevronUp className="w-3 h-3" />
              ) : (
                <ChevronDown className="w-3 h-3" />
              ))}
          </button>
        ),
        cell: (row) => (
          <span className="text-sm text-gray-500 dark:text-gray-400 whitespace-nowrap">
            {formatTime(row.event_timestamp || row.created_at, format)}
          </span>
        ),
        width: "100px",
      },
      {
        key: "actions",
        header: "",
        cell: (row) => (
          <div className="flex items-center gap-1 justify-end">
            <button
              onClick={() => router.push(`/${locale}/alerts/${row.id}`)}
              className="p-1.5 text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 rounded hover:bg-gray-100 active:bg-gray-100 dark:hover:bg-gray-700 active:bg-gray-700 transition-colors"
              title={tCommon("view")}
            >
              <Eye className="w-4 h-4" />
            </button>
            <button
              onClick={() => handleDelete(row.id)}
              className="p-1.5 text-gray-400 hover:text-red-600 rounded hover:bg-gray-100 active:bg-gray-100 dark:hover:bg-gray-700 active:bg-gray-700 transition-colors"
              title={tCommon("delete")}
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        ),
        width: "80px",
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
    ]
  );

  // ── Mobile Card Render ────────────────────────────────

  const renderMobileCard = (alert: SecurityAlertItem) => (
    <div
      key={alert.id}
      className={cn(
        "bg-white dark:bg-gray-800 rounded-lg focus-visible:ring-2 focus-visible:ring-primary-600/50 border p-4 transition-colors",
        selectedIds.has(alert.id)
          ? "border-blue-500 ring-1 ring-blue-500"
          : "border-gray-200 dark:border-gray-700"
      )}
    >
      <div className="flex items-start gap-3">
        <input
          type="checkbox"
          checked={selectedIds.has(alert.id)}
          onChange={() => toggleSelect(alert.id)}
          className="mt-1 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
        />
        <div className="flex-1 min-w-0">
          <button
            onClick={() => router.push(`/${locale}/alerts/${alert.id}`)}
            className="text-sm font-semibold text-gray-900 dark:text-white hover:text-blue-600 dark:hover:text-blue-400 text-left line-clamp-2"
          >
            {alert.title}
          </button>
          <div className="flex flex-wrap items-center gap-2 mt-2">
            <SeverityTag severity={alert.severity} />
            <StatusTag status={alert.status} />
            <span className="text-xs text-gray-400">{alert.source}</span>
          </div>
          <div className="flex items-center gap-2 mt-2 text-xs text-gray-500">
            <Clock className="w-3 h-3" />
            {formatTime(alert.event_timestamp || alert.created_at, format)}
            {alert.source_ip && (
              <>
                <span className="text-gray-300">·</span>
                <Server className="w-3 h-3" />
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

      {/* Toolbar: Search + Filters + Refresh */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 mb-4">
        {/* Search */}
        <div className="relative flex-1 max-w-md w-full">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t("list.searchPlaceholder")}
            className="w-full pl-10 pr-4 py-2.5 text-sm bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900 dark:text-white placeholder-gray-400"
          />
          {search && (
            <button
              onClick={() => setSearch("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              <X className="w-4 h-4" />
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

        {/* Refresh */}
        {/* Import Alerts Button */}
        <button
          onClick={() => setShowImportModal(true)}
          className="flex items-center gap-2 px-3 py-2 text-sm font-medium bg-blue-600 text-white rounded-lg focus-visible:ring-2 focus-visible:ring-primary-600/50 hover:bg-blue-700 active:bg-blue-700 transition-colors shadow-sm"
          title={t("importAlerts")}
        >
          <Upload className="w-4 h-4" />
          <span className="hidden sm:inline">{tCommon("import")}</span>
        </button>

        <button
          onClick={() => refetch()}
          className="p-2.5 text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 rounded-lg focus-visible:ring-2 focus-visible:ring-primary-600/50 hover:bg-gray-100 active:bg-gray-100 dark:hover:bg-gray-700 active:bg-gray-700 transition-colors"
          title={tCommon("refresh")}
        >
          <RefreshCw className="w-4 h-4" />
        </button>

        {/* Mobile Filter Toggle */}
        <button
          onClick={() => setShowMobileFilters(!showMobileFilters)}
          className="sm:hidden flex items-center gap-2 px-3 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400"
        >
          <Filter className="w-3.5 h-3.5" />
          Filters
          {(statusFilter.length > 0 || severityFilter.length > 0) && (
            <span className="px-1.5 py-0.5 text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-600 rounded-full">
              {statusFilter.length + severityFilter.length}
            </span>
          )}
        </button>
      </div>

      {/* Mobile Filters Panel */}
      {showMobileFilters && (
        <div className="sm:hidden bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 mb-4 space-y-3">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Status</h3>
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
                    ? "border-blue-500 bg-blue-50 text-blue-700 dark:border-blue-400 dark:bg-blue-900/30 dark:text-blue-300"
                    : "border-gray-200 text-gray-500 dark:border-gray-600 dark:text-gray-400"
                )}
              >
                {opt.label}
              </button>
            ))}
          </div>
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Severity</h3>
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
                    ? "border-blue-500 bg-blue-50 text-blue-700 dark:border-blue-400 dark:bg-blue-900/30 dark:text-blue-300"
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
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3 mb-4 flex items-center gap-3 flex-wrap">
          <span className="text-sm font-medium text-blue-700 dark:text-blue-300">
            {selectedIds.size} selected
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => handleBatchStatus("resolved")}
              className="px-3 py-1.5 text-xs font-medium bg-green-600 text-white rounded hover:bg-green-700 transition-colors flex items-center gap-1"
            >
              <CheckCircle className="w-3 h-3" />
              Resolve
            </button>
            <button
              onClick={() => handleBatchStatus("false_positive")}
              className="px-3 py-1.5 text-xs font-medium bg-gray-600 text-white rounded hover:bg-gray-700 active:bg-gray-700 transition-colors"
            >
              False Positive
            </button>
            <button
              onClick={() => handleBatchStatus("investigating")}
              className="px-3 py-1.5 text-xs font-medium bg-yellow-600 text-white rounded hover:bg-yellow-700 transition-colors"
            >
              Investigate
            </button>
          </div>
          <button
            onClick={() => setSelectedIds(new Set())}
            className="ml-auto text-sm text-gray-500 hover:text-gray-700"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Desktop Table */}
      <div className="hidden sm:block bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
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
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <AlertTriangle className="w-12 h-12 text-gray-300 dark:text-gray-600 mb-3" />
            <p className="text-sm text-gray-500 dark:text-gray-400">{t("list.emptyTitle")}</p>
          </div>
        ) : (
          sortedAlerts.map(renderMobileCard)
        )}

        {/* Mobile Pagination */}
        {total > PAGE_SIZE && (
          <div className="flex items-center justify-center gap-2 pt-4">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="px-3 py-1.5 text-sm border rounded disabled:opacity-40"
            >
              ← Prev
            </button>
            <span className="text-sm text-gray-500">
              {page} / {Math.ceil(total / PAGE_SIZE)}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(Math.ceil(total / PAGE_SIZE), p + 1))}
              disabled={page >= Math.ceil(total / PAGE_SIZE)}
              className="px-3 py-1.5 text-sm border rounded disabled:opacity-40"
            >
              Next →
            </button>
          </div>
        )}
      </div>
    </>
  );

  // ── Render ──────────────────────────────────────────

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
              <Shield className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900 dark:text-white">{t("title")}</h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {total > 0 ? `${total} alerts` : t("subtitle")}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
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
      </main>

      {/* Import Alert Modal */}
      <ImportAlertModal
        open={showImportModal}
        onClose={() => setShowImportModal(false)}
        onImportSuccess={() => {
          refetch();
        }}
      />
    </div>
  );
}
