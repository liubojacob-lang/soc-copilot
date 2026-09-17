"use client";

import { useState, useEffect } from "react";
import { useRouter } from "@/i18n/navigation";
import { useFormatter, useTranslations, useLocale } from "next-intl";
import { PageHeader } from "@/components/common/PageHeader";
import { SkeletonTable } from "@/components/common/LoadingState";
import { loadAuthState, authFetch } from "@/lib/auth";
import { useKeyboardShortcuts } from "@/hooks/useKeyboardShortcuts";
import {
  Search,
  RefreshCw,
  CheckCircle,
  XCircle,
  Clock,
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  Play,
} from "lucide-react";

interface Approval {
  id: string;
  run_id: string;
  node_id: string;
  status: "pending" | "approved" | "rejected" | "expired";
  title: string;
  message: string | null;
  comments: string | null;
  requested_by: string | null;
  approved_by: string | null;
  rejected_by: string | null;
  created_at: string;
  decided_at: string | null;
  expires_at: string | null;
}

interface PaginationState {
  currentPage: number;
  pageSize: number;
  total: number;
}

export default function PlaybookApprovalsPage() {
  const router = useRouter();
  const locale = useLocale();
  const t = useTranslations("playbooks");
  const format = useFormatter();
  const tCommon = useTranslations("common");

  const [mounted, setMounted] = useState(false);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const [pagination, setPagination] = useState<PaginationState>({
    currentPage: 1,
    pageSize: 10,
    total: 0,
  });

  const loadApprovals = async (page: number = 1) => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pagination.pageSize.toString(),
      });
      if (statusFilter) {
        params.append("status", statusFilter);
      }

      const response = await authFetch(`/api/playbook/approvals?${params.toString()}`);

      if (response.ok) {
        const data = await response.json();
        setApprovals(data.items || []);
        setPagination({
          currentPage: page,
          pageSize: pagination.pageSize,
          total: data.total || 0,
        });
      } else if (response.status === 401) {
        router.push("/login");
        return;
      } else {
        setError(`Failed to load approvals: ${response.statusText}`);
      }
    } catch (e) {
      console.error("Failed to load approvals:", e);
      setError((e as Error)?.message ?? "Error loading approvals");
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadApprovals(pagination.currentPage);
    setRefreshing(false);
  };

  const handlePageChange = (newPage: number) => {
    loadApprovals(newPage);
  };

  const handleApprove = async (approvalId: string) => {
    setActionLoading(approvalId);
    try {
      const response = await authFetch(`/api/playbook/approvals/${approvalId}/approve`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ comments: "" }),
      });

      if (response.ok) {
        await loadApprovals(pagination.currentPage);
      } else {
        const data = await response.json();
        setError(data.detail || "Failed to approve");
      }
    } catch (e) {
      setError((e as Error)?.message ?? "Error approving");
    } finally {
      setActionLoading(null);
    }
  };

  const handleReject = async (approvalId: string) => {
    setActionLoading(approvalId);
    try {
      const response = await authFetch(`/api/playbook/approvals/${approvalId}/reject`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ comments: "" }),
      });

      if (response.ok) {
        await loadApprovals(pagination.currentPage);
      } else {
        const data = await response.json();
        setError(data.detail || "Failed to reject");
      }
    } catch (e) {
      setError((e as Error)?.message ?? "Error rejecting");
    } finally {
      setActionLoading(null);
    }
  };

  useEffect(() => {
    setMounted(true);
    const authState = loadAuthState();
    if (!authState?.isAuthenticated) {
      router.push("/login");
      return;
    }
    loadApprovals(1);
  }, [router, statusFilter]);

  // Keyboard shortcuts
  useKeyboardShortcuts(
    {
      r: () => {
        setRefreshing(true);
        loadApprovals(pagination.currentPage).finally(() => setRefreshing(false));
      },
      "/": () => {
        document.querySelector<HTMLInputElement>('input[type="text"]')?.focus();
      },
    },
    { enabled: mounted && !loading }
  );

  if (!mounted) return null;

  const totalPages = Math.ceil(pagination.total / pagination.pageSize);

  const filteredApprovals = approvals.filter((approval) => {
    if (!searchQuery) return true;
    const search = searchQuery.toLowerCase();
    return (
      approval.title.toLowerCase().includes(search) ||
      approval.run_id.toLowerCase().includes(search) ||
      (approval.message?.toLowerCase().includes(search) ?? false)
    );
  });

  const STATUS_COLORS: Record<string, string> = {
    pending: "bg-amber-500/15 text-amber-700 dark:text-amber-400 border border-amber-500/30",
    approved:
      "bg-success-500/15 text-success-700 dark:text-success-400 border border-success-500/30",
    rejected: "bg-danger-500/15 text-danger-700 dark:text-danger-400 border border-danger-500/30",
    expired: "bg-surface-hover text-text-tertiary border border-border-subtle",
  };

  return (
    <div className="min-h-screen bg-surface-page transition-colors pb-16">
      <PageHeader
        title={t("approvals.title") || "Approvals"}
        subtitle={t("approvals.subtitle") || "Manage playbook approval requests"}
      />

      <main className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-5">
        {/* Toolbar */}
        <div className="flex flex-col sm:flex-row sm:items-center gap-2.5 mb-3.5">
          <div className="flex-1 relative min-w-[200px] max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
            <input
              type="text"
              placeholder={t("approvals.searchPlaceholder") || "Search approvals..."}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-sm border border-border-default rounded-lg bg-surface-input text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent-500/20 focus:border-accent-600 transition-colors h-9"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-1.5 text-sm border border-border-default rounded-lg bg-surface-input text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-500/20 focus:border-accent-600 transition-colors h-9"
          >
            <option value="">{t("allStatuses") || "All Statuses"}</option>
            <option value="pending">{t("statuses.pending") || "Pending"}</option>
            <option value="approved">{t("statuses.approved") || "Approved"}</option>
            <option value="rejected">{t("statuses.rejected") || "Rejected"}</option>
            <option value="expired">{t("statuses.expired") || "Expired"}</option>
          </select>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="h-9 px-3 bg-accent-600 text-white rounded-lg hover:bg-accent-700 text-sm font-medium disabled:opacity-50 flex items-center gap-1.5 transition-colors shadow-subtle"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} />
            {refreshing ? tCommon("loading") : tCommon("refresh")}
          </button>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-3.5 p-3.5 bg-danger-500/10 border border-danger-500/30 rounded-xl flex items-center gap-2 text-sm text-danger-700 dark:text-danger-300">
            <AlertCircle className="w-4 h-4 shrink-0 text-danger-600 dark:text-danger-400" />
            <span>{error}</span>
          </div>
        )}

        {/* Content */}
        {loading ? (
          <div className="bg-surface-card border border-border-subtle rounded-xl p-4 shadow-subtle">
            <SkeletonTable rows={5} columns={5} />
          </div>
        ) : filteredApprovals.length === 0 ? (
          <div className="text-center py-12 bg-surface-card rounded-xl border border-border-subtle">
            <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-surface-hover flex items-center justify-center">
              <CheckCircle className="w-6 h-6 text-text-muted" />
            </div>
            <p className="text-text-primary text-base font-medium mb-1">
              {t("approvals.noApprovals") || "No approval requests found"}
            </p>
            <p className="text-text-tertiary text-xs">
              {t("approvals.noApprovalsDesc") || "Pending approvals will appear here"}
            </p>
          </div>
        ) : (
          <div className="bg-surface-card rounded-xl overflow-hidden shadow-subtle border border-border-subtle">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-surface-hover/50 border-b border-border-subtle">
                  <tr>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold text-text-muted uppercase tracking-wider">
                      {t("approvals.title") || "Title"}
                    </th>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold text-text-muted uppercase tracking-wider">
                      {t("approvals.runId") || "Run ID"}
                    </th>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold text-text-muted uppercase tracking-wider">
                      {t("approvals.status") || "Status"}
                    </th>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold text-text-muted uppercase tracking-wider">
                      {t("approvals.requestedBy") || "Requested By"}
                    </th>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold text-text-muted uppercase tracking-wider">
                      {t("approvals.created") || "Created"}
                    </th>
                    <th className="px-4 py-2.5 text-right text-xs font-semibold text-text-muted uppercase tracking-wider">
                      {t("approvals.actions") || "Actions"}
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-subtle">
                  {filteredApprovals.map((approval) => (
                    <tr key={approval.id} className="hover:bg-surface-hover/50 transition-colors">
                      <td className="px-4 py-2.5">
                        <div className="font-medium text-text-primary">{approval.title}</div>
                        {approval.message && (
                          <div className="text-xs text-text-tertiary mt-0.5">
                            {approval.message}
                          </div>
                        )}
                      </td>
                      <td className="px-6 py-3.5">
                        <a
                          href={`/${locale}/playbooks/${approval.run_id}`}
                          className="text-accent-600 hover:text-accent-700 dark:text-accent-400 dark:hover:text-accent-300 font-mono text-sm font-medium"
                        >
                          {approval.run_id.slice(0, 8)}...
                        </a>
                      </td>
                      <td className="px-6 py-3.5">
                        <span
                          className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[approval.status]}`}
                        >
                          {approval.status === "pending" && <Clock className="w-3 h-3" />}
                          {approval.status === "approved" && <CheckCircle className="w-3 h-3" />}
                          {approval.status === "rejected" && <XCircle className="w-3 h-3" />}
                          {approval.status}
                        </span>
                      </td>
                      <td className="px-6 py-3.5 text-sm text-text-secondary">
                        {approval.requested_by || "-"}
                      </td>
                      <td className="px-6 py-3.5 text-sm text-text-secondary">
                        {format.dateTime(new Date(approval.created_at), { dateStyle: "medium" })}
                        <div className="text-xs text-text-muted mt-0.5">
                          {format.dateTime(new Date(approval.created_at), { timeStyle: "medium" })}
                        </div>
                      </td>
                      <td className="px-6 py-3.5 text-right">
                        {approval.status === "pending" ? (
                          <div className="flex items-center justify-end gap-2">
                            <button
                              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-success-600 text-white rounded-lg hover:bg-success-700 disabled:opacity-50 transition-colors text-xs font-medium shadow-subtle"
                              onClick={() => handleApprove(approval.id)}
                              disabled={actionLoading === approval.id}
                            >
                              <CheckCircle className="w-3.5 h-3.5" />
                              {t("approvals.approve") || "Approve"}
                            </button>
                            <button
                              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-danger-600 text-white rounded-lg hover:bg-danger-700 disabled:opacity-50 transition-colors text-xs font-medium shadow-subtle"
                              onClick={() => handleReject(approval.id)}
                              disabled={actionLoading === approval.id}
                            >
                              <XCircle className="w-3.5 h-3.5" />
                              {t("approvals.reject") || "Reject"}
                            </button>
                          </div>
                        ) : (
                          <div className="text-sm text-text-muted">
                            {approval.approved_by && `Approved by ${approval.approved_by}`}
                            {approval.rejected_by && `Rejected by ${approval.rejected_by}`}
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between px-6 py-4 border-t border-border-subtle text-sm text-text-tertiary">
                  <div>
                    Showing {(pagination.currentPage - 1) * pagination.pageSize + 1} to{" "}
                    {Math.min(pagination.currentPage * pagination.pageSize, pagination.total)} of{" "}
                    {pagination.total} results
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handlePageChange(pagination.currentPage - 1)}
                      disabled={pagination.currentPage === 1}
                      className="p-2 border border-border-subtle rounded-lg bg-surface-card hover:bg-surface-hover text-text-secondary disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </button>
                    <span className="text-sm text-text-secondary">
                      Page {pagination.currentPage} of {totalPages}
                    </span>
                    <button
                      onClick={() => handlePageChange(pagination.currentPage + 1)}
                      disabled={pagination.currentPage === totalPages}
                      className="p-2 border border-border-subtle rounded-lg bg-surface-card hover:bg-surface-hover text-text-secondary disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
