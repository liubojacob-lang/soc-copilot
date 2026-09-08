"use client";

import { useState, useEffect } from "react";
import { useRouter } from "@/i18n/navigation";
import { useTranslations, useLocale } from "next-intl";
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
} from "lucide-react";

interface ReportTemplate {
  id: string;
  name: string;
  description: string;
  icon: React.ReactNode;
}

export default function ReportsPage() {
  const t = useTranslations("reports");
  const tCommon = useTranslations("common");
  const locale = useLocale();
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

  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [alertId, setAlertId] = useState("");
  const [additionalNotes, setAdditionalNotes] = useState("");
  const [generatedReports, setGeneratedReports] = useState<{
    ticket_template?: string;
    daily_report_template?: string;
    postmortem_template?: string;
  } | null>(null);
  const [copiedTemplate, setCopiedTemplate] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const authState = loadAuthState();
    if (!authState?.isAuthenticated) {
      router.push("/login");
    }
  }, [router]);

  const generateReports = async () => {
    if (!alertId.trim()) {
      setError(t("enterAlertId"));
      return;
    }

    setGenerating(true);
    setError("");
    setGeneratedReports(null);

    try {
      const alertData = await authFetchJSON<Record<string, unknown>>(
        `/api/security-alerts/${alertId}`
      );

      const response = await authFetchJSON<Record<string, unknown>>("/api/generate-report", {
        method: "POST",
        body: JSON.stringify({
          alert_json: JSON.stringify(alertData),
          additional_notes: additionalNotes,
        }),
      });

      setGeneratedReports(response);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t("generateFailed"));
    } finally {
      setGenerating(false);
    }
  };

  const copyToClipboard = (content: string, templateId: string) => {
    navigator.clipboard.writeText(content);
    setCopiedTemplate(templateId);
    setTimeout(() => setCopiedTemplate(null), 2000);
  };

  return (
    <div className="min-h-screen bg-surface-ground pb-12">
      <PageHeader title={t("title")} subtitle={t("subtitle")} />

      <main className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {error && (
          <div className="mb-4 p-3.5 bg-danger-500/10 border border-danger-500/25 rounded-xl text-xs sm:text-sm text-danger-700 dark:text-danger-400">
            <p>{error}</p>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Generate Report */}
          <div className="lg:col-span-1">
            <div className="bg-surface-card rounded-xl border border-border-subtle shadow-subtle p-5 sm:p-6">
              <h2 className="text-base font-semibold tracking-tight text-text-primary mb-2">
                {t("generateReports")}
              </h2>
              <p className="text-xs sm:text-sm text-text-secondary mb-4 leading-relaxed">
                {t("description")}
              </p>

              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-text-secondary mb-1.5">
                    {t("alertId")}
                  </label>
                  <input
                    type="text"
                    value={alertId}
                    onChange={(e) => setAlertId(e.target.value)}
                    placeholder={t("alertIdPlaceholder")}
                    className="w-full px-3 py-2 text-xs sm:text-sm border border-border-default rounded-lg bg-surface-input text-text-primary placeholder:text-text-disabled focus:outline-none focus:ring-2 focus:ring-accent-500/20 focus:border-accent-600 transition-all font-mono"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-text-secondary mb-1.5">
                    {t("additionalNotes")}
                  </label>
                  <textarea
                    value={additionalNotes}
                    onChange={(e) => setAdditionalNotes(e.target.value)}
                    placeholder={t("notesPlaceholder")}
                    rows={3}
                    className="w-full px-3 py-2 text-xs sm:text-sm border border-border-default rounded-lg bg-surface-input text-text-primary placeholder:text-text-disabled focus:outline-none focus:ring-2 focus:ring-accent-500/20 focus:border-accent-600 transition-all"
                  />
                </div>

                <button
                  onClick={generateReports}
                  disabled={generating || !alertId.trim()}
                  className="w-full px-4 py-2.5 bg-accent-600 hover:bg-accent-700 active:bg-accent-800 text-white rounded-lg disabled:opacity-50 flex items-center justify-center gap-2 text-xs sm:text-sm font-medium shadow-sm transition-all"
                >
                  {generating ? (
                    <>{t("generating")}</>
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
            <div className="bg-surface-card rounded-xl border border-border-subtle shadow-subtle p-5 sm:p-6 mt-6">
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
          </div>

          {/* Right Column - Generated Reports */}
          <div className="lg:col-span-2">
            {generatedReports ? (
              <div className="space-y-6">
                {generatedReports.ticket_template && (
                  <div className="bg-surface-card rounded-xl border border-border-subtle shadow-subtle overflow-hidden">
                    <div className="flex justify-between items-center p-4 bg-surface-ground border-b border-border-subtle">
                      <div className="flex items-center gap-2.5">
                        <Ticket className="w-5 h-5 text-accent-500" />
                        <h3 className="font-semibold text-text-primary text-sm">
                          {t("templates.ticket.name")}
                        </h3>
                      </div>
                      <button
                        onClick={() => copyToClipboard(generatedReports.ticket_template!, "ticket")}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-text-secondary hover:text-text-primary hover:bg-surface-card rounded-lg transition-colors border border-border-subtle"
                      >
                        {copiedTemplate === "ticket" ? (
                          <Check className="w-3.5 h-3.5 text-emerald-500" />
                        ) : (
                          <Copy className="w-3.5 h-3.5" />
                        )}
                        {copiedTemplate === "ticket" ? tCommon("copied") : tCommon("copy")}
                      </button>
                    </div>
                    <pre className="p-4 text-xs sm:text-sm text-text-primary overflow-x-auto whitespace-pre-wrap font-mono leading-relaxed">
                      {generatedReports.ticket_template}
                    </pre>
                  </div>
                )}

                {generatedReports.daily_report_template && (
                  <div className="bg-surface-card rounded-xl border border-border-subtle shadow-subtle overflow-hidden">
                    <div className="flex justify-between items-center p-4 bg-surface-ground border-b border-border-subtle">
                      <div className="flex items-center gap-2.5">
                        <BarChart3 className="w-5 h-5 text-emerald-500" />
                        <h3 className="font-semibold text-text-primary text-sm">
                          {t("templates.daily.name")}
                        </h3>
                      </div>
                      <button
                        onClick={() =>
                          copyToClipboard(generatedReports.daily_report_template!, "daily")
                        }
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-text-secondary hover:text-text-primary hover:bg-surface-card rounded-lg transition-colors border border-border-subtle"
                      >
                        {copiedTemplate === "daily" ? (
                          <Check className="w-3.5 h-3.5 text-emerald-500" />
                        ) : (
                          <Copy className="w-3.5 h-3.5" />
                        )}
                        {copiedTemplate === "daily" ? tCommon("copied") : tCommon("copy")}
                      </button>
                    </div>
                    <pre className="p-4 text-xs sm:text-sm text-text-primary overflow-x-auto whitespace-pre-wrap font-mono leading-relaxed">
                      {generatedReports.daily_report_template}
                    </pre>
                  </div>
                )}

                {generatedReports.postmortem_template && (
                  <div className="bg-surface-card rounded-xl border border-border-subtle shadow-subtle overflow-hidden">
                    <div className="flex justify-between items-center p-4 bg-surface-ground border-b border-border-subtle">
                      <div className="flex items-center gap-2.5">
                        <ClipboardList className="w-5 h-5 text-amber-500" />
                        <h3 className="font-semibold text-text-primary text-sm">
                          {t("templates.postmortem.name")}
                        </h3>
                      </div>
                      <button
                        onClick={() =>
                          copyToClipboard(generatedReports.postmortem_template!, "postmortem")
                        }
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-text-secondary hover:text-text-primary hover:bg-surface-card rounded-lg transition-colors border border-border-subtle"
                      >
                        {copiedTemplate === "postmortem" ? (
                          <Check className="w-3.5 h-3.5 text-emerald-500" />
                        ) : (
                          <Copy className="w-3.5 h-3.5" />
                        )}
                        {copiedTemplate === "postmortem" ? tCommon("copied") : tCommon("copy")}
                      </button>
                    </div>
                    <pre className="p-4 text-xs sm:text-sm text-text-primary overflow-x-auto whitespace-pre-wrap font-mono leading-relaxed">
                      {generatedReports.postmortem_template}
                    </pre>
                  </div>
                )}
              </div>
            ) : (
              <div className="bg-surface-card rounded-xl border border-border-subtle shadow-subtle p-12 text-center">
                <FileText className="w-12 h-12 mx-auto text-text-muted mb-3 opacity-60" />
                <h3 className="text-base font-semibold text-text-primary mb-1.5">
                  {t("noReportsGenerated")}
                </h3>
                <p className="text-xs sm:text-sm text-text-muted max-w-sm mx-auto leading-relaxed">
                  {t("noReportsDescription")}
                </p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
