"use client";

/**
 * Root Cause Analysis section (T2.4)
 *
 * 数据全部来自 /api/v1/alerts/{id}/root-cause-analysis（真实 LLM CoT 分析），
 * 字段契约见 `lib/api/rootCause.ts`。
 *
 * 硬性约束（延续"不虚构数据"原则）：
 *  - 后端在 LLM 不可用时返回 503（拒绝编造分析），此处如实展示"AI 暂不可用"，
 *    绝不渲染任何本地兜底结论
 *  - 未运行分析时显示空态 + 运行按钮
 *  - 分析师反馈（准确/部分准确/不准确）回写 human_verified 闭环
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState } from "react";
import {
  BrainCircuit,
  PlayCircle,
  RefreshCw,
  CheckCircle2,
  CircleAlert,
  Lightbulb,
  ListChecks,
  ShieldQuestion,
  ThumbsUp,
  ThumbsDown,
  MinusCircle,
} from "lucide-react";

import {
  listRootCauseAnalyses,
  runRootCauseAnalysis,
  submitRootCauseFeedback,
  type RootCauseAnalysis,
  type RootCauseFeedbackVerdict,
} from "@/lib/api/rootCause";
import { Badge, AIBadge, type Severity } from "@/components/ui/Badge";
import { Button } from "@/components/common/Button";
import { EmptyState } from "@/components/EmptyState";

const PRIORITY_SEVERITY: Record<string, Severity> = {
  critical: "critical",
  high: "high",
  medium: "medium",
  low: "low",
};

const CATEGORY_I18N: Record<string, string> = {
  attack: "categoryAttack",
  misconfiguration: "categoryMisconfiguration",
  failure: "categoryFailure",
  human_error: "categoryHumanError",
  false_positive: "categoryFalsePositive",
  unknown: "categoryUnknown",
};

export function RootCauseSection({ alertId }: { alertId: number | string }) {
  const t = useTranslations("alerts.detail.rootCause");
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const history = useQuery({
    queryKey: ["root-cause-analyses", String(alertId)],
    queryFn: () => listRootCauseAnalyses(alertId),
  });

  const run = useMutation({
    mutationFn: () => runRootCauseAnalysis(alertId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["root-cause-analyses", String(alertId)] });
    },
  });

  const feedback = useMutation({
    mutationFn: ({ id, verdict }: { id: string; verdict: RootCauseFeedbackVerdict }) =>
      submitRootCauseFeedback(id, verdict),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["root-cause-analyses", String(alertId)] });
    },
  });

  const items = history.data?.items ?? [];
  const latest = items[0];
  const current: RootCauseAnalysis | undefined = items.find((i) => i.id === selectedId) ?? latest;

  const categoryKey = CATEGORY_I18N[current?.root_cause_category ?? "unknown"] ?? "categoryUnknown";

  return (
    <div className="space-y-5">
      {/* Header + run button */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <BrainCircuit className="w-4 h-4 text-accent-500" />
          <h4 className="text-sm font-semibold tracking-tight text-text-primary">{t("title")}</h4>
          {items.length > 0 && (
            <span className="text-[11px] text-text-muted">
              {t("historyCount", { count: items.length })}
            </span>
          )}
        </div>
        <Button variant="outline" size="sm" onClick={() => run.mutate()} disabled={run.isPending}>
          {run.isPending ? (
            <RefreshCw className="w-3.5 h-3.5 mr-1.5 animate-spin" />
          ) : (
            <PlayCircle className="w-3.5 h-3.5 mr-1.5" />
          )}
          {items.length > 0 ? t("rerun") : t("run")}
        </Button>
      </div>

      {/* Run error: LLM unavailable (503) or others — show as-is, no fallback conclusions */}
      {run.isError && (
        <div className="rounded-lg border border-warning-500/40 bg-warning-500/10 p-3 text-xs text-text-primary">
          {t("runFailed")}
        </div>
      )}

      {/* Empty state */}
      {!current && !run.isPending && (
        <EmptyState
          icon="custom"
          customIcon={<ShieldQuestion className="w-8 h-8 text-text-muted" />}
          title={t("emptyTitle")}
          description={t("emptyDescription")}
        />
      )}

      {current && (
        <div className="space-y-4">
          {/* Verdict summary */}
          <div className="flex flex-wrap items-center gap-2">
            <AIBadge state="analysis" label={t("aiBadge")} size="xs" />
            <Badge severity={PRIORITY_SEVERITY[current.remediation_priority] ?? "info"}>
              {t(`priority.${current.remediation_priority}`) !==
              `priority.${current.remediation_priority}`
                ? t(`priority.${current.remediation_priority}`)
                : current.remediation_priority}
            </Badge>
            <Badge severity="info">{t(categoryKey)}</Badge>
            {current.root_cause_subcategory && (
              <span className="text-xs text-text-muted">{current.root_cause_subcategory}</span>
            )}
            <span className="ml-auto text-[11px] text-text-muted font-mono">
              {current.ai_model} · {Math.round(current.confidence * 100)}% · {t("confidence")}
            </span>
          </div>

          {/* Reasoning steps */}
          {current.reasoning_steps.length > 0 && (
            <div>
              <h5 className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-2">
                {t("reasoningTitle")}
              </h5>
              <ol className="space-y-2">
                {current.reasoning_steps.map((step, idx) => (
                  <li key={idx} className="flex gap-2.5 text-xs text-text-secondary">
                    <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-accent-500/15 text-[10px] font-bold text-accent-600 dark:text-accent-400">
                      {step.step ?? idx + 1}
                    </span>
                    <div>
                      {step.description && (
                        <p className="font-medium text-text-primary">{step.description}</p>
                      )}
                      {step.findings && step.findings.length > 0 && (
                        <ul className="mt-1 list-disc pl-4 space-y-0.5">
                          {step.findings.map((f, i) => (
                            <li key={i}>{f}</li>
                          ))}
                        </ul>
                      )}
                    </div>
                  </li>
                ))}
              </ol>
            </div>
          )}

          {/* Evidence chain */}
          {current.evidence_chain.length > 0 && (
            <div>
              <h5 className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-2">
                {t("evidenceTitle")}
              </h5>
              <ul className="space-y-1.5">
                {current.evidence_chain.map((e, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-xs text-text-secondary">
                    <CheckCircle2 className="w-3.5 h-3.5 mt-0.5 shrink-0 text-success-500" />
                    <span>
                      {e.evidence}
                      {e.supports && <span className="text-text-muted"> → {e.supports}</span>}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Verification steps */}
          {current.verification_steps.length > 0 && (
            <div>
              <h5 className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-2 flex items-center gap-1.5">
                <ListChecks className="w-3.5 h-3.5" />
                {t("verificationTitle")}
              </h5>
              <ul className="space-y-1">
                {current.verification_steps.map((v, idx) => (
                  <li
                    key={idx}
                    className="text-xs text-text-secondary font-mono pl-3 border-l border-border-subtle"
                  >
                    {v}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Remediation */}
          {current.suggested_remediation && (
            <div className="rounded-lg border border-success-500/30 bg-success-500/5 p-3">
              <h5 className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-1 flex items-center gap-1.5">
                <Lightbulb className="w-3.5 h-3.5 text-success-500" />
                {t("remediationTitle")}
              </h5>
              <p className="text-xs text-text-primary">{current.suggested_remediation}</p>
            </div>
          )}

          {/* Feedback loop */}
          <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-border-subtle">
            {current.human_verified ? (
              <span className="inline-flex items-center gap-1.5 text-[11px] text-text-muted">
                <CheckCircle2 className="w-3.5 h-3.5 text-success-500" />
                {t("feedbackRecorded", { verdict: t(`verdict.${current.feedback_category}`) })}
              </span>
            ) : (
              <>
                <span className="text-[11px] text-text-muted">{t("feedbackPrompt")}</span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => feedback.mutate({ id: current.id, verdict: "accurate" })}
                  disabled={feedback.isPending}
                >
                  <ThumbsUp className="w-3 h-3 mr-1" /> {t("verdict.accurate")}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => feedback.mutate({ id: current.id, verdict: "partially_accurate" })}
                  disabled={feedback.isPending}
                >
                  <MinusCircle className="w-3 h-3 mr-1" /> {t("verdict.partially_accurate")}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => feedback.mutate({ id: current.id, verdict: "inaccurate" })}
                  disabled={feedback.isPending}
                >
                  <ThumbsDown className="w-3 h-3 mr-1" /> {t("verdict.inaccurate")}
                </Button>
              </>
            )}
          </div>

          {/* History selector */}
          {items.length > 1 && (
            <div className="flex items-center gap-2 text-[11px] text-text-muted">
              <CircleAlert className="w-3 h-3" />
              {t("historyPrompt")}
              <select
                // 原先这里用的是一个不存在的 surface 槽位（"面板"名）：surface 规模只有
                // page / ground / canvas / card / hover / active / input，Tailwind 生成不出
                // 任何 CSS，于是这个下拉框根本拿不到我们定义的背景色。
                // 表单控件统一用 surface-input。
                //
                // ⚠️ 别在注释里把那个槽位名原样写出来：scripts/check-design-tokens.mjs
                // 扫的是源码原文（含注释），会把注释里的死类名当成仍在使用的 token 报错。
                className="border border-border-subtle rounded px-1.5 py-0.5 bg-surface-input text-text-primary"
                value={current.id}
                onChange={(e) => setSelectedId(e.target.value)}
              >
                {items.map((i) => (
                  <option key={i.id} value={i.id}>
                    {new Date(i.created_at).toLocaleString()} · {i.root_cause_category}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      )}

      {/* Loading */}
      {(run.isPending || history.isLoading) && (
        <div className="flex items-center gap-2 text-xs text-text-muted">
          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
          {t("loading")}
        </div>
      )}
    </div>
  );
}
