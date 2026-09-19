"use client";

/**
 * LogTimelineAnalyzer — Investigation tool backed by the real
 * POST /api/v1/build-timeline endpoint (backend/routers/timeline.py).
 *
 * Analyst pastes raw log content; the AI returns a structured event
 * timeline, top suspicious events, extracted IOCs, impact analysis and
 * threat-intel enrichment. Degraded-mode responses are surfaced honestly.
 */

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import {
  Activity,
  AlertTriangle,
  Clock,
  FileSearch,
  Globe,
  Network,
  RefreshCw,
  ShieldAlert,
  Sparkles,
  Hash,
  ShieldCheck,
} from "lucide-react";

import {
  buildTimeline,
  type TimelineResponse,
  type IOCsGrouped,
  type ImpactAnalysis,
  type ThreatIntelAnalysisTL,
  type ThreatIntelItemTL,
} from "@/lib/api/alerts";
import { Badge, type Severity } from "@/components/ui/Badge";
import { Button } from "@/components/common/Button";
import { Card } from "@/components/common";
import { Select, Textarea } from "@/components/common/Input";

type LogType = "sysmon" | "windows" | "linux" | "nginx";

const LOG_TYPES: LogType[] = ["sysmon", "windows", "linux", "nginx"];

/** Map impact/severity levels to Badge severity tokens. */
function toBadgeSeverity(s: string | undefined): Severity {
  switch (s) {
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

/** Map a threat-intel verdict to Badge severity tokens. */
function verdictToSeverity(v: string): Severity {
  switch (v) {
    case "malicious":
      return "critical";
    case "suspicious":
      return "medium";
    case "benign":
      return "low";
    default:
      return "info";
  }
}

// ── IOC chips ───────────────────────────────────────────

function IocGroup({
  icon,
  label,
  values,
}: {
  icon: React.ReactNode;
  label: string;
  values: string[];
}) {
  if (values.length === 0) return null;
  return (
    <div>
      <p className="flex items-center gap-1.5 text-xs font-medium text-text-muted mb-1.5">
        {icon}
        {label} ({values.length})
      </p>
      <div className="flex flex-wrap gap-1.5">
        {values.map((v) => (
          <span
            key={v}
            className="inline-block max-w-full truncate px-2 py-0.5 rounded-md bg-surface-hover border border-border-subtle text-xs font-mono text-text-primary"
            title={v}
          >
            {v}
          </span>
        ))}
      </div>
    </div>
  );
}

function IocsSection({
  iocs,
  iocCount,
}: {
  iocs: IOCsGrouped;
  iocCount: TimelineResponse["ioc_count"];
}) {
  const t = useTranslations("logTimeline");
  const isEmpty =
    iocCount.total === 0 ||
    (iocs.ips.length === 0 &&
      iocs.domains.length === 0 &&
      iocs.urls.length === 0 &&
      iocs.hashes.length === 0);

  if (isEmpty) {
    return <p className="text-xs text-text-muted italic">{t("iocNone")}</p>;
  }

  return (
    <div className="space-y-3">
      <IocGroup icon={<Network className="w-3.5 h-3.5" />} label={t("iocIps")} values={iocs.ips} />
      <IocGroup
        icon={<Globe className="w-3.5 h-3.5" />}
        label={t("iocDomains")}
        values={iocs.domains}
      />
      <IocGroup
        icon={<FileSearch className="w-3.5 h-3.5" />}
        label={t("iocUrls")}
        values={iocs.urls}
      />
      <IocGroup
        icon={<Hash className="w-3.5 h-3.5" />}
        label={t("iocHashes")}
        values={iocs.hashes}
      />
    </div>
  );
}

// ── Impact analysis ─────────────────────────────────────

function ImpactSection({ impact }: { impact: ImpactAnalysis }) {
  const t = useTranslations("logTimeline");
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <Badge severity={toBadgeSeverity(impact.severity)}>{impact.severity}</Badge>
        <div className="flex-1 h-2 bg-surface-ground rounded-full overflow-hidden border border-border-subtle">
          <div
            className={
              impact.risk_score >= 80
                ? "h-full rounded-full bg-severity-critical-bg"
                : impact.risk_score >= 50
                  ? "h-full rounded-full bg-severity-high-bg"
                  : "h-full rounded-full bg-severity-low-bg"
            }
            style={{ width: `${Math.min(100, Math.max(0, impact.risk_score))}%` }}
          />
        </div>
        <span className="text-sm font-semibold tabular-nums text-text-primary">
          {impact.risk_score}
        </span>
      </div>

      <div>
        <p className="text-xs font-medium text-text-muted mb-1">{t("businessImpact")}</p>
        <p className="text-sm text-text-secondary leading-relaxed">{impact.business_impact}</p>
      </div>

      {impact.affected_assets.length > 0 && (
        <div>
          <p className="text-xs font-medium text-text-muted mb-1.5">{t("affectedAssets")}</p>
          <ul className="space-y-1">
            {impact.affected_assets.map((a) => (
              <li
                key={a.asset_id}
                className="text-xs text-text-secondary flex items-baseline gap-2"
              >
                <span className="font-mono text-text-primary">
                  {a.hostname || a.ip || a.asset_id}
                </span>
                <span className="text-text-muted">·</span>
                <span className="truncate">{a.reason}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {impact.containment_priority.length > 0 && (
        <div>
          <p className="text-xs font-medium text-text-muted mb-1.5">{t("containmentPriority")}</p>
          <ul className="space-y-1">
            {[...impact.containment_priority]
              .sort((a, b) => a.priority - b.priority)
              .slice(0, 5)
              .map((c) => (
                <li
                  key={c.asset_id}
                  className="text-xs text-text-secondary flex items-center gap-2"
                >
                  <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-surface-hover border border-border-subtle text-[10px] font-semibold tabular-nums">
                    {c.priority}
                  </span>
                  <span className="font-mono text-text-primary">{c.asset_id}</span>
                  <span className="truncate text-text-muted">{c.reason}</span>
                </li>
              ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// ── Threat intel ────────────────────────────────────────

function ThreatIntelSection({ ti }: { ti: ThreatIntelAnalysisTL }) {
  const t = useTranslations("logTimeline");
  const verdictLabel = (v: string) =>
    v === "malicious"
      ? t("verdictMalicious")
      : v === "suspicious"
        ? t("verdictSuspicious")
        : v === "benign"
          ? t("verdictBenign")
          : t("verdictUnknown");

  return (
    <div className="space-y-3">
      {ti.disabled && (
        <p className="text-xs text-text-muted flex items-center gap-1.5">
          <ShieldCheck className="w-3.5 h-3.5" />
          {t("threatIntelDisabled")}
        </p>
      )}
      {ti.skipped && <p className="text-xs text-status-warning-fg">{t("threatIntelSkipped")}</p>}
      {ti.filtered_items.length > 0 && (
        <p className="text-xs text-text-muted">
          {t("threatIntelFiltered", { count: ti.filtered_items.length })}
        </p>
      )}
      {ti.error_reason && !ti.disabled && (
        <p className="text-xs text-status-failed-fg">{ti.error_reason}</p>
      )}

      {ti.items.length === 0 ? (
        <p className="text-xs text-text-muted italic">{t("iocNone")}</p>
      ) : (
        <ul className="divide-y divide-border-subtle">
          {ti.items.map((item: ThreatIntelItemTL) => (
            <li key={`${item.ioc_type}:${item.ioc_value}`} className="py-2 first:pt-0 last:pb-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs font-mono text-text-primary break-all">
                  {item.ioc_value}
                </span>
                <Badge severity={verdictToSeverity(item.verdict)} variant="pill">
                  {verdictLabel(item.verdict)}
                </Badge>
                <span className="text-[11px] text-text-muted tabular-nums ml-auto">
                  {item.score}
                  {item.cached ? " · cached" : ""}
                </span>
              </div>
              {item.tags && item.tags.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-1">
                  {item.tags.slice(0, 6).map((tag) => (
                    <span
                      key={tag}
                      className="px-1.5 py-0.5 rounded bg-surface-hover text-[10px] text-text-muted"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ── Loading skeleton ────────────────────────────────────

function AnalyzingSkeleton() {
  return (
    <div className="space-y-4 animate-pulse" aria-busy="true" aria-live="polite">
      {[3, 4, 3, 2].map((lines, sectionIdx) => (
        <div key={sectionIdx} className="space-y-2">
          <div className="h-3.5 w-32 rounded bg-surface-hover" />
          {Array.from({ length: lines }).map((_, i) => (
            <div
              key={i}
              className="h-3 rounded bg-surface-hover"
              style={{ width: `${90 - i * 12}%` }}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

// ── Main component ──────────────────────────────────────

export function LogTimelineAnalyzer() {
  const t = useTranslations("logTimeline");
  const [rawLog, setRawLog] = useState("");
  const [logType, setLogType] = useState<LogType | "">("");

  const mutation = useMutation<TimelineResponse, Error>({
    mutationFn: () =>
      buildTimeline({
        raw_log: rawLog.trim(),
        log_type: logType || undefined,
      }),
  });

  const data = mutation.data;

  const handleSubmit = () => {
    if (!rawLog.trim() || mutation.isPending) return;
    mutation.mutate();
  };

  return (
    <div className="space-y-6">
      {/* Input */}
      <Card className="p-4 space-y-4">
        <div>
          <h3 className="text-sm font-semibold text-text-primary flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-ai-fg" />
            {t("title")}
          </h3>
          <p className="text-xs text-text-muted mt-1 leading-relaxed">{t("description")}</p>
        </div>

        <Textarea
          label={t("rawLogLabel")}
          value={rawLog}
          onChange={(e) => setRawLog(e.target.value)}
          placeholder={t("rawLogPlaceholder")}
          rows={10}
          className="font-mono text-xs"
        />

        <div className="flex flex-col sm:flex-row sm:items-end gap-3">
          <div className="w-full sm:w-56">
            <Select
              label={t("logTypeLabel")}
              value={logType}
              onChange={(e) => setLogType(e.target.value as LogType | "")}
            >
              <option value="">{t("logTypeAuto")}</option>
              {LOG_TYPES.map((lt) => (
                <option key={lt} value={lt}>
                  {t(
                    `logType${lt.charAt(0).toUpperCase()}${lt.slice(1)}` as Parameters<typeof t>[0]
                  )}
                </option>
              ))}
            </Select>
          </div>
          <Button
            onClick={handleSubmit}
            disabled={!rawLog.trim() || mutation.isPending}
            className="sm:mb-[2px]"
          >
            {mutation.isPending ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                {t("analyzing")}
              </>
            ) : (
              <>
                <Activity className="w-4 h-4" />
                {t("analyze")}
              </>
            )}
          </Button>
        </div>
      </Card>

      {/* Error */}
      {mutation.isError && (
        <Card className="p-4 border-status-failed-border bg-status-failed-bg">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-4 h-4 text-status-failed-fg mt-0.5 shrink-0" />
            <div className="flex-1">
              <p className="text-sm text-status-failed-fg">{t("failed")}</p>
              <Button variant="outline" size="sm" className="mt-2" onClick={() => mutation.reset()}>
                {t("analyze")}
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* Results */}
      {mutation.isPending && (
        <Card className="p-4">
          <AnalyzingSkeleton />
        </Card>
      )}

      {data && !mutation.isPending && (
        <>
          {data.degraded && (
            <Card className="p-3 border-status-warning-border bg-status-warning-bg">
              <p className="text-xs text-status-warning-fg flex items-center gap-1.5">
                <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                {t("degradedWarning")}
                {data.model_used && (
                  <span className="ml-auto text-text-muted shrink-0">
                    {t("modelUsed", { model: data.model_used })}
                  </span>
                )}
              </p>
            </Card>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Impact analysis */}
            <Card className="p-4">
              <h4 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-severity-high-fg" />
                {t("impactTitle")}
                <span className="ml-auto text-[11px] font-normal text-text-muted">
                  {t("riskScore")}
                </span>
              </h4>
              <ImpactSection impact={data.impact_analysis} />
            </Card>

            {/* Event timeline */}
            <Card className="p-4">
              <h4 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
                <Clock className="w-4 h-4 text-text-muted" />
                {t("timelineTitle")}
                <span className="ml-auto text-[11px] font-normal text-text-muted tabular-nums">
                  {data.timeline.length}
                </span>
              </h4>
              {data.timeline.length === 0 ? (
                <p className="text-xs text-text-muted italic">{t("noEvents")}</p>
              ) : (
                <ol className="relative border-l border-border-subtle ml-1.5 space-y-3 max-h-96 overflow-y-auto">
                  {data.timeline.map((ev, i) => (
                    <li key={`${ev.timestamp}-${i}`} className="pl-4">
                      <span className="absolute -left-[5px] w-2.5 h-2.5 rounded-full bg-surface-hover border border-border-strong mt-1" />
                      <p className="text-[11px] text-text-muted font-mono tabular-nums">
                        {ev.timestamp}
                      </p>
                      <p className="text-xs text-text-secondary mt-0.5 leading-relaxed">
                        {ev.description}
                      </p>
                      <span className="inline-block mt-1 px-1.5 py-0.5 rounded bg-surface-hover text-[10px] text-text-muted">
                        {ev.type}
                      </span>
                    </li>
                  ))}
                </ol>
              )}
            </Card>

            {/* Suspicious top5 */}
            <Card className="p-4">
              <h4 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-severity-medium-fg" />
                {t("suspiciousTitle")}
              </h4>
              {data.suspicious_top5.length === 0 ? (
                <p className="text-xs text-text-muted italic">{t("noEvents")}</p>
              ) : (
                <ul className="space-y-3">
                  {data.suspicious_top5.map((ev, i) => (
                    <li key={`${ev.timestamp}-${i}`} className="flex items-start gap-2.5">
                      <Badge severity={toBadgeSeverity(ev.severity)} variant="pill">
                        {ev.severity}
                      </Badge>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs text-text-secondary leading-relaxed">
                          {ev.description}
                        </p>
                        <p className="text-[11px] text-text-muted mt-0.5 leading-relaxed">
                          <span className="font-medium">{t("reasoning")}:</span> {ev.reasoning}
                        </p>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </Card>

            {/* IOCs */}
            <Card className="p-4">
              <h4 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
                <Hash className="w-4 h-4 text-text-muted" />
                {t("iocTitle")}
                <span className="ml-auto text-[11px] font-normal text-text-muted tabular-nums">
                  {data.ioc_count.total}
                </span>
              </h4>
              <IocsSection iocs={data.iocs} iocCount={data.ioc_count} />
            </Card>

            {/* Threat intel */}
            <Card className="p-4">
              <h4 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
                <Globe className="w-4 h-4 text-text-muted" />
                {t("threatIntelTitle")}
                <span className="ml-auto text-[11px] font-normal text-text-muted">
                  {data.threat_intel.provider}
                </span>
              </h4>
              <ThreatIntelSection ti={data.threat_intel} />
            </Card>

            {/* Next steps */}
            <Card className="p-4">
              <h4 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-ai-fg" />
                {t("nextStepsTitle")}
              </h4>
              {data.next_steps.length === 0 ? (
                <p className="text-xs text-text-muted italic">{t("noEvents")}</p>
              ) : (
                <ol className="space-y-2">
                  {data.next_steps.map((step, i) => (
                    <li
                      key={i}
                      className="flex items-start gap-2.5 text-xs text-text-secondary leading-relaxed"
                    >
                      <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-ai-bg text-ai-fg text-[10px] font-semibold shrink-0 mt-0.5">
                        {i + 1}
                      </span>
                      <span>{step}</span>
                    </li>
                  ))}
                </ol>
              )}
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
