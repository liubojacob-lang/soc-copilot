"use client";

/**
 * Security Case Detail Page
 *
 * Features:
 * - Case basic info (title, description, severity, status, assigned, SLA)
 * - Status action bar with transitions + reason
 * - Linked alerts (add/remove)
 * - Timeline (aggregated view)
 * - Comments section
 * - Activity log
 */

import { useState, useMemo, useCallback } from "react";
import { useParams } from "next/navigation";
import { useRouter } from "@/i18n/navigation";
import { useFormatter, useTranslations } from "next-intl";
import {
  ArrowLeft,
  Briefcase,
  Clock,
  User,
  Tag,
  Shield,
  AlertTriangle,
  RefreshCw,
  MessageSquare,
  Link as LinkIcon,
  Unlink,
  Send,
  History,
  Timer,
  Trash2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/Badge";
import { LoadingState } from "@/components/common/LoadingState";
import { EmptyState } from "@/components/EmptyState";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { Button } from "@/components/common/Button";
import { BackButton } from "@/components/common";
import { useToast } from "@/components/Toast";
import {
  useCaseDetail,
  useCaseAlerts,
  useCaseComments,
  useCaseTimeline,
  useTransitionCase,
  useUpdateCase,
  useDeleteCase,
  useLinkAlert,
  useUnlinkAlert,
  useAddCaseComment,
} from "@/hooks/useCases";
import {
  mapCaseSeverity,
  STATUS_TRANSITIONS,
  type CaseStatus,
  type SecurityCase,
  type CaseAlert,
  type CaseComment,
  type CaseTimelineEvent,
} from "@/lib/api/cases";

// ── Helpers ──────────────────────────────────────────────

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

function getStatusColor(status: string): string {
  const m: Record<string, string> = {
    new: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
    investigating: "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300",
    contained: "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300",
    remediated: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
    closed: "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300",
    false_positive: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
  };
  return m[status] || "bg-gray-100 dark:bg-gray-800";
}

function getTimelineIcon(eventType: string) {
  const icons: Record<string, React.ReactNode> = {
    created: <Shield className="w-3.5 h-3.5 text-blue-500" />,
    status_changed: <RefreshCw className="w-3.5 h-3.5 text-amber-500" />,
    assigned: <User className="w-3.5 h-3.5 text-purple-500" />,
    sla_updated: <Timer className="w-3.5 h-3.5 text-orange-500" />,
    alert_linked: <LinkIcon className="w-3.5 h-3.5 text-green-500" />,
    alert_unlinked: <Unlink className="w-3.5 h-3.5 text-red-500" />,
    comment_added: <MessageSquare className="w-3.5 h-3.5 text-indigo-500" />,
    updated: <Clock className="w-3.5 h-3.5 text-gray-500" />,
  };
  return icons[eventType] || <Clock className="w-3.5 h-3.5 text-gray-400" />;
}

function getSlaInfo(slaDeadline: string | null): {
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
  return { text: `${hours}h ${minutes}m`, expired: false, urgent: hours < 4 };
}

function formatDate(dateStr: string, format: ReturnType<typeof useFormatter>): string {
  return format.dateTime(new Date(dateStr), { dateStyle: "medium", timeStyle: "medium" });
}

// ── Status Transition Modal ──────────────────────────────

function StatusModal({
  isOpen,
  onClose,
  currentStatus,
  onTransition,
  t,
}: {
  isOpen: boolean;
  onClose: () => void;
  currentStatus: string;
  onTransition: (status: CaseStatus, reason: string) => void;
  t: (key: string) => string;
}) {
  const [selectedStatus, setSelectedStatus] = useState<CaseStatus | "">("");
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const availableTransitions = STATUS_TRANSITIONS[currentStatus] || [];

  const handleSubmit = async () => {
    if (!selectedStatus) return;
    setSubmitting(true);
    try {
      await onTransition(selectedStatus, reason.trim());
      onClose();
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-white dark:bg-gray-800 rounded-2xl shadow-xl border border-gray-200 dark:border-gray-700 w-full max-w-md mx-4 p-6 animate-fade-in-up">
        <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">
          {t("cases.transitionStatus")}
        </h3>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              {t("cases.newStatus")}
            </label>
            <div className="flex flex-wrap gap-2">
              {availableTransitions.map((status) => (
                <button
                  key={status}
                  onClick={() => setSelectedStatus(status as CaseStatus)}
                  className={cn(
                    "px-3 py-1.5 rounded-lg focus-visible:ring-2 focus-visible:ring-primary-600/50 text-sm font-medium border transition-colors",
                    selectedStatus === status
                      ? "border-blue-500 bg-blue-50 text-blue-700 dark:border-blue-400 dark:bg-blue-900/30 dark:text-blue-300"
                      : "border-gray-200 text-gray-600 dark:border-gray-600 dark:text-gray-400 hover:border-gray-300"
                  )}
                >
                  {getStatusLabel(status, t)}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              {t("cases.reason")}
            </label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={2}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-sm"
              placeholder={t("cases.reasonPlaceholder")}
            />
          </div>
        </div>

        <div className="flex justify-end gap-2 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 active:bg-gray-100 dark:hover:bg-gray-700 active:bg-gray-700 rounded-lg"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!selectedStatus || submitting}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 active:bg-blue-700 disabled:opacity-50"
          >
            {submitting ? "..." : t("cases.confirmTransition")}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Link Alert Modal ──────────────────────────────────────

function LinkAlertModal({
  isOpen,
  onClose,
  onLink,
  t,
}: {
  isOpen: boolean;
  onClose: () => void;
  onLink: (alertId: number) => void;
  t: (key: string) => string;
}) {
  const [alertId, setAlertId] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const id = parseInt(alertId, 10);
    if (isNaN(id)) return;
    setSubmitting(true);
    try {
      await onLink(id);
      onClose();
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-white dark:bg-gray-800 rounded-2xl shadow-xl border border-gray-200 dark:border-gray-700 w-full max-w-sm mx-4 p-6 animate-fade-in-up">
        <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">
          {t("cases.linkAlert")}
        </h3>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              {t("cases.alertId")}
            </label>
            <input
              type="number"
              value={alertId}
              onChange={(e) => setAlertId(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-sm"
              placeholder="e.g. 1234"
              required
            />
          </div>
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 active:bg-gray-100 dark:hover:bg-gray-700 active:bg-gray-700 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting || !alertId}
              className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 active:bg-blue-700 disabled:opacity-50"
            >
              {submitting ? "..." : t("cases.link")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Main Component ─────────────────────────────────────

export default function CaseDetailPage() {
  const format = useFormatter();
  const params = useParams();
  const router = useRouter();
  const t = useTranslations();
  const { showToast: addToast } = useToast();
  const id = params?.id as string;

  // ── Data ───────────────────────────────────────────
  const { data: caseData, isLoading, error } = useCaseDetail(id);
  const { data: alerts } = useCaseAlerts(id);
  const { data: comments } = useCaseComments(id);
  const { data: timeline } = useCaseTimeline(id);

  // ── Mutations ──────────────────────────────────────
  const transitionCase = useTransitionCase();
  const linkAlert = useLinkAlert();
  const unlinkAlert = useUnlinkAlert();
  const addComment = useAddCaseComment();
  const deleteCase = useDeleteCase();
  const updateCase = useUpdateCase();

  // ── Modal state ────────────────────────────────────
  const [statusModalOpen, setStatusModalOpen] = useState(false);
  const [linkAlertModalOpen, setLinkAlertModalOpen] = useState(false);
  const [newComment, setNewComment] = useState("");
  const [submittingComment, setSubmittingComment] = useState(false);

  // ── Handlers ───────────────────────────────────────
  const handleTransition = useCallback(
    async (status: CaseStatus, reason: string) => {
      await transitionCase.mutateAsync({ id, payload: { status, reason } });
      addToast(`Status changed to ${getStatusLabel(status, t)}`, "success");
    },
    [id, transitionCase, addToast, t]
  );

  const handleLinkAlert = useCallback(
    async (alertId: number) => {
      await linkAlert.mutateAsync({ caseId: id, alertId });
      addToast("Alert linked", "success");
    },
    [id, linkAlert, addToast]
  );

  const handleUnlinkAlert = useCallback(
    async (alertId: number) => {
      await unlinkAlert.mutateAsync({ caseId: id, alertId });
      addToast("Alert unlinked", "success");
    },
    [id, unlinkAlert, addToast]
  );

  const handleAddComment = useCallback(async () => {
    if (!newComment.trim()) return;
    setSubmittingComment(true);
    try {
      await addComment.mutateAsync({ caseId: id, payload: { content: newComment.trim() } });
      setNewComment("");
      addToast("Comment added", "success");
    } catch {
      addToast("Failed to add comment", "error");
    } finally {
      setSubmittingComment(false);
    }
  }, [id, newComment, addComment, addToast]);

  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const handleDelete = useCallback(() => {
    setShowDeleteConfirm(true);
  }, []);

  const confirmDelete = useCallback(async () => {
    try {
      await deleteCase.mutateAsync(id);
      addToast("Case deleted", "success");
      router.push("/cases");
    } catch {
      addToast("Failed to delete case", "error");
    } finally {
      setShowDeleteConfirm(false);
    }
  }, [id, deleteCase, addToast, router]);

  // ── Loading ────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <LoadingState isLoading={true} type="skeleton" skeletonType="card" />
        </div>
      </div>
    );
  }

  // ── Error ──────────────────────────────────────────
  if (error || !caseData) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <EmptyState
            icon="alert"
            title={t("cases.notFoundTitle")}
            description={t("cases.notFoundDescription")}
            action={
              <button
                onClick={() => router.push("/cases")}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 active:bg-blue-700 text-sm"
              >
                ← Back to Cases
              </button>
            }
          />
        </div>
      </div>
    );
  }

  const c = caseData;
  const sla = getSlaInfo(c.sla_deadline);

  return (
    <div className="min-h-screen bg-surface-ground pb-12">
      {/* Header */}
      <div className="bg-surface-card border-b border-border-subtle shadow-xs">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center gap-3 mb-2">
            <BackButton fallbackUrl="/cases" label={t("common.back")} />
            <div className="p-2 bg-accent-500/10 border border-accent-500/20 rounded-lg">
              <Briefcase className="w-5 h-5 text-accent-600 dark:text-accent-400" />
            </div>
            <h1 className="text-xl font-bold tracking-tight text-text-primary flex-1 min-w-0 truncate">
              {c.title}
            </h1>
          </div>

          {/* Meta badges */}
          <div className="flex flex-wrap items-center gap-2 ml-11">
            <Badge severity={mapCaseSeverity(c.severity) as any} variant="pill">
              {c.severity}
            </Badge>
            <span
              className={cn(
                "px-2.5 py-0.5 rounded-full text-xs font-medium",
                getStatusColor(c.status)
              )}
            >
              {getStatusLabel(c.status, t)}
            </span>
            {sla.expired && (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-danger-500/10 text-danger-600 dark:text-danger-400 border border-danger-500/20 flex items-center gap-1">
                <AlertTriangle className="w-3 h-3" />
                SLA OVERDUE
              </span>
            )}
            {sla.urgent && !sla.expired && (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-warning-500/10 text-warning-600 dark:text-warning-400 border border-warning-500/20 flex items-center gap-1">
                <Timer className="w-3 h-3" />
                SLA: {sla.text}
              </span>
            )}
          </div>
        </div>
      </div>

      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left column: Main content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Case Info */}
            <section className="bg-surface-card rounded-xl border border-border-subtle p-5 shadow-subtle">
              <h2 className="text-sm font-semibold tracking-tight text-text-primary mb-3">
                {t("cases.details")}
              </h2>

              {c.description && (
                <div className="mb-4">
                  <p className="text-sm text-text-secondary whitespace-pre-wrap leading-relaxed">
                    {c.description}
                  </p>
                </div>
              )}

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-500">{t("cases.severity")}</p>
                  <p className="text-sm font-medium text-gray-900 dark:text-white capitalize">
                    {c.severity}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-500">{t("cases.status")}</p>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {getStatusLabel(c.status, t)}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-500">{t("cases.assigned")}</p>
                  <p className="text-sm font-medium text-gray-900 dark:text-white flex items-center gap-1">
                    <User className="w-3.5 h-3.5 text-gray-400" />
                    {c.assigned_analyst_name || c.assigned_to || "—"}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-500">{t("cases.sla")}</p>
                  <p
                    className={cn(
                      "text-sm font-medium",
                      sla.expired
                        ? "text-red-600"
                        : sla.urgent
                          ? "text-amber-600"
                          : "text-gray-900 dark:text-white"
                    )}
                  >
                    {sla.text}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-500">{t("cases.created")}</p>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {formatDate(c.created_at, format)}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-500">{t("cases.updated")}</p>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {formatDate(c.updated_at, format)}
                  </p>
                </div>
              </div>

              {c.tags && c.tags.length > 0 && (
                <div className="mt-4 pt-4 border-t border-gray-100 dark:border-gray-700">
                  <div className="flex flex-wrap gap-1.5">
                    {c.tags.map((tag) => (
                      <span
                        key={tag}
                        className="px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700 text-xs text-gray-600 dark:text-gray-400 flex items-center gap-1"
                      >
                        <Tag className="w-3 h-3" />
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </section>

            {/* Status Action Bar */}
            <section className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
              <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
                {t("cases.actions")}
              </h2>
              <div className="flex flex-wrap items-center gap-2">
                <button
                  onClick={() => setStatusModalOpen(true)}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg focus-visible:ring-2 focus-visible:ring-primary-600/50 hover:bg-blue-700 active:bg-blue-700 text-sm font-medium transition-colors"
                >
                  {t("cases.transitionStatus")}
                </button>
                {c.status !== "closed" && c.status !== "false_positive" && (
                  <button
                    onClick={() => setLinkAlertModalOpen(true)}
                    className="px-4 py-2 bg-green-600 text-white rounded-lg focus-visible:ring-2 focus-visible:ring-primary-600/50 hover:bg-green-700 text-sm font-medium flex items-center gap-1.5 transition-colors"
                  >
                    <LinkIcon className="w-4 h-4" />
                    {t("cases.linkAlert")}
                  </button>
                )}
                <button
                  onClick={handleDelete}
                  className="px-4 py-2 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded-lg focus-visible:ring-2 focus-visible:ring-primary-600/50 hover:bg-red-100 active:bg-red-100 dark:hover:bg-red-900 active:bg-red-900/40 text-sm font-medium flex items-center gap-1.5 transition-colors ml-auto"
                >
                  <Trash2 className="w-4 h-4" />
                  {t("cases.delete")}
                </button>
              </div>
              {c.resolution_note && (
                <div className="mt-3 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                  <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                    {t("cases.resolutionNote")}
                  </p>
                  <p className="text-sm text-gray-700 dark:text-gray-300">{c.resolution_note}</p>
                </div>
              )}
            </section>

            {/* Linked Alerts */}
            <section className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
              <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
                {t("cases.linkedAlerts")} ({alerts?.length ?? 0})
              </h2>
              {!alerts || alerts.length === 0 ? (
                <p className="text-sm text-gray-500 dark:text-gray-400">{t("cases.noAlerts")}</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-xs text-gray-500 dark:text-gray-400 border-b border-gray-100 dark:border-gray-700">
                        <th className="pb-2 font-medium">{t("cases.alertId")}</th>
                        <th className="pb-2 font-medium">{t("cases.title")}</th>
                        <th className="pb-2 font-medium">{t("cases.severity")}</th>
                        <th className="pb-2 font-medium">{t("cases.status")}</th>
                        <th className="pb-2 font-medium text-right">{t("cases.actions")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {alerts.map((alert: CaseAlert) => (
                        <tr
                          key={alert.id}
                          className="border-b border-gray-50 dark:border-gray-700/50"
                        >
                          <td className="py-2.5 text-gray-900 dark:text-white">#{alert.id}</td>
                          <td className="py-2.5 text-gray-700 dark:text-gray-300 max-w-[200px] truncate">
                            {alert.title}
                          </td>
                          <td className="py-2.5 capitalize">{alert.severity}</td>
                          <td className="py-2.5">{alert.status}</td>
                          <td className="py-2.5 text-right">
                            <button
                              onClick={() => handleUnlinkAlert(alert.id)}
                              className="p-1 rounded text-gray-400 hover:text-red-500 hover:bg-red-50 active:bg-red-50 dark:hover:bg-red-900 active:bg-red-900/20"
                              title={t("cases.unlink")}
                            >
                              <Unlink className="w-4 h-4" />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            {/* Comments */}
            <section className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
              <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">
                {t("cases.comments")} ({comments?.length ?? 0})
              </h2>

              {/* Comment input */}
              <div className="flex gap-2 mb-4">
                <input
                  type="text"
                  value={newComment}
                  onChange={(e) => setNewComment(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleAddComment()}
                  placeholder={t("cases.commentPlaceholder")}
                  className="flex-1 px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
                />
                <button
                  onClick={handleAddComment}
                  disabled={submittingComment || !newComment.trim()}
                  className="px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 active:bg-blue-700 disabled:opacity-50 flex items-center gap-1 text-sm"
                >
                  <Send className="w-4 h-4" />
                </button>
              </div>

              {/* Comments list */}
              <div className="space-y-3 max-h-96 overflow-y-auto">
                {!comments || comments.length === 0 ? (
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {t("cases.noComments")}
                  </p>
                ) : (
                  comments.map((comment: CaseComment) => (
                    <div key={comment.id} className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
                          {comment.username}
                        </span>
                        <span className="text-xs text-gray-400">
                          {formatDate(comment.created_at, format)}
                        </span>
                      </div>
                      <p className="text-sm text-gray-600 dark:text-gray-400 whitespace-pre-wrap">
                        {comment.content}
                      </p>
                    </div>
                  ))
                )}
              </div>
            </section>
          </div>

          {/* Right column: Timeline / Activity */}
          <div className="space-y-6">
            <section className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
              <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4 flex items-center gap-2">
                <History className="w-4 h-4 text-gray-400" />
                {t("cases.timeline")}
              </h2>

              {!timeline || timeline.length === 0 ? (
                <p className="text-sm text-gray-500 dark:text-gray-400">{t("cases.noEvents")}</p>
              ) : (
                <div className="space-y-0">
                  {timeline.map((event: CaseTimelineEvent) => (
                    <div
                      key={event.id}
                      className="relative pl-5 pb-4 last:pb-0 border-l border-gray-200 dark:border-gray-700"
                    >
                      <div className="absolute left-0 top-1 -translate-x-1/2 w-5 h-5 rounded-full bg-white dark:bg-gray-800 border-2 border-gray-200 dark:border-gray-700 flex items-center justify-center">
                        {getTimelineIcon(event.event_type)}
                      </div>
                      <div className="ml-1">
                        <p className="text-xs text-gray-600 dark:text-gray-400 leading-relaxed">
                          {event.description}
                        </p>
                        {event.user && (
                          <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
                            by {event.user}
                          </p>
                        )}
                        <p className="text-[10px] text-gray-400 dark:text-gray-500 mt-0.5">
                          {formatDate(event.timestamp, format)}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </div>
        </div>
      </main>

      {/* Modals */}
      <StatusModal
        isOpen={statusModalOpen}
        onClose={() => setStatusModalOpen(false)}
        currentStatus={c.status}
        onTransition={handleTransition}
        t={t}
      />
      <LinkAlertModal
        isOpen={linkAlertModalOpen}
        onClose={() => setLinkAlertModalOpen(false)}
        onLink={handleLinkAlert}
        t={t}
      />

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={showDeleteConfirm}
        onCancel={() => setShowDeleteConfirm(false)}
        onConfirm={confirmDelete}
        title="Delete Case"
        description="Are you sure you want to delete this case? This cannot be undone."
        variant="danger"
        confirmText="Delete"
      />
    </div>
  );
}
