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
import { useFormatter, useTranslations } from "next-intl";

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
import { Button } from "@/components/common/Button";
import { Card, BackButton } from "@/components/common";
import { LoadingState } from "@/components/common/LoadingState";
import { useToast } from "@/components/Toast";
import {
  useAlertDetail,
  useAlertLifecycle,
  useUpdateAlert,
  useAddAlertNote,
} from "@/hooks/useAlerts";
import type { AlertNoteItem, SecurityAlertItem } from "@/lib/api";

// ── Helpers ────────────────────────────────────────────

function formatDateTime(ts: string | null | undefined, format: Formatter): string {
  if (!ts) return "-";
  try {
    const d = new Date(ts);
    if (isNaN(d.getTime())) return "-";
    return format.dateTime(d, { dateStyle: "medium", timeStyle: "medium" });
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

// ── IOC Display ────────────────────────────────────────

function IOCSection({ iocs }: { iocs?: SecurityAlertItem["iocs"] }) {
  const t = useTranslations("alerts.detail");
  if (!iocs || iocs.length === 0) {
    return <div className="text-xs text-text-muted italic">{t("noIOCs")}</div>;
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
          <h4 className="text-xs font-semibold text-text-secondary uppercase mb-2 flex items-center gap-1.5">
            {typeIcons[type]} {type}s ({items.length})
          </h4>
          <div className="flex flex-wrap gap-1.5">
            {items.map((ioc, idx) => (
              <span
                key={idx}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-mono bg-surface-ground text-text-primary rounded-lg border border-border-subtle shadow-xs"
              >
                {ioc.value}
                {ioc.reputation && (
                  <Badge
                    size="xs"
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

function TimelineView({ events }: { events?: TimelineEventLocal[] }) {
  const format = useFormatter();
  const t = useTranslations("alerts.detail");
  if (!events || events.length === 0) {
    return <div className="text-xs text-text-muted italic text-center py-6">{t("noTimeline")}</div>;
  }

  const iconMap: Record<string, React.ReactNode> = {
    created: <Activity className="w-3.5 h-3.5 text-accent-500" />,
    status_changed: <RefreshCw className="w-3.5 h-3.5 text-amber-500" />,
    assigned: <User className="w-3.5 h-3.5 text-purple-500" />,
    enriched: <Shield className="w-3.5 h-3.5 text-emerald-500" />,
    correlated: <Link className="w-3.5 h-3.5 text-indigo-500" />,
    escalated: <AlertTriangle className="w-3.5 h-3.5 text-danger-500" />,
    resolved: <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />,
    noted: <FileText className="w-3.5 h-3.5 text-text-muted" />,
  };

  return (
    <div className="space-y-0 py-1">
      {events.map((event, idx) => (
        <div key={event.id || idx} className="relative pl-7 pb-5 last:pb-0">
          {/* Connector line */}
          {idx < events.length - 1 && (
            <div className="absolute left-[13px] top-6 bottom-0 w-px bg-border-subtle" />
          )}
          {/* Icon */}
          <div className="absolute left-0 top-1 flex items-center justify-center w-7 h-7 rounded-full bg-surface-ground border border-border-subtle shadow-xs">
            {iconMap[event.event_type] || <Info className="w-3.5 h-3.5 text-text-muted" />}
          </div>
          {/* Content */}
          <div className="pt-0.5">
            <p className="text-xs sm:text-sm font-medium text-text-primary">{event.description}</p>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-[11px] text-text-muted">
                {formatDateTime(event.timestamp, format)}
              </span>
              {event.user && (
                <span className="text-[11px] text-text-secondary">by {event.user}</span>
              )}
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
          className="flex-1 px-3 py-2 text-xs sm:text-sm border border-border-default rounded-lg bg-surface-input text-text-primary placeholder:text-text-disabled focus:outline-none focus:ring-2 focus:ring-accent-500/20 focus:border-accent-600 transition-all"
        />
        <Button
          onClick={handleSubmit}
          disabled={!newNote.trim() || isAdding}
          isLoading={isAdding}
          variant="primary"
          size="sm"
        >
          <Send className="w-4 h-4" />
        </Button>
      </div>

      {/* Note list */}
      {!notes || notes.length === 0 ? (
        <div className="text-xs text-text-muted italic text-center py-4">{t("noNotes")}</div>
      ) : (
        <div className="space-y-2.5">
          {notes.map((note) => (
            <div
              key={note.id}
              className="bg-surface-ground rounded-xl p-3.5 border border-border-subtle"
            >
              <p className="text-xs sm:text-sm text-text-primary leading-relaxed">{note.content}</p>
              <div className="flex items-center gap-2 mt-2 text-[11px] text-text-muted">
                <User className="w-3 h-3" />
                <span className="font-medium text-text-secondary">{note.username}</span>
                <span>·</span>
                <span>{formatDateTime(note.created_at, format)}</span>
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
    <Card className="p-4 sm:p-5">
      <h3 className="text-sm font-semibold tracking-tight text-text-primary mb-3">
        {t("triageTitle")}
      </h3>
      <div className="space-y-3">
        {/* Current status indicator */}
        <div className="flex items-center justify-between px-3 py-2 bg-surface-ground rounded-lg border border-border-subtle">
          <span className="text-xs font-medium text-text-muted">{t("currentStatus")}:</span>
          <Badge severity={mapStatusBadge(status)} variant="pill">
            {STATUS_LABELS[status] || status}
          </Badge>
        </div>

        {/* Transition buttons */}
        <div className="grid grid-cols-2 gap-2">
          {transitions.map((nextStatus) => {
            let variant: "primary" | "secondary" | "outline" | "danger" = "secondary";
            let customClass = "";
            if (nextStatus === "resolved") {
              variant = "primary";
              customClass = "bg-emerald-600 hover:bg-emerald-700 text-white";
            } else if (nextStatus === "escalated") {
              variant = "danger";
            } else if (nextStatus === "false_positive") {
              variant = "outline";
            }

            return (
              <Button
                key={nextStatus}
                onClick={() => onStatusChange(nextStatus)}
                disabled={isUpdating}
                size="sm"
                variant={variant}
                className={cn("w-full text-xs font-medium justify-center", customClass)}
                leftIcon={
                  nextStatus === "resolved" ? (
                    <CheckCircle className="w-3.5 h-3.5" />
                  ) : nextStatus === "false_positive" ? (
                    <XCircle className="w-3.5 h-3.5" />
                  ) : nextStatus === "investigating" ? (
                    <Activity className="w-3.5 h-3.5" />
                  ) : nextStatus === "escalated" ? (
                    <AlertTriangle className="w-3.5 h-3.5" />
                  ) : (
                    <RotateCcw className="w-3.5 h-3.5" />
                  )
                }
              >
                {STATUS_LABELS[nextStatus] || nextStatus}
              </Button>
            );
          })}
        </div>
      </div>
    </Card>
  );
}

// ── Page Component ──────────────────────────────────────

export default function AlertDetailPage() {
  const format = useFormatter();
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
      router.push("/login");
    }
  }, [router]);

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
      } catch {
        showToast("Failed to add note", "error");
      }
    },
    [alert?.id, addNote, showToast]
  );

  if (!mounted) return null;

  // ── Loading ──────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="min-h-screen bg-surface-ground">
        <div className="max-w-[1600px] mx-auto px-4 py-6">
          <LoadingState isLoading={true} type="skeleton" skeletonType="card" />
        </div>
      </div>
    );
  }

  // ── Error / Not Found ────────────────────────────────
  if (error || !alert) {
    return (
      <div className="min-h-screen bg-surface-ground">
        <div className="max-w-[1600px] mx-auto px-4 py-8">
          <LoadingState
            isLoading={false}
            error={error || "Alert not found"}
            onRetry={() => refetch()}
          />
          <BackButton fallbackUrl="/alerts" label={tCommon("back")} className="mt-4" />
        </div>
      </div>
    );
  }

  // ── Render ──────────────────────────────────────────

  return (
    <div className="min-h-screen bg-surface-ground pb-12">
      {/* Header */}
      <div className="bg-surface-card border-b border-border-subtle shadow-xs">
        <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-start gap-4">
            <BackButton fallbackUrl="/alerts" label={tCommon("back")} className="mt-0.5 shrink-0" />

            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1.5">
                <Badge severity={mapSeverityBadge(alert.severity)} variant="pill">
                  {alert.severity?.toUpperCase()}
                </Badge>
                <Badge severity={mapStatusBadge(alert.status)} variant="pill">
                  {STATUS_LABELS[alert.status] || alert.status}
                </Badge>
              </div>
              <h1 className="text-lg sm:text-xl font-bold tracking-tight text-text-primary">
                {alert.title}
              </h1>
              <div className="flex flex-wrap items-center gap-2 mt-1.5 text-xs text-text-muted">
                <span className="flex items-center gap-1 font-mono">
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

            <Button
              variant="outline"
              size="icon"
              onClick={() => refetch()}
              title={tCommon("refresh")}
              aria-label={tCommon("refresh")}
            >
              <RefreshCw className="w-4 h-4 text-text-muted" />
            </Button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Column (2/3) */}
          <div className="lg:col-span-2 space-y-6">
            {/* Description */}
            {alert.description && (
              <Card className="p-5">
                <h3 className="text-sm font-semibold tracking-tight text-text-primary mb-2.5 flex items-center gap-2">
                  <Info className="w-4 h-4 text-accent-500" />
                  {t("description")}
                </h3>
                <p className="text-xs sm:text-sm text-text-secondary leading-relaxed whitespace-pre-wrap">
                  {alert.description}
                </p>
              </Card>
            )}

            {/* Tabs: Overview / Timeline / Notes */}
            <Card className="overflow-hidden">
              {/* Tab Header */}
              <div className="flex border-b border-border-subtle px-3 bg-surface-ground/40">
                {[
                  { key: "overview", label: t("tabOverview") },
                  { key: "timeline", label: t("tabTimeline") },
                  { key: "notes", label: t("tabNotes") },
                ].map((tab) => (
                  <button
                    key={tab.key}
                    onClick={() => setActiveTab(tab.key as typeof activeTab)}
                    className={cn(
                      "px-4 py-3 text-xs sm:text-sm font-medium border-b-2 transition-all",
                      activeTab === tab.key
                        ? "border-accent-600 text-accent-600 dark:text-accent-400"
                        : "border-transparent text-text-muted hover:text-text-primary"
                    )}
                  >
                    {tab.label}
                    {tab.key === "notes" && lifecycle?.notes?.length ? (
                      <span className="ml-1.5 px-1.5 py-0.2 text-[10px] bg-accent-500/20 text-accent-600 rounded-full font-semibold">
                        {lifecycle.notes.length}
                      </span>
                    ) : null}
                  </button>
                ))}
              </div>

              {/* Tab Content */}
              <div className="p-5 sm:p-6">
                {activeTab === "overview" && (
                  <div className="space-y-6">
                    {/* Technical Details Grid */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs sm:text-sm">
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
                      <div className="pt-4 border-t border-border-subtle">
                        <h4 className="text-xs font-semibold text-text-secondary uppercase mb-2">
                          {t("threatIntelTitle")}
                        </h4>
                        <a
                          href={`https://www.virustotal.com/gui/ip-address/${alert.source_ip}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1.5 text-xs sm:text-sm text-accent-600 dark:text-accent-400 hover:underline font-mono"
                        >
                          Lookup {alert.source_ip} on VirusTotal
                          <ExternalLink className="w-3.5 h-3.5" />
                        </a>
                      </div>
                    )}

                    {/* IOCs */}
                    <div className="pt-4 border-t border-border-subtle">
                      <h4 className="text-sm font-semibold tracking-tight text-text-primary mb-3 flex items-center gap-2">
                        <Tag className="w-4 h-4 text-accent-500" />
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
            </Card>
          </div>

          {/* Sidebar Column (1/3) */}
          <div className="space-y-5">
            {/* Triage Panel */}
            <TriagePanel
              currentStatus={alert.status}
              onStatusChange={handleStatusChange}
              isUpdating={updateAlert.isPending}
            />

            {/* Quick Info */}
            <Card className="p-4 sm:p-5">
              <h3 className="text-sm font-semibold tracking-tight text-text-primary mb-3">
                {t("quickInfoTitle")}
              </h3>
              <div className="space-y-2.5 text-xs sm:text-sm">
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
            </Card>

            {/* Threat Score */}
            {alert.threat_score != null && (
              <Card className="p-4 sm:p-5">
                <h3 className="text-sm font-semibold tracking-tight text-text-primary mb-2">
                  {t("threatScoreTitle")}
                </h3>
                <div className="flex items-center gap-3">
                  <div className="text-2xl font-bold tracking-tight text-danger-600 dark:text-danger-400 tabular-nums">
                    {alert.threat_score}
                  </div>
                  <div className="flex-1 h-2 bg-surface-ground rounded-full overflow-hidden border border-border-subtle">
                    <div
                      className={cn(
                        "h-full rounded-full transition-all",
                        alert.threat_score >= 80
                          ? "bg-danger-500"
                          : alert.threat_score >= 50
                            ? "bg-amber-500"
                            : "bg-emerald-500"
                      )}
                      style={{ width: `${Math.min(100, alert.threat_score)}%` }}
                    />
                  </div>
                </div>
              </Card>
            )}

            {/* Affected Assets */}
            {alert.agent_name && (
              <Card className="p-4 sm:p-5">
                <h3 className="text-sm font-semibold tracking-tight text-text-primary mb-2 flex items-center gap-2">
                  <Server className="w-4 h-4 text-text-muted" />
                  {t("affectedAssetTitle")}
                </h3>
                <p className="text-xs sm:text-sm font-medium text-text-primary font-mono">
                  {alert.agent_name}
                </p>
                {alert.agent_ip && (
                  <p className="text-xs text-text-muted mt-1 font-mono">IP: {alert.agent_ip}</p>
                )}
              </Card>
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
      <span className="text-text-muted text-xs">{label}</span>
      <p
        className={cn(
          "mt-0.5 text-text-primary font-medium",
          mono && "font-mono text-xs",
          !value && "text-text-disabled italic font-normal"
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
      <span className="text-text-muted text-xs whitespace-nowrap">{label}</span>
      <span className="text-text-primary font-medium text-xs text-right break-all">{value}</span>
    </div>
  );
}
