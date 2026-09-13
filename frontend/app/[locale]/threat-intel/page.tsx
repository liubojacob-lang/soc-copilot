"use client";

/**
 * Threat Intelligence — IOC lookup & batch enrichment page.
 *
 * Backed by the real backend endpoints:
 *   GET  /api/v1/ti/otx     (single IOC lookup)
 *   POST /api/v1/ti/batch   (batch query, max 50)
 *
 * The previous version called a non-existent /api/ti/search endpoint and
 * always failed at runtime; this page replaces it with the typed contract
 * in lib/api/threat-intel.ts.
 */

import { useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import {
  AlertTriangle,
  ExternalLink,
  Globe,
  Hash,
  ListChecks,
  Network,
  Search,
} from "lucide-react";

import {
  batchIocQuery,
  detectIocType,
  lookupIoc,
  type IOCBatchResultItem,
  type TIIOCType,
  type ThreatIntelLookupResponse,
  type TIVerdict,
} from "@/lib/api/threat-intel";
import { Badge, type Severity } from "@/components/ui/Badge";
import { Button } from "@/components/common/Button";
import { Card } from "@/components/common";
import { Input, Select, Textarea } from "@/components/common/Input";
import { PageHeader } from "@/components/common/PageHeader";

const IOC_TYPES: TIIOCType[] = ["ip", "domain", "url", "hash"];
const MAX_BATCH = 50;

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

function TypeIcon({ type }: { type: string }) {
  switch (type) {
    case "ip":
      return <Network className="w-3.5 h-3.5" />;
    case "domain":
      return <Globe className="w-3.5 h-3.5" />;
    case "hash":
      return <Hash className="w-3.5 h-3.5" />;
    default:
      return <ExternalLink className="w-3.5 h-3.5" />;
  }
}

/** Parsed batch input line. */
interface ParsedIoc {
  ioc_type: TIIOCType;
  ioc_value: string;
}

// ── Single lookup panel ─────────────────────────────────

function ScoreBar({ score }: { score: number }) {
  const pct = Math.min(100, Math.max(0, score));
  return (
    <div className="flex items-center gap-2 min-w-32">
      <div className="flex-1 h-2 bg-surface-ground rounded-full overflow-hidden border border-border-subtle">
        <div
          className={
            score >= 70
              ? "h-full rounded-full bg-severity-critical-bg"
              : score >= 40
                ? "h-full rounded-full bg-severity-high-bg"
                : "h-full rounded-full bg-severity-low-bg"
          }
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-sm font-semibold text-text-primary tabular-nums">{score}</span>
    </div>
  );
}

function SingleResult({ result }: { result: ThreatIntelLookupResponse }) {
  const t = useTranslations("threatIntel");
  const severity = verdictToSeverity(result.verdict);

  return (
    <Card className="p-5 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-surface-hover border border-border-subtle text-[10px] font-semibold uppercase text-text-muted shrink-0">
            <TypeIcon type={result.ioc_type} />
            <span className="ml-1">{result.ioc_type}</span>
          </span>
          <h3 className="text-sm font-mono font-semibold text-text-primary truncate">
            {result.ioc_value}
          </h3>
        </div>
        <Badge severity={severity}>{t(`verdict_${result.verdict as TIVerdict}`)}</Badge>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-x-6 gap-y-3 text-sm">
        <div className="flex items-center justify-between gap-3">
          <span className="text-text-muted">{t("score")}</span>
          <ScoreBar score={result.score} />
        </div>
        <div className="flex items-center justify-between gap-3">
          <span className="text-text-muted">{t("pulseCount")}</span>
          <span className="text-text-primary font-medium tabular-nums">{result.pulse_count}</span>
        </div>
        <div className="flex items-center justify-between gap-3">
          <span className="text-text-muted">{t("provider")}</span>
          <span className="text-text-primary font-medium">{result.provider}</span>
        </div>
        <div className="flex items-center justify-between gap-3">
          <span className="text-text-muted">{t("cached")}</span>
          <span className="text-text-primary font-medium">
            {result.cached ? t("yes") : t("no")}
          </span>
        </div>
      </div>

      {result.tags.length > 0 && (
        <div>
          <p className="text-xs font-medium text-text-muted mb-1.5">{t("tags")}</p>
          <div className="flex flex-wrap gap-1.5">
            {result.tags.map((tag) => (
              <span
                key={tag}
                className="inline-block px-2 py-0.5 rounded-md bg-surface-hover border border-border-subtle text-xs text-text-primary"
              >
                {tag}
              </span>
            ))}
          </div>
        </div>
      )}

      {result.references.length > 0 && (
        <div>
          <p className="text-xs font-medium text-text-muted mb-1.5">{t("references")}</p>
          <ul className="space-y-1">
            {result.references.map((ref) => (
              <li key={ref}>
                <a
                  href={ref}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-xs text-ai-fg hover:underline break-all"
                >
                  <ExternalLink className="w-3 h-3 shrink-0" />
                  {ref}
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}

      {result.skipped_reason && (
        <Card className="p-3 border-status-warning-border bg-status-warning-bg">
          <p className="text-xs text-status-warning-fg">
            {t("skippedReason")}: {result.skipped_reason}
          </p>
        </Card>
      )}
      {result.error_reason && (
        <Card className="p-3 border-status-failed-border bg-status-failed-bg">
          <p className="text-xs text-status-failed-fg">
            {t("errorReason")}: {result.error_reason}
          </p>
        </Card>
      )}

      {result.raw && Object.keys(result.raw).length > 0 && (
        <details className="text-xs">
          <summary className="cursor-pointer text-text-muted hover:text-text-primary select-none">
            {t("rawDetails")}
          </summary>
          <pre className="mt-2 p-3 rounded-md bg-surface-hover border border-border-subtle overflow-x-auto text-text-muted font-mono whitespace-pre-wrap break-all">
            {JSON.stringify(result.raw, null, 2)}
          </pre>
        </details>
      )}
    </Card>
  );
}

function SingleLookupPanel() {
  const t = useTranslations("threatIntel");
  const [value, setValue] = useState("");
  const [mode, setMode] = useState<"auto" | TIIOCType>("auto");
  const [clientError, setClientError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: ({ iocType, iocValue }: { iocType: TIIOCType; iocValue: string }) =>
      lookupIoc(iocType, iocValue),
    onSuccess: () => setClientError(null),
  });

  const handleSubmit = () => {
    const trimmed = value.trim();
    if (!trimmed) return;
    let iocType: TIIOCType | null;
    if (mode === "auto") {
      iocType = detectIocType(trimmed);
      if (!iocType) {
        setClientError(t("cannotDetect"));
        return;
      }
    } else {
      iocType = mode;
    }
    setClientError(null);
    mutation.mutate({ iocType, iocValue: trimmed });
  };

  return (
    <div className="space-y-4">
      <Card className="p-4">
        <div className="flex flex-col sm:flex-row gap-3">
          <Select
            value={mode}
            onChange={(e) => setMode(e.target.value as "auto" | TIIOCType)}
            className="sm:w-40"
            aria-label={t("iocType")}
          >
            <option value="auto">{t("autoDetect")}</option>
            {IOC_TYPES.map((type) => (
              <option key={type} value={type}>
                {t(`type_${type}`)}
              </option>
            ))}
          </Select>
          <Input
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
            placeholder={t("searchPlaceholder")}
            className="flex-1 font-mono"
          />
          <Button
            onClick={handleSubmit}
            disabled={mutation.isPending || !value.trim()}
            leftIcon={<Search className="w-4 h-4" />}
            className="shrink-0"
          >
            {mutation.isPending ? t("searching") : t("search")}
          </Button>
        </div>
      </Card>

      {(clientError || mutation.isError) && (
        <Card className="p-4 border-status-failed-border bg-status-failed-bg">
          <div className="flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-status-failed-fg mt-0.5 shrink-0" />
            <p className="text-sm text-status-failed-fg">
              {clientError ??
                (mutation.error instanceof Error ? mutation.error.message : t("lookupFailed"))}
            </p>
          </div>
        </Card>
      )}

      {mutation.isPending && (
        <Card className="p-6">
          <div className="animate-pulse space-y-3">
            <div className="h-4 bg-surface-hover rounded w-1/3" />
            <div className="h-3 bg-surface-hover rounded w-2/3" />
            <div className="h-3 bg-surface-hover rounded w-1/2" />
          </div>
        </Card>
      )}

      {mutation.isSuccess && mutation.data && <SingleResult result={mutation.data} />}
    </div>
  );
}

// ── Batch lookup panel ──────────────────────────────────

function BatchRow({ item }: { item: IOCBatchResultItem }) {
  const t = useTranslations("threatIntel");
  return (
    <tr className="border-b border-border-subtle last:border-0">
      <td className="py-2 pr-3">
        <div className="flex items-center gap-1.5 min-w-0">
          <span className="text-text-muted shrink-0">
            <TypeIcon type={item.ioc_type} />
          </span>
          <span className="font-mono text-xs text-text-primary truncate" title={item.ioc_value}>
            {item.ioc_value}
          </span>
        </div>
      </td>
      <td className="py-2 pr-3">
        <Badge severity={verdictToSeverity(item.verdict)}>
          {t(`verdict_${item.verdict as TIVerdict}`)}
        </Badge>
      </td>
      <td className="py-2 pr-3 text-sm text-text-primary tabular-nums text-right">{item.score}</td>
      <td className="py-2 pr-3 text-xs text-text-muted tabular-nums text-right">
        {item.pulse_count}
      </td>
      <td className="py-2 pr-3 text-xs text-text-muted">{item.source}</td>
      <td className="py-2 text-xs max-w-xs sm:max-w-sm">
        {item.error ? (
          <span className="text-status-failed-fg truncate block" title={item.error}>
            {item.error}
          </span>
        ) : item.tags.length > 0 ? (
          <span className="text-text-muted truncate block" title={item.tags.join(", ")}>
            {item.tags.join(", ")}
          </span>
        ) : (
          <span className="text-text-muted">—</span>
        )}
      </td>
    </tr>
  );
}

function BatchLookupPanel() {
  const t = useTranslations("threatIntel");
  const [raw, setRaw] = useState("");

  const parsed = useMemo(() => {
    const lines = raw
      .split(/\r?\n/)
      .map((l) => l.trim())
      .filter(Boolean);
    const valid: ParsedIoc[] = [];
    let invalid = 0;
    for (const line of lines.slice(0, MAX_BATCH)) {
      const type = detectIocType(line);
      if (type) {
        valid.push({ ioc_type: type, ioc_value: line });
      } else {
        invalid += 1;
      }
    }
    return { valid, invalid, overflow: Math.max(0, lines.length - MAX_BATCH) };
  }, [raw]);

  const mutation = useMutation({ mutationFn: batchIocQuery });

  const summary = useMemo(() => {
    if (!mutation.data) return null;
    const counts: Record<TIVerdict, number> = {
      malicious: 0,
      suspicious: 0,
      unknown: 0,
      benign: 0,
    };
    for (const r of mutation.data.results) {
      counts[r.verdict] = (counts[r.verdict] ?? 0) + 1;
    }
    return counts;
  }, [mutation.data]);

  const canSubmit = parsed.valid.length > 0 && !mutation.isPending;

  return (
    <div className="space-y-4">
      <Card className="p-4 space-y-3">
        <Textarea
          value={raw}
          onChange={(e) => setRaw(e.target.value)}
          rows={6}
          placeholder={t("batchPlaceholder")}
          className="font-mono"
          aria-label={t("batchInput")}
        />
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <p className="text-xs text-text-muted">
            {parsed.valid.length > 0
              ? t("parseSummary", { count: parsed.valid.length, invalid: parsed.invalid })
              : t("batchHint", { max: MAX_BATCH })}
            {parsed.overflow > 0 ? ` · ${t("overflow", { count: parsed.overflow })}` : ""}
          </p>
          <Button
            onClick={() => parsed.valid.length > 0 && mutation.mutate(parsed.valid)}
            disabled={!canSubmit}
            leftIcon={<ListChecks className="w-4 h-4" />}
            className="shrink-0"
          >
            {mutation.isPending ? t("searching") : t("batchQuery")}
          </Button>
        </div>
      </Card>

      {mutation.isError && (
        <Card className="p-4 border-status-failed-border bg-status-failed-bg">
          <div className="flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-status-failed-fg mt-0.5 shrink-0" />
            <p className="text-sm text-status-failed-fg">
              {mutation.error instanceof Error ? mutation.error.message : t("lookupFailed")}
            </p>
          </div>
        </Card>
      )}

      {mutation.isPending && (
        <Card className="p-6">
          <div className="animate-pulse space-y-3">
            <div className="h-3 bg-surface-hover rounded w-full" />
            <div className="h-3 bg-surface-hover rounded w-5/6" />
            <div className="h-3 bg-surface-hover rounded w-4/6" />
          </div>
        </Card>
      )}

      {mutation.isSuccess && mutation.data && (
        <Card className="p-4">
          <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
            <p className="text-xs text-text-muted">
              {t("batchSummary", { total: mutation.data.total })} ·{" "}
              <span className="text-status-failed-fg">
                {t("verdict_malicious")} {summary?.malicious ?? 0}
              </span>{" "}
              ·{" "}
              <span className="text-status-warning-fg">
                {t("verdict_suspicious")} {summary?.suspicious ?? 0}
              </span>{" "}
              ·{" "}
              <span className="text-status-success-fg">
                {t("verdict_benign")} {summary?.benign ?? 0}
              </span>
            </p>
            <code className="text-[10px] text-text-muted">
              {t("requestId")}: {mutation.data.request_id}
            </code>
          </div>

          {mutation.data.skipped_count > 0 && (
            <p className="text-xs text-status-warning-fg mb-3">
              {t("batchSkipped", { count: mutation.data.skipped_count })}
            </p>
          )}

          {mutation.data.results.length === 0 ? (
            <p className="text-sm text-text-muted py-6 text-center">{t("noResults")}</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr className="border-b border-border-subtle">
                    <th className="py-2 pr-3 text-xs font-medium text-text-muted">{t("colIoc")}</th>
                    <th className="py-2 pr-3 text-xs font-medium text-text-muted">
                      {t("colVerdict")}
                    </th>
                    <th className="py-2 pr-3 text-xs font-medium text-text-muted text-right">
                      {t("colScore")}
                    </th>
                    <th className="py-2 pr-3 text-xs font-medium text-text-muted text-right">
                      {t("colPulses")}
                    </th>
                    <th className="py-2 pr-3 text-xs font-medium text-text-muted">
                      {t("colSource")}
                    </th>
                    <th className="py-2 text-xs font-medium text-text-muted">{t("colTags")}</th>
                  </tr>
                </thead>
                <tbody>
                  {mutation.data.results.map((item, idx) => (
                    <BatchRow key={`${item.ioc_type}-${item.ioc_value}-${idx}`} item={item} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}

// ── Page ────────────────────────────────────────────────

type Tab = "single" | "batch";

export default function ThreatIntelPage() {
  const t = useTranslations("threatIntel");
  const [tab, setTab] = useState<Tab>("single");

  const tabs: Array<{ key: Tab; label: string; icon: React.ReactNode }> = [
    { key: "single", label: t("tabSingle"), icon: <Search className="w-4 h-4" /> },
    { key: "batch", label: t("tabBatch"), icon: <ListChecks className="w-4 h-4" /> },
  ];

  return (
    <div className="min-h-screen bg-surface-ground">
      <PageHeader title={t("title")} subtitle={t("description")} />

      <main className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Provider notice: the backend currently exposes OTX only. */}
        <Card className="p-3 border-border-subtle bg-surface-hover">
          <p className="text-xs text-text-muted">{t("providerNotice")}</p>
        </Card>

        {/* Tabs */}
        <div
          className="flex gap-1 border-b border-border-subtle"
          role="tablist"
          aria-label={t("title")}
        >
          {tabs.map((item) => (
            <button
              key={item.key}
              role="tab"
              aria-selected={tab === item.key}
              onClick={() => setTab(item.key)}
              className={
                tab === item.key
                  ? "flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-ai-fg border-b-2 border-ai-fg -mb-px"
                  : "flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-text-muted hover:text-text-primary border-b-2 border-transparent -mb-px"
              }
            >
              {item.icon}
              {item.label}
            </button>
          ))}
        </div>

        {tab === "single" ? <SingleLookupPanel /> : <BatchLookupPanel />}
      </main>
    </div>
  );
}
