"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { Link, useRouter } from "@/i18n/navigation";
import { useTranslations, useFormatter } from "next-intl";
import ReactMarkdown from "react-markdown";
import { loadAuthState, authFetchJSON } from "@/lib/auth";
import { PageHeader } from "@/components/common/PageHeader";
import {
  FileText,
  Download,
  Plus,
  Copy,
  Check,
  Ticket,
  BarChart3,
  ClipboardList,
  History,
  Clock,
  RotateCcw,
  Eye,
  Code2,
  Layers,
  ChevronRight,
  AlertCircle,
  ArrowRight,
  Loader2,
  X,
} from "lucide-react";

interface ReportTemplate {
  id: string;
  name: string;
  description: string;
  icon: React.ReactNode;
}

interface ReportHistoryItem {
  id: string;
  module: string;
  created_at: string;
  input_text: string;
  output_json?: GeneratedReports | string | null;
  output_markdown?: string | null;
  model_used?: string | null;
}

type ReportTemplateId = "ticket" | "daily" | "postmortem";
type ReportTab = "all" | ReportTemplateId;

/** 历史记录里的 input_text 形如 `Alert: {...}`，且可能被后端截断（以 `...` 结尾）。 */
interface ParsedAlertInput {
  id?: string;
  title?: string;
}

const TEMPLATE_FIELD: Record<ReportTemplateId, keyof GeneratedReports> = {
  ticket: "ticket_template",
  daily: "daily_report_template",
  postmortem: "postmortem_template",
};

interface GeneratedReports {
  ticket_template?: string;
  daily_report_template?: string;
  postmortem_template?: string;
}

function countTemplates(reports: GeneratedReports | null): number {
  if (!reports) return 0;
  return (Object.keys(TEMPLATE_FIELD) as ReportTemplateId[]).filter((id) =>
    Boolean(reports[TEMPLATE_FIELD[id]])
  ).length;
}

/**
 * 从历史记录的 input_text 中提取可读的告警信息。
 * 优先按 JSON 解析，失败（截断 / 非法 JSON）时退回正则抽取，绝不把原始 JSON 丢到界面上。
 */
function parseAlertInput(input?: string | null): ParsedAlertInput {
  if (!input) return {};
  const raw = input
    .replace(/^Alert:\s*/i, "")
    .trim()
    .replace(/\.\.\.$/, "");
  if (!raw) return {};

  try {
    const obj = JSON.parse(raw) as Record<string, unknown>;
    return {
      id: obj.id != null && obj.id !== "" ? String(obj.id) : undefined,
      title: typeof obj.title === "string" && obj.title.trim() ? obj.title.trim() : undefined,
    };
  } catch {
    const idMatch = raw.match(/"id"\s*:\s*"?([\w.-]+)"?/);
    const titleMatch = raw.match(/"title"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"/);
    return { id: idMatch?.[1], title: titleMatch?.[1]?.trim() || undefined };
  }
}

/** 历史条目里可用的模板数量：output_json 可能是对象，也可能是被字符串化的 JSON。 */
function historyTemplateCount(item: ReportHistoryItem): number {
  if (typeof item.output_json === "string") {
    try {
      return countTemplates(JSON.parse(item.output_json) as GeneratedReports);
    } catch {
      return item.output_markdown ? 1 : 0;
    }
  }
  if (item.output_json) return countTemplates(item.output_json);
  return item.output_markdown ? 1 : 0;
}

function MarkdownRenderer({ content }: { content: string }) {
  return (
    <ReactMarkdown
      components={{
        table({ children }) {
          return (
            <div className="overflow-x-auto my-3 rounded-lg border border-border-subtle">
              <table className="min-w-full divide-y divide-border-subtle text-xs">{children}</table>
            </div>
          );
        },
        thead({ children }) {
          return <thead className="bg-surface-ground font-medium">{children}</thead>;
        },
        th({ children }) {
          return (
            <th className="px-3 py-2 text-left text-xs font-semibold text-text-primary border-b border-border-subtle">
              {children}
            </th>
          );
        },
        td({ children }) {
          return (
            <td className="px-3 py-2 text-xs text-text-secondary border-b border-border-subtle/50">
              {children}
            </td>
          );
        },
        h1({ children }) {
          return (
            <h1 className="text-lg font-bold my-4 first:mt-0 text-text-primary border-b border-border-subtle pb-2">
              {children}
            </h1>
          );
        },
        h2({ children }) {
          return (
            <h2 className="text-base font-bold mt-4 mb-2 first:mt-0 text-text-primary">
              {children}
            </h2>
          );
        },
        h3({ children }) {
          return (
            <h3 className="text-sm font-bold mt-3.5 mb-1.5 first:mt-0 text-text-secondary uppercase tracking-wide">
              {children}
            </h3>
          );
        },
        p({ children }) {
          return (
            <p className="mb-3 last:mb-0 leading-relaxed text-text-primary text-sm">{children}</p>
          );
        },
        ul({ children }) {
          return (
            <ul className="list-disc pl-5 my-2.5 space-y-1.5 text-text-primary text-sm">
              {children}
            </ul>
          );
        },
        ol({ children }) {
          return (
            <ol className="list-decimal pl-5 my-2.5 space-y-1.5 text-text-primary text-sm">
              {children}
            </ol>
          );
        },
        li({ children }) {
          return <li className="leading-relaxed">{children}</li>;
        },
        code({ className, children, ...props }: React.HTMLAttributes<HTMLElement>) {
          return (
            <code
              className={`px-1.5 py-0.5 rounded bg-surface-ground border border-border-subtle text-accent-600 dark:text-accent-400 font-mono text-xs ${className ?? ""}`}
              {...props}
            >
              {children}
            </code>
          );
        },
        blockquote({ children }) {
          return (
            <blockquote className="border-l-4 border-accent-500/50 pl-3 my-2 text-text-secondary italic bg-accent-50/20 dark:bg-accent-950/20 py-1 rounded-r">
              {children}
            </blockquote>
          );
        },
        hr() {
          return <hr className="my-3 border-border-subtle" />;
        },
      }}
    >
      {content}
    </ReactMarkdown>
  );
}

export default function ReportsPage() {
  const t = useTranslations("reports");
  const tCommon = useTranslations("common");
  const format = useFormatter();
  const router = useRouter();

  const TEMPLATES: ReportTemplate[] = [
    {
      id: "ticket",
      name: t("templates.ticket.name"),
      description: t("templates.ticket.description"),
      icon: <Ticket className="w-5 h-5 text-accent-500" />,
    },
    {
      id: "daily",
      name: t("templates.daily.name"),
      description: t("templates.daily.description"),
      icon: <BarChart3 className="w-5 h-5 text-emerald-500" />,
    },
    {
      id: "postmortem",
      name: t("templates.postmortem.name"),
      description: t("templates.postmortem.description"),
      icon: <ClipboardList className="w-5 h-5 text-amber-500" />,
    },
  ];

  const [generating, setGenerating] = useState(false);
  const [alertId, setAlertId] = useState("");
  const [additionalNotes, setAdditionalNotes] = useState("");
  const [generatedReports, setGeneratedReports] = useState<GeneratedReports | null>(null);
  const [copiedTemplate, setCopiedTemplate] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [historyList, setHistoryList] = useState<ReportHistoryItem[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [historyError, setHistoryError] = useState("");
  const [selectedHistoryId, setSelectedHistoryId] = useState<string | null>(null);
  const [selectedTab, setSelectedTab] = useState<ReportTab>("all");
  const [viewMode, setViewMode] = useState<"preview" | "raw">("preview");

  /** 右侧详情面板唯一的滚动容器：切 tab / 选历史 / 新生成时都回到顶部，保证滚动连贯。 */
  const detailsScrollRef = useRef<HTMLDivElement>(null);
  const scrollDetailsToTop = useCallback(() => {
    requestAnimationFrame(() => {
      detailsScrollRef.current?.scrollTo({ top: 0, behavior: "smooth" });
    });
  }, []);

  /** 统一写入入口：当前 tab 在新报告里不存在时回落到「全部模板」，避免空白详情页。 */
  const applyGeneratedReports = useCallback(
    (reports: GeneratedReports | null) => {
      setGeneratedReports(reports);
      setSelectedTab((tab) => (tab === "all" || reports?.[TEMPLATE_FIELD[tab]] ? tab : "all"));
      scrollDetailsToTop();
    },
    [scrollDetailsToTop]
  );

  const switchTab = (tab: ReportTab) => {
    setSelectedTab(tab);
    scrollDetailsToTop();
  };

  const closeReport = () => {
    setGeneratedReports(null);
    setSelectedHistoryId(null);
    setSelectedTab("all");
    scrollDetailsToTop();
  };

  const fetchHistory = useCallback(async () => {
    try {
      setLoadingHistory(true);
      setHistoryError("");
      const res = await authFetchJSON<{ items: ReportHistoryItem[]; total: number }>(
        "/api/v1/history?module=report&limit=20"
      );
      setHistoryList(res?.items || []);
    } catch (e) {
      console.error("Failed to load report history:", e);
      setHistoryError(e instanceof Error ? e.message : t("historyLoadFailed"));
    } finally {
      setLoadingHistory(false);
    }
  }, [t]);

  useEffect(() => {
    const authState = loadAuthState();
    if (!authState?.isAuthenticated) {
      router.push("/login");
    } else {
      fetchHistory();
    }
  }, [router, fetchHistory]);

  const generateReports = async () => {
    if (!alertId.trim()) {
      setError(t("enterAlertId"));
      return;
    }

    const requestedAlertId = alertId.trim();
    setGenerating(true);
    setError("");
    setGeneratedReports(null);
    setSelectedHistoryId(null);
    setSelectedTab("all");
    setViewMode("preview");
    scrollDetailsToTop();

    try {
      const alertData = await authFetchJSON<Record<string, unknown>>(
        `/api/security-alerts/${encodeURIComponent(requestedAlertId)}`
      );

      const response = await authFetchJSON<GeneratedReports>("/api/generate-report", {
        method: "POST",
        body: JSON.stringify({
          alert_json: JSON.stringify(alertData),
          additional_notes: additionalNotes,
        }),
      });

      applyGeneratedReports(response ?? null);
      fetchHistory();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t("generateFailed"));
    } finally {
      setGenerating(false);
    }
  };

  const selectHistoryItem = (item: ReportHistoryItem) => {
    setSelectedHistoryId(item.id);
    setError("");

    let parsed: GeneratedReports | null = null;
    if (typeof item.output_json === "string") {
      try {
        parsed = JSON.parse(item.output_json) as GeneratedReports;
      } catch {
        parsed = null;
      }
    } else if (item.output_json) {
      parsed = item.output_json;
    }

    if (parsed && countTemplates(parsed) > 0) {
      applyGeneratedReports(parsed);
      return;
    }
    if (item.output_markdown) {
      applyGeneratedReports({ ticket_template: item.output_markdown });
      return;
    }

    applyGeneratedReports(null);
    setError(t("reportUnavailable"));
  };

  const copyToClipboard = async (content: string, templateId: string) => {
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(content);
      } else {
        throw new Error("Clipboard API unavailable");
      }
      setCopiedTemplate(templateId);
      setTimeout(() => setCopiedTemplate(null), 2000);
    } catch {
      setError(t("copyFailed"));
    }
  };

  const downloadReportMarkdown = (title: string, content: string) => {
    const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${title.toLowerCase().replace(/\s+/g, "_")}_${new Date().toISOString().slice(0, 10)}.md`;
    document.body.appendChild(a);
    a.click();
    URL.revokeObjectURL(url);
    document.body.removeChild(a);
  };

  const hasTicket = Boolean(generatedReports?.ticket_template);
  const hasDaily = Boolean(generatedReports?.daily_report_template);
  const hasPostmortem = Boolean(generatedReports?.postmortem_template);
  const availableTemplatesCount = [hasTicket, hasDaily, hasPostmortem].filter(Boolean).length;

  const renderTemplateCard = (
    templateId: ReportTemplateId,
    title: string,
    icon: React.ReactNode,
    content: string,
    isSingleView: boolean
  ) => {
    return (
      <div
        key={templateId}
        className={`bg-surface-card rounded-xl border border-border-subtle shadow-subtle overflow-hidden flex flex-col ${
          isSingleView ? "h-full flex-1 min-h-0" : ""
        }`}
      >
        <div className="flex justify-between items-center p-3.5 sm:p-4 bg-surface-ground border-b border-border-subtle shrink-0">
          <div className="flex items-center gap-2.5">
            {icon}
            <h3 className="font-semibold text-text-primary text-sm">{title}</h3>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => downloadReportMarkdown(title, content)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-text-secondary hover:text-text-primary hover:bg-surface-card rounded-lg transition-colors border border-border-subtle focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-500/40"
              aria-label={`${t("download")} — ${title}`}
              title={t("download")}
            >
              <Download className="w-3.5 h-3.5" />
              <span>{t("download")}</span>
            </button>
            <button
              type="button"
              onClick={() => copyToClipboard(content, templateId)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-text-secondary hover:text-text-primary hover:bg-surface-card rounded-lg transition-colors border border-border-subtle focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-500/40"
              aria-label={`${copiedTemplate === templateId ? tCommon("copied") : tCommon("copy")} — ${title}`}
            >
              {copiedTemplate === templateId ? (
                <Check className="w-3.5 h-3.5 text-emerald-500" />
              ) : (
                <Copy className="w-3.5 h-3.5" />
              )}
              <span>{copiedTemplate === templateId ? tCommon("copied") : tCommon("copy")}</span>
            </button>
          </div>
        </div>

        <div
          className={`bg-surface-card p-4 sm:p-5 ${
            isSingleView ? "flex-1 min-h-0 overflow-y-auto custom-scrollbar" : ""
          }`}
        >
          {viewMode === "preview" ? (
            <MarkdownRenderer content={content} />
          ) : (
            <pre className="text-xs sm:text-sm text-text-primary overflow-x-auto whitespace-pre-wrap font-mono leading-relaxed">
              {content}
            </pre>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen lg:h-[calc(100vh-var(--header-h,3.5rem))] lg:overflow-hidden flex flex-col bg-surface-ground pb-6 lg:pb-0">
      <PageHeader title={t("title")} subtitle={t("subtitle")} />

      <main className="max-w-[1600px] w-full mx-auto px-4 sm:px-6 lg:px-8 py-4 sm:py-6 flex-1 flex flex-col min-h-0 lg:overflow-hidden">
        {error && (
          <div
            role="alert"
            className="mb-4 p-3.5 bg-danger-500/10 border border-danger-500/25 rounded-xl text-xs sm:text-sm text-danger-700 dark:text-danger-400 shrink-0 flex items-start gap-2.5"
          >
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <p className="flex-1 min-w-0">{error}</p>
            <button
              type="button"
              onClick={() => setError("")}
              aria-label={t("dismissError")}
              className="shrink-0 -m-1 p-1 rounded-md text-danger-700/70 hover:text-danger-700 hover:bg-danger-500/10 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-danger-500/40"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-[minmax(320px,380px)_minmax(0,1fr)] xl:grid-cols-[minmax(360px,430px)_minmax(0,1fr)] gap-5 xl:gap-6 flex-1 min-h-0 lg:overflow-hidden">
          {/* Left Column - Generate Report, Templates, History */}
          <div className="lg:h-full lg:overflow-y-auto custom-scrollbar space-y-5 lg:pr-1.5">
            {/* Generate Report Form */}
            <div className="bg-surface-card rounded-xl border border-border-subtle shadow-subtle p-4 sm:p-5">
              <h2 className="text-base font-semibold tracking-tight text-text-primary mb-2">
                {t("generateReports")}
              </h2>
              <p
                id="reports-form-hint"
                className="text-xs sm:text-sm text-text-secondary mb-4 leading-relaxed"
              >
                {t("pageDescription")}
              </p>

              <div className="space-y-4">
                <div>
                  <label
                    htmlFor="reports-alert-id"
                    className="block text-xs font-medium text-text-secondary mb-1.5"
                  >
                    {t("alertId")}
                  </label>
                  <input
                    id="reports-alert-id"
                    type="text"
                    value={alertId}
                    onChange={(e) => setAlertId(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !generating && alertId.trim()) {
                        generateReports();
                      }
                    }}
                    placeholder={t("alertIdPlaceholder")}
                    aria-describedby="reports-form-hint"
                    disabled={generating}
                    className="w-full px-3 py-2 text-xs sm:text-sm border border-border-default rounded-lg bg-surface-input text-text-primary placeholder:text-text-disabled focus:outline-none focus:ring-2 focus:ring-accent-500/20 focus:border-accent-600 transition-all font-mono disabled:opacity-60 disabled:cursor-not-allowed"
                  />
                </div>

                <div>
                  <label
                    htmlFor="reports-notes"
                    className="block text-xs font-medium text-text-secondary mb-1.5"
                  >
                    {t("additionalNotes")}
                  </label>
                  <textarea
                    id="reports-notes"
                    value={additionalNotes}
                    onChange={(e) => setAdditionalNotes(e.target.value)}
                    placeholder={t("notesPlaceholder")}
                    rows={3}
                    disabled={generating}
                    className="w-full px-3 py-2 text-xs sm:text-sm border border-border-default rounded-lg bg-surface-input text-text-primary placeholder:text-text-disabled focus:outline-none focus:ring-2 focus:ring-accent-500/20 focus:border-accent-600 transition-all disabled:opacity-60 disabled:cursor-not-allowed"
                  />
                </div>

                <button
                  type="button"
                  onClick={generateReports}
                  disabled={generating || !alertId.trim()}
                  aria-busy={generating}
                  className="w-full px-4 py-2.5 bg-accent-600 hover:bg-accent-700 active:bg-accent-800 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 text-xs sm:text-sm font-medium shadow-xs transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-500/40"
                >
                  {generating ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      {t("generating")}
                    </>
                  ) : (
                    <>
                      <Plus className="w-4 h-4" />
                      {t("generate")}
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Report Templates Info */}
            <div className="bg-surface-card rounded-xl border border-border-subtle shadow-subtle p-4 sm:p-5">
              <h3 className="text-sm font-semibold tracking-tight text-text-primary mb-3">
                {t("availableTemplates")}
              </h3>
              <div className="space-y-3">
                {TEMPLATES.map((template) => (
                  <div
                    key={template.id}
                    className="flex items-start gap-3 p-3 bg-surface-ground rounded-xl border border-border-subtle"
                  >
                    <div className="p-2 rounded-lg bg-surface-card border border-border-subtle shrink-0">
                      {template.icon}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-text-primary">{template.name}</p>
                      <p className="text-xs text-text-secondary mt-0.5 leading-relaxed">
                        {template.description}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Report History List */}
            <div className="bg-surface-card rounded-xl border border-border-subtle shadow-subtle p-4 sm:p-5">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold tracking-tight text-text-primary flex items-center gap-2">
                  <History className="w-4 h-4 text-accent-500" />
                  {t("history")}
                  {historyList.length > 0 && (
                    <span className="text-[10px] font-medium text-text-muted px-1.5 py-0.5 rounded-full bg-surface-ground border border-border-subtle">
                      {historyList.length}
                    </span>
                  )}
                </h3>
                <button
                  type="button"
                  onClick={fetchHistory}
                  disabled={loadingHistory}
                  aria-label={t("refreshHistory")}
                  className="text-text-muted hover:text-text-primary p-1 rounded-md transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-500/40 disabled:cursor-not-allowed"
                  title={t("refreshHistory")}
                >
                  <RotateCcw className={`w-3.5 h-3.5 ${loadingHistory ? "animate-spin" : ""}`} />
                </button>
              </div>

              {historyError ? (
                <p className="text-xs text-danger-600 dark:text-danger-400 py-2" role="alert">
                  {historyError}
                </p>
              ) : loadingHistory ? (
                <div className="space-y-2 py-2" aria-hidden="true">
                  <div className="h-12 bg-surface-ground animate-pulse rounded-lg" />
                  <div className="h-12 bg-surface-ground animate-pulse rounded-lg" />
                  <div className="h-12 bg-surface-ground animate-pulse rounded-lg" />
                </div>
              ) : historyList.length === 0 ? (
                <p className="text-xs text-text-muted py-2">{t("noReports")}</p>
              ) : (
                <ul className="space-y-2">
                  {historyList.map((item) => {
                    const alert = parseAlertInput(item.input_text);
                    const label =
                      alert.title ||
                      (alert.id ? t("alertNumber", { id: alert.id }) : t("untitledReport"));
                    const templateCount = historyTemplateCount(item);
                    const isSelected = selectedHistoryId === item.id;
                    return (
                      <li key={item.id}>
                        <button
                          type="button"
                          onClick={() => selectHistoryItem(item)}
                          aria-current={isSelected ? "true" : undefined}
                          className={`w-full text-left p-2.5 rounded-lg border transition-all group focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-500/40 ${
                            isSelected
                              ? "border-accent-500/60 bg-accent-50/60 dark:bg-accent-950/30 shadow-xs"
                              : "border-border-subtle bg-surface-ground hover:border-border-default hover:bg-surface-card"
                          }`}
                        >
                          <div className="flex items-center justify-between gap-2 text-xs mb-1">
                            <span
                              className="font-medium text-text-primary truncate min-w-0"
                              title={label}
                            >
                              {label}
                            </span>
                            <span className="text-[10px] text-text-muted flex items-center gap-1 shrink-0">
                              <Clock className="w-3 h-3" />
                              {format.dateTime(new Date(item.created_at), {
                                hour: "2-digit",
                                minute: "2-digit",
                              })}
                            </span>
                          </div>
                          <div className="text-[11px] text-text-secondary flex items-center justify-between gap-2">
                            <div className="flex items-center gap-1.5 min-w-0">
                              <span className="shrink-0">
                                {format.dateTime(new Date(item.created_at), {
                                  dateStyle: "medium",
                                })}
                              </span>
                              {item.model_used && (
                                <span className="text-[10px] px-1 truncate bg-surface-card dark:bg-surface-ground rounded border border-border-subtle text-text-tertiary">
                                  {item.model_used}
                                </span>
                              )}
                            </div>
                            <span className="shrink-0 flex items-center gap-2">
                              {templateCount > 0 && (
                                <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-surface-card dark:bg-surface-ground border border-border-subtle text-text-tertiary">
                                  {t("templateCount", { count: templateCount })}
                                </span>
                              )}
                              <span className="text-[10px] font-medium text-accent-600 dark:text-accent-400 flex items-center gap-0.5 group-hover:translate-x-0.5 transition-transform">
                                {tCommon("viewDetails")}
                                <ChevronRight className="w-3 h-3" />
                              </span>
                            </span>
                          </div>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          </div>

          {/* Right Column - Generated Reports / Details */}
          <div className="lg:h-full flex flex-col min-h-0 lg:overflow-hidden">
            {generating ? (
              <div
                role="status"
                aria-live="polite"
                className="bg-surface-card rounded-xl border border-border-subtle shadow-subtle p-4 sm:p-5 h-full flex flex-col gap-4 overflow-hidden"
              >
                <div className="flex items-center gap-2.5 text-xs sm:text-sm text-text-secondary shrink-0">
                  <Loader2 className="w-4 h-4 animate-spin text-accent-500" />
                  {t("generatingHint")}
                </div>
                <div className="space-y-3" aria-hidden="true">
                  <div className="h-4 w-1/3 bg-surface-ground animate-pulse rounded" />
                  <div className="h-3 w-full bg-surface-ground animate-pulse rounded" />
                  <div className="h-3 w-11/12 bg-surface-ground animate-pulse rounded" />
                  <div className="h-3 w-4/5 bg-surface-ground animate-pulse rounded" />
                  <div className="h-24 w-full bg-surface-ground animate-pulse rounded-lg mt-4" />
                  <div className="h-3 w-full bg-surface-ground animate-pulse rounded" />
                  <div className="h-3 w-3/4 bg-surface-ground animate-pulse rounded" />
                </div>
              </div>
            ) : generatedReports ? (
              <div className="flex flex-col h-full min-h-0">
                {/* Details Top Toolbar: Tabs & View Mode */}
                <div className="flex flex-wrap items-center justify-between gap-2.5 pb-3 border-b border-border-subtle shrink-0">
                  {/* Template tabs switcher */}
                  <div
                    role="group"
                    aria-label={t("availableTemplates")}
                    className="flex items-center gap-1 p-1 bg-surface-card rounded-lg border border-border-subtle overflow-x-auto max-w-full"
                  >
                    <button
                      type="button"
                      onClick={() => switchTab("all")}
                      aria-pressed={selectedTab === "all"}
                      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all shrink-0 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-500/40 ${
                        selectedTab === "all"
                          ? "bg-accent-600 text-white shadow-xs"
                          : "text-text-secondary hover:text-text-primary hover:bg-surface-ground"
                      }`}
                    >
                      <Layers className="w-3.5 h-3.5" />
                      <span>{t("allTemplates")}</span>
                      {availableTemplatesCount > 0 && (
                        <span
                          className={`text-[10px] px-1.5 py-0.5 rounded-full ${
                            selectedTab === "all"
                              ? "bg-white/20 text-white"
                              : "bg-surface-ground text-text-muted"
                          }`}
                        >
                          {availableTemplatesCount}
                        </span>
                      )}
                    </button>

                    {hasTicket && (
                      <button
                        type="button"
                        onClick={() => switchTab("ticket")}
                        aria-pressed={selectedTab === "ticket"}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all shrink-0 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-500/40 ${
                          selectedTab === "ticket"
                            ? "bg-accent-600 text-white shadow-xs"
                            : "text-text-secondary hover:text-text-primary hover:bg-surface-ground"
                        }`}
                      >
                        <Ticket className="w-3.5 h-3.5" />
                        <span>{t("templates.ticket.name")}</span>
                      </button>
                    )}

                    {hasDaily && (
                      <button
                        type="button"
                        onClick={() => switchTab("daily")}
                        aria-pressed={selectedTab === "daily"}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all shrink-0 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-500/40 ${
                          selectedTab === "daily"
                            ? "bg-accent-600 text-white shadow-xs"
                            : "text-text-secondary hover:text-text-primary hover:bg-surface-ground"
                        }`}
                      >
                        <BarChart3 className="w-3.5 h-3.5" />
                        <span>{t("templates.daily.name")}</span>
                      </button>
                    )}

                    {hasPostmortem && (
                      <button
                        type="button"
                        onClick={() => switchTab("postmortem")}
                        aria-pressed={selectedTab === "postmortem"}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all shrink-0 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-500/40 ${
                          selectedTab === "postmortem"
                            ? "bg-accent-600 text-white shadow-xs"
                            : "text-text-secondary hover:text-text-primary hover:bg-surface-ground"
                        }`}
                      >
                        <ClipboardList className="w-3.5 h-3.5" />
                        <span>{t("templates.postmortem.name")}</span>
                      </button>
                    )}
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    {/* Mode switch: Preview vs Raw */}
                    <div
                      role="group"
                      aria-label={t("format")}
                      className="flex items-center gap-1 p-0.5 bg-surface-card rounded-lg border border-border-subtle"
                    >
                      <button
                        type="button"
                        onClick={() => setViewMode("preview")}
                        aria-pressed={viewMode === "preview"}
                        className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-500/40 ${
                          viewMode === "preview"
                            ? "bg-accent-600 text-white shadow-xs"
                            : "text-text-secondary hover:text-text-primary hover:bg-surface-ground"
                        }`}
                        title={t("preview")}
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span>{t("preview")}</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => setViewMode("raw")}
                        aria-pressed={viewMode === "raw"}
                        className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-500/40 ${
                          viewMode === "raw"
                            ? "bg-accent-600 text-white shadow-xs"
                            : "text-text-secondary hover:text-text-primary hover:bg-surface-ground"
                        }`}
                        title={t("rawMarkdown")}
                      >
                        <Code2 className="w-3.5 h-3.5" />
                        <span>{t("rawMarkdown")}</span>
                      </button>
                    </div>

                    <button
                      type="button"
                      onClick={closeReport}
                      aria-label={t("closeReport")}
                      title={t("closeReport")}
                      className="text-text-muted hover:text-text-primary p-1.5 rounded-md border border-border-subtle hover:bg-surface-ground transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-500/40"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                {/* Details Content Area — 本面板唯一滚动容器；单模板视图由卡片自身撑满滚动 */}
                <div
                  ref={detailsScrollRef}
                  aria-live="polite"
                  className={`flex-1 min-h-0 custom-scrollbar pt-4 pr-1 ${
                    selectedTab === "all" ? "overflow-y-auto" : "overflow-hidden"
                  }`}
                >
                  {selectedTab === "all" ? (
                    <div className="space-y-5">
                      {hasTicket &&
                        renderTemplateCard(
                          "ticket",
                          t("templates.ticket.name"),
                          <Ticket className="w-5 h-5 text-accent-500" />,
                          generatedReports.ticket_template!,
                          false
                        )}

                      {hasDaily &&
                        renderTemplateCard(
                          "daily",
                          t("templates.daily.name"),
                          <BarChart3 className="w-5 h-5 text-emerald-500" />,
                          generatedReports.daily_report_template!,
                          false
                        )}

                      {hasPostmortem &&
                        renderTemplateCard(
                          "postmortem",
                          t("templates.postmortem.name"),
                          <ClipboardList className="w-5 h-5 text-amber-500" />,
                          generatedReports.postmortem_template!,
                          false
                        )}
                    </div>
                  ) : selectedTab === "ticket" && hasTicket ? (
                    renderTemplateCard(
                      "ticket",
                      t("templates.ticket.name"),
                      <Ticket className="w-5 h-5 text-accent-500" />,
                      generatedReports.ticket_template!,
                      true
                    )
                  ) : selectedTab === "daily" && hasDaily ? (
                    renderTemplateCard(
                      "daily",
                      t("templates.daily.name"),
                      <BarChart3 className="w-5 h-5 text-emerald-500" />,
                      generatedReports.daily_report_template!,
                      true
                    )
                  ) : selectedTab === "postmortem" && hasPostmortem ? (
                    renderTemplateCard(
                      "postmortem",
                      t("templates.postmortem.name"),
                      <ClipboardList className="w-5 h-5 text-amber-500" />,
                      generatedReports.postmortem_template!,
                      true
                    )
                  ) : (
                    <div className="bg-surface-card rounded-xl border border-border-subtle shadow-subtle p-8 text-center">
                      <p className="text-xs sm:text-sm text-text-muted">{t("noReports")}</p>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="bg-surface-card rounded-xl border border-border-subtle shadow-subtle p-12 text-center h-full flex flex-col items-center justify-center">
                <FileText className="w-12 h-12 text-text-muted mb-3 opacity-60" />
                <h3 className="text-base font-semibold text-text-primary mb-1.5">
                  {t("noReportsGenerated")}
                </h3>
                <p className="text-xs sm:text-sm text-text-muted max-w-sm mx-auto leading-relaxed">
                  {t("noReportsDescription")}
                </p>
                <Link
                  href="/alerts"
                  className="mt-4 inline-flex items-center gap-1.5 px-3.5 py-2 text-xs sm:text-sm font-medium text-accent-700 dark:text-accent-400 bg-accent-50 dark:bg-accent-950/40 border border-accent-500/30 rounded-lg hover:bg-accent-100 dark:hover:bg-accent-950/60 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-500/40"
                >
                  {t("browseAlerts")}
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
