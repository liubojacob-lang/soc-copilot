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
  Briefcase,
  Sparkles,
} from "lucide-react";
import { loadAuthState } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/common/Button";
import { Card, BackButton } from "@/components/common";
import { Modal } from "@/components/common/Modal";
import { createCase } from "@/lib/api/cases";
import { AIAnalysisPanel } from "@/components/alerts/AIAnalysisPanel";
import { RootCauseSection } from "@/components/alerts/RootCauseSection";
import { RelatedAlertsPanel } from "@/components/alerts/RelatedAlertsPanel";
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

// 状态/严重度 → i18n 命名空间键（复用全局 status / severity，避免硬编码英文）
const STATUS_I18N_KEY: Record<string, string> = {
  new: "new",
  investigating: "investigating",
  resolved: "resolved",
  false_positive: "falsePositive",
  escalated: "escalated",
};

const SEVERITY_I18N_KEY: Record<string, string> = {
  critical: "critical",
  high: "high",
  medium: "medium",
  low: "low",
  info: "info",
  neutral: "neutral",
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
                className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-mono bg-surface-ground text-text-primary rounded-lg border border-border-subtle shadow-subtle"
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
    created: <Activity className="w-3.5 h-3.5 text-text-link" />,
    status_changed: <RefreshCw className="w-3.5 h-3.5 text-status-warning-fg" />,
    assigned: <User className="w-3.5 h-3.5 text-ai-fg" />,
    enriched: <Shield className="w-3.5 h-3.5 text-status-success-fg" />,
    correlated: <Link className="w-3.5 h-3.5 text-ai-fg" />,
    escalated: <AlertTriangle className="w-3.5 h-3.5 text-severity-critical-fg" />,
    resolved: <CheckCircle className="w-3.5 h-3.5 text-status-success-fg" />,
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
          <div className="absolute left-0 top-1 flex items-center justify-center w-7 h-7 rounded-full bg-surface-ground border border-border-subtle shadow-subtle">
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
                <span className="text-[11px] text-text-secondary">
                  {t("timelineBy", { user: event.user })}
                </span>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Entities ───────────────────────────────────────────

/**
 * 从真实告警字段推导「涉及哪些实体」。不做推断、不做补全：
 * 字段为空即不展示该实体，全部为空则显示明确的空态。
 */
function EntitiesSection({ alert }: { alert: SecurityAlertItem }) {
  const t = useTranslations("alerts.detail");

  const groups: Array<{ kind: string; icon: React.ReactNode; items: string[] }> = [
    {
      kind: t("entityHost"),
      icon: <Server className="w-3.5 h-3.5" />,
      items: [alert.agent_name, alert.agent_id].filter(Boolean) as string[],
    },
    {
      kind: t("entityIp"),
      icon: <Globe className="w-3.5 h-3.5" />,
      items: [alert.source_ip, alert.destination_ip, alert.agent_ip].filter(Boolean) as string[],
    },
    {
      kind: t("entitySource"),
      icon: <Activity className="w-3.5 h-3.5" />,
      items: [alert.source].filter(Boolean) as string[],
    },
    {
      kind: t("entityRule"),
      icon: <Tag className="w-3.5 h-3.5" />,
      items: [alert.rule_id].filter(Boolean) as string[],
    },
  ].filter((g) => g.items.length > 0);

  if (groups.length === 0) {
    return <p className="text-xs italic text-text-muted">{t("entityNone")}</p>;
  }

  return (
    <div className="space-y-3">
      {groups.map((group) => (
        <div key={group.kind}>
          <h4 className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase text-text-secondary">
            {group.icon} {group.kind}
          </h4>
          <div className="flex flex-wrap gap-1.5">
            {group.items.map((value) => (
              <span
                key={value}
                className="inline-flex items-center gap-1.5 rounded-lg border border-border-subtle bg-surface-ground px-2.5 py-1 font-mono text-xs text-text-primary"
              >
                {value}
              </span>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

// ── MITRE ATT&CK ───────────────────────────────────────

/**
 * 优先渲染结构化的 mitre_tactics；缺失时退化为后端返回的 rule_mitre 原始字符串；
 * 两者都缺失则不渲染该区块（而不是画一张空表）。
 */
function MitreSection({
  tactics,
  fallback,
}: {
  tactics?: SecurityAlertItem["mitre_tactics"];
  fallback?: string | null;
}) {
  const t = useTranslations("alerts.detail");

  if (tactics && tactics.length > 0) {
    return (
      <div className="space-y-3">
        {tactics.map((m) => (
          <div key={m.tactic}>
            <p className="text-xs font-medium text-text-primary">{m.tactic}</p>
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {(m.techniques ?? []).map((tech) => (
                <span
                  key={tech}
                  className="rounded border border-border-subtle bg-surface-hover px-1.5 py-0.5 font-mono text-[11px] text-text-secondary"
                >
                  {tech}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (fallback) {
    return <p className="font-mono text-xs text-text-secondary">{fallback}</p>;
  }

  return null;
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
          className="flex-1 px-3 py-2 text-xs sm:text-sm border border-border-default rounded-lg bg-surface-input text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent-500/20 focus:border-accent-600 transition-all"
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
//
// 设计规则（对应 UI设计优化方案 P0-2）：
//
//  1. 全屏只保留 **一个实心主按钮** —— 状态机的"前进"动作，也就是最高频操作。
//     主按钮统一用 accent（蓝），因为蓝色在本产品里的语义是"可操作"，
//     不承载任何严重度含义；状态语义由上方 Badge 承载。
//
//  2. "升级"是正常的、负责任的分诊动作，**绝不复用 danger 红**。
//     红色在全站只代表"严重/失败"（与 --sev-critical 同值），
//     把它涂在"升级"上等于告诉操作员"别点这个"——压制的正是应当鼓励的行为。
//
//  3. 次级操作一律中性描边。语义色只上图标与文字，不上整块填色，
//     避免多个彩色按钮互相争夺注意力、把权重与操作频次弄反。
//
//  4. 终态动作（已解决 / 误报）单击不可逆，统一走二次确认后才提交。

/** 状态机里唯一的"前进"动作：每个状态至多一个 */
const ADVANCE_ACTION: Record<string, string | undefined> = {
  new: "investigating",
  investigating: "resolved",
  escalated: "resolved",
};

/** 动作文案 —— 用动词短语描述"点了会发生什么"，不复述状态名 */
const ACTION_I18N_KEY: Record<string, string> = {
  investigating: "actionInvestigating",
  resolved: "actionResolved",
  false_positive: "actionFalsePositive",
  escalated: "actionEscalated",
  new: "actionReopen",
};

/** 终态动作：不可逆，需二次确认 */
const TERMINAL_STATUSES = new Set(["resolved", "false_positive"]);

function actionIcon(status: string, className: string): React.ReactNode {
  switch (status) {
    case "investigating":
      return <Activity className={className} />;
    case "resolved":
      return <CheckCircle className={className} />;
    case "false_positive":
      return <XCircle className={className} />;
    // 升级 = 呈报/转派，是正向流转，用 Send 而不是警告三角
    case "escalated":
      return <Send className={className} />;
    default:
      return <RotateCcw className={className} />;
  }
}

function TriagePanel({
  currentStatus,
  onStatusChange,
  onCreateCase,
  isUpdating,
}: {
  currentStatus?: string;
  onStatusChange: (status: string) => void;
  onCreateCase?: () => void;
  isUpdating: boolean;
}) {
  const t = useTranslations("alerts.detail");
  const tCommon = useTranslations("common");
  const tStatus = useTranslations("status");
  const status = currentStatus || "new";
  const transitions = STATUS_TRANSITIONS[status] || [];
  const statusLabel = (s: string) => tStatus(STATUS_I18N_KEY[s] || "unknown");
  const actionLabel = (s: string) => t(ACTION_I18N_KEY[s] as never) as string;

  const [pendingConfirm, setPendingConfirm] = useState<string | null>(null);

  const advance = ADVANCE_ACTION[status];
  const secondaries = transitions.filter((s) => s !== advance);

  const run = (next: string) => {
    if (next === "escalated" && onCreateCase) {
      onCreateCase();
    } else {
      onStatusChange(next);
    }
  };

  const request = (next: string) => {
    if (TERMINAL_STATUSES.has(next)) setPendingConfirm(next);
    else run(next);
  };

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
            {statusLabel(status)}
          </Badge>
        </div>

        {/* 唯一主操作 —— 状态机的"前进"动作 */}
        {advance && (
          <Button
            onClick={() => request(advance)}
            disabled={isUpdating}
            size="md"
            variant="primary"
            className="w-full justify-center text-xs font-semibold"
            leftIcon={actionIcon(advance, "w-4 h-4")}
          >
            {actionLabel(advance)}
          </Button>
        )}

        {/* 次级操作 —— 中性描边，不做彩色填充 */}
        {secondaries.length > 0 && (
          <div className={cn("grid gap-2", secondaries.length > 1 ? "grid-cols-2" : "grid-cols-1")}>
            {secondaries.map((nextStatus) => (
              <Button
                key={nextStatus}
                onClick={() => request(nextStatus)}
                disabled={isUpdating}
                size="sm"
                variant="outline"
                className="w-full justify-center text-xs font-medium text-text-secondary"
                leftIcon={actionIcon(nextStatus, "w-3.5 h-3.5 text-text-tertiary")}
              >
                {actionLabel(nextStatus)}
              </Button>
            ))}
          </div>
        )}

        {/* 状态机说明 —— 降低"该点哪个"的决策成本 */}
        <p className="text-[11px] leading-relaxed text-text-tertiary">{t("triageHint")}</p>
      </div>

      {/* 终态动作二次确认 */}
      <Modal
        open={pendingConfirm !== null}
        onClose={() => setPendingConfirm(null)}
        title={t("confirmStatusTitle")}
        size="sm"
        footer={
          <div className="flex justify-end gap-2">
            <Button variant="ghost" size="sm" onClick={() => setPendingConfirm(null)}>
              {tCommon("cancel")}
            </Button>
            <Button
              variant="primary"
              size="sm"
              isLoading={isUpdating}
              onClick={() => {
                const next = pendingConfirm;
                setPendingConfirm(null);
                if (next) run(next);
              }}
            >
              {tCommon("confirm")}
            </Button>
          </div>
        }
      >
        <p className="text-sm text-text-secondary">
          {t("confirmStatusBody", { status: pendingConfirm ? statusLabel(pendingConfirm) : "" })}
        </p>
      </Modal>
    </Card>
  );
}

// ── Related Cases Panel ────────────────────────────────

function RelatedCasesPanel({
  cases,
}: {
  cases?: Array<{
    id: string;
    title: string;
    severity: string;
    status: string;
    created_at?: string | null;
  }>;
}) {
  const t = useTranslations("alerts.detail");
  return (
    <Card className="p-4 sm:p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold tracking-tight text-text-primary flex items-center gap-2">
          <Briefcase className="w-4 h-4 text-accent-600 dark:text-accent-400" />
          <span>{t("relatedCasesTitle") || "关联事件工单"}</span>
          {cases && cases.length > 0 && (
            <span className="px-1.5 py-0.2 text-[11px] bg-accent-500/20 text-accent-600 rounded-full font-semibold">
              {cases.length}
            </span>
          )}
        </h3>
      </div>

      {/* 这里此前还有一个「升级为工单」按钮，与页头那个是**同一个动作**，
          却用了两种权重（页头实心主按钮 / 卡片描边小按钮）。
          同一动作在同一屏出现两次、且主次不一，用户会以为它们是两件事。
          现在卡片只做"结果展示"，唯一入口收敛到页头。 */}
      {!cases || cases.length === 0 ? (
        <div className="py-2">
          <p className="text-xs text-text-tertiary">
            {t("noRelatedCases") || "当前告警暂未关联任何事件工单"}
          </p>
          <p className="mt-1 text-[11px] text-text-muted">{t("noRelatedCasesHint")}</p>
        </div>
      ) : (
        <div className="space-y-2">
          {cases.map((c) => (
            <a
              key={c.id}
              href={`/cases/${c.id}`}
              className="block p-2.5 rounded-lg border border-border-subtle bg-surface-ground hover:border-accent-500/50 hover:bg-surface-hover transition-colors"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-medium text-text-primary truncate">{c.title}</span>
                <Badge size="xs" severity={c.severity as any}>
                  {c.severity}
                </Badge>
              </div>
              <div className="flex items-center gap-2 mt-1 text-[11px] text-text-muted">
                <span className="capitalize">{c.status}</span>
              </div>
            </a>
          ))}
        </div>
      )}
    </Card>
  );
}

// ── Create Case Modal ──────────────────────────────────

interface CreateCaseModalProps {
  open: boolean;
  onClose: () => void;
  alert: {
    id: number | string;
    title: string;
    description?: string | null;
    severity?: string | null;
    source?: string | null;
  };
  onSuccess: (caseId: string) => void;
}

function CreateCaseModal({ open, onClose, alert, onSuccess }: CreateCaseModalProps) {
  const t = useTranslations("alerts.detail");
  const tCommon = useTranslations("common");
  const [title, setTitle] = useState(`[Alert #${alert.id}] ${alert.title}`);
  const [description, setDescription] = useState(
    alert.description || `Escalated from security alert #${alert.id} (${alert.source || "unknown"})`
  );
  const [severity, setSeverity] = useState<"critical" | "high" | "medium" | "low">(
    (["critical", "high", "medium", "low"].includes((alert.severity || "").toLowerCase())
      ? (alert.severity || "").toLowerCase()
      : "medium") as any
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setTitle(`[Alert #${alert.id}] ${alert.title}`);
      setDescription(
        alert.description ||
          `Escalated from security alert #${alert.id} (${alert.source || "unknown"})`
      );
      setSeverity(
        (["critical", "high", "medium", "low"].includes((alert.severity || "").toLowerCase())
          ? (alert.severity || "").toLowerCase()
          : "medium") as any
      );
      setError(null);
    }
  }, [open, alert]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const created = await createCase({
        title: title.trim(),
        description: description.trim() || undefined,
        severity,
        alert_ids: [alert.id],
      });
      onSuccess(created.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create case");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={
        <div className="flex items-center gap-2">
          <Briefcase className="w-5 h-5 text-accent-600 dark:text-accent-400" />
          <span>{t("createCaseModalTitle") || "升级为事件调查工单"}</span>
        </div>
      }
      size="lg"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="p-3 text-xs bg-rose-50 border border-rose-200 text-rose-700 dark:bg-rose-900/20 dark:border-rose-800 dark:text-rose-300 rounded-lg">
            {error}
          </div>
        )}

        <div>
          <label className="block text-xs font-semibold text-text-secondary mb-1">
            {tCommon("title") || "工单标题"} *
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
            className="w-full px-3 py-2 text-xs sm:text-sm border border-border-default rounded-lg bg-surface-input text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-500/20 focus:border-accent-600"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-text-secondary mb-1">
            {tCommon("severity") || "严重级别"}
          </label>
          <select
            value={severity}
            onChange={(e) => setSeverity(e.target.value as any)}
            className="w-full px-3 py-2 text-xs sm:text-sm border border-border-default rounded-lg bg-surface-input text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-500/20 focus:border-accent-600"
          >
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
        </div>

        <div>
          <label className="block text-xs font-semibold text-text-secondary mb-1">
            {tCommon("description") || "调查描述"}
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={4}
            className="w-full px-3 py-2 text-xs sm:text-sm border border-border-default rounded-lg bg-surface-input text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-500/20 focus:border-accent-600"
          />
        </div>

        <div className="p-3 bg-surface-ground rounded-lg border border-border-subtle text-xs text-text-muted flex items-center gap-2">
          <Info className="w-4 h-4 text-accent-500 shrink-0" />
          <span>
            {t("createCaseHint") || `此工单将自动关联告警 #${alert.id}，并录入事件调查时间线。`}
          </span>
        </div>

        <div className="flex justify-end gap-2 pt-2 border-t border-border-subtle">
          <Button variant="secondary" size="sm" type="button" onClick={onClose} disabled={loading}>
            {tCommon("cancel") || "取消"}
          </Button>
          <Button variant="primary" size="sm" type="submit" isLoading={loading}>
            {t("createCaseConfirm") || "确认升级工单"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

// ── Page Component ──────────────────────────────────────

export default function AlertDetailPage() {
  const format = useFormatter();
  const t = useTranslations("alerts.detail");
  const tCommon = useTranslations("common");
  const tStatus = useTranslations("status");
  const tSeverity = useTranslations("severity");
  const params = useParams();
  const router = useRouter();
  const { showToast } = useToast();
  const alertId = params.id as string;

  const statusLabel = useCallback(
    (s?: string | null) => tStatus(STATUS_I18N_KEY[s || "new"] || "unknown"),
    [tStatus]
  );
  const severityLabel = useCallback(
    (s?: string | null) => tSeverity(SEVERITY_I18N_KEY[s || "neutral"] || "neutral"),
    [tSeverity]
  );

  const [mounted, setMounted] = useState(false);
  const [activeTab, setActiveTab] = useState<"overview" | "timeline" | "notes" | "rootCause">(
    "overview"
  );
  const [showCreateCaseModal, setShowCreateCaseModal] = useState(false);

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

  // ── 概览字段清单 ─────────────────────────────────────
  // 先把字段声明成数据再渲染，才能把"有值/无值"分开处理：
  // 有值的进网格，无值的折叠为一行计数，不再各占一个等宽槽位。
  const overviewFields = [
    { label: t("fieldSourceIP"), value: alert?.source_ip, mono: true },
    { label: t("fieldDestIP"), value: alert?.destination_ip, mono: true },
    { label: t("fieldAgent"), value: alert?.agent_name },
    { label: t("fieldRuleID"), value: alert?.rule_id, mono: true },
    { label: t("fieldEventType"), value: alert?.event_type },
    { label: t("fieldProtocol"), value: alert?.protocol },
    { label: t("fieldRuleLevel"), value: alert?.rule_level?.toString() },
    // 有结构化 MITRE 时改由下方专门区块呈现，避免重复
    ...(alert && !alert.mitre_tactics?.length
      ? [{ label: t("fieldMITRE"), value: alert.rule_mitre || undefined, mono: false }]
      : []),
  ];
  const overviewEmptyCount = overviewFields.filter((f) => !f.value).length;

  // Status change handler
  const handleStatusChange = useCallback(
    async (newStatus: string) => {
      if (!alert?.id) return;
      try {
        await updateAlert.mutateAsync({
          id: alert.id,
          payload: { status: newStatus },
        });
        showToast(t("statusChanged", { status: statusLabel(newStatus) }), "success");
      } catch (err) {
        showToast(
          t("statusChangeFailed", { error: err instanceof Error ? err.message : "Unknown" }),
          "error"
        );
      }
    },
    [alert?.id, updateAlert, showToast, t, statusLabel]
  );

  // Add note handler
  const handleAddNote = useCallback(
    async (content: string) => {
      if (!alert?.id) return;
      try {
        await addNote.mutateAsync({ alertId: alert.id, content });
        showToast(t("noteAdded"), "success");
      } catch {
        showToast(t("noteAddFailed"), "error");
      }
    },
    [alert?.id, addNote, showToast, t]
  );

  if (!mounted) return null;

  // ── Loading ──────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="min-h-screen bg-surface-ground">
        <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <LoadingState isLoading={true} type="skeleton" skeletonType="card" />
        </div>
      </div>
    );
  }

  // ── Error / Not Found ────────────────────────────────
  if (error || !alert) {
    return (
      <div className="min-h-screen bg-surface-ground">
        <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-8">
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
      {/* Header — Linear/Vercel style */}
      <div className="bg-surface-card border-b border-border-subtle shadow-subtle">
        <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 pt-3 pb-4">
          {/* Ghost breadcrumb back link */}
          <BackButton
            fallbackUrl="/alerts"
            label={tCommon("back")}
            variant="ghost"
            className="mb-2 -ml-1"
          />

          {/* Title + badges + refresh */}
          <div className="flex items-start gap-3">
            <div className="flex-1 min-w-0">
              {/* Title inline with severity/status badges */}
              <div className="flex items-center gap-2 flex-wrap">
                <h1 className="text-lg sm:text-xl font-bold tracking-tight text-text-primary leading-snug">
                  {alert.title}
                </h1>
                <Badge severity={mapSeverityBadge(alert.severity)} variant="pill">
                  {severityLabel(alert.severity)}
                </Badge>
                <Badge severity={mapStatusBadge(alert.status)} variant="pill">
                  {statusLabel(alert.status)}
                </Badge>
              </div>
              {/* Meta info row */}
              <div className="flex flex-wrap items-center gap-2 mt-1.5 text-xs text-text-muted">
                <span className="flex items-center gap-1 font-mono">
                  <Server className="w-3.5 h-3.5" />
                  {alert.source || t("unknownSource")}
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

            {/* Actions — top-right, aligned with title row */}
            <div className="flex items-center gap-2">
              <Button
                variant="primary"
                size="sm"
                onClick={() => setShowCreateCaseModal(true)}
                leftIcon={<Briefcase className="w-4 h-4" />}
                className="bg-accent-600 hover:bg-accent-700 text-white"
              >
                <span>{t("createCase") || "升级为工单"}</span>
              </Button>
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

            {/* AI Pre-triage Card (T2.5) */}
            {Boolean((alert.raw_data as any)?.pipeline?.ai_triage) && (
              <Card className="p-5 border-purple-200 dark:border-purple-900/50 bg-gradient-to-r from-purple-50/50 to-transparent dark:from-purple-950/20">
                <div className="flex items-center justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                    <h3 className="text-sm font-semibold tracking-tight text-text-primary">
                      AI 自动化分诊结论
                    </h3>
                    <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-purple-100 text-purple-800 dark:bg-purple-900/60 dark:text-purple-200">
                      后台预分诊
                    </span>
                  </div>
                  {Boolean((alert.raw_data as any)?.pipeline?.ai_suggested_severity) && (
                    <span className="text-xs text-text-muted">
                      建议严重度:{" "}
                      <span className="font-semibold uppercase text-purple-700 dark:text-purple-300">
                        {(alert.raw_data as any).pipeline.ai_suggested_severity}
                      </span>
                    </span>
                  )}
                </div>
                <p className="text-xs sm:text-sm text-text-secondary leading-relaxed whitespace-pre-wrap">
                  {(alert.raw_data as any)?.pipeline?.ai_triage?.summary}
                </p>
                <div className="flex items-center gap-4 mt-3 text-[11px] text-text-muted">
                  {Boolean((alert.raw_data as any)?.pipeline?.ai_triage?.completed_at) && (
                    <span>
                      分诊时间:{" "}
                      {new Date(
                        (alert.raw_data as any).pipeline.ai_triage.completed_at
                      ).toLocaleString()}
                    </span>
                  )}
                  {Boolean((alert.raw_data as any)?.pipeline?.ai_triage?.model_used) && (
                    <span>模型: {(alert.raw_data as any).pipeline.ai_triage.model_used}</span>
                  )}
                </div>
              </Card>
            )}

            {/* AI Analysis — "AI 怎么看 / 我该做什么"（真实调用 analyze-alert，不预置结论） */}
            <AIAnalysisPanel
              alert={{
                id: alert.id,
                title: alert.title,
                description: alert.description,
                source: alert.source,
                severity: alert.severity,
                raw_log: (alert as any).raw_log || (alert as any).raw_data || null,
              }}
              onAddNote={handleAddNote}
            />

            {/* Tabs: Overview / Timeline / Notes */}
            <Card className="overflow-hidden">
              {/* Tab Header */}
              <div className="flex border-b border-border-subtle px-3 bg-surface-ground/40">
                {[
                  { key: "overview", label: t("tabOverview") },
                  { key: "timeline", label: t("tabTimeline") },
                  { key: "notes", label: t("tabNotes") },
                  { key: "rootCause", label: t("tabRootCause") },
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
                    {/* Technical Details Grid
                        此前 8 个字段**全部**渲染，其中 5 个是 N/A，却仍各占一个等宽槽位
                        —— 用户必须"扫过 5 个 N/A 才能找到 3 个真值"。
                        现在只渲有值的字段，空字段折叠成一行"另有 N 项无数据"。 */}
                    <div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs sm:text-sm">
                        {overviewFields
                          .filter((f) => f.value)
                          .map((f) => (
                            <DetailItem
                              key={f.label}
                              label={f.label}
                              value={f.value}
                              mono={f.mono}
                            />
                          ))}
                      </div>
                      {overviewEmptyCount > 0 && (
                        <p className="mt-3 text-[11px] text-text-muted">
                          {t("overviewEmptyFields", { count: overviewEmptyCount })}
                        </p>
                      )}
                    </div>

                    {/* Entities — 从真实字段推导的实体清单 */}
                    <div className="pt-4 border-t border-border-subtle">
                      <h4 className="text-sm font-semibold tracking-tight text-text-primary mb-3 flex items-center gap-2">
                        <Globe className="w-4 h-4 text-accent-500" />
                        {t("entitiesTitle")}
                      </h4>
                      <EntitiesSection alert={alert} />
                    </div>

                    {/* MITRE ATT&CK — 结构化呈现（缺失时自动隐藏） */}
                    {(alert.mitre_tactics?.length || alert.rule_mitre) && (
                      <div className="pt-4 border-t border-border-subtle">
                        <h4 className="text-sm font-semibold tracking-tight text-text-primary mb-3 flex items-center gap-2">
                          <Shield className="w-4 h-4 text-accent-500" />
                          {t("mitreTitle")}
                        </h4>
                        <MitreSection
                          tactics={alert.mitre_tactics}
                          fallback={alert.rule_mitre || undefined}
                        />
                      </div>
                    )}

                    {/* Tags — 仅在后端提供时展示 */}
                    {alert.tags && alert.tags.length > 0 && (
                      <div className="pt-4 border-t border-border-subtle">
                        <h4 className="text-xs font-semibold text-text-secondary uppercase mb-2">
                          {t("tagsTitle")}
                        </h4>
                        <div className="flex flex-wrap gap-1.5">
                          {alert.tags.map((tag) => (
                            <Badge key={tag} severity="neutral" size="xs">
                              {tag}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}

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
                          {t("lookupVirusTotal", { ip: alert.source_ip })}
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

                {activeTab === "rootCause" && <RootCauseSection alertId={alert.id} />}
              </div>
            </Card>
          </div>

          {/* Sidebar Column (1/3) */}
          <div className="space-y-5">
            {/* Triage Panel */}
            <TriagePanel
              currentStatus={alert.status}
              onStatusChange={handleStatusChange}
              onCreateCase={() => setShowCreateCaseModal(true)}
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
                  <div className="text-2xl font-bold tracking-tight text-severity-critical-fg tabular-nums">
                    {alert.threat_score}
                  </div>
                  <div className="flex-1 h-2 bg-surface-ground rounded-full overflow-hidden border border-border-subtle">
                    <div
                      className={cn(
                        "h-full rounded-full transition-all",
                        alert.threat_score >= 80
                          ? "bg-severity-critical"
                          : alert.threat_score >= 50
                            ? "bg-severity-medium"
                            : "bg-status-success"
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

            {/* Related Cases — 关联事件调查工单（纯展示；创建入口在页头唯一一处） */}
            <RelatedCasesPanel cases={lifecycle?.related_cases} />

            {/* Related Alerts — 同一资产/源 IP 的其他告警（真实后端过滤，非编造关联度） */}
            <RelatedAlertsPanel
              alertId={alert.id}
              agentName={alert.agent_name}
              sourceIp={alert.source_ip}
              severityOf={mapSeverityBadge}
            />
          </div>
        </div>
      </div>

      {/* Create Case Modal */}
      {alert && (
        <CreateCaseModal
          open={showCreateCaseModal}
          onClose={() => setShowCreateCaseModal(false)}
          alert={{
            id: alert.id,
            title: alert.title,
            description: alert.description,
            severity: alert.severity,
            source: alert.source,
          }}
          onSuccess={(newCaseId) => {
            setShowCreateCaseModal(false);
            showToast(t("caseCreatedSuccess") || "已成功创建并升级为事件调查工单", "success");
            router.push(`/cases/${newCaseId}`);
          }}
        />
      )}
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
          // 尺寸统一交给父容器的 text-xs sm:text-sm —— 值一律同字号。
          // （此前 mono 分支额外加了 text-xs，导致同一网格里 IP 是 12px、
          //   其他值是 14px，视觉上像是两级信息。）
          "mt-0.5 text-text-primary font-medium",
          // 技术标识符（IP / 哈希 / 规则 ID）用等宽 + 等宽数字，
          // 逐位比对时字形宽度一致才数得清楚。
          mono && "font-mono tabular-nums",
          !value && "text-text-tertiary font-normal"
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
      {/* break-all 会在任意字符处断行（把日期、ID 切得看不出结构）；
          overflow-wrap:anywhere 只在放不下时才断，且配合 tabular-nums 让数字列对齐 */}
      <span className="text-right text-xs font-medium tabular-nums text-text-primary [overflow-wrap:anywhere]">
        {value}
      </span>
    </div>
  );
}
