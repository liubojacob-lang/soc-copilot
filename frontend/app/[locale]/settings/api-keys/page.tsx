"use client";

import { useState, useEffect } from "react";
import { useRouter } from "@/i18n/navigation";
import { useFormatter, useTranslations } from "next-intl";
import { loadAuthState, logout, authFetchJSON } from "@/lib/auth";
import { PageHeader } from "@/components/common/PageHeader";
import { ConfirmDialog } from "@/components/common";
import { useToast } from "@/components/Toast";

interface APIKey {
  id: string;
  key_prefix: string;
  description: string;
  is_active: boolean;
  created_at: string;
  last_used_at: string | null;
  expires_at: string | null;
}

interface CreateKeyResponse {
  id: string;
  key_prefix: string;
  description: string;
  is_active: boolean;
  created_at: string;
  last_used_at: string | null;
  expires_at: string | null;
  plain_key: string;
}

export default function APIKeysPage() {
  const format = useFormatter();
  const router = useRouter();
  const tApiKeys = useTranslations("settingsApiKeys");
  const tCommon = useTranslations("common");
  const { showToast } = useToast();
  const [apiKeys, setApiKeys] = useState<APIKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<APIKey | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newKeyDescription, setNewKeyDescription] = useState("");
  const [newKeyExpiresInDays, setNewKeyExpiresInDays] = useState<number | null>(null);
  const [creating, setCreating] = useState(false);
  const [showKeyModal, setShowKeyModal] = useState(false);
  const [newlyCreatedKey, setNewlyCreatedKey] = useState("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const authState = loadAuthState();
    if (!authState?.isAuthenticated) {
      router.push("/login");
      return;
    }
    fetchAPIKeys();
  }, [router]);

  const fetchAPIKeys = async () => {
    try {
      const data = await authFetchJSON<{ items: APIKey[]; total: number }>("/api/api-keys");
      setApiKeys(data.items);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load API keys");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateKey = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setError("");

    try {
      const response = await authFetchJSON<CreateKeyResponse>("/api/api-keys", {
        method: "POST",
        body: JSON.stringify({
          description: newKeyDescription,
          expires_in_days: newKeyExpiresInDays,
        }),
      });

      setNewlyCreatedKey(response.plain_key);
      setShowKeyModal(true);
      setShowCreateModal(false);
      setNewKeyDescription("");
      setNewKeyExpiresInDays(null);

      // Refresh the list
      await fetchAPIKeys();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create API key");
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteKey = async (id: string) => {
    setDeleting(true);
    setError("");

    try {
      await authFetchJSON(`/api/api-keys/${id}`, {
        method: "DELETE",
      });
      setDeleteTarget(null);
      await fetchAPIKeys();
      showToast(tApiKeys("deletedSuccess"), "success");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to delete API key");
      showToast(err instanceof Error ? err.message : tApiKeys("failedToDelete"), "error");
    } finally {
      setDeleting(false);
    }
  };

  const handleDisableKey = async (id: string) => {
    try {
      await authFetchJSON(`/api/api-keys/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ is_active: false }),
      });
      await fetchAPIKeys();
      showToast(tApiKeys("disabledSuccess"), "success");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to disable API key");
      showToast(err instanceof Error ? err.message : tApiKeys("failedToDisable"), "error");
    }
  };

  const handleEnableKey = async (id: string) => {
    try {
      await authFetchJSON(`/api/api-keys/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ is_active: true }),
      });
      await fetchAPIKeys();
      showToast(tApiKeys("enabledSuccess"), "success");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to enable API key");
      showToast(err instanceof Error ? err.message : tApiKeys("failedToEnable"), "error");
    }
  };

  const handleCopyKey = () => {
    navigator.clipboard.writeText(newlyCreatedKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return tCommon("never");
    return format.dateTime(new Date(dateStr), { dateStyle: "medium", timeStyle: "medium" });
  };

  const isExpired = (expiresAt: string | null) => {
    if (!expiresAt) return false;
    return new Date(expiresAt) < new Date();
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="text-gray-600 dark:text-gray-400">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Navigation */}
      <PageHeader
        title={tApiKeys("title")}
        subtitle={tApiKeys("subtitle")}
        actions={
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors shadow-sm"
          >
            + {tApiKeys("createNewKey")}
          </button>
        }
      />

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Error Message */}
        {error && (
          <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
          </div>
        )}

        {/* API Keys List */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
          {apiKeys.length === 0 ? (
            <div className="p-8 text-center">
              <p className="text-gray-500 dark:text-gray-400">{tApiKeys("noApiKeysFound")}</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-700">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      {tApiKeys("keyPrefix")}
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      {tApiKeys("description")}
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      {tApiKeys("status")}
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      {tApiKeys("created")}
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      {tApiKeys("lastUsed")}
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      {tApiKeys("expires")}
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      {tApiKeys("actions")}
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                  {apiKeys.map((key) => (
                    <tr key={key.id}>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <code className="text-sm font-mono text-gray-900 dark:text-white bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">
                          {key.key_prefix}***
                        </code>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                        {key.description || (
                          <span className="text-gray-400 italic">{tApiKeys("noDescription")}</span>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {isExpired(key.expires_at) ? (
                          <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-red-100 text-red-800">
                            {tCommon("expired")}
                          </span>
                        ) : key.is_active ? (
                          <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                            {tCommon("active")}
                          </span>
                        ) : (
                          <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-gray-100 text-gray-800">
                            {tCommon("disabled")}
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                        {formatDate(key.created_at)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                        {formatDate(key.last_used_at)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                        {key.expires_at ? formatDate(key.expires_at) : tCommon("never")}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        {key.is_active ? (
                          <button
                            onClick={() => handleDisableKey(key.id)}
                            className="text-orange-600 hover:text-orange-900 mr-3"
                          >
                            {tCommon("disable")}
                          </button>
                        ) : (
                          <button
                            onClick={() => handleEnableKey(key.id)}
                            className="text-green-600 hover:text-green-900 mr-3"
                          >
                            {tCommon("enable")}
                          </button>
                        )}
                        <button
                          onClick={() => setDeleteTarget(key)}
                          className="text-red-600 hover:text-red-900"
                        >
                          {tCommon("delete")}
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
          <h3 className="text-sm font-medium text-blue-800 dark:text-blue-300 mb-2">
            {tApiKeys("aboutApiKeys")}
          </h3>
          <ul className="text-sm text-blue-700 dark:text-blue-400 space-y-1 list-disc list-inside">
            <li>{tApiKeys("aboutApiKeysInfo1")}</li>
            <li>{tApiKeys("aboutApiKeysInfo2")}</li>
            <li>{tApiKeys("aboutApiKeysInfo3")}</li>
          </ul>
        </div>
      </main>

      {/* Create Key Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
              {tApiKeys("createNewApiKey")}
            </h3>

            <form onSubmit={handleCreateKey} className="space-y-4">
              <div>
                <label
                  htmlFor="description"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
                >
                  {tApiKeys("description")}
                </label>
                <input
                  id="description"
                  type="text"
                  required
                  value={newKeyDescription}
                  onChange={(e) => setNewKeyDescription(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                  placeholder={tApiKeys("descriptionPlaceholder")}
                />
              </div>

              <div>
                <label
                  htmlFor="expires"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
                >
                  {tApiKeys("expiresInDays")}
                </label>
                <input
                  id="expires"
                  type="number"
                  min="1"
                  value={newKeyExpiresInDays ?? ""}
                  onChange={(e) =>
                    setNewKeyExpiresInDays(e.target.value ? parseInt(e.target.value) : null)
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                  placeholder={tApiKeys("expiresPlaceholder")}
                />
              </div>

              <div className="flex justify-end space-x-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600"
                >
                  {tCommon("cancel")}
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {creating ? tApiKeys("creating") : tApiKeys("createKey")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Show Key Modal */}
      {showKeyModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4">
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
                {tApiKeys("apiKeyCreated")}
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400 text-center mt-2">
                {tApiKeys("copyKeyNow")}
              </p>
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                {tApiKeys("yourApiKey")}
              </label>
              <div className="flex">
                <input
                  type="text"
                  readOnly
                  value={newlyCreatedKey}
                  className="flex-1 px-3 py-2 bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-l-md text-sm font-mono text-gray-900 dark:text-white"
                />
                <button
                  onClick={handleCopyKey}
                  className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-r-md hover:bg-blue-700"
                >
                  {copied ? tCommon("copied") : tCommon("copy")}
                </button>
              </div>
            </div>

            <button
              onClick={() => setShowKeyModal(false)}
              className="w-full px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
            >
              {tApiKeys("iveSavedMyKey")}
            </button>
          </div>
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={!!deleteTarget}
        title={tApiKeys("deleteKeyTitle")}
        description={tApiKeys("deleteKeyConfirm")}
        confirmText={tCommon("delete")}
        cancelText={tCommon("cancel")}
        variant="danger"
        loading={deleting}
        onConfirm={() => {
          if (deleteTarget) handleDeleteKey(deleteTarget.id);
        }}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
