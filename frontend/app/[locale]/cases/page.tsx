"use client";

/**
 * Security Cases List Page
 *
 * Features:
 * - Search: by title, description, case ID
 * - Filters: status, severity, assigned analyst
 * - Sort + Pagination (via DataTable)
 * - Table columns: title, status, severity, assigned, SLA countdown, created
 * - Create case button (modal)
 * - Loading/Empty/Error states
 * - Responsive: card view on mobile, table on desktop
 */

import { useState, useMemo, useCallback } from "react";
import { useRouter } from "@/i18n/navigation";
import { useFormatter, useLocale, useTranslations } from "next-intl";
import {
  Briefcase,
  Search,
  Filter,
  X,
  ArrowUpDown,
  Trash2,
  Eye,
  Plus,
  Clock,
  AlertTriangle,
  RefreshCw,
  User,
  Timer,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/Badge";
import { DataTable, type ColumnDef, type TableSeverity } from "@/components/ui/DataTable";
import { LoadingState } from "@/components/common/LoadingState";
import { EmptyState } from "@/components/EmptyState";
import { useToast } from "@/components/Toast";
import { useCases, useCreateCase } from "@/hooks/useCases";
import { mapCaseSeverity, type SecurityCase, type CaseFilters } from "@/lib/api/cases";
import type { CaseSeverity } from "@/lib/api/cases";

// ── Constants ──────────────────────────────────────────

const PAGE_SIZE = 20;

type SortField = "created_at" | "severity" | "status" | "sla_deadline";
type SortDir = "asc" | "desc";

// ── Helper: map severity to TableSeverity ────────────────

function mapToTableSeverity(s: string): TableSeverity {
  const m: Record<string, TableSeverity> = {
    critical: "critical",
    high: "high",
    medium: "medium",
    low: "low",
  };
  return m[s] || "neutral";
}

// ── SLA Countdown Helper ───────────────────────────────

function getSlaRemaining(slaDeadline: string | null): {
  text: string;
  expired: boolean;
  urgent: boolean;
} {
  if (!slaDeadline) return { text: "—", expired: false, urgent: false };
  const now = Date.now();
  const deadline = new Date(slaDeadline).getTime();
  const diff = deadline - now;

  if (diff <= 0) return { text: "OVERDUE", expired: true, urgent: true };

  const hours = Math.floor(diff / (1000 * 60 * 60));
  const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

  if (hours > 24) {
    const days = Math.floor(hours / 24);
    return { text: `${days}d ${hours % 24}h`, expired: false, urgent: false };
  }

  return {
    text: `${hours}h ${minutes}m`,
    expired: false,
    urgent: hours < 4,
  };
}

// ── Status label helper ──────────────────────────────────

function getStatusLabel(status: string, t: (key: string) => string): string {
  const map: Record<string, string> = {
    new: t("cases.statusNew"),
    investigating: t("cases.statusInvestigating"),
    contained: t("cases.statusContained"),
    remediated: t("cases.statusRemediated"),
    closed: t("cases.statusClosed"),
    false_positive: t("cases.statusFalsePositive"),
  };
  return map[status] || status;
}

// ── Create Case Modal ───────────────────────────────────

function CreateCaseModal({
  isOpen,
  onClose,
  onCreated,
  t,
  tCommon,
}: {
  isOpen: boolean;
  onClose: () => void;
  onCreated: () => void;
  t: (key: string) => string;
  tCommon: (key: string) => string;
}) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [severity, setSeverity] = useState<CaseSeverity>("medium");
  const [submitting, setSubmitting] = useState(false);
  const { showToast: addToast } = useToast();

  const createCase = useCreateCase();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;

    setSubmitting(true);
    try {
      await createCase.mutateAsync({
        title: title.trim(),
        description: description.trim() || undefined,
        severity,
      });
      addToast(t("cases.created"), "success");
      onCreated();
      onClose();
    } catch {
      addToast(t("common.error"), "error");
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-white dark:bg-gray-800 rounded-2xl shadow-xl border border-gray-200 dark:border-gray-700 w-full max-w-lg mx-4 p-6 animate-fade-in-up">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-gray-900 dark:text-white">
            {t("cases.createTitle")}
          </h2>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 active:bg-gray-100 dark:hover:bg-gray-700 active:bg-gray-700"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              {t("cases.title")} *
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder={t("cases.titlePlaceholder")}
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              {t("cases.description")}
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder={t("cases.descriptionPlaceholder")}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              {t("cases.severity")}
            </label>
            <select
              value={severity}
              onChange={(e) => setSeverity(e.target.value as CaseSeverity)}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="critical">{t("cases.severityCritical")}</option>
              <option value="high">{t("cases.severityHigh")}</option>
              <option value="medium">{t("cases.severityMedium")}</option>
              <option value="low">{t("cases.severityLow")}</option>
            </select>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 active:bg-gray-100 dark:hover:bg-gray-700 active:bg-gray-700 rounded-lg"
            >
              {tCommon("cancel")}
            </button>
            <button
              type="submit"
              disabled={submitting || !title.trim()}
              className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 active:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {submitting ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  {tCommon("loading")}
                </>
              ) : (
                <>
                  <Plus className="w-4 h-4" />
                  {tCommon("create")}
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Main Component ─────────────────────────────────────

export default function CasesPage() {
  const router = useRouter();
  const t = useTranslations();
  const format = useFormatter();
  const tCommon = useTranslations("common");

  // ── State ──────────────────────────────────────────
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string[]>([]);
  const [severityFilter, setSeverityFilter] = useState<string[]>([]);
  const [sortField, setSortField] = useState<SortField>("created_at");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [page, setPage] = useState(1);
  const [showMobileFilters, setShowMobileFilters] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);

  // ── Build filters ──────────────────────────────────
  const filters: CaseFilters = useMemo(
    () => ({
      search: search || undefined,
      severity: severityFilter.length === 1 ? severityFilter[0] : undefined,
      status: statusFilter.length === 1 ? statusFilter[0] : undefined,
      sort_by: sortField,
      sort_order: sortDir,
      page,
      page_size: PAGE_SIZE,
    }),
    [search, severityFilter, statusFilter, sortField, sortDir, page]
  );

  // ── Data fetching ──────────────────────────────────
  const { data: casesData, isLoading, error, refetch } = useCases(filters);
  const cases = casesData?.cases ?? [];
  const total = casesData?.total ?? 0;

  // ── Error state ────────────────────────────────────
  const errorState = useMemo(() => {
    if (!error) return null;
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 mb-6">
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-red-500 mt-0.5 shrink-0" />
          <div className="flex-1">
            <p className="text-sm font-medium text-red-800 dark:text-red-200">
              Failed to load cases
            </p>
            <p className="text-xs text-red-600 dark:text-red-400 mt-1">
              {error instanceof Error ? error.message : "Unknown error"}
            </p>
          </div>
          <button
            onClick={() => refetch()}
            className="px-3 py-1.5 text-xs bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded-lg hover:bg-red-200 active:bg-red-200 dark:hover:bg-red-900 active:bg-red-900/50 flex items-center gap-1 shrink-0"
          >
            <RefreshCw className="w-3 h-3" />
            Retry
          </button>
        </div>
      </div>
    );
  }, [error, refetch]);

  // ── Table columns ──────────────────────────────────
  const columns = useMemo<ColumnDef<SecurityCase>[]>(
    () => [
      {
        key: "title",
        header: t("cases.title"),
        width: "2fr",
        cell: (row) => (
          <div className="min-w-0">
            <button
              onClick={() => router.push(`/cases/${row.id}`)}
              className="text-sm font-medium text-blue-600 dark:text-blue-400 hover:underline truncate block max-w-[300px] text-left"
            >
              {row.title}
            </button>
            {row.description && (
              <p className="text-xs text-gray-500 dark:text-gray-400 truncate max-w-[300px] mt-0.5">
                {row.description}
              </p>
            )}
          </div>
        ),
      },
      {
        key: "status",
        header: t("cases.status"),
        width: "130px",
        align: "center",
        cell: (row) => (
          <Badge
            severity={mapToTableSeverity(
              mapCaseSeverity(
                row.status === "contained"
                  ? "medium"
                  : row.status === "investigating"
                    ? "high"
                    : "low"
              )
            )}
          >
            {getStatusLabel(row.status, t)}
          </Badge>
        ),
      },
      {
        key: "severity",
        header: t("cases.severity"),
        width: "100px",
        align: "center",
        cell: (row) => (
          <Badge severity={mapToTableSeverity(mapCaseSeverity(row.severity))}>{row.severity}</Badge>
        ),
      },
      {
        key: "assigned_to",
        header: t("cases.assigned"),
        width: "140px",
        cell: (row) => (
          <span className="text-sm text-gray-700 dark:text-gray-300 flex items-center gap-1.5">
            <User className="w-3.5 h-3.5 text-gray-400" />
            {row.assigned_analyst_name || row.assigned_to || "—"}
          </span>
        ),
      },
      {
        key: "sla",
        header: t("cases.sla"),
        width: "110px",
        align: "center",
        cell: (row) => {
          const sla = getSlaRemaining(row.sla_deadline);
          return (
            <span
              className={cn(
                "text-sm font-mono flex items-center gap-1 justify-center",
                sla.expired
                  ? "text-red-600 dark:text-red-400 font-bold"
                  : sla.urgent
                    ? "text-amber-600 dark:text-amber-400 font-semibold"
                    : "text-gray-600 dark:text-gray-400"
              )}
            >
              <Timer className="w-3.5 h-3.5" />
              {sla.text}
            </span>
          );
        },
      },
      {
        key: "created_at",
        header: t("cases.created"),
        width: "140px",
        align: "right",
        cell: (row) => (
          <span className="text-sm text-gray-500 dark:text-gray-400 flex items-center gap-1 justify-end">
            <Clock className="w-3.5 h-3.5" />
            {format.dateTime(new Date(row.created_at), { dateStyle: "medium" })}
          </span>
        ),
      },
    ],
    [t, router]
  );

  // ── Mobile card render ─────────────────────────────
  const renderMobileCard = useCallback(
    (c: SecurityCase) => {
      const sla = getSlaRemaining(c.sla_deadline);
      return (
        <div
          key={c.id}
          className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-3 shadow-sm"
        >
          <div className="flex items-start justify-between gap-2">
            <button
              onClick={() => router.push(`/cases/${c.id}`)}
              className="text-sm font-semibold text-blue-600 dark:text-blue-400 hover:underline text-left"
            >
              {c.title}
            </button>
            <Badge severity={mapToTableSeverity(mapCaseSeverity(c.severity))}>{c.severity}</Badge>
          </div>

          {c.description && (
            <p className="text-xs text-gray-500 dark:text-gray-400 line-clamp-2">{c.description}</p>
          )}

          <div className="flex items-center justify-between">
            <Badge
              severity={mapToTableSeverity(
                mapCaseSeverity(c.status === "contained" ? "medium" : "low")
              )}
            >
              {getStatusLabel(c.status, t)}
            </Badge>
            <span className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1">
              <User className="w-3 h-3" />
              {c.assigned_analyst_name || "Unassigned"}
            </span>
          </div>

          <div className="flex items-center justify-between pt-2 border-t border-gray-100 dark:border-gray-700">
            <span
              className={cn(
                "text-xs font-mono flex items-center gap-1",
                sla.expired
                  ? "text-red-600 dark:text-red-400 font-bold"
                  : sla.urgent
                    ? "text-amber-600 dark:text-amber-400"
                    : "text-gray-500 dark:text-gray-400"
              )}
            >
              <Timer className="w-3 h-3" /> SLA: {sla.text}
            </span>
            <span className="text-xs text-gray-400">
              {format.dateTime(new Date(c.created_at), { dateStyle: "medium" })}
            </span>
          </div>
        </div>
      );
    },
    [t, router]
  );

  // ── Content ────────────────────────────────────────
  const content = useMemo(() => {
    if (!isLoading && total === 0) {
      return (
        <EmptyState
          icon="inbox"
          title={t("cases.emptyTitle")}
          description={t("cases.emptyDescription")}
          action={
            <button
              onClick={() => setShowCreateModal(true)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 active:bg-blue-700 text-sm flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              {t("cases.createCase")}
            </button>
          }
        />
      );
    }

    return (
      <>
        {/* Desktop Table */}
        <div className="hidden sm:block bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
          <DataTable
            data={cases}
            columns={columns}
            currentPage={page}
            pageSize={PAGE_SIZE}
            total={total}
            onPageChange={setPage}
            emptyState={{
              title: t("cases.emptyTitle"),
              description: t("cases.emptyDescription"),
            }}
            showPagination={total > PAGE_SIZE}
          />
        </div>

        {/* Mobile Cards */}
        <div className="sm:hidden space-y-3">
          {cases.map(renderMobileCard)}

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
  }, [isLoading, total, cases, columns, page, t, renderMobileCard]);

  // ── Render ─────────────────────────────────────────
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                <Briefcase className="w-6 h-6 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900 dark:text-white">
                  {t("cases.title")}
                </h1>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {total > 0 ? `${total} ${t("cases.cases").toLowerCase()}` : t("cases.subtitle")}
                </p>
              </div>
            </div>

            <button
              onClick={() => setShowCreateModal(true)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg focus-visible:ring-2 focus-visible:ring-primary-600/50 hover:bg-blue-700 active:bg-blue-700 text-sm font-medium flex items-center gap-2 transition-colors"
            >
              <Plus className="w-4 h-4" />
              <span className="hidden sm:inline">{t("cases.createCase")}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Search & Filter Bar */}
        <div className="flex flex-col sm:flex-row gap-3 mb-6">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              placeholder={t("cases.searchPlaceholder")}
              className="w-full pl-9 pr-4 py-2.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Status filter */}
          <select
            value={statusFilter[0] || ""}
            onChange={(e) => {
              setStatusFilter(e.target.value ? [e.target.value] : []);
              setPage(1);
            }}
            className="px-3 py-2.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm text-gray-700 dark:text-gray-300"
          >
            <option value="">{t("cases.status")}</option>
            <option value="new">{t("cases.statusNew")}</option>
            <option value="investigating">{t("cases.statusInvestigating")}</option>
            <option value="contained">{t("cases.statusContained")}</option>
            <option value="remediated">{t("cases.statusRemediated")}</option>
            <option value="closed">{t("cases.statusClosed")}</option>
            <option value="false_positive">{t("cases.statusFalsePositive")}</option>
          </select>

          {/* Severity filter */}
          <select
            value={severityFilter[0] || ""}
            onChange={(e) => {
              setSeverityFilter(e.target.value ? [e.target.value] : []);
              setPage(1);
            }}
            className="px-3 py-2.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm text-gray-700 dark:text-gray-300"
          >
            <option value="">{t("cases.severity")}</option>
            <option value="critical">{t("cases.severityCritical")}</option>
            <option value="high">{t("cases.severityHigh")}</option>
            <option value="medium">{t("cases.severityMedium")}</option>
            <option value="low">{t("cases.severityLow")}</option>
          </select>

          <button
            onClick={() => setShowMobileFilters(!showMobileFilters)}
            className="sm:hidden px-3 py-2.5 rounded-lg border border-gray-300 dark:border-gray-600 text-sm text-gray-700 dark:text-gray-300 flex items-center gap-1.5"
          >
            <Filter className="w-4 h-4" />
            Filters
          </button>
        </div>

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

      {/* Create Case Modal */}
      <CreateCaseModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onCreated={() => refetch()}
        t={t}
        tCommon={tCommon}
      />
    </div>
  );
}
