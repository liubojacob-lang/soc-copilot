"use client";

/**
 * Alert Detail Page
 *
 * Features:
 * - Alert basic info (title, description, severity, status, source, time)
 * - Triage panel: status change buttons (new→triaged→investigating→resolved/false_positive)
 * - IOC display (IPs, domains, URLs, hashes)
 * - Associated asset info
 * - Threat intelligence links
 * - Related cases list
 * - Operation history timeline
 * - Status change reason notes
 * - Loading/Error/Empty state coverage
 */

import { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import { useRouter } from "@/i18n/navigation";
import { useFormatter, useLocale, useTranslations } from "next-intl";

type Formatter = ReturnType<typeof useFormatter>;
import {
  ArrowLeft,
  RefreshCw,
  AlertTriangle,
  Shield,
  Clock,
  Server,
  Globe,
  Link,
  Hash,
  FileText,
  User,
  Activity,
  CheckCircle,
  XCircle,
  RotateCcw,
  Send,
  ExternalLink,
  Tag,
  Info,
  Calendar,
} from "lucide-react";
import { loadAuthState } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/Badge";
import { LoadingState } from "@/components/common/LoadingState";
import { useToast } from "@/components/Toast";
import {
  useAlertDetail,
  useAlertLifecycle,
  useUpdateAlert,
  useAddAlertNote,
} from "@/hooks/useAlerts";
import type { AlertSeverity, AlertStatus, AlertNoteItem, SecurityAlertItem } from "@/lib/api";

// ── Helpers ────────────────────────────────────────────

function formatDateTime(ts: string | null | undefined, format: Formatter): string {
  if (!ts) return "-";
  try {
    return format.dateTime(new Date(ts), { dateStyle: "medium", timeStyle: "medium" });
  } catch {
    return "-";
  }
}

function mapSeverityBadge(s: string): "critical" | "high" | "medium" | "low" | "info" | "neutral" {
  const m: Record<string, "critical" | "high" | "medium" | "low" | "info" | "neutral"> = {
    critical: "critical",
    high: "high",
    medium: "medium",
    low: "low",
    info: "info",
  };
  return m[s] || "neutral";
}

function mapStatusBadge(s: string): "critical" | "high" | "medium" | "low" | "info" | "neutral" {
  const m: Record<string, "critical" | "high" | "medium" | "low" | "info" | "neutral"> = {
    new: "info",
    investigating: "medium",
    resolved: "low",
    false_positive: "neutral",
    escalated: "high",
  };
  return m[s] || "neutral";
}

// ── Status Flow ────────────────────────────────────────

const STATUS_TRANSITIONS: Record<string, string[]> = {
  new: ["investigating", "resolved", "false_positive", "escalated"],
  investigating: ["resolved", "false_positive", "escalated"],
  escalated: ["investigating", "resolved", "false_positive"],
  resolved: ["investigating", "new"],
  false_positive: ["new"],
};

const STATUS_LABELS: Record<string, string> = {
  new: "New",
  investigating: "Investigating",
  resolved: "Resolved",
  false_positive: "False Positive",
  escalated: "Escalated",
};

const STATUS_COLORS: Record<string, string> = {
  new: "bg-blue-600 hover:bg-blue-700 text-white",
  investigating: "bg-yellow-600 hover:bg-yellow-700 text-white",
  resolved: "bg-green-600 hover:bg-green-700 text-white",
  false_positive: "bg-gray-600 hover:bg-gray-700 text-white",
  escalated: "bg-red-600 hover:bg-red-700 text-white",
};

// ── IOC Display ────────────────────────────────────────

function IOCSection({ iocs }: { iocs?: SecurityAlertItem["iocs"] }) {
  const t = useTranslations("alerts.detail");
  if (!iocs || iocs.length === 0) {
    return <div className="text-sm text-gray-400 dark:text-gray-500 italic">{t("noIOCs")}</div>;
  }

  const grouped: Record<string, typeof iocs> = {};
  iocs.forEach((ioc) => {
    const type = ioc.type || "other";
    if (!grouped[type]) grouped[type] = [];
    grouped[type].push(ioc);
  });

  const typeIcons: Record<string, React.ReactNode> = {
    ip: <Server className="w-3.5 h-3.5" />,
    domain: <Globe className="w-3.5 h-3.5" />,
    url: <Link className="w-3.5 h-3.5" />,
    hash: <Hash className="w-3.5 h-3.5" />,
  };

  return (
    <div className="space-y-3">
      {Object.entries(grouped).map(([type, items]) => (
        <div key={type}>
          <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase mb-1.5 flex items-center gap-1">
            {typeIcons[type]} {type}s ({items.length})
          </h4>
          <div className="flex flex-wrap gap-1.5">
            {items.map((ioc, idx) => (
              <span
                key={idx}
                className="inline-flex items-center gap-1 px-2 py-1 text-xs font-mono bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded border border-gray-200 dark:border-gray-600"
              >
                {ioc.value}
                {ioc.reputation && (
                  <Badge
                    severity={
                      ioc.reputation === "malicious"
                        ? "critical"
                        : ioc.reputation === "suspicious"
                          ? "high"
                          : "neutral"
                    }
                  >
                    {ioc.reputation}
                  </Badge>
                )}
              </span>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Timeline ───────────────────────────────────────────

interface TimelineEventLocal {
  id: string;
  timestamp: string;
  event_type: string;
  description: string;
  user?: string;
  details?: Record<string, unknown>;
}

function TimelineView({ events }: { events?: TimelineEventLocal[] | any[] }) {
  const format = useFormatter();
  const t = useTranslations("alerts.detail");
  if (!events || events.length === 0) {
    return (
      <div className="text-sm text-gray-400 dark:text-gray-500 italic text-center py-6">
        {t("noTimeline")}
      </div>
    );
  }

  const iconMap: Record<string, React.ReactNode> = {
    created: <Activity className="w-4 h-4 text-blue-500" />,
    status_changed: <RefreshCw className="w-4 h-4 text-yellow-500" />,
    assigned: <User className="w-4 h-4 text-purple-500" />,
    enriched: <Shield className="w-4 h-4 text-green-500" />,
    correlated: <Link className="w-4 h-4 text-indigo-500" />,
    escalated: <AlertTriangle className="w-4 h-4 text-red-500" />,
    resolved: <CheckCircle className="w-4 h-4 text-green-600" />,
    noted: <FileText className="w-4 h-4 text-gray-500" />,
  };

  return (
    <div className="space-y-0">
      {events.map((event, idx) => (
        <div key={event.id || idx} className="relative pl-8 pb-4 last:pb-0">
          {/* Connector line */}
          {idx < events.length - 1 && (
            <div className="absolute left-[15px] top-6 bottom-0 w-px bg-gray-200 dark:bg-gray-700" />
          )}
          {/* Icon */}
          <div className="absolute left-1 top-1 flex items-center justify-center w-7 h-7 rounded-full bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
            {iconMap[event.event_type] || <Info className="w-4 h-4 text-gray-400" />}
          </div>
          {/* Content */}
          <div>
            <p className="text-sm text-gray-900 dark:text-white">{event.description}</p>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-xs text-gray-400">
                {formatDateTime(event.timestamp, format)}
              </span>
              {event.user && <span className="text-xs text-gray-500">by {event.user}</span>}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Notes Section ──────────────────────────────────────

function NotesSection({
  notes,
  onAdd,
  isAdding,
}: {
  notes?: AlertNoteItem[];
  onAdd: (content: string) => void;
  isAdding: boolean;
}) {
  const t = useTranslations("alerts.detail");
  const format = useFormatter();
  const [newNote, setNewNote] = useState("");

  const handleSubmit = () => {
    if (!newNote.trim()) return;
    onAdd(newNote.trim());
    setNewNote("");
  };

  return (
    <div className="space-y-4">
      {/* Add note input */}
      <div className="flex gap-2">
        <input
          type="text"
          value={newNote}
          onChange={(e) => setNewNote(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
          placeholder={t("addNotePlaceholder")}
          className="flex-1 px-3 py-2 text-sm border border-gray-200 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          onClick={handleSubmit}
          disabled={!newNote.trim() || isAdding}
          className="px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          <Send className="w-4 h-4" />
        </button>
      </div>

      {/* Note list */}
      {!notes || notes.length === 0 ? (
        <div className="text-sm text-gray-400 dark:text-gray-500 italic text-center py-4">
          {t("noNotes")}
        </div>
      ) : (
        <div className="space-y-3">
          {notes.map((note) => (
            <div
              key={note.id}
              className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3 border border-gray-100 dark:border-gray-700"
            >
              <p className="text-sm text-gray-800 dark:text-gray-200">{note.content}</p>
              <div className="flex items-center gap-2 mt-1.5">
                <User className="w-3 h-3 text-gray-400" />
                <span className="text-xs text-gray-500">{note.username}</span>
                <span className="text-xs text-gray-400">·</span>
                <span className="text-xs text-gray-400">
                  {formatDateTime(note.created_at, format)}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Triage Panel ───────────────────────────────────────

function TriagePanel({
  currentStatus,
  onStatusChange,
  isUpdating,
}: {
  currentStatus?: string;
  onStatusChange: (status: string) => void;
  isUpdating: boolean;
}) {
  const t = useTranslations("alerts.detail");
  const status = currentStatus || "new";
  const transitions = STATUS_TRANSITIONS[status] || [];

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
      <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
        {t("triageTitle")}
      </h3>
      <div className="space-y-2">
        {/* Current status indicator */}
        <div className="flex items-center gap-2 mb-3 px-3 py-2 bg-gray-50 dark:bg-gray-900 rounded-lg">
          <span className="text-xs text-gray-500 dark:text-gray-400">{t("currentStatus")}:</span>
          <Badge severity={mapStatusBadge(status)}>{STATUS_LABELS[status] || status}</Badge>
        </div>

        {/* Transition buttons */}
        <div className="grid grid-cols-2 gap-2">
          {transitions.map((nextStatus) => (
            <button
              key={nextStatus}
              onClick={() => onStatusChange(nextStatus)}
              disabled={isUpdating}
              className={cn(
                "px-3 py-2 text-xs font-medium rounded-lg transition-colors disabled:opacity-50 flex items-center justify-center gap-1.5",
                STATUS_COLORS[nextStatus] || "bg-gray-100 text-gray-700 hover:bg-gray-200"
              )}
            >
              {nextStatus === "resolved" && <CheckCircle className="w-3.5 h-3.5" />}
              {nextStatus === "false_positive" && <XCircle className="w-3.5 h-3.5" />}
              {nextStatus === "investigating" && <Activity className="w-3.5 h-3.5" />}
              {nextStatus === "escalated" && <AlertTriangle className="w-3.5 h-3.5" />}
              {nextStatus === "new" && <RotateCcw className="w-3.5 h-3.5" />}
              {STATUS_LABELS[nextStatus] || nextStatus}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Page Component ──────────────────────────────────────

export default function AlertDetailPage() {
  const format = useFormatter();
  const locale = useLocale();
  const t = useTranslations("alerts.detail");
  const tCommon = useTranslations("common");
  const params = useParams();
  const router = useRouter();
  const { showToast } = useToast();
  const alertId = params.id as string;

  const [mounted, setMounted] = useState(false);
  const [activeTab, setActiveTab] = useState<"overview" | "timeline" | "notes">("overview");

  // Auth
  useEffect(() => {
    setMounted(true);
    const authState = loadAuthState();
    if (!authState?.isAuthenticated) {
      router.push(`/${locale}/login`);
    }
  }, [router, locale]);

  // Data fetching
  const { data: alert, isLoading, error, refetch } = useAlertDetail(alertId);
  const { data: lifecycle } = useAlertLifecycle(alertId);
  const updateAlert = useUpdateAlert();
  const addNote = useAddAlertNote();

  // Status change handler
  const handleStatusChange = useCallback(
    async (newStatus: string) => {
      if (!alert?.id) return;
      try {
        await updateAlert.mutateAsync({
          id: alert.id,
          payload: { status: newStatus },
        });
        showToast(`Status changed to "${STATUS_LABELS[newStatus] || newStatus}"`, "success");
      } catch (err) {
        showToast(
          `Status change failed: ${err instanceof Error ? err.message : "Unknown error"}`,
          "error"
        );
      }
    },
    [alert?.id, updateAlert, showToast]
  );

  // Add note handler
  const handleAddNote = useCallback(
    async (content: string) => {
      if (!alert?.id) return;
      try {
        await addNote.mutateAsync({ alertId: alert.id, content });
        showToast("Note added", "success");
      } catch (err) {
        showToast("Failed to add note", "error");
      }
    },
    [alert?.id, addNote, showToast]
  );

  if (!mounted) return null;

  // ── Loading ──────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <LoadingState isLoading={true} type="skeleton" skeletonType="card" />
        </div>
      </div>
    );
  }

  // ── Error / Not Found ────────────────────────────────
  if (error || !alert) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <div className="max-w-7xl mx-auto px-4 py-8">
          <LoadingState
            isLoading={false}
            error={error || "Alert not found"}
            onRetry={() => refetch()}
          />
          <button
            onClick={() => router.back()}
            className="mt-4 px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
          >
            ← Back
          </button>
        </div>
      </div>
    );
  }

  // ── Render ──────────────────────────────────────────

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-start gap-4">
            <button
              onClick={() => router.back()}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors mt-1"
              title={tCommon("back")}
            >
              <ArrowLeft className="w-5 h-5 text-gray-500" />
            </button>

            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <Badge severity={mapSeverityBadge(alert.severity)}>
                  {alert.severity?.toUpperCase()}
                </Badge>
                <Badge severity={mapStatusBadge(alert.status)}>
                  {STATUS_LABELS[alert.status] || alert.status}
                </Badge>
              </div>
              <h1 className="text-xl font-bold text-gray-900 dark:text-white">{alert.title}</h1>
              <div className="flex flex-wrap items-center gap-2 mt-1 text-sm text-gray-500 dark:text-gray-400">
                <span className="flex items-center gap-1">
                  <Server className="w-3.5 h-3.5" />
                  {alert.source || "unknown"}
                </span>
                <span>·</span>
                <span className="flex items-center gap-1">
                  <Calendar className="w-3.5 h-3.5" />
                  {formatDateTime(alert.event_timestamp || alert.created_at, format)}
                </span>
                {alert.assigned_to && (
                  <>
                    <span>·</span>
                    <span className="flex items-center gap-1">
                      <User className="w-3.5 h-3.5" />
                      {alert.assigned_to}
                    </span>
                  </>
                )}
              </div>
            </div>

            <button
              onClick={() => refetch()}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
              title={tCommon("refresh")}
            >
              <RefreshCw className="w-5 h-5 text-gray-400" />
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Column (2/3) */}
          <div className="lg:col-span-2 space-y-6">
            {/* Description */}
            {alert.description && (
              <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-5">
                <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2 flex items-center gap-2">
                  <Info className="w-4 h-4 text-gray-400" />
                  {t("description")}
                </h3>
                <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                  {alert.description}
                </p>
              </div>
            )}

            {/* Tabs: Overview / Timeline / Notes */}
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
              {/* Tab Header */}
              <div className="flex border-b border-gray-200 dark:border-gray-700">
                {[
                  { key: "overview", label: t("tabOverview") },
                  { key: "timeline", label: t("tabTimeline") },
                  { key: "notes", label: t("tabNotes") },
                ].map((tab) => (
                  <button
                    key={tab.key}
                    onClick={() => setActiveTab(tab.key as typeof activeTab)}
                    className={cn(
                      "px-4 py-3 text-sm font-medium border-b-2 transition-colors",
                      activeTab === tab.key
                        ? "border-blue-600 text-blue-600 dark:text-blue-400 dark:border-blue-400"
                        : "border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                    )}
                  >
                    {tab.label}
                    {tab.key === "notes" && lifecycle?.notes?.length ? (
                      <span className="ml-1.5 px-1.5 py-0.5 text-xs bg-gray-100 dark:bg-gray-700 rounded-full">
                        {lifecycle.notes.length}
                      </span>
                    ) : null}
                  </button>
                ))}
              </div>

              {/* Tab Content */}
              <div className="p-5">
                {activeTab === "overview" && (
                  <div className="space-y-6">
                    {/* Technical Details Grid */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
                      <DetailItem label={t("fieldSourceIP")} value={alert.source_ip} mono />
                      <DetailItem label={t("fieldDestIP")} value={alert.destination_ip} mono />
                      <DetailItem label={t("fieldAgent")} value={alert.agent_name} />
                      <DetailItem label={t("fieldRuleID")} value={alert.rule_id} mono />
                      <DetailItem label={t("fieldEventType")} value={alert.event_type} />
                      <DetailItem label={t("fieldProtocol")} value={alert.protocol} />
                      <DetailItem
                        label={t("fieldRuleLevel")}
                        value={alert.rule_level?.toString()}
                      />
                      <DetailItem label={t("fieldMITRE")} value={alert.rule_mitre || undefined} />
                    </div>

                    {/* Source IP */}
                    {alert.source_ip && (
                      <div>
                        <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1.5">
                          {t("threatIntelTitle")}
                        </h4>
                        <a
                          href={`https://www.virustotal.com/gui/ip-address/${alert.source_ip}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1.5 text-sm text-blue-600 dark:text-blue-400 hover:underline"
                        >
                          Lookup {alert.source_ip} on VirusTotal
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      </div>
                    )}

                    {/* IOCs */}
                    <div>
                      <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
                        <Tag className="w-4 h-4 text-gray-400" />
                        {t("iocTitle")}
                      </h4>
                      <IOCSection iocs={alert.iocs} />
                    </div>
                  </div>
                )}

                {activeTab === "timeline" && <TimelineView events={lifecycle?.timeline} />}

                {activeTab === "notes" && (
                  <NotesSection
                    notes={lifecycle?.notes}
                    onAdd={handleAddNote}
                    isAdding={addNote.isPending}
                  />
                )}
              </div>
            </div>
          </div>

          {/* Sidebar Column (1/3) */}
          <div className="space-y-4">
            {/* Triage Panel */}
            <TriagePanel
              currentStatus={alert.status}
              onStatusChange={handleStatusChange}
              isUpdating={updateAlert.isPending}
            />

            {/* Quick Info */}
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
                {t("quickInfoTitle")}
              </h3>
              <div className="space-y-2 text-sm">
                <InfoRow label={t("fieldID")} value={`#${alert.id}`} />
                <InfoRow
                  label={t("fieldCreated")}
                  value={formatDateTime(alert.created_at, format)}
                />
                <InfoRow
                  label={t("fieldEventTime")}
                  value={formatDateTime(alert.event_timestamp, format)}
                />
                {alert.resolved_at && (
                  <InfoRow
                    label={t("fieldResolved")}
                    value={formatDateTime(alert.resolved_at, format)}
                  />
                )}
                {alert.resolved_by && (
                  <InfoRow label={t("fieldResolvedBy")} value={alert.resolved_by} />
                )}
                {alert.resolution_note && (
                  <InfoRow label={t("fieldResolution")} value={alert.resolution_note} />
                )}
              </div>
            </div>

            {/* Threat Score */}
            {alert.threat_score != null && (
              <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
                <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">
                  {t("threatScoreTitle")}
                </h3>
                <div className="flex items-center gap-3">
                  <div className="text-2xl font-bold text-red-600 dark:text-red-400">
                    {alert.threat_score}
                  </div>
                  <div className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                    <div
                      className={cn(
                        "h-full rounded-full transition-all",
                        alert.threat_score >= 80
                          ? "bg-red-500"
                          : alert.threat_score >= 50
                            ? "bg-yellow-500"
                            : "bg-green-500"
                      )}
                      style={{ width: `${Math.min(100, alert.threat_score)}%` }}
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Affected Assets */}
            {alert.agent_name && (
              <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
                <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2 flex items-center gap-2">
                  <Server className="w-4 h-4 text-gray-400" />
                  {t("affectedAssetTitle")}
                </h3>
                <p className="text-sm text-gray-700 dark:text-gray-300">{alert.agent_name}</p>
                {alert.agent_ip && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    IP: {alert.agent_ip}
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Small Helper Components ────────────────────────────

function DetailItem({
  label,
  value,
  mono = false,
}: {
  label: string;
  value?: string | null;
  mono?: boolean;
}) {
  return (
    <div>
      <span className="text-gray-500 dark:text-gray-400 text-xs">{label}</span>
      <p
        className={cn(
          "mt-0.5 text-gray-900 dark:text-white",
          mono && "font-mono",
          !value && "text-gray-300 dark:text-gray-600 italic"
        )}
      >
        {value || "N/A"}
      </p>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between items-start gap-2">
      <span className="text-gray-500 dark:text-gray-400 text-xs whitespace-nowrap">{label}</span>
      <span className="text-gray-900 dark:text-white text-xs text-right break-all">{value}</span>
    </div>
  );
}
