"use client";

/**
 * Alert AI Analysis Panel
 *
 * 数据全部来自 POST /api/v1/analyze-alert（真实 AI 服务），字段契约见
 * `lib/api/alerts.ts` 的 AlertAnalysisResponse：
 *   summary / attack_pattern / iocs / ioc_count / recommended_actions / confidence / model_used
 *
 * 硬性约束（对应审计 P1-11 与"不虚构数据"原则）：
 *  - confidence 缺失时渲染 "Confidence unavailable"，**绝不回退到编造的默认百分比**
 *  - 未运行分析时显示空态 + 运行按钮，不展示任何预置结论
 *  - model_used 展示真实模型名；AI 产出与人工操作使用不同视觉语言（ai-* 令牌）
 */

import { useMutation } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import {
  Brain,
  Sparkles,
  RefreshCw,
  AlertTriangle,
  ShieldCheck,
  MessageCircleQuestion,
  PlusCircle,
  PlayCircle,
  Info,
} from "lucide-react";

import { analyzeAlert, type AlertAnalysisResponse } from "@/lib/api/alerts";
import { Link } from "@/i18n/navigation";
import { Badge, ConfidenceBadge, AIBadge, type Severity } from "@/components/ui/Badge";
import { Button } from "@/components/common/Button";
import { Card } from "@/components/common";

interface AIAnalysisPanelProps {
  alert: {
    id?: string | number;
    title?: string;
    description?: string | null;
    source?: string | null;
    severity?: string | null;
    raw_log?: string | null;
  };
  onAddNote?: (note: string) => void;
}

const PRIORITY_TO_SEVERITY: Record<string, Severity> = {
  critical: "critical",
  high: "high",
  medium: "medium",
  low: "low",
};

export function AIAnalysisPanel({ alert, onAddNote }: AIAnalysisPanelProps) {
  const t = useTranslations("alerts.detail.ai");

  const mutation = useMutation<AlertAnalysisResponse, Error>({
    mutationFn: () => {
      const rawLog =
        alert.raw_log ||
        [
          alert.title ? `Alert: ${alert.title}` : "",
          alert.severity ? `Severity: ${alert.severity}` : "",
          alert.source ? `Source: ${alert.source}` : "",
          alert.description ? `Description: ${alert.description}` : "",
        ]
          .filter(Boolean)
          .join("\n");

      return analyzeAlert({
        title: alert.title ?? "",
        description: alert.description ?? "",
        source: alert.source ?? undefined,
        severity: alert.severity ?? undefined,
        raw_log: rawLog,
      });
    },
  });

  const data = mutation.data;

  return (
    <Card className="overflow-hidden">
      <div className="flex items-center justify-between gap-3 border-b border-border-subtle px-5 py-3">
        <h3 className="flex items-center gap-2 text-sm font-semibold tracking-tight text-text-primary">
          <Brain className="h-4 w-4 text-ai" />
          {t("title")}
        </h3>
        <div className="flex items-center gap-2">
          {alert.id != null && (
            <Link
              href={`/ai-assistant?alert=${alert.id}`}
              title={t("askMore")}
              className="inline-flex items-center gap-1.5 rounded-md border border-border-subtle px-2 py-1 text-xs text-text-secondary transition-colors hover:border-border-strong hover:text-text-primary"
            >
              <MessageCircleQuestion className="h-3.5 w-3.5" />
              {t("askMore")}
            </Link>
          )}
          {data && typeof data.confidence === "number" && (
            <ConfidenceBadge value={data.confidence} unavailableLabel={t("unavailable")} showBar />
          )}
          {data && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => mutation.mutate()}
              disabled={mutation.isPending}
            >
              <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
              {mutation.isPending ? t("running") : t("rerun")}
            </Button>
          )}
        </div>
      </div>

      <div className="p-5">
        {/* ── 未运行：空态 + 明确的下一步 ───────────────── */}
        {!data && !mutation.isPending && !mutation.isError && (
          <div className="flex flex-col items-start gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-medium text-text-secondary">{t("notRun")}</p>
              <p className="mt-0.5 text-xs text-text-muted">{t("notRunSub")}</p>
            </div>
            <Button size="sm" onClick={() => mutation.mutate()} className="shrink-0">
              <Sparkles className="mr-1.5 h-3.5 w-3.5" />
              {t("run")}
            </Button>
          </div>
        )}

        {mutation.isPending && (
          <div className="space-y-2" aria-live="polite" aria-busy="true">
            <div className="h-3 w-1/3 animate-pulse rounded bg-surface-active" />
            <div className="h-3 w-full animate-pulse rounded bg-surface-active" />
            <div className="h-3 w-4/5 animate-pulse rounded bg-surface-active" />
            <span className="sr-only">{t("running")}</span>
          </div>
        )}

        {mutation.isError && (
          <div className="flex items-center justify-between gap-3 rounded-lg border border-severity-critical-border bg-severity-critical-bg px-4 py-3">
            <p className="flex items-center gap-2 text-sm text-severity-critical-fg">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              {t("failed")}
            </p>
            <Button variant="outline" size="sm" onClick={() => mutation.mutate()}>
              {t("retry")}
            </Button>
          </div>
        )}

        {data && (
          <div className="space-y-5">
            {/* ── API / Mode Notification Banner ─────────────── */}
            {data.degraded ? (
              <div className="flex items-start gap-2.5 rounded-lg border border-amber-500/20 bg-amber-500/10 px-3.5 py-2.5 text-xs text-amber-800 dark:text-amber-300">
                <Info className="mt-0.5 h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400" />
                <div className="space-y-0.5">
                  <span className="font-semibold">{t("degradedNoticeTitle")}</span>
                  <p className="leading-relaxed text-amber-700/90 dark:text-amber-400/90">
                    {t("degradedNoticeDesc")}
                  </p>
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-2 rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-3.5 py-2 text-xs text-emerald-800 dark:text-emerald-300">
                <Sparkles className="h-4 w-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
                <span className="font-medium">{t("llmSuccessNotice")}</span>
              </div>
            )}

            {/* ── Assessment：AI 判定的严重程度 ───────────── */}
            <div className="flex flex-wrap items-center gap-2">
              <AIBadge state="analysis" label={t("title")} size="xs" />
              <Badge severity={PRIORITY_TO_SEVERITY[data.severity] ?? "neutral"} size="xs" dot>
                {data.severity}
              </Badge>
              <Badge severity={data.degraded ? "medium" : "low"} size="xs">
                {data.degraded ? t("modeHeuristic") : t("modeLLM")}
              </Badge>
              {data.model_used && (
                <span className="text-[11px] text-text-muted">
                  {t("modelUsed")}: <span className="font-mono">{data.model_used}</span>
                </span>
              )}
            </div>

            {/* ── Analysis ─────────────────────────────── */}
            {data.summary && (
              <p className="text-[13px] leading-relaxed text-text-secondary">{data.summary}</p>
            )}

            {/* ── Attack pattern ───────────────────────── */}
            {data.attack_pattern && (
              <div>
                <h4 className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-text-tertiary">
                  {t("attackPattern")}
                </h4>
                <p className="text-[13px] leading-relaxed text-text-secondary">
                  {data.attack_pattern}
                </p>
              </div>
            )}

            {/* ── Evidence：证据 ────────────────────────── */}
            <div>
              <h4 className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-text-tertiary">
                {t("evidence")}
              </h4>
              <p className="mb-2 text-xs tabular-nums text-text-muted">
                {t("iocCount", {
                  ip: data.ioc_count?.ips ?? 0,
                  domain: data.ioc_count?.domains ?? 0,
                  url: data.ioc_count?.urls ?? 0,
                  hash: data.ioc_count?.hashes ?? 0,
                })}
              </p>
              {data.iocs && (
                <div className="flex flex-wrap gap-1.5">
                  {[
                    ...(data.iocs.ips ?? []).map((v) => `IP ${v}`),
                    ...(data.iocs.domains ?? []).map((v) => `DOMAIN ${v}`),
                    ...(data.iocs.urls ?? []).map((v) => `URL ${v}`),
                    ...(data.iocs.hashes ?? []).map((v) => `HASH ${v}`),
                  ].map((chip) => (
                    <span
                      key={chip}
                      className="rounded border border-border-subtle bg-surface-hover px-1.5 py-0.5 font-mono text-[11px] text-text-secondary"
                    >
                      {chip}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* ── Recommendation：区分可自动化 / 需人工 ────── */}
            <div>
              <h4 className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-text-tertiary">
                {t("recommendation")}
              </h4>
              {data.recommended_actions && data.recommended_actions.length > 0 ? (
                <ol className="space-y-2">
                  {data.recommended_actions.map((action, idx) => (
                    <li
                      key={`${action.action}-${idx}`}
                      className="flex items-start gap-2.5 rounded-lg border border-border-subtle bg-surface-hover/50 px-3 py-2"
                    >
                      <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-surface-active text-[10px] font-semibold tabular-nums text-text-secondary">
                        {idx + 1}
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-1.5">
                          <span className="text-[13px] font-medium text-text-primary">
                            {action.action}
                          </span>
                          <Badge
                            severity={PRIORITY_TO_SEVERITY[action.priority] ?? "neutral"}
                            size="xs"
                          >
                            {action.priority}
                          </Badge>
                          {/* Human-in-the-loop：可自动化 ≠ 自动执行，仍需审批 */}
                          {action.automated ? (
                            <AIBadge state="approval" label={t("approvalRequired")} size="xs" />
                          ) : (
                            <AIBadge state="analysis" label={t("manual")} size="xs" />
                          )}
                        </div>
                        {(action.description || (action as any).details) && (
                          <p className="mt-0.5 text-xs leading-relaxed text-text-tertiary">
                            {action.description || (action as any).details}
                          </p>
                        )}
                        <div className="mt-2 flex items-center gap-2">
                          {onAddNote && (
                            <button
                              type="button"
                              onClick={() =>
                                onAddNote(`[AI建议] ${action.action}: ${action.description || ""}`)
                              }
                              className="inline-flex items-center gap-1 text-[11px] font-medium text-text-secondary hover:text-accent-600 bg-surface-hover hover:bg-surface-active px-2 py-0.5 rounded border border-border-subtle transition-colors"
                              title={t("addToNotes")}
                            >
                              <PlusCircle className="h-3 w-3" />
                              {t("addToNotes")}
                            </button>
                          )}
                          <Link
                            href={`/playbooks`}
                            className="inline-flex items-center gap-1 text-[11px] font-medium text-accent-600 hover:text-accent-700 bg-accent-500/10 hover:bg-accent-500/20 px-2 py-0.5 rounded transition-colors"
                            title={t("executePlaybook")}
                          >
                            <PlayCircle className="h-3 w-3" />
                            {t("executePlaybook")}
                          </Link>
                        </div>
                      </div>
                    </li>
                  ))}
                </ol>
              ) : (
                <p className="flex items-center gap-2 text-xs text-text-muted">
                  <ShieldCheck className="h-3.5 w-3.5" />
                  {t("noRecommendation")}
                </p>
              )}
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}
