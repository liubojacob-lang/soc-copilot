'use client';

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useTranslations, useLocale } from 'next-intl';
import { loadAuthState, authFetchJSON } from "@/lib/auth";
import Navigation from "@/components/Navigation";
import { TableSkeleton } from "@/components/Skeleton";

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
  const t = useTranslations('triggers');
  const tPage = useTranslations('triggersPage');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const router = useRouter();
  const [triggers, setTriggers] = useState<Trigger[]>([]);
  const [definitions, setDefinitions] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filterType, setFilterType] = useState<string>("all");
  const [copiedSecret, setCopiedSecret] = useState<string | null>(null);
  const [testingWebhook, setTestingWebhook] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<{success: boolean; message: string} | null>(null);

  useEffect(() => {
    const authState = loadAuthState();
    if (!authState?.isAuthenticated) {
      router.push(`/${locale}/login`);
      return;
    }
    fetchTriggers();
  }, [router, locale]);

  const fetchTriggers = async () => {
    try {
      const data = await authFetchJSON<{items: Trigger[], total: number}>("/api/triggers");
      setTriggers(data.items);

      // Fetch definitions to get names
      const defPromises = data.items.map(t =>
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
    } catch (err: any) {
      setError(err.message || t('errors.loadFailed'));
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteTrigger = async (id: string) => {
    if (!confirm(t('modal.deleteConfirm'))) {
      return;
    }

    try {
      await authFetchJSON(`/api/triggers/${id}`, { method: "DELETE" });
      await fetchTriggers();
    } catch (err: any) {
      setError(err.message || t('errors.deleteFailed'));
    }
  };

  const handleToggleActive = async (id: string, isActive: boolean) => {
    try {
      await authFetchJSON(`/api/triggers/${id}`, {
        method: "PUT",
        body: JSON.stringify({ is_active: !isActive }),
      });
      await fetchTriggers();
    } catch (err: any) {
      setError(err.message || t('errors.toggleFailed'));
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
      const response = await authFetchJSON<{success: boolean; message: string}>(
        `/api/triggers/${trigger.id}/test`,
        { method: "POST" }
      );
      setTestResult(response);
    } catch (err: any) {
      setTestResult({ success: false, message: err.message || "Test failed" });
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
        return "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300";
    }
  };

  const filteredTriggers = triggers.filter(t =>
    filterType === "all" || t.type === filterType
  );

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <Navigation title={t('title')} subtitle={t('subtitle')} />
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
            <div className="p-6">
              <TableSkeleton rows={5} cols={7} />
            </div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Navigation title={t('title')} subtitle={t('subtitle')} />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Error Message */}
        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-md">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        {/* Test Result */}
        {testResult && (
          <div className={`mb-4 p-4 rounded-md ${testResult.success ? "bg-green-50 border border-green-200" : "bg-red-50 border border-red-200"}`}>
            <p className={`text-sm ${testResult.success ? "text-green-600" : "text-red-600"}`}>
              {testResult.success ? "✓ " : "✗ "}{testResult.message}
            </p>
          </div>
        )}

        {/* Page Header */}
        <div className="flex justify-between items-center mb-6">
          <div>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">{tPage('pageHeader')}</h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              {tPage('pageDescription')}
            </p>
          </div>
          <div className="flex space-x-2">
            <button
              onClick={() => router.push(`/${locale}/triggers/webhook/new`)}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
            >
              + {t('webhookTrigger')}
            </button>
            <button
              onClick={() => router.push(`/${locale}/triggers/cron/new`)}
              className="px-4 py-2 text-sm font-medium text-white bg-purple-600 rounded-md hover:bg-purple-700"
            >
              + {t('cronTrigger')}
            </button>
          </div>
        </div>

        {/* Filters */}
        <div className="mb-4 flex space-x-2">
          <button
            onClick={() => setFilterType("all")}
            className={`px-3 py-1 text-sm rounded-md ${
              filterType === "all"
                ? "bg-gray-800 text-white dark:bg-gray-700"
                : "bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-300"
            }`}
          >
            {tPage('all')}
          </button>
          <button
            onClick={() => setFilterType("webhook")}
            className={`px-3 py-1 text-sm rounded-md ${
              filterType === "webhook"
                ? "bg-blue-600 text-white"
                : "bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-300"
            }`}
          >
            {tPage('webhooks')}
          </button>
          <button
            onClick={() => setFilterType("cron")}
            className={`px-3 py-1 text-sm rounded-md ${
              filterType === "cron"
                ? "bg-purple-600 text-white"
                : "bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-300"
            }`}
          >
            {tPage('cron')}
          </button>
        </div>

        {/* Triggers List */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
          {filteredTriggers.length === 0 ? (
            <div className="p-8 text-center">
              <p className="text-gray-500 dark:text-gray-400">
                {filterType === "all" ? tPage('noTriggers') : tPage('noTriggersType', { type: filterType })}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-700">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      {tPage('type')}
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      {tPage('name')}
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      {t('playbook')}
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      {tPage('details')}
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      {t('status')}
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      {t('lastTriggered')}
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      {tCommon('actions')}
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                  {filteredTriggers.map((trigger) => (
                    <tr key={trigger.id}>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 py-1 text-xs font-medium rounded-full ${getTriggerTypeBadge(trigger.type)}`}>
                          {trigger.type}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                        {trigger.name || <span className="text-gray-400 italic">{tPage('unnamed')}</span>}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
                        {definitions[trigger.definition_id] || trigger.definition_id}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">
                        {trigger.type === "webhook" && trigger.webhook_url && (
                          <div className="flex items-center space-x-2">
                            <code className="text-xs bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">
                              {trigger.webhook_url}
                            </code>
                            <button
                              onClick={() => handleCopyWebhookUrl(trigger.webhook_url!)}
                              className="text-blue-600 hover:text-blue-700 text-xs"
                            >
                              {tCommon('copy')}
                            </button>
                          </div>
                        )}
                        {trigger.type === "cron" && trigger.cron_expr && (
                          <code className="text-xs bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">
                            {trigger.cron_expr}
                          </code>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {trigger.is_active ? (
                          <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                            {t('active')}
                          </span>
                        ) : (
                          <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-gray-100 text-gray-800">
                            {t('inactive')}
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                        {trigger.last_triggered_at
                          ? new Date(trigger.last_triggered_at).toLocaleString()
                          : tPage('never')}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        {trigger.type === "webhook" && (
                          <button
                            onClick={() => handleTestWebhook(trigger)}
                            disabled={testingWebhook === trigger.id}
                            className="text-green-600 hover:text-green-900 mr-3 disabled:opacity-50"
                          >
                            {testingWebhook === trigger.id ? "..." : tPage('test')}
                          </button>
                        )}
                        <button
                          onClick={() => handleToggleActive(trigger.id, trigger.is_active)}
                          className={`${
                            trigger.is_active ? "text-orange-600 hover:text-orange-900" : "text-green-600 hover:text-green-900"
                          } mr-3`}
                        >
                          {trigger.is_active ? tPage('disable') : tPage('enable')}
                        </button>
                        <button
                          onClick={() => handleDeleteTrigger(trigger.id)}
                          className="text-red-600 hover:text-red-900"
                        >
                          {t('delete')}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Info Box */}
        <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md">
          <h3 className="text-sm font-medium text-blue-800 dark:text-blue-300 mb-2">{tPage('infoBox.title')}</h3>
          <ul className="text-sm text-blue-700 dark:text-blue-400 space-y-1 list-disc list-inside">
            <li><strong>{tPage('infoBox.webhook')}</strong></li>
            <li><strong>{tPage('infoBox.cron')}</strong></li>
            <li>{tPage('infoBox.logs')}</li>
          </ul>
        </div>
      </main>
    </div>
  );
}
