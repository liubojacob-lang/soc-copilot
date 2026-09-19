"use client";

import React, { useState, useEffect, useRef } from "react";
import { useTranslations, useFormatter } from "next-intl";
import { Link } from "@/i18n/navigation";
import {
  X,
  Shield,
  Clock,
  Activity,
  Layers,
  Copy,
  Check,
  ExternalLink,
  Loader2,
  User,
  Server,
  Globe,
  AlertTriangle,
  CheckCircle2,
  ArrowRight,
  FileText,
  Radio,
  Tag,
  Share2,
} from "lucide-react";
import { Badge, type Severity } from "@/components/ui/Badge";
import { useFocusTrap } from "@/hooks/useFocusTrap";

export interface Incident {
  id: string;
  title: string;
  description: string | null;
  severity: string;
  attack_type: string | null;
  confidence_score: number;
  raw_event_count: number;
  common_entities: Record<string, any>;
  first_seen: string;
  last_seen: string;
  status: string;
  risk_score: number;
  created_at: string;
}

interface IncidentDetailsDrawerProps {
  incident: Incident | null;
  isOpen: boolean;
  onClose: () => void;
  onStatusChange?: (incidentId: string, newStatus: string) => Promise<void>;
}

const ATTACK_TYPE_LABELS: Record<string, string> = {
  ransomware: "勒索软件 (Ransomware)",
  account_takeover: "凭据失陷与账户接管 (Account Takeover)",
  brute_force: "分布式爆破集群 (Brute Force)",
  c2_communication: "C2 远控信道 (C2 Communication)",
  data_exfiltration: "敏感数据外发 (Data Exfiltration)",
  privilege_escalation: "权限提升 (Privilege Escalation)",
  lateral_movement: "内网横向移动 (Lateral Movement)",
};

function formatDuration(firstSeen: string, lastSeen: string): string {
  try {
    const start = new Date(firstSeen).getTime();
    const end = new Date(lastSeen).getTime();
    const diffMs = Math.abs(end - start);
    const diffSec = Math.floor(diffMs / 1000);
    if (diffSec < 60) return `${diffSec} 秒`;
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `${diffMin} 分钟`;
    const diffHours = Math.floor(diffMin / 60);
    const remMin = diffMin % 60;
    if (diffHours < 24) return `${diffHours} 小时 ${remMin} 分钟`;
    const diffDays = Math.floor(diffHours / 24);
    const remHours = diffHours % 24;
    return `${diffDays} 天 ${remHours} 小时`;
  } catch {
    return "—";
  }
}

function normalizeSeverity(sev: string): Severity {
  switch (sev?.toLowerCase()) {
    case "critical":
      return "critical";
    case "high":
      return "high";
    case "medium":
      return "medium";
    case "low":
      return "low";
    default:
      return "info";
  }
}

export function IncidentDetailsDrawer({
  incident,
  isOpen,
  onClose,
  onStatusChange,
}: IncidentDetailsDrawerProps) {
  const t = useTranslations("correlation");
  const format = useFormatter();

  const [copiedId, setCopiedId] = useState(false);
  const [copiedEntity, setCopiedEntity] = useState<string | null>(null);
  const [selectedStatus, setSelectedStatus] = useState<string>("");
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);
  const [statusFeedback, setStatusFeedback] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);

  // Sync selectedStatus when incident changes
  useEffect(() => {
    if (incident) {
      setSelectedStatus(incident.status);
      setStatusFeedback(null);
    }
  }, [incident]);

  // Lock background scroll when drawer is open
  useEffect(() => {
    if (!isOpen) return;
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prevOverflow;
    };
  }, [isOpen]);

  const drawerRef = useRef<HTMLDivElement>(null);
  useFocusTrap(isOpen && !!incident, onClose, drawerRef);

  if (!isOpen || !incident) return null;

  const handleCopyId = () => {
    navigator.clipboard.writeText(incident.id);
    setCopiedId(true);
    setTimeout(() => setCopiedId(false), 2000);
  };

  const handleCopyText = (val: string, key: string) => {
    navigator.clipboard.writeText(val);
    setCopiedEntity(key);
    setTimeout(() => setCopiedEntity(null), 2000);
  };

  const handleUpdateStatus = async () => {
    if (!onStatusChange || selectedStatus === incident.status) return;
    setIsUpdatingStatus(true);
    setStatusFeedback(null);
    try {
      await onStatusChange(incident.id, selectedStatus);
      setStatusFeedback({
        type: "success",
        text: t("statusUpdated"),
      });
      setTimeout(() => setStatusFeedback(null), 3000);
    } catch (err: any) {
      setStatusFeedback({
        type: "error",
        text: err?.message || t("statusUpdateFailed"),
      });
    } finally {
      setIsUpdatingStatus(false);
    }
  };

  const severityTone = normalizeSeverity(incident.severity);
  const entities = incident.common_entities || {};
  const sourceIps: string[] = Array.isArray(entities.source_ips) ? entities.source_ips : [];
  const targetHosts: string[] = Array.isArray(entities.hosts) ? entities.hosts : [];
  const users: string[] = Array.isArray(entities.users) ? entities.users : [];
  const destinationIps: string[] = Array.isArray(entities.destination_ips)
    ? entities.destination_ips
    : [];

  const otherEntityEntries = Object.entries(entities).filter(
    ([k]) => !["source_ips", "hosts", "users", "destination_ips"].includes(k)
  );

  const hasAnyEntity =
    sourceIps.length > 0 ||
    targetHosts.length > 0 ||
    users.length > 0 ||
    destinationIps.length > 0 ||
    otherEntityEntries.length > 0;

  const displayAttackType =
    (incident.attack_type && ATTACK_TYPE_LABELS[incident.attack_type]) ||
    incident.attack_type ||
    "多源告警复合关联 (Correlated Cluster)";

  const durationText = formatDuration(incident.first_seen, incident.last_seen);

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end bg-black/40 backdrop-blur-sm animate-in fade-in duration-200"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={drawerRef}
        className="w-full max-w-2xl bg-surface-card border-l border-border-subtle shadow-2xl h-full flex flex-col overflow-hidden animate-in slide-in-from-right duration-250"
        role="dialog"
        aria-modal="true"
        aria-labelledby="incident-details-title"
        tabIndex={-1}
        onMouseDown={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-6 border-b border-border-subtle shrink-0 bg-surface-card">
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-2 min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <Badge severity={severityTone} dot size="sm">
                  {t(incident.severity as any) || incident.severity.toUpperCase()}
                </Badge>
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border border-border-subtle bg-surface-hover text-text-secondary capitalize">
                  <Radio className="w-3 h-3 text-accent-600 animate-pulse" />
                  {incident.status}
                </span>
                <span className="text-xs text-text-muted font-mono">
                  {t("aggregatedEvents")}: {incident.raw_event_count}
                </span>
              </div>
              <h2
                id="incident-details-title"
                className="text-lg font-bold text-text-primary leading-snug break-words"
              >
                {incident.title}
              </h2>
              <div className="flex flex-wrap items-center gap-3 text-xs text-text-muted">
                <div className="flex items-center gap-1 font-mono">
                  <span>{t("incidentId")}:</span>
                  <span className="truncate max-w-xs">{incident.id}</span>
                  <button
                    type="button"
                    onClick={handleCopyId}
                    title="复制事件 ID"
                    aria-label="复制事件 ID"
                    className="p-1 hover:text-text-primary transition-colors rounded hover:bg-surface-hover"
                  >
                    {copiedId ? (
                      <Check className="w-3 h-3 text-status-success-fg" />
                    ) : (
                      <Copy className="w-3 h-3" />
                    )}
                  </button>
                </div>
              </div>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-lg text-text-muted hover:text-text-primary hover:bg-surface-hover transition-colors shrink-0"
              aria-label="关闭详情"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Scrollable Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Top KPI Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="p-3.5 rounded-xl border border-border-subtle bg-surface-ground">
              <span className="text-xs text-text-muted font-medium block">{t("riskScore")}</span>
              <div className="mt-1.5 flex items-baseline gap-1.5">
                <span
                  className={`text-xl font-bold tabular-nums ${
                    incident.risk_score >= 80
                      ? "text-severity-critical-fg"
                      : incident.risk_score >= 50
                        ? "text-severity-high-fg"
                        : "text-text-primary"
                  }`}
                >
                  {incident.risk_score.toFixed(1)}
                </span>
                <span className="text-[10px] text-text-muted">/ 100</span>
              </div>
            </div>

            <div className="p-3.5 rounded-xl border border-border-subtle bg-surface-ground">
              <span className="text-xs text-text-muted font-medium block">
                {t("confidenceScore")}
              </span>
              <div className="mt-1.5 flex items-baseline gap-1.5">
                <span className="text-xl font-bold text-accent-600 dark:text-accent-400 tabular-nums">
                  {(incident.confidence_score * 100).toFixed(0)}%
                </span>
              </div>
            </div>

            <div className="p-3.5 rounded-xl border border-border-subtle bg-surface-ground">
              <span className="text-xs text-text-muted font-medium block">{t("events")}</span>
              <div className="mt-1.5 flex items-center gap-1.5">
                <Layers className="w-4 h-4 text-text-muted shrink-0" />
                <span className="text-xl font-bold text-text-primary tabular-nums">
                  {incident.raw_event_count}
                </span>
              </div>
            </div>

            <div className="p-3.5 rounded-xl border border-border-subtle bg-surface-ground">
              <span className="text-xs text-text-muted font-medium block">{t("duration")}</span>
              <div className="mt-1.5 flex items-center gap-1 text-xs font-semibold text-text-primary">
                <Clock className="w-3.5 h-3.5 text-text-muted shrink-0" />
                <span className="truncate">{durationText}</span>
              </div>
            </div>
          </div>

          {/* Attack Type Banner */}
          <div className="p-4 rounded-xl border border-border-subtle bg-surface-ground flex items-center justify-between gap-3">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-8 h-8 rounded-lg bg-accent-500/10 text-accent-600 dark:text-accent-400 flex items-center justify-center shrink-0">
                <Shield className="w-4 h-4" />
              </div>
              <div className="min-w-0">
                <span className="text-[11px] text-text-muted block font-medium">
                  {t("attackType")}
                </span>
                <p className="text-sm font-semibold text-text-primary truncate">
                  {displayAttackType}
                </p>
              </div>
            </div>
            <Link
              href="/threat-hunting"
              className="inline-flex items-center gap-1 text-xs font-medium text-accent-600 hover:text-accent-700 transition-colors whitespace-nowrap"
            >
              <span>{t("jumpToThreatIntel")}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          {/* Description */}
          {incident.description && (
            <div className="space-y-2">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-text-muted">
                {t("incidentDescription")}
              </h3>
              <div className="p-4 rounded-xl border border-border-subtle bg-surface-hover/30 text-xs text-text-secondary leading-relaxed">
                {incident.description}
              </div>
            </div>
          )}

          {/* Timeline & Window */}
          <div className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-text-muted">
              {t("timelineSection")}
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="p-3.5 rounded-xl border border-border-subtle bg-surface-ground flex items-center gap-3">
                <Clock className="w-4 h-4 text-text-muted shrink-0" />
                <div>
                  <span className="text-[11px] text-text-muted block">{t("firstSeen")}</span>
                  <span className="text-xs font-mono font-medium text-text-primary">
                    {format.dateTime(new Date(incident.first_seen), {
                      dateStyle: "medium",
                      timeStyle: "medium",
                    })}
                  </span>
                </div>
              </div>

              <div className="p-3.5 rounded-xl border border-border-subtle bg-surface-ground flex items-center gap-3">
                <Activity className="w-4 h-4 text-text-muted shrink-0" />
                <div>
                  <span className="text-[11px] text-text-muted block">{t("lastSeen")}</span>
                  <span className="text-xs font-mono font-medium text-text-primary">
                    {format.dateTime(new Date(incident.last_seen), {
                      dateStyle: "medium",
                      timeStyle: "medium",
                    })}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Common Entities */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-text-muted">
                {t("commonEntities")}
              </h3>
              <span className="text-xs text-text-muted">
                {hasAnyEntity ? "多源同质特征收敛" : t("noEntities")}
              </span>
            </div>

            <div className="space-y-3">
              {/* Source IPs */}
              {sourceIps.length > 0 && (
                <div className="p-3.5 rounded-xl border border-border-subtle bg-surface-ground space-y-2">
                  <span className="text-xs font-medium text-text-secondary flex items-center gap-1.5">
                    <Globe className="w-3.5 h-3.5 text-accent-600" />
                    {t("sourceIps")} ({sourceIps.length})
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {sourceIps.map((ip, idx) => (
                      <div
                        key={`sip-${idx}`}
                        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-border-subtle bg-surface-card text-xs font-mono font-medium text-text-primary"
                      >
                        <span>{ip}</span>
                        <button
                          type="button"
                          onClick={() => handleCopyText(ip, `sip-${idx}`)}
                          className="text-text-muted hover:text-text-primary p-0.5 rounded"
                          title="复制 IP"
                        >
                          {copiedEntity === `sip-${idx}` ? (
                            <Check className="w-3 h-3 text-status-success-fg" />
                          ) : (
                            <Copy className="w-3 h-3" />
                          )}
                        </button>
                        <Link
                          href={`/threat-intel`}
                          className="text-accent-600 hover:text-accent-700 ml-0.5"
                          title="在威胁情报中研判"
                        >
                          <ExternalLink className="w-3 h-3" />
                        </Link>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Target Hosts */}
              {targetHosts.length > 0 && (
                <div className="p-3.5 rounded-xl border border-border-subtle bg-surface-ground space-y-2">
                  <span className="text-xs font-medium text-text-secondary flex items-center gap-1.5">
                    <Server className="w-3.5 h-3.5 text-purple-600" />
                    {t("targetHosts")} ({targetHosts.length})
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {targetHosts.map((host, idx) => (
                      <div
                        key={`host-${idx}`}
                        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-border-subtle bg-surface-card text-xs font-mono font-medium text-text-primary"
                      >
                        <span>{host}</span>
                        <button
                          type="button"
                          onClick={() => handleCopyText(host, `host-${idx}`)}
                          className="text-text-muted hover:text-text-primary p-0.5 rounded"
                          title="复制主机名"
                        >
                          {copiedEntity === `host-${idx}` ? (
                            <Check className="w-3 h-3 text-status-success-fg" />
                          ) : (
                            <Copy className="w-3 h-3" />
                          )}
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Users */}
              {users.length > 0 && (
                <div className="p-3.5 rounded-xl border border-border-subtle bg-surface-ground space-y-2">
                  <span className="text-xs font-medium text-text-secondary flex items-center gap-1.5">
                    <User className="w-3.5 h-3.5 text-amber-600" />
                    {t("users")} ({users.length})
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {users.map((usr, idx) => (
                      <div
                        key={`user-${idx}`}
                        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-border-subtle bg-surface-card text-xs font-mono font-medium text-text-primary"
                      >
                        <span>{usr}</span>
                        <button
                          type="button"
                          onClick={() => handleCopyText(usr, `user-${idx}`)}
                          className="text-text-muted hover:text-text-primary p-0.5 rounded"
                          title="复制用户名"
                        >
                          {copiedEntity === `user-${idx}` ? (
                            <Check className="w-3 h-3 text-status-success-fg" />
                          ) : (
                            <Copy className="w-3 h-3" />
                          )}
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Destination IPs */}
              {destinationIps.length > 0 && (
                <div className="p-3.5 rounded-xl border border-border-subtle bg-surface-ground space-y-2">
                  <span className="text-xs font-medium text-text-secondary flex items-center gap-1.5">
                    <Globe className="w-3.5 h-3.5 text-emerald-600" />
                    {t("destinationIps")} ({destinationIps.length})
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {destinationIps.map((ip, idx) => (
                      <div
                        key={`dip-${idx}`}
                        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-border-subtle bg-surface-card text-xs font-mono font-medium text-text-primary"
                      >
                        <span>{ip}</span>
                        <button
                          type="button"
                          onClick={() => handleCopyText(ip, `dip-${idx}`)}
                          className="text-text-muted hover:text-text-primary p-0.5 rounded"
                          title="复制目标 IP"
                        >
                          {copiedEntity === `dip-${idx}` ? (
                            <Check className="w-3 h-3 text-status-success-fg" />
                          ) : (
                            <Copy className="w-3 h-3" />
                          )}
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Other entities */}
              {otherEntityEntries.map(([key, val], idx) => (
                <div
                  key={`other-${idx}`}
                  className="p-3.5 rounded-xl border border-border-subtle bg-surface-ground space-y-2"
                >
                  <span className="text-xs font-medium text-text-secondary capitalize flex items-center gap-1.5">
                    <Tag className="w-3.5 h-3.5 text-text-muted" />
                    {key.replace("_", " ")}
                  </span>
                  <div className="p-2.5 rounded-lg border border-border-subtle bg-surface-card font-mono text-xs text-text-primary overflow-x-auto">
                    {typeof val === "object" ? JSON.stringify(val, null, 2) : String(val)}
                  </div>
                </div>
              ))}

              {!hasAnyEntity && (
                <div className="p-6 rounded-xl border border-border-subtle bg-surface-ground text-center text-xs text-text-muted">
                  {t("noEntities")}
                </div>
              )}
            </div>
          </div>

          {/* Workflow & Status Management */}
          <div className="space-y-3 pt-2">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-text-muted">
              {t("workflowSection")}
            </h3>
            <div className="p-4 rounded-xl border border-border-subtle bg-surface-ground space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="space-y-0.5">
                  <span className="text-xs font-medium text-text-primary block">
                    {t("changeStatus")}
                  </span>
                  <span className="text-[11px] text-text-muted">
                    流转处置生命周期并同步写入安全审计记录
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <select
                    value={selectedStatus}
                    onChange={(e) => setSelectedStatus(e.target.value)}
                    disabled={isUpdatingStatus}
                    className="px-3 py-1.5 text-xs font-medium rounded-lg border border-border-subtle bg-surface-card text-text-primary focus:outline-none focus:border-accent-500 transition-colors"
                  >
                    <option value="open">{t("statusOpen")}</option>
                    <option value="investigating">{t("statusInvestigating")}</option>
                    <option value="resolved">{t("statusResolved")}</option>
                    <option value="false_positive">{t("statusFalsePositive")}</option>
                    <option value="closed">{t("statusClosed")}</option>
                  </select>

                  <button
                    type="button"
                    onClick={handleUpdateStatus}
                    disabled={isUpdatingStatus || selectedStatus === incident.status}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-accent-600 hover:bg-accent-700 disabled:opacity-50 text-white rounded-lg text-xs font-semibold shadow-sm transition-colors cursor-pointer"
                  >
                    {isUpdatingStatus ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        <span>{t("updatingIncident")}</span>
                      </>
                    ) : (
                      <>
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>{t("updateIncident")}</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              {statusFeedback && (
                <div
                  className={`p-2.5 rounded-lg text-xs flex items-center gap-2 ${
                    statusFeedback.type === "success"
                      ? "bg-status-success-bg text-status-success-fg border border-status-success-border"
                      : "bg-status-failed-bg text-status-failed-fg border border-status-failed-border"
                  }`}
                >
                  {statusFeedback.type === "success" ? (
                    <CheckCircle2 className="w-4 h-4 shrink-0" />
                  ) : (
                    <AlertTriangle className="w-4 h-4 shrink-0" />
                  )}
                  <span>{statusFeedback.text}</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="p-4 border-t border-border-subtle bg-surface-card flex flex-wrap items-center justify-between gap-3 shrink-0">
          <div className="flex items-center gap-2">
            <Link
              href="/alerts"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border-subtle text-text-secondary hover:bg-surface-hover hover:text-text-primary text-xs font-medium transition-colors"
            >
              <FileText className="w-3.5 h-3.5" />
              <span>{t("jumpToAlerts")}</span>
            </Link>
            <Link
              href="/cases"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-accent-50 text-accent-700 dark:bg-accent-950/40 dark:text-accent-300 hover:bg-accent-100 dark:hover:bg-accent-900/60 text-xs font-medium transition-colors"
            >
              <Share2 className="w-3.5 h-3.5" />
              <span>{t("jumpToCases")}</span>
            </Link>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg border border-border-subtle text-text-secondary hover:bg-surface-hover text-xs font-medium transition-colors"
          >
            {t("cancel")}
          </button>
        </div>
      </div>
    </div>
  );
}
