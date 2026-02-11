"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { loadAuthState, logout, isAdmin, authFetchJSON } from "@/lib/auth";
import Navigation from "@/components/Navigation";

interface Secret {
  id: string;
  name: string;
  value_preview: string;
  created_at: string;
  updated_at: string;
  created_by_user_id: string | null;
}

export default function SecretsPage() {
  const router = useRouter();
  const [secrets, setSecrets] = useState<Secret[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [selectedSecret, setSelectedSecret] = useState<Secret | null>(null);
  const [creating, setCreating] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // Form state
  const [secretName, setSecretName] = useState("");
  const [secretValue, setSecretValue] = useState("");

  useEffect(() => {
    const authState = loadAuthState();
    if (!authState?.isAuthenticated) {
      router.push("/login");
      return;
    }
    if (!isAdmin(authState.user)) {
      router.push("/");
      return;
    }
    fetchSecrets();
  }, [router]);

  const fetchSecrets = async () => {
    try {
      const data = await authFetchJSON<{ items: Secret[]; total: number }>("/api/secrets");
      setSecrets(data.items);
    } catch (err: any) {
      setError(err.message || "Failed to load secrets");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateSecret = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setError("");

    try {
      await authFetchJSON("/api/secrets", {
        method: "POST",
        body: JSON.stringify({
          name: secretName,
          value: secretValue,
        }),
      });

      setShowCreateModal(false);
      resetCreateForm();
      await fetchSecrets();
    } catch (err: any) {
      setError(err.message || "Failed to create secret");
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteSecret = async () => {
    if (!selectedSecret) return;

    setDeleting(true);
    setError("");

    try {
      await authFetchJSON(`/api/secrets/${selectedSecret.name}`, {
        method: "DELETE",
      });

      setShowDeleteModal(false);
      setSelectedSecret(null);
      await fetchSecrets();
    } catch (err: any) {
      setError(err.message || "Failed to delete secret");
    } finally {
      setDeleting(false);
    }
  };

  const resetCreateForm = () => {
    setSecretName("");
    setSecretValue("");
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString();
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
      <Navigation title="Secrets Management" subtitle="Manage encrypted secrets and credentials (Admin)" />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-md">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        <div className="flex justify-between items-center mb-6">
          <div>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Secrets</h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              Encrypted credential storage for playbook variables
            </p>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
          >
            Create Secret
          </button>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
          {secrets.length === 0 ? (
            <div className="p-8 text-center">
              <p className="text-gray-500 dark:text-gray-400">No secrets found.</p>
              <p className="text-sm text-gray-400 dark:text-gray-500 mt-2">
                Create secrets to use <code className="bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">{"{{secret.secret_name}}"}</code> in playbooks
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-700">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      Name
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      Value Preview
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      Created
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      Updated
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                  {secrets.map((secret) => (
                    <tr key={secret.id}>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <svg className="w-5 h-5 text-gray-400 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                          </svg>
                          <span className="text-sm font-medium text-gray-900 dark:text-white font-mono">
                            {secret.name}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <code className="text-sm text-gray-600 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">
                          {secret.value_preview}
                        </code>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                        {formatDate(secret.created_at)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                        {formatDate(secret.updated_at)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <button
                          onClick={() => {
                            setSelectedSecret(secret);
                            setShowDeleteModal(true);
                          }}
                          className="text-red-600 hover:text-red-900"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md">
          <h3 className="text-sm font-medium text-blue-800 dark:text-blue-300 mb-2">Using Secrets in Playbooks</h3>
          <p className="text-sm text-blue-700 dark:text-blue-400 mb-2">
            Reference secrets in playbook node inputs using the <code className="bg-blue-100 dark:bg-blue-800 px-1 rounded">{"{{secret.secret_name}}"}</code> syntax:
          </p>
          <ul className="text-sm text-blue-700 dark:text-blue-400 space-y-1 list-disc list-inside">
            <li><code className="bg-blue-100 dark:bg-blue-800 px-1 rounded">{"{{secret.SLACK_WEBHOOK}}"}</code> - Slack webhook URL</li>
            <li><code className="bg-blue-100 dark:bg-blue-800 px-1 rounded">{"{{secret.API_KEY}}"}</code> - API authentication key</li>
            <li><code className="bg-blue-100 dark:bg-blue-800 px-1 rounded">{"{{secret.DB_PASSWORD}}"}</code> - Database credential</li>
          </ul>
        </div>
      </main>

      {/* Create Secret Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Create New Secret</h3>

            <form onSubmit={handleCreateSecret} className="space-y-4">
              <div>
                <label htmlFor="secretName" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Secret Name
                </label>
                <input
                  id="secretName"
                  type="text"
                  required
                  pattern="[A-Z_][A-Z0-9_]*"
                  title="Use uppercase letters, numbers, and underscores only"
                  value={secretName}
                  onChange={(e) => setSecretName(e.target.value.toUpperCase().replace(/[^A-Z0-9_]/g, ""))}
                  placeholder="API_KEY"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white font-mono"
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  Use uppercase with underscores (e.g., SLACK_WEBHOOK)
                </p>
              </div>

              <div>
                <label htmlFor="secretValue" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Secret Value
                </label>
                <textarea
                  id="secretValue"
                  required
                  value={secretValue}
                  onChange={(e) => setSecretValue(e.target.value)}
                  rows={4}
                  placeholder="https://hooks.slack.com/services/..."
                  className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white font-mono text-sm"
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  Value will be encrypted before storage
                </p>
              </div>

              <div className="flex justify-end space-x-3 pt-4">
                <button
                  type="button"
                  onClick={() => {
                    setShowCreateModal(false);
                    resetCreateForm();
                  }}
                  className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {creating ? "Creating..." : "Create Secret"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteModal && selectedSecret && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4">
            <div className="flex items-center mb-4">
              <div className="flex-shrink-0 w-10 h-10 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
                <svg className="w-6 h-6 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <h3 className="ml-3 text-lg font-medium text-gray-900 dark:text-white">Delete Secret</h3>
            </div>

            <div className="mb-4">
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Are you sure you want to delete the secret <code className="bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded font-mono">{selectedSecret.name}</code>?
              </p>
              <p className="text-sm text-red-600 dark:text-red-400 mt-2">
                This action cannot be undone. Any playbooks using this secret will fail.
              </p>
            </div>

            <div className="flex justify-end space-x-3">
              <button
                onClick={() => {
                  setShowDeleteModal(false);
                  setSelectedSecret(null);
                }}
                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteSecret}
                disabled={deleting}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {deleting ? "Deleting..." : "Delete Secret"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
