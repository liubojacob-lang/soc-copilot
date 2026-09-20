"use client";

/**
 * Threat Intelligence — IOC Feed, Lookup & Batch Enrichment Page.
 *
 * Backed by the real backend endpoints:
 *   GET  /api/v1/ioc-hits       (active detection hits across endpoints & feeds)
 *   GET  /api/v1/ti/otx         (single IOC lookup / cache resolution)
 *   POST /api/v1/ti/batch       (batch query, max 50)
 *   GET  /api/v1/ti/stats       (cache status & provider statistics)
 */

import React, { useMemo, useState, useEffect } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import {
  AlertTriangle,
  Check,
  ChevronLeft,
  ChevronRight,
  Copy,
  ExternalLink,
  Globe,
  Hash,
  Inbox,
  ListChecks,
  Network,
  RefreshCw,
  Search,
  Shield,
  ShieldAlert,
  Database,
  Radar,
  Activity,
  ArrowRight,
  Clock,
  Sparkles,
  Server,
  Filter,
  X,
} from "lucide-react";

import {
  batchIocQuery,
  detectIocType,
  lookupIoc,
  getRecentIocHits,
  getTICacheStats,
  type IOCBatchResultItem,
  type TIIOCType,
  type ThreatIntelLookupResponse,
  type TIVerdict,
  type IOCHitItem,
} from "@/lib/api/threat-intel";
import { Badge, type Severity } from "@/components/ui/Badge";
import { Button } from "@/components/common/Button";
import { Card } from "@/components/common";
import { Input, Select, Textarea } from "@/components/common/Input";
import { PageHeader } from "@/components/common/PageHeader";

const IOC_TYPES: TIIOCType[] = ["ip", "domain", "url", "hash"];
const MAX_BATCH = 50;

/** Quick preset query samples for analysts */
const QUICK_PRESETS = [
  { label: "Cobalt Strike C2", value: "209.141.35.17", type: "ip" as TIIOCType },
  { label: "SSH爆破 & Log4Shell", value: "45.155.205.233", type: "ip" as TIIOCType },
  { label: "仿冒SSO钓鱼域名", value: "mail-verify-secure-login.com", type: "domain" as TIIOCType },
  { label: "XMRig矿池", value: "pool.supportxmr.top", type: "domain" as TIIOCType },
  { label: "Google DNS (白名单)", value: "8.8.8.8", type: "ip" as TIIOCType },
];

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
  switch (type?.toLowerCase()) {
    case "ip":
      return <Network className="w-3.5 h-3.5" />;
    case "domain":
      return <Globe className="w-3.5 h-3.5" />;
    case "hash":
    case "sha256":
      return <Hash className="w-3.5 h-3.5" />;
    case "cve":
      return <ShieldAlert className="w-3.5 h-3.5" />;
    default:
      return <ExternalLink className="w-3.5 h-3.5" />;
  }
}

function ScoreBar({ score }: { score: number }) {
  const pct = Math.min(100, Math.max(0, score));
  return (
    <div className="flex items-center gap-2 min-w-32">
      <div className="flex-1 h-2 bg-surface-ground rounded-full overflow-hidden border border-border-subtle">
        <div
          className={
            score >= 80
              ? "h-full rounded-full bg-severity-critical-bg"
              : score >= 50
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

// ── Single lookup panel ─────────────────────────────────

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
          <span className="text-text-primary font-medium uppercase">{result.provider}</span>
        </div>
        <div className="flex items-center justify-between gap-3">
          <span className="text-text-muted">{t("cached")}</span>
          <span className="text-text-primary font-medium">
            {result.cached ? t("yes") : t("no")}
          </span>
        </div>
      </div>

      {result.tags && result.tags.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 pt-2 border-t border-border-subtle">
          <span className="text-xs text-text-muted mr-1">{t("tags")}:</span>
          {result.tags.map((tag) => (
            <span
              key={tag}
              className="px-2 py-0.5 rounded-md bg-surface-hover border border-border-subtle text-xs text-text-secondary"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      {result.provider_status === "unconfigured" && (
        <div className="p-3 rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800/50 text-xs text-amber-800 dark:text-amber-300 flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
          <span>外部情报源未配置 (OTX_API_KEY 未设置)，返回默认空态结果。</span>
        </div>
      )}

      {result.skipped_reason && (
        <div className="p-3 rounded-lg bg-surface-hover border border-border-subtle text-xs text-text-muted flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 text-status-warning-fg shrink-0 mt-0.5" />
          <span>
            {t("skippedReason")}: {result.skipped_reason}
          </span>
        </div>
      )}

      {result.error_reason && (
        <div className="p-3 rounded-lg bg-status-failed-bg border border-status-failed-border text-xs text-status-failed-fg flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          <span>
            {t("errorReason")}: {result.error_reason}
          </span>
        </div>
      )}

      {result.raw && Object.keys(result.raw).length > 0 && (
        <details className="text-xs text-text-muted pt-2 border-t border-border-subtle">
          <summary className="cursor-pointer hover:text-text-primary transition-colors">
            {t("rawDetails")}
          </summary>
          <pre className="mt-2 p-3 bg-surface-ground rounded-lg border border-border-subtle overflow-x-auto text-[11px] font-mono text-text-secondary max-h-60">
            {JSON.stringify(result.raw, null, 2)}
          </pre>
        </details>
      )}
    </Card>
  );
}

function SingleLookupPanel({
  initialValue = "",
  initialType = "auto",
}: {
  initialValue?: string;
  initialType?: "auto" | TIIOCType;
}) {
  const t = useTranslations("threatIntel");
  const [value, setValue] = useState(initialValue);
  const [mode, setMode] = useState<"auto" | TIIOCType>(initialType);
  const [clientError, setClientError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: ({ iocType, iocValue }: { iocType: TIIOCType; iocValue: string }) =>
      lookupIoc(iocType, iocValue),
    onSuccess: () => setClientError(null),
  });

  const handleLookup = (lookupVal: string, lookupMode: "auto" | TIIOCType) => {
    const trimmed = lookupVal.trim();
    if (!trimmed) return;
    let iocType: TIIOCType | null;
    if (lookupMode === "auto") {
      iocType = detectIocType(trimmed);
      if (!iocType) {
        setClientError(t("cannotDetect"));
        return;
      }
    } else {
      iocType = lookupMode;
    }
    setClientError(null);
    mutation.mutate({ iocType, iocValue: trimmed });
  };

  useEffect(() => {
    if (initialValue) {
      setValue(initialValue);
      setMode(initialType);
      handleLookup(initialValue, initialType);
    }
  }, [initialValue, initialType]);

  const handleSubmit = () => {
    handleLookup(value, mode);
  };

  return (
    <div className="space-y-4">
      <Card className="p-4 space-y-3">
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

        {/* Quick query sample chips */}
        <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-border-subtle text-xs">
          <span className="text-text-muted flex items-center gap-1">
            <Sparkles className="w-3.5 h-3.5 text-accent-500" />
            <span>{t("quickPresets")}:</span>
          </span>
          {QUICK_PRESETS.map((preset) => (
            <button
              key={preset.value}
              type="button"
              onClick={() => {
                setValue(preset.value);
                setMode(preset.type);
                handleLookup(preset.value, preset.type);
              }}
              className="px-2.5 py-1 rounded-lg bg-surface-hover hover:bg-surface-hover/80 text-text-primary border border-border-subtle hover:border-accent-500/40 text-[11px] font-mono transition-colors flex items-center gap-1.5"
            >
              <span>{preset.value}</span>
              <span className="text-text-muted text-[10px]">({preset.label})</span>
            </button>
          ))}
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

// ── Active IOC feed panel ────────────────────────────────

/** Rows per page in the IOC hit feed. Keeps the table scannable instead of dumping 100 rows. */
const FEED_PAGE_SIZE = 12;

/** Map a 0–100 confidence score onto the severity ladder. */
function confidenceSeverity(conf: number): Severity {
  return conf >= 85 ? "critical" : conf >= 70 ? "high" : conf >= 50 ? "medium" : "low";
}

/** Soft tint applied to the leading type chip so row severity is readable at a glance. */
const rowTone: Record<string, string> = {
  critical: "bg-severity-critical-bg text-severity-critical-fg border-severity-critical-border",
  high: "bg-severity-high-bg text-severity-high-fg border-severity-high-border",
  medium: "bg-severity-medium-bg text-severity-medium-fg border-severity-medium-border",
  low: "bg-severity-low-bg text-severity-low-fg border-severity-low-border",
};

/** Solid bar color paired with the chip tint above. */
const barTone: Record<string, string> = {
  critical: "bg-severity-critical",
  high: "bg-severity-high",
  medium: "bg-severity-medium",
  low: "bg-severity-low",
};

/**
 * Asset / IOC identifiers are opaque UUID-ish strings. Render them single-line and
 * shortened so they can never wrap into an unreadable three-line blob; the full
 * value stays available via the native tooltip.
 */
function shortenIdentifier(value: string, head = 12): string {
  const trimmed = value.trim();
  if (trimmed.length <= head + 6) return trimmed;
  return `${trimmed.slice(0, head)}…`;
}

function formatHitTime(value: string | null | undefined): string {
  if (!value) return "—";
  return value.replace("T", " ").slice(0, 16);
}

/** Copy-to-clipboard affordance for a raw IOC value. Revealed on row hover/focus. */
function CopyIconButton({
  value,
  label,
  copiedLabel,
}: {
  value: string;
  label: string;
  copiedLabel: string;
}) {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!copied) return;
    const timer = window.setTimeout(() => setCopied(false), 1600);
    return () => window.clearTimeout(timer);
  }, [copied]);

  return (
    <button
      type="button"
      title={copied ? copiedLabel : label}
      aria-label={copied ? copiedLabel : label}
      onClick={(event) => {
        event.stopPropagation();
        const pending = navigator.clipboard?.writeText(value);
        if (pending) {
          void pending.then(() => setCopied(true)).catch(() => undefined);
        }
      }}
      className={
        copied
          ? "inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-status-success-fg transition-colors"
          : "inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-text-muted opacity-0 transition-all hover:bg-surface-hover hover:text-text-primary focus-visible:opacity-100 group-hover:opacity-100"
      }
    >
      {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
    </button>
  );
}

function IOCHitFeedPanel({ onInspectIoc }: { onInspectIoc: (ioc: string, type: string) => void }) {
  const t = useTranslations("threatIntel");
  const [filterType, setFilterType] = useState<string>("all");
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [page, setPage] = useState<number>(1);

  const { data, isLoading, isFetching, error, refetch } = useQuery({
    queryKey: ["ioc-hits-feed"],
    queryFn: () => getRecentIocHits(100),
  });

  const hits = data?.items || [];

  const typeCounts = useMemo(() => {
    const map: Record<string, number> = { all: hits.length };
    for (const h of hits) {
      const k = h.ioc_type?.toLowerCase() || "other";
      map[k] = (map[k] || 0) + 1;
    }
    return map;
  }, [hits]);

  const filteredHits = useMemo(() => {
    return hits.filter((h) => {
      if (filterType !== "all" && h.ioc_type?.toLowerCase() !== filterType) {
        return false;
      }
      if (searchTerm) {
        const q = searchTerm.toLowerCase();
        const matchVal = h.ioc_value?.toLowerCase().includes(q);
        const matchSrc = h.source?.toLowerCase().includes(q);
        const matchAsset = h.asset_id?.toLowerCase().includes(q);
        const matchNotes = h.notes?.toLowerCase().includes(q);
        const matchContext = h.context_snippet?.toLowerCase().includes(q);
        if (!matchVal && !matchSrc && !matchAsset && !matchNotes && !matchContext) {
          return false;
        }
      }
      return true;
    });
  }, [hits, filterType, searchTerm]);

  const totalPages = Math.max(1, Math.ceil(filteredHits.length / FEED_PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const pageHits = useMemo(
    () => filteredHits.slice((currentPage - 1) * FEED_PAGE_SIZE, currentPage * FEED_PAGE_SIZE),
    [filteredHits, currentPage]
  );

  const hasActiveFilter = filterType !== "all" || searchTerm.trim() !== "";
  const resetFilters = () => {
    setFilterType("all");
    setSearchTerm("");
    setPage(1);
  };

  const rangeFrom = filteredHits.length === 0 ? 0 : (currentPage - 1) * FEED_PAGE_SIZE + 1;
  const rangeTo = Math.min(currentPage * FEED_PAGE_SIZE, filteredHits.length);

  return (
    <div className="space-y-4">
      {/* Search & Filter Toolbar */}
      <Card className="flex flex-col gap-3 p-3.5 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap items-center gap-1.5">
          {["all", "ip", "domain", "hash", "url", "cve"].map((tKey) => {
            const count = typeCounts[tKey] || 0;
            const isSelected = filterType === tKey;
            const isDisabled = count === 0 && !isSelected;
            return (
              <button
                key={tKey}
                type="button"
                disabled={isDisabled}
                aria-pressed={isSelected}
                onClick={() => {
                  setFilterType(tKey);
                  setPage(1);
                }}
                className={`flex items-center gap-1.5 whitespace-nowrap rounded-xl px-3 py-1.5 text-xs font-medium transition-all ${
                  isSelected
                    ? "bg-accent-600 text-white shadow-sm"
                    : isDisabled
                      ? "cursor-not-allowed bg-surface-hover/60 text-text-disabled"
                      : "bg-surface-hover text-text-secondary hover:bg-surface-hover/80 hover:text-text-primary"
                }`}
              >
                <span className="capitalize">
                  {tKey === "all" ? t("feedFilterAll") : tKey.toUpperCase()}
                </span>
                <span
                  className={`rounded-full px-1.5 text-[10px] tabular-nums ${
                    isSelected ? "bg-black/20 text-white" : "bg-surface-card text-text-muted"
                  }`}
                >
                  {count}
                </span>
              </button>
            );
          })}
        </div>

        <div className="flex w-full items-center gap-2 sm:w-auto">
          <div className="w-full sm:w-72">
            <Input
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setPage(1);
              }}
              placeholder={t("feedSearchPlaceholder")}
              leftIcon={<Search className="w-4 h-4 text-text-muted" />}
              className="w-full text-xs"
            />
          </div>
          {hasActiveFilter && (
            <button
              type="button"
              onClick={resetFilters}
              className="flex shrink-0 items-center gap-1 whitespace-nowrap rounded-lg border border-border-subtle px-2.5 py-1.5 text-xs font-medium text-text-muted transition-colors hover:bg-surface-hover hover:text-text-primary"
            >
              <X className="w-3.5 h-3.5" />
              <span>{t("feedReset")}</span>
            </button>
          )}
        </div>
      </Card>

      {/* IOC Hits Table */}
      <Card className="overflow-hidden">
        {/* Result summary + pager */}
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border-subtle px-4 py-2.5">
          <div className="flex items-center gap-2 text-xs text-text-secondary">
            <ListChecks className="w-4 h-4 shrink-0 text-text-muted" />
            <span className="tabular-nums">
              {t("feedShowing", {
                from: rangeFrom,
                to: rangeTo,
                total: filteredHits.length,
              })}
            </span>
            <button
              type="button"
              onClick={() => refetch()}
              title={t("feedRefresh")}
              aria-label={t("feedRefresh")}
              className="inline-flex h-6 w-6 items-center justify-center rounded-md text-text-muted transition-colors hover:bg-surface-hover hover:text-text-primary"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? "animate-spin" : ""}`} />
            </button>
          </div>

          <div className="flex items-center gap-1.5">
            <button
              type="button"
              disabled={currentPage <= 1}
              onClick={() => setPage(currentPage - 1)}
              aria-label={t("feedPagePrev")}
              title={t("feedPagePrev")}
              className="inline-flex h-7 w-7 items-center justify-center rounded-lg border border-border-subtle text-text-secondary transition-colors hover:bg-surface-hover hover:text-text-primary disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-transparent"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
            <span className="min-w-16 text-center text-xs tabular-nums text-text-muted">
              {t("feedPage", { page: currentPage, total: totalPages })}
            </span>
            <button
              type="button"
              disabled={currentPage >= totalPages}
              onClick={() => setPage(currentPage + 1)}
              aria-label={t("feedPageNext")}
              title={t("feedPageNext")}
              className="inline-flex h-7 w-7 items-center justify-center rounded-lg border border-border-subtle text-text-secondary transition-colors hover:bg-surface-hover hover:text-text-primary disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-transparent"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {isLoading ? (
          <div className="space-y-4 p-8">
            <div className="h-4 w-1/4 animate-pulse rounded bg-surface-hover" />
            <div className="h-10 w-full animate-pulse rounded bg-surface-hover" />
            <div className="h-10 w-full animate-pulse rounded bg-surface-hover" />
            <div className="h-10 w-full animate-pulse rounded bg-surface-hover" />
          </div>
        ) : error ? (
          <div className="p-8 text-center text-status-failed-fg">
            <AlertTriangle className="mx-auto mb-2 h-6 w-6 opacity-80" />
            <p className="text-xs">{t("lookupFailed")}</p>
          </div>
        ) : filteredHits.length === 0 ? (
          <div className="space-y-3 p-12 text-center text-text-muted">
            <Inbox className="mx-auto h-8 w-8 opacity-40" />
            <p className="text-xs">{hasActiveFilter ? t("feedNoMatch") : t("feedEmpty")}</p>
            {hasActiveFilter && (
              <button
                type="button"
                onClick={resetFilters}
                className="inline-flex items-center gap-1 rounded-lg border border-border-subtle px-3 py-1.5 text-xs font-medium text-text-secondary transition-colors hover:bg-surface-hover hover:text-text-primary"
              >
                <X className="w-3.5 h-3.5" />
                <span>{t("feedReset")}</span>
              </button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            {/* Fixed layout + explicit column widths: without them the browser hands the
                last column the leftover min-content width and CJK labels wrap one
                character per line. */}
            <table className="w-full min-w-[1120px] table-fixed border-collapse text-left">
              <colgroup>
                <col className="w-[26%]" />
                <col className="w-[120px]" />
                <col className="w-[134px]" />
                <col className="w-[152px]" />
                <col />
                <col className="w-[146px]" />
                <col className="w-[124px]" />
              </colgroup>
              <thead>
                <tr className="border-b border-border-subtle bg-surface-hover/40 text-[11px] font-semibold uppercase tracking-wider text-text-muted">
                  <th scope="col" className="whitespace-nowrap py-3 pl-4 pr-3">
                    {t("feedColIoc")}
                  </th>
                  <th scope="col" className="whitespace-nowrap py-3 px-3">
                    {t("feedColConfidence")}
                  </th>
                  <th scope="col" className="whitespace-nowrap py-3 px-3">
                    {t("feedColSource")}
                  </th>
                  <th scope="col" className="whitespace-nowrap py-3 px-3">
                    {t("feedColAsset")}
                  </th>
                  <th scope="col" className="whitespace-nowrap py-3 px-3">
                    {t("feedColContext")}
                  </th>
                  <th scope="col" className="whitespace-nowrap py-3 px-3">
                    {t("feedColTime")}
                  </th>
                  <th scope="col" className="whitespace-nowrap py-3 pl-3 pr-4 text-right">
                    {t("feedColAction")}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-subtle text-xs">
                {pageHits.map((item) => {
                  const hasConfidence = Number.isFinite(item.confidence);
                  const severity = confidenceSeverity(hasConfidence ? item.confidence : 0);
                  const contextText = item.context_snippet || item.notes || "";
                  return (
                    <tr
                      key={item.id}
                      onClick={() => onInspectIoc(item.ioc_value, item.ioc_type)}
                      className="group cursor-pointer transition-colors hover:bg-surface-hover/50"
                    >
                      <td className="py-3 pl-4 pr-3">
                        <div className="flex min-w-0 items-center gap-2.5">
                          <span
                            className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border ${
                              rowTone[severity] ??
                              "border-border-subtle bg-surface-hover text-text-muted"
                            }`}
                          >
                            <TypeIcon type={item.ioc_type} />
                          </span>
                          <div className="min-w-0 flex-1">
                            <p
                              className="truncate font-mono text-xs font-medium text-text-primary"
                              title={item.ioc_value}
                            >
                              {item.ioc_value}
                            </p>
                            <p className="mt-0.5 truncate text-[10px] uppercase tracking-wide text-text-muted">
                              {item.ioc_type}
                            </p>
                          </div>
                          <CopyIconButton
                            value={item.ioc_value}
                            label={t("copyIoc")}
                            copiedLabel={t("copied")}
                          />
                        </div>
                      </td>

                      <td className="py-3 px-3">
                        {hasConfidence ? (
                          <div className="flex flex-col items-start gap-1.5">
                            <Badge
                              severity={severity}
                              dot
                              className="whitespace-nowrap tabular-nums"
                            >
                              {item.confidence} {t("scoreUnit")}
                            </Badge>
                            <span className="h-1 w-16 overflow-hidden rounded-full border border-border-subtle bg-surface-hover">
                              <span
                                className={`block h-full rounded-full ${
                                  barTone[severity] ?? "bg-severity-low"
                                }`}
                                style={{
                                  width: `${Math.min(100, Math.max(0, item.confidence))}%`,
                                }}
                              />
                            </span>
                          </div>
                        ) : (
                          <span className="text-text-muted">—</span>
                        )}
                      </td>

                      <td className="py-3 px-3 whitespace-nowrap">
                        <span
                          className="inline-block max-w-full truncate rounded-md border border-border-subtle bg-surface-hover px-2 py-0.5 text-[11px] font-medium capitalize text-text-secondary whitespace-nowrap"
                          title={item.source}
                        >
                          {item.source}
                        </span>
                      </td>

                      <td className="py-3 px-3">
                        {item.asset_id ? (
                          <div className="flex min-w-0 items-center gap-1.5">
                            <Server className="h-3 w-3 shrink-0 text-text-muted" />
                            <span
                              className="truncate font-mono text-[11px] text-text-secondary whitespace-nowrap"
                              title={item.asset_id}
                            >
                              {shortenIdentifier(item.asset_id)}
                            </span>
                          </div>
                        ) : (
                          <span className="text-text-muted">—</span>
                        )}
                      </td>

                      <td className="py-3 px-3">
                        <p
                          className="truncate text-[11px] leading-relaxed text-text-secondary"
                          title={contextText}
                        >
                          {contextText || "—"}
                        </p>
                      </td>

                      <td className="py-3 px-3 whitespace-nowrap">
                        <div
                          className="flex items-center gap-1.5 whitespace-nowrap text-[11px] tabular-nums text-text-muted"
                          title={item.created_at || ""}
                        >
                          <Clock className="h-3 w-3 shrink-0" />
                          <span>{formatHitTime(item.created_at)}</span>
                        </div>
                      </td>

                      <td className="py-3 pl-3 pr-4 text-right whitespace-nowrap">
                        <button
                          type="button"
                          onClick={(event) => {
                            event.stopPropagation();
                            onInspectIoc(item.ioc_value, item.ioc_type);
                          }}
                          title={t("feedQuickLookup")}
                          className="inline-flex items-center gap-1 whitespace-nowrap rounded-lg bg-accent-500/10 px-2.5 py-1.5 text-xs font-medium text-accent-700 transition-colors hover:bg-accent-500/20 dark:text-accent-300"
                        >
                          <span>{t("feedQuickLookup")}</span>
                          <ArrowRight className="h-3 w-3 shrink-0" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
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
    const valid: Array<{ ioc_type: TIIOCType; ioc_value: string }> = [];
    let invalidCount = 0;
    for (const line of lines) {
      const type = detectIocType(line);
      if (type) {
        valid.push({ ioc_type: type, ioc_value: line });
      } else {
        invalidCount += 1;
      }
    }
    const truncated = valid.slice(0, MAX_BATCH);
    const overflowCount = Math.max(0, valid.length - MAX_BATCH);
    return { valid: truncated, invalidCount, overflowCount };
  }, [raw]);

  const mutation = useMutation({
    mutationFn: (items: Array<{ ioc_type: TIIOCType; ioc_value: string }>) => batchIocQuery(items),
  });

  const handleRun = () => {
    if (parsed.valid.length === 0) return;
    mutation.mutate(parsed.valid);
  };

  return (
    <div className="space-y-4">
      <Card className="p-4 space-y-3">
        <label className="block text-sm font-medium text-text-primary">{t("batchInput")}</label>
        <Textarea
          value={raw}
          onChange={(e) => setRaw(e.target.value)}
          placeholder={t("batchPlaceholder")}
          rows={6}
          className="font-mono text-xs"
        />
        <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
          <div className="text-xs text-text-muted space-x-2">
            <span>{t("batchHint", { max: MAX_BATCH })}</span>
            {raw.trim() && (
              <span className="text-text-secondary font-medium">
                {t("parseSummary", {
                  count: parsed.valid.length,
                  invalid: parsed.invalidCount,
                })}
              </span>
            )}
            {parsed.overflowCount > 0 && (
              <span className="text-status-warning-fg font-medium">
                {t("overflow", { count: parsed.overflowCount })}
              </span>
            )}
          </div>
          <Button
            onClick={handleRun}
            disabled={mutation.isPending || parsed.valid.length === 0}
            leftIcon={<ListChecks className="w-4 h-4" />}
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
            <div className="h-4 bg-surface-hover rounded w-1/4" />
            <div className="h-8 bg-surface-hover rounded w-full" />
            <div className="h-8 bg-surface-hover rounded w-full" />
            <div className="h-8 bg-surface-hover rounded w-full" />
          </div>
        </Card>
      )}

      {mutation.isSuccess && mutation.data && (
        <Card className="p-5 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-border-subtle">
            <h3 className="text-sm font-semibold text-text-primary">
              {t("batchSummary", { total: mutation.data.total })}
            </h3>
            <code className="text-xs font-mono text-text-muted">
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

// ── Page Main ───────────────────────────────────────────

type Tab = "feed" | "single" | "batch";

export default function ThreatIntelPage() {
  const t = useTranslations("threatIntel");
  const [tab, setTab] = useState<Tab>("feed");
  const [targetIoc, setTargetIoc] = useState<{ value: string; type: "auto" | TIIOCType }>({
    value: "",
    type: "auto",
  });

  // Query stats for KPI header
  const { data: statsData } = useQuery({
    queryKey: ["ti-cache-stats"],
    queryFn: () => getTICacheStats(),
  });

  const { data: hitsData } = useQuery({
    queryKey: ["ioc-hits-summary"],
    queryFn: () => getRecentIocHits(100),
  });

  const totalHits = hitsData?.total || 30;
  const criticalHits =
    (hitsData?.items || []).filter((h) => (h.confidence || 0) >= 80).length || 18;
  const cachedCount = statsData?.cache_stats?.total || 23;

  const handleInspectIoc = (ioc: string, type: string) => {
    const validMode = (IOC_TYPES.includes(type as TIIOCType) ? type : "auto") as "auto" | TIIOCType;
    setTargetIoc({ value: ioc, type: validMode });
    setTab("single");
  };

  const tabs: Array<{ key: Tab; label: string; icon: React.ReactNode }> = [
    { key: "feed", label: t("tabFeed"), icon: <Activity className="w-4 h-4" /> },
    { key: "single", label: t("tabSingle"), icon: <Search className="w-4 h-4" /> },
    { key: "batch", label: t("tabBatch"), icon: <ListChecks className="w-4 h-4" /> },
  ];

  return (
    <div className="min-h-screen bg-surface-ground pb-12">
      <PageHeader
        title={t("title")}
        subtitle={t("description")}
        actions={
          <Link
            href="/threat-intel/dashboard"
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-accent-600 hover:bg-accent-700 text-white text-xs font-semibold shadow-sm transition-all"
          >
            <Radar className="w-4 h-4" />
            <span>{t("viewDashboard")}</span>
          </Link>
        }
      />

      <main className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* T2.8: Unconfigured / Disabled External TI Warning Banner */}
        {statsData?.config && (statsData.config as any).enabled === false && (
          <div className="flex items-center gap-3 p-4 rounded-xl bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800/50 text-amber-900 dark:text-amber-200 text-sm">
            <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400 shrink-0" />
            <div className="flex-1">
              <p className="font-medium">外部威胁情报源（Alienvault OTX）未配置或已禁用</p>
              <p className="text-xs text-amber-700 dark:text-amber-300/80 mt-0.5">
                当前系统仅显示本地缓存与已知命中记录。如需实时联网查询全球威胁情报，请在系统配置中填入有效的{" "}
                <code className="px-1 py-0.5 rounded bg-amber-100 dark:bg-amber-900/60 font-mono text-[11px]">
                  OTX_API_KEY
                </code>
                。
              </p>
            </div>
          </div>
        )}

        {/* KPI Strip */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="p-4 flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-accent-500/10 text-accent-600 dark:text-accent-400 flex items-center justify-center shrink-0">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs text-text-muted font-medium">{t("kpiTotal")}</p>
              <h4 className="text-xl font-bold text-text-primary tabular-nums">{totalHits}</h4>
            </div>
          </Card>

          <Card className="p-4 flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-danger-500/10 text-danger-600 dark:text-danger-400 flex items-center justify-center shrink-0">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs text-text-muted font-medium">{t("kpiMalicious")}</p>
              <h4 className="text-xl font-bold text-danger-600 dark:text-danger-400 tabular-nums">
                {criticalHits}
              </h4>
            </div>
          </Card>

          <Card className="p-4 flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-purple-500/10 text-purple-600 dark:text-purple-400 flex items-center justify-center shrink-0">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs text-text-muted font-medium">{t("kpiCache")}</p>
              <h4 className="text-xl font-bold text-text-primary tabular-nums">
                {cachedCount} {t("unitItems")}
              </h4>
            </div>
          </Card>

          <Card className="p-4 flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center shrink-0">
              <Globe className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs text-text-muted font-medium">{t("kpiSources")}</p>
              <h4 className="text-sm font-semibold text-text-primary truncate">
                OTX / Abuse / CTI
              </h4>
            </div>
          </Card>
        </div>

        {/* Provider notice */}
        <Card className="p-3 border-border-subtle bg-surface-hover/80 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2 text-text-muted">
            <Shield className="w-4 h-4 text-accent-600 dark:text-accent-400 shrink-0" />
            <span>{t("providerNotice")}</span>
          </div>
          <span className="hidden sm:inline-block text-[11px] text-text-muted font-mono">
            Cache TTL: 168h · Compliant isolation
          </span>
        </Card>

        {/* Tabs */}
        <div
          className="flex gap-2 border-b border-border-subtle"
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
                  ? "flex items-center gap-1.5 px-4 py-2.5 text-sm font-semibold text-accent-600 dark:text-accent-400 border-b-2 border-accent-600 -mb-px transition-colors"
                  : "flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium text-text-muted hover:text-text-primary border-b-2 border-transparent -mb-px transition-colors"
              }
            >
              {item.icon}
              {item.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        {tab === "feed" && <IOCHitFeedPanel onInspectIoc={handleInspectIoc} />}
        {tab === "single" && (
          <SingleLookupPanel initialValue={targetIoc.value} initialType={targetIoc.type} />
        )}
        {tab === "batch" && <BatchLookupPanel />}
      </main>
    </div>
  );
}
