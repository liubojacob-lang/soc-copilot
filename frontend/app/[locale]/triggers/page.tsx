"use client";

import { useState, useEffect } from "react";
import { useRouter } from "@/i18n/navigation";
import { useFormatter, useTranslations, useLocale } from "next-intl";
import { loadAuthState, authFetchJSON } from "@/lib/auth";
import { PageHeader } from "@/components/common/PageHeader";
import { LoadingState } from "@/components/common/LoadingState";
import { ConfirmDialog } from "@/components/common";
import { useToast } from "@/components/Toast";
import { Zap, Clock, Info, CheckCircle2, XCircle } from "lucide-react";

interface Trigger {
  id: string;
  definition_id: string;
  type: string;
  name: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  last_triggered_at: string | null;
  secret_prefix?: string;
  cron_expr?: string;
  webhook_url?: string;
}

interface Definition {
  id: string;
  name: string;
}

export default function TriggersPage() {
  const t = useTranslations("triggers");
  const format = useFormatter();
  const tPage = useTranslations("triggersPage");
  const tCommon = useTranslations("common");
  const { showToast } = useToast();
  const locale = useLocale();
  const router = useRouter();
  const [triggers, setTriggers] = useState<Trigger[]>([]);
  const [definitions, setDefinitions] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<Trigger | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [filterType, setFilterType] = useState<string>("all");
  const [copiedSecret, setCopiedSecret] = useState<string | null>(null);
  const [testingWebhook, setTestingWebhook] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

  useEffect(() => {
    const authState = loadAuthState();
    if (!authState?.isAuthenticated) {
      router.push("/login");
      return;
    }
    fetchTriggers();
  }, [router]);

  const fetchTriggers = async () => {
    try {
      const data = await authFetchJSON<{ items: Trigger[]; total: number }>("/api/triggers");
      setTriggers(data.items);

      // Fetch definitions to get names
      const defPromises = data.items.map((t) =>
        authFetchJSON<Definition>(`/api/playbook-definitions/${t.definition_id}`)
      );
      const defResults = await Promise.allSettled(defPromises);
      const defMap: Record<string, string> = {};
      defResults.forEach((result, index) => {
        if (result.status === "fulfilled") {
          defMap[data.items[index].definition_id] = result.value.name;
        }
      });
      setDefinitions(defMap);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t("errors.loadFailed"));
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteTrigger = async (id: string) => {
    setDeleting(true);
    setError("");

    try {
      await authFetchJSON(`/api/triggers/${id}`, { method: "DELETE" });
      setDeleteTarget(null);
      await fetchTriggers();
      showToast(t("deleteSuccess"), "success");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t("errors.deleteFailed"));
      showToast(err instanceof Error ? err.message : t("errors.deleteFailed"), "error");
    } finally {
      setDeleting(false);
    }
  };

  const handleToggleActive = async (id: string, isActive: boolean) => {
    try {
      await authFetchJSON(`/api/triggers/${id}`, {
        method: "PUT",
        body: JSON.stringify({ is_active: !isActive }),
      });
      await fetchTriggers();
      showToast(t("toggleSuccess"), "success");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t("errors.toggleFailed"));
      showToast(err instanceof Error ? err.message : t("errors.toggleFailed"), "error");
    }
  };

  const handleCopySecret = (secret: string) => {
    navigator.clipboard.writeText(secret);
    setCopiedSecret(secret);
    setTimeout(() => setCopiedSecret(null), 2000);
  };

  const handleCopyWebhookUrl = (url: string) => {
    navigator.clipboard.writeText(url);
    setTimeout(() => setCopiedSecret(null), 2000);
  };

  const handleTestWebhook = async (trigger: Trigger) => {
    if (!trigger.webhook_url) return;

    setTestingWebhook(trigger.id);
    setTestResult(null);

    try {
      const response = await authFetchJSON<{ success: boolean; message: string }>(
        `/api/triggers/${trigger.id}/test`,
        { method: "POST" }
      );
      setTestResult(response);
    } catch (err: unknown) {
      setTestResult({
        success: false,
        message:
          err instanceof Error
            ? err.message
            : locale.startsWith("zh")
              ? "测试触发器请求失败"
              : "Test failed",
      });
    } finally {
      setTestingWebhook(null);
    }
  };

  const getTriggerTypeBadge = (type: string) => {
    switch (type) {
      case "webhook":
        return "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300";
      case "cron":
        return "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300";
      default:
        return "bg-surface-hover text-text-primary dark:bg-surface-active dark:text-text-muted";
    }
  };

  const filteredTriggers = triggers.filter((t) => filterType === "all" || t.type === filterType);

  return (
    <div className="min-h-screen bg-surface-page transition-colors">
      <PageHeader
        title={t("title")}
        subtitle={t("subtitle")}
        actions={
          <div className="flex items-center gap-2">
            <button
              onClick={() => router.push("/triggers/webhook/new")}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors shadow-xs h-9"
            >
              <Zap className="w-3.5 h-3.5" />
              <span>{t("webhookTrigger")}</span>
            </button>
            <button
              onClick={() => router.push("/triggers/cron/new")}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-purple-600 rounded-lg hover:bg-purple-700 transition-colors shadow-xs h-9"
            >
              <Clock className="w-3.5 h-3.5" />
              <span>{t("cronTrigger")}</span>
            </button>
          </div>
        }
      />

      <main className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-5 space-y-3.5">
        {/* Error Message */}
        {error && (
          <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-xs text-red-600 dark:text-red-400">
            {error}
          </div>
        )}

        {/* Test Result */}
        {testResult && (
          <div
            className={`p-3 rounded-lg border text-xs ${testResult.success ? "bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800 text-green-700 dark:text-green-400" : "bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800 text-red-600 dark:text-red-400"}`}
          >
            {testResult.success ? "✓ " : "✗ "}
            {testResult.message}
          </div>
        )}

        {/* Filters */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setFilterType("all")}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors h-8 ${
              filterType === "all"
                ? "bg-accent-600 text-white shadow-xs"
                : "bg-surface-card border border-border-default text-text-secondary hover:bg-surface-hover"
            }`}
          >
            {tPage("all")}
          </button>
          <button
            onClick={() => setFilterType("webhook")}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors h-8 ${
              filterType === "webhook"
                ? "bg-blue-600 text-white shadow-xs"
                : "bg-surface-card border border-border-default text-text-secondary hover:bg-surface-hover"
            }`}
          >
            {tPage("webhooks")}
          </button>
          <button
            onClick={() => setFilterType("cron")}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors h-8 ${
              filterType === "cron"
                ? "bg-purple-600 text-white shadow-xs"
                : "bg-surface-card border border-border-default text-text-secondary hover:bg-surface-hover"
            }`}
          >
            {tPage("cron")}
          </button>
        </div>

        {/* Triggers List */}
        <div className="bg-surface-card rounded-xl border border-border-subtle shadow-subtle overflow-hidden">
          <LoadingState
            isLoading={loading}
            empty={!loading && filteredTriggers.length === 0}
            emptyMessage={
              filterType === "all"
                ? tPage("noTriggers")
                : tPage("noTriggersType", { type: filterType === "webhook" ? "Webhook" : "Cron" })
            }
            skeletonType="table"
            skeletonProps={{ rows: 5, columns: 7 }}
          >
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-border-subtle text-sm">
                <thead className="bg-surface-hover/50 border-b border-border-subtle text-xs uppercase text-text-muted">
                  <tr>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold text-text-muted uppercase tracking-wider">
                      {tPage("type")}
                    </th>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold text-text-muted uppercase tracking-wider">
                      {tPage("name")}
                    </th>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold text-text-muted uppercase tracking-wider">
                      {tPage("playbook")}
                    </th>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold text-text-muted uppercase tracking-wider">
                      {tPage("details")}
                    </th>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold text-text-muted uppercase tracking-wider">
                      {tPage("status")}
                    </th>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold text-text-muted uppercase tracking-wider">
                      {tPage("lastTriggered")}
                    </th>
                    <th className="px-4 py-2.5 text-right text-xs font-semibold text-text-muted uppercase tracking-wider">
                      {tPage("actions")}
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-subtle">
                  {filteredTriggers.map((trigger) => (
                    <tr key={trigger.id} className="hover:bg-surface-hover/50 transition-colors">
                      <td className="px-4 py-2.5 whitespace-nowrap">
                        <span
                          className={`px-2 py-0.5 text-xs font-medium rounded-full ${getTriggerTypeBadge(trigger.type)}`}
                        >
                          {trigger.type === "webhook"
                            ? "Webhook"
                            : trigger.type === "cron"
                              ? "Cron"
                              : trigger.type}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 whitespace-nowrap text-sm font-medium text-text-primary">
                        {trigger.name || (
                          <span className="text-text-disabled italic">{tPage("unnamed")}</span>
                        )}
                      </td>
                      <td className="px-4 py-2.5 whitespace-nowrap text-sm text-text-secondary">
                        {definitions[trigger.definition_id] || trigger.definition_id}
                      </td>
                      <td className="px-4 py-2.5 text-sm text-text-secondary">
                        {trigger.type === "webhook" && trigger.webhook_url && (
                          <div className="flex items-center gap-1.5">
                            <code className="text-xs bg-surface-hover px-2 py-0.5 rounded font-mono text-text-secondary border border-border-subtle">
                              {trigger.webhook_url}
                            </code>
                            <button
                              onClick={() => handleCopyWebhookUrl(trigger.webhook_url!)}
                              className="text-accent-600 hover:text-accent-700 text-xs font-medium"
                            >
                              {tCommon("copy")}
                            </button>
                          </div>
                        )}
                        {trigger.type === "cron" && trigger.cron_expr && (
                          <code className="text-xs bg-surface-hover px-2 py-0.5 rounded font-mono text-text-secondary border border-border-subtle">
                            {trigger.cron_expr}
                          </code>
                        )}
                      </td>
                      <td className="px-4 py-2.5 whitespace-nowrap">
                        {trigger.is_active ? (
                          <span className="px-2 py-0.5 inline-flex items-center gap-1 text-xs font-medium rounded-full bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">
                            <CheckCircle2 className="w-3 h-3" />
                            {t("active")}
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 inline-flex items-center gap-1 text-xs font-medium rounded-full bg-surface-hover text-text-muted">
                            <XCircle className="w-3 h-3" />
                            {t("inactive")}
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-2.5 whitespace-nowrap text-xs text-text-secondary">
                        {trigger.last_triggered_at
                          ? format.dateTime(new Date(trigger.last_triggered_at), {
                              dateStyle: "medium",
                              timeStyle: "medium",
                            })
                          : tPage("never")}
                      </td>
                      <td className="px-4 py-2.5 whitespace-nowrap text-right text-xs font-medium">
                        <div className="flex items-center justify-end gap-2.5">
                          {trigger.type === "webhook" && (
                            <button
                              onClick={() => handleTestWebhook(trigger)}
                              disabled={testingWebhook === trigger.id}
                              className="text-xs text-green-600 hover:text-green-700 dark:text-green-400 font-medium disabled:opacity-50"
                            >
                              {testingWebhook === trigger.id ? "..." : tPage("test")}
                            </button>
                          )}
                          <button
                            onClick={() => handleToggleActive(trigger.id, trigger.is_active)}
                            className={`text-xs font-medium ${
                              trigger.is_active
                                ? "text-amber-600 hover:text-amber-700 dark:text-amber-400"
                                : "text-accent-600 hover:text-accent-700 dark:text-accent-400"
                            }`}
                          >
                            {trigger.is_active ? tPage("disable") : tPage("enable")}
                          </button>
                          <button
                            onClick={() => setDeleteTarget(trigger)}
                            className="text-xs text-red-600 hover:text-red-700 dark:text-red-400 font-medium"
                          >
                            {t("delete")}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </LoadingState>
        </div>

        {/* Info Box */}
        <div className="p-4 bg-surface-card rounded-xl border border-border-subtle shadow-subtle">
          <h3 className="text-xs font-semibold text-text-primary mb-2 flex items-center gap-1.5">
            <Info className="w-3.5 h-3.5 text-accent-600 dark:text-accent-400" />
            <span>{tPage("infoBox.title")}</span>
          </h3>
          <ul className="text-xs text-text-secondary space-y-1.5 list-disc list-inside">
            <li>{tPage("infoBox.webhook")}</li>
            <li>{tPage("infoBox.cron")}</li>
            <li>{tPage("infoBox.logs")}</li>
          </ul>
        </div>
      </main>

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={!!deleteTarget}
        title={t("delete")}
        description={t("modal.deleteConfirm")}
        confirmText={t("delete")}
        cancelText={tCommon("cancel")}
        variant="danger"
        loading={deleting}
        onConfirm={() => {
          if (deleteTarget) handleDeleteTrigger(deleteTarget.id);
        }}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
