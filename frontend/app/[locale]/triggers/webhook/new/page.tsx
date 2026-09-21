"use client";

import { useState, useEffect } from "react";
import { useRouter } from "@/i18n/navigation";
import { useTranslations } from "next-intl";
import { loadAuthState, authFetchJSON } from "@/lib/auth";
import { PageHeader } from "@/components/common/PageHeader";

interface Definition {
  id: string;
  name: string;
  description: string | null;
  is_active: boolean;
}

interface WebhookTriggerResponse {
  id: string;
  definition_id: string;
  type: "webhook";
  name: string | null;
  secret: string;
  webhook_url: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  last_triggered_at: string | null;
}

export default function NewWebhookTriggerPage() {
  const router = useRouter();
  const t = useTranslations("triggers");
  const tNewWebhook = useTranslations("triggers.newWebhook");
  const tCommon = useTranslations("common");
  const [definitions, setDefinitions] = useState<Definition[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [createdTrigger, setCreatedTrigger] = useState<WebhookTriggerResponse | null>(null);
  const [copied, setCopied] = useState(false);

  const [formData, setFormData] = useState({
    definition_id: "",
    name: "",
    is_active: true,
  });

  useEffect(() => {
    const authState = loadAuthState();
    if (!authState?.isAuthenticated) {
      router.push("/login");
      return;
    }
    fetchDefinitions();
  }, [router]);

  // Lock background scroll when modal is open
  useEffect(() => {
    if (showSuccessModal) {
      const prevOverflow = document.body.style.overflow;
      document.body.style.overflow = "hidden";
      return () => {
        document.body.style.overflow = prevOverflow;
      };
    }
  }, [showSuccessModal]);

  const fetchDefinitions = async () => {
    try {
      const data = await authFetchJSON<{ items: Definition[]; total: number }>(
        "/api/playbook-definitions?page=1&page_size=100"
      );
      setDefinitions(data.items.filter((d: Definition) => d.is_active));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t("failedToLoadDefinitions"));
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setError("");

    try {
      const response = await authFetchJSON<WebhookTriggerResponse>("/api/triggers/webhook", {
        method: "POST",
        body: JSON.stringify(formData),
      });

      setCreatedTrigger(response);
      setShowSuccessModal(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t("failedToCreateWebhook"));
    } finally {
      setCreating(false);
    }
  };

  const handleCopySecret = () => {
    if (createdTrigger) {
      navigator.clipboard.writeText(createdTrigger.secret);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleCopyUrl = () => {
    if (createdTrigger) {
      navigator.clipboard.writeText(createdTrigger.webhook_url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleCloseModal = () => {
    setShowSuccessModal(false);
    router.push("/triggers");
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="text-gray-600 dark:text-gray-400">{tCommon("loading")}</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <PageHeader title={tNewWebhook("title")} subtitle={tNewWebhook("subtitle")} />

      <main className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Error Message */}
        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-md">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        {/* Form */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Playbook Definition */}
            <div>
              <label
                htmlFor="definition_id"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
              >
                {t("playbookDefinition")}
                {t("required")}
              </label>
              <select
                id="definition_id"
                required
                value={formData.definition_id}
                onChange={(e) => setFormData({ ...formData, definition_id: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              >
                <option value="">{t("selectPlaybook")}</option>
                {definitions.map((def) => (
                  <option key={def.id} value={def.id}>
                    {def.name} {def.description ? `- ${def.description}` : ""}
                  </option>
                ))}
              </select>
            </div>

            {/* Trigger Name */}
            <div>
              <label
                htmlFor="name"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
              >
                {t("triggerName")}
              </label>
              <input
                id="name"
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                placeholder={t("webhookTriggerNamePlaceholder")}
              />
            </div>

            {/* Active Status */}
            <div className="flex items-center">
              <input
                id="is_active"
                type="checkbox"
                checked={formData.is_active}
                onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <label
                htmlFor="is_active"
                className="ml-2 block text-sm text-gray-900 dark:text-white"
              >
                {t("activateTrigger")}
              </label>
            </div>

            {/* Submit */}
            <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200 dark:border-gray-700">
              <button
                type="button"
                onClick={() => router.push("/triggers")}
                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600"
              >
                {tCommon("cancel")}
              </button>
              <button
                type="submit"
                disabled={creating}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {creating ? t("creatingWebhook") : t("createWebhook")}
              </button>
            </div>
          </form>
        </div>

        {/* Info Box */}
        <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md">
          <h3 className="text-sm font-medium text-blue-800 dark:text-blue-300 mb-2">
            {t("aboutWebhookTriggers")}
          </h3>
          <ul className="text-sm text-blue-700 dark:text-blue-400 space-y-1 list-disc list-inside">
            <li>{t("aboutWebhookInfo1")}</li>
            <li>{t("aboutWebhookInfo2")}</li>
            <li>{t("aboutWebhookInfo3")}</li>
            <li>{t("aboutWebhookInfo4")}</li>
          </ul>
        </div>
      </main>

      {/* Success Modal */}
      {showSuccessModal && createdTrigger && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) handleCloseModal();
          }}
        >
          <div
            className="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-lg w-full mx-4"
            onMouseDown={(e) => e.stopPropagation()}
          >
            <div className="mb-4">
              <div className="flex items-center justify-center w-12 h-12 bg-green-100 rounded-full mb-4">
                <svg
                  className="w-6 h-6 text-green-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M5 13l4 4L19 7"
                  />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-gray-900 dark:text-white text-center">
                {t("webhookTriggerCreated")}
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400 text-center mt-2">
                {t("webhookCreatedDesc")}
              </p>
            </div>

            {/* Webhook URL */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                {t("webhookUrl")}
              </label>
              <div className="flex">
                <input
                  type="text"
                  readOnly
                  value={createdTrigger.webhook_url}
                  className="flex-1 px-3 py-2 bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-l-md text-sm font-mono text-gray-900 dark:text-white"
                />
                <button
                  onClick={handleCopyUrl}
                  className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-r-md hover:bg-blue-700"
                >
                  {copied ? tCommon("copied") : tCommon("copy")}
                </button>
              </div>
            </div>

            {/* Secret */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                {t("webhookSecret")}
              </label>
              <div className="flex">
                <input
                  type="text"
                  readOnly
                  value={createdTrigger.secret}
                  className="flex-1 px-3 py-2 bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-l-md text-sm font-mono text-gray-900 dark:text-white"
                />
                <button
                  onClick={handleCopySecret}
                  className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-r-md hover:bg-blue-700"
                >
                  {copied ? tCommon("copied") : tCommon("copy")}
                </button>
              </div>
            </div>

            {/* Usage Example */}
            <div className="mb-4 p-3 bg-gray-50 dark:bg-gray-700 rounded-md">
              <p className="text-xs text-gray-600 dark:text-gray-400 mb-2">{t("usageExample")}</p>
              <pre className="text-xs text-gray-800 dark:text-gray-300 overflow-x-auto">
                {`curl -X POST ${createdTrigger.webhook_url} \\
  -H "X-Webhook-Secret: ${createdTrigger.secret}" \\
  -H "Content-Type: application/json" \\
  -d '{"alert_id": "12345", "severity": "high"}'`}
              </pre>
            </div>

            <button
              onClick={handleCloseModal}
              className="w-full px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
            >
              {t("iveSavedMyWebhook")}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
