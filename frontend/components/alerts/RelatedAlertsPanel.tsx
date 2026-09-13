"use client";

/**
 * Related Alerts Panel
 *
 * 回答调查中的关键问题：「这是孤例，还是持续活动？」
 *
 * 数据来源是真实后端 `GET /api/v1/security-alerts`，按 `agent_name` 过滤，
 * 无 agent 信息时回退到 `source_ip`。**明确标注关联维度**，不使用任何后端
 * 未提供的"相似度 / 关联度"指标，避免制造不可解释的伪科学评分。
 */

import { useTranslations, useFormatter } from "next-intl";
import { Server, Globe, AlertCircle } from "lucide-react";

import { Link } from "@/i18n/navigation";
import { useAlerts } from "@/hooks/useAlerts";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/common";

type Formatter = ReturnType<typeof useFormatter>;

interface RelatedAlertsPanelProps {
  alertId: string | number;
  agentName?: string | null;
  sourceIp?: string | null;
  severity?: string | null;
  /** 关联维度 → 严重级映射，用于给每行上色 */
  severityOf?: (severity: string) => "critical" | "high" | "medium" | "low" | "info" | "neutral";
}

const MAX_ITEMS = 5;

function formatShort(ts: string | null | undefined, format: Formatter): string {
  if (!ts) return "—";
  try {
    const d = new Date(ts);
    if (isNaN(d.getTime())) return "—";
    return format.dateTime(d, { dateStyle: "short", timeStyle: "short" });
  } catch {
    return "—";
  }
}

export function RelatedAlertsPanel({
  alertId,
  agentName,
  sourceIp,
  severityOf,
}: RelatedAlertsPanelProps) {
  const t = useTranslations("alerts.detail");
  const format = useFormatter();

  // 关联维度：优先资产（agent），缺失时退化为源 IP。两者都没有则不请求。
  const useAgent = Boolean(agentName);
  const filters = useAgent
    ? { agent_name: agentName as string, page_size: MAX_ITEMS + 1 }
    : sourceIp
      ? { source_ip: sourceIp, page_size: MAX_ITEMS + 1 }
      : null;

  const { data, isLoading, isError } = useAlerts(filters ?? {});

  // 无任何可关联维度时不渲染该模块，而不是展示一张空卡。
  if (!filters) return null;

  const others = (data?.alerts ?? []).filter((a) => String(a.id) !== String(alertId));
  const visible = others.slice(0, MAX_ITEMS);

  return (
    <Card className="overflow-hidden">
      <div className="border-b border-border-subtle px-4 py-3 sm:px-5">
        <h3 className="text-sm font-semibold tracking-tight text-text-primary">
          {t("relatedTitle")}
        </h3>
        <p className="mt-0.5 truncate text-[11px] text-text-muted">
          {useAgent
            ? t("relatedSameAsset", { asset: agentName as string })
            : t("relatedSameIp", { ip: sourceIp as string })}
        </p>
      </div>

      <div className="p-4 sm:p-5">
        {isLoading && (
          <div className="space-y-2" aria-busy="true" aria-live="polite">
            <div className="h-9 animate-pulse rounded-lg bg-surface-active" />
            <div className="h-9 animate-pulse rounded-lg bg-surface-active" />
          </div>
        )}

        {isError && (
          <p className="flex items-center gap-2 text-xs text-text-muted">
            <AlertCircle className="h-3.5 w-3.5 shrink-0" />
            {t("relatedLoadFailed")}
          </p>
        )}

        {!isLoading && !isError && visible.length === 0 && (
          <p className="text-xs italic text-text-muted">{t("relatedNone")}</p>
        )}

        {!isLoading && !isError && visible.length > 0 && (
          <ul className="space-y-2">
            {visible.map((a) => (
              <li key={a.id}>
                <Link
                  href={`/alerts/${a.id}`}
                  className="block rounded-lg border border-border-subtle bg-surface-hover/50 px-3 py-2 transition-colors hover:border-border-strong hover:bg-surface-hover"
                >
                  <div className="flex items-start gap-2">
                    <Badge severity={severityOf ? severityOf(a.severity) : "neutral"} size="xs" dot>
                      {a.severity}
                    </Badge>
                    <span className="min-w-0 flex-1 truncate text-[13px] font-medium text-text-primary">
                      {a.title}
                    </span>
                  </div>
                  <div className="mt-1 flex items-center gap-2 text-[11px] text-text-muted">
                    {useAgent ? (
                      <span className="inline-flex items-center gap-1 truncate font-mono">
                        <Server className="h-3 w-3 shrink-0" />
                        {a.source || "—"}
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 truncate font-mono">
                        <Globe className="h-3 w-3 shrink-0" />
                        {a.source_ip || "—"}
                      </span>
                    )}
                    <span>·</span>
                    <span className="shrink-0">
                      {formatShort(a.event_timestamp || a.created_at, format)}
                    </span>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </Card>
  );
}
