'use client';

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useTranslations, useLocale } from 'next-intl';
import { loadAuthState, authFetchJSON } from "@/lib/auth";
import Navigation from "@/components/Navigation";
import { FileText, Download, Plus, Copy, Check } from "lucide-react";

interface ReportTemplate {
  id: string;
  name: string;
  description: string;
  icon: string;
}

const TEMPLATES: ReportTemplate[] = [
  {
    id: "ticket",
    name: "Incident Ticket",
    description: "Create a formatted incident ticket for tracking and escalation",
    icon: "🎫"
  },
  {
    id: "daily",
    name: "Daily SOC Report",
    description: "Daily security operations center summary report",
    icon: "📊"
  },
  {
    id: "postmortem",
    name: "Post-Incident Report",
    description: "Detailed post-incident analysis and lessons learned",
    icon: "📋"
  }
];

export default function ReportsPage() {
  const t = useTranslations('reports');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const router = useRouter();
  
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
      router.push(`/${locale}/login`);
    }
  }, [router, locale]);

  const generateReports = async () => {
    if (!alertId.trim()) {
      setError("Please enter an alert ID");
      return;
    }

    setGenerating(true);
    setError("");
    setGeneratedReports(null);

    try {
      const alertData = await authFetchJSON<any>(`/api/alerts/${alertId}`);
      
      const response = await authFetchJSON<any>("/api/generate-report", {
        method: "POST",
        body: JSON.stringify({
          alert_json: JSON.stringify(alertData),
          additional_notes: additionalNotes
        })
      });
      
      setGeneratedReports(response);
    } catch (err: any) {
      setError(err.message || "Failed to generate reports");
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
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Navigation title={t('title')} subtitle="Generate and manage security reports" />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-md">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Generate Report */}
          <div className="lg:col-span-1">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Generate Reports
              </h2>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                Enter an alert ID to generate three report templates using AI
              </p>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Alert ID
                  </label>
                  <input
                    type="text"
                    value={alertId}
                    onChange={(e) => setAlertId(e.target.value)}
                    placeholder="e.g., alert-123"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md dark:bg-gray-700 dark:text-white"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Additional Notes (optional)
                  </label>
                  <textarea
                    value={additionalNotes}
                    onChange={(e) => setAdditionalNotes(e.target.value)}
                    placeholder="Any specific requirements or notes..."
                    rows={3}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md dark:bg-gray-700 dark:text-white"
                  />
                </div>

                <button
                  onClick={generateReports}
                  disabled={generating || !alertId.trim()}
                  className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {generating ? (
                    <>Generating...</>
                  ) : (
                    <>
                      <Plus className="w-4 h-4" />
                      {t('generate')}
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Report Templates Info */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 mt-6">
              <h3 className="text-md font-semibold text-gray-900 dark:text-white mb-3">
                Available Templates
              </h3>
              <div className="space-y-3">
                {TEMPLATES.map((template) => (
                  <div key={template.id} className="flex items-start gap-3 p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                    <span className="text-xl">{template.icon}</span>
                    <div>
                      <p className="text-sm font-medium text-gray-900 dark:text-white">
                        {template.name}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
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
                  <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
                    <div className="flex justify-between items-center p-4 bg-gray-50 dark:bg-gray-700 border-b border-gray-200 dark:border-gray-600">
                      <div className="flex items-center gap-2">
                        <span className="text-xl">🎫</span>
                        <h3 className="font-semibold text-gray-900 dark:text-white">Incident Ticket</h3>
                      </div>
                      <button
                        onClick={() => copyToClipboard(generatedReports.ticket_template!, "ticket")}
                        className="flex items-center gap-1 px-3 py-1 text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 rounded"
                      >
                        {copiedTemplate === "ticket" ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                        {copiedTemplate === "copied" ? "Copied!" : "Copy"}
                      </button>
                    </div>
                    <pre className="p-4 text-sm text-gray-700 dark:text-gray-300 overflow-x-auto whitespace-pre-wrap font-mono">
                      {generatedReports.ticket_template}
                    </pre>
                  </div>
                )}

                {generatedReports.daily_report_template && (
                  <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
                    <div className="flex justify-between items-center p-4 bg-gray-50 dark:bg-gray-700 border-b border-gray-200 dark:border-gray-600">
                      <div className="flex items-center gap-2">
                        <span className="text-xl">📊</span>
                        <h3 className="font-semibold text-gray-900 dark:text-white">Daily SOC Report</h3>
                      </div>
                      <button
                        onClick={() => copyToClipboard(generatedReports.daily_report_template!, "daily")}
                        className="flex items-center gap-1 px-3 py-1 text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 rounded"
                      >
                        {copiedTemplate === "daily" ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                        Copy
                      </button>
                    </div>
                    <pre className="p-4 text-sm text-gray-700 dark:text-gray-300 overflow-x-auto whitespace-pre-wrap font-mono">
                      {generatedReports.daily_report_template}
                    </pre>
                  </div>
                )}

                {generatedReports.postmortem_template && (
                  <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
                    <div className="flex justify-between items-center p-4 bg-gray-50 dark:bg-gray-700 border-b border-gray-200 dark:border-gray-600">
                      <div className="flex items-center gap-2">
                        <span className="text-xl">📋</span>
                        <h3 className="font-semibold text-gray-900 dark:text-white">Post-Incident Report</h3>
                      </div>
                      <button
                        onClick={() => copyToClipboard(generatedReports.postmortem_template!, "postmortem")}
                        className="flex items-center gap-1 px-3 py-1 text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 rounded"
                      >
                        {copiedTemplate === "postmortem" ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                        Copy
                      </button>
                    </div>
                    <pre className="p-4 text-sm text-gray-700 dark:text-gray-300 overflow-x-auto whitespace-pre-wrap font-mono">
                      {generatedReports.postmortem_template}
                    </pre>
                  </div>
                )}
              </div>
            ) : (
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-12 text-center">
                <FileText className="w-16 h-16 mx-auto text-gray-400 mb-4" />
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                  No Reports Generated
                </h3>
                <p className="text-gray-500 dark:text-gray-400">
                  Enter an alert ID and click Generate to create report templates
                </p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
