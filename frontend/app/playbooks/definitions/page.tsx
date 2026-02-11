"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { loadAuthState, logout } from "@/lib/auth";
import Navigation from "@/components/Navigation";
import { Plus, Play, Edit, Trash2, Search } from "lucide-react";

export default function PlaybookDefinitionsPage() {
  const router = useRouter();
  const [definitions, setDefinitions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [mounted, setMounted] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    setMounted(true);

    // Check authentication
    const authState = loadAuthState();
    if (!authState?.isAuthenticated) {
      router.push("/login");
      return;
    }

    loadDefinitions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  if (!mounted) return null;

  async function loadDefinitions() {
    setLoading(true);
    setError(null);
    try {
      const response = await api.listPlaybookDefinitions({ is_active: true, page_size: 50 });
      // Backend returns 'items', frontend expects 'definitions' - map it here
      setDefinitions((response as any).items || []);
    } catch (e: unknown) {
      setError((e as Error)?.message ?? "Failed to load playbook definitions");
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(definitionId: string) {
    if (!confirm("Are you sure you want to delete this playbook definition?")) {
      return;
    }

    setDeletingId(definitionId);
    try {
      // Note: Delete endpoint not yet implemented, would need to add
      await fetch(`/api/playbook-definitions/${definitionId}`, {
        method: "DELETE",
        headers: {
          "Authorization": `Bearer ${localStorage.getItem("access_token")}`,
        },
      });
      await loadDefinitions();
    } catch (e: unknown) {
      setError((e as Error)?.message ?? "Failed to delete definition");
    } finally {
      setDeletingId(null);
    }
  }

  async function handleExecute(definitionId: string) {
    try {
      const result = await api.executeDAGDefinition(definitionId, "dry_run");
      router.push(`/playbooks/${result.run_id}`);
    } catch (e: unknown) {
      setError((e as Error)?.message ?? "Failed to execute playbook");
    }
  }

  const filteredDefinitions = (definitions || []).filter(def =>
    def?.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (def?.description && def.description.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Navigation title="Playbook Definitions" subtitle="Manage DAG-based playbook workflows" />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Actions Bar */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 mb-6">
          <div className="flex gap-4 items-center">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search definitions..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
              />
            </div>
            <button
              onClick={() => router.push("/playbooks/definitions/new")}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <Plus className="w-5 h-5" />
              Create Definition
            </button>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 px-4 py-3 rounded-lg mb-6">
            {error}
          </div>
        )}

        {/* Loading State */}
        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
            <p className="mt-4 text-gray-600 dark:text-gray-400">Loading definitions...</p>
          </div>
        ) : filteredDefinitions.length === 0 ? (
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-12 text-center">
            <div className="w-16 h-16 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-4">
              <Plus className="w-8 h-8 text-gray-400" />
            </div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">No playbook definitions</h3>
            <p className="text-gray-600 dark:text-gray-400 mb-4">
              {searchQuery ? "No definitions match your search." : "Get started by creating your first DAG-based playbook."}
            </p>
            <button
              onClick={() => router.push("/playbooks/definitions/new")}
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <Plus className="w-5 h-5" />
              Create Definition
            </button>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {filteredDefinitions.map((definition) => (
              <div
                key={definition.id}
                className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-5 hover:shadow-lg transition-shadow"
              >
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="font-semibold text-gray-900 dark:text-white">{definition.name}</h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">v{definition.version}</p>
                  </div>
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                    definition.is_active
                      ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                      : "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-400"
                  }`}>
                    {definition.is_active ? "Active" : "Inactive"}
                  </span>
                </div>

                {definition.description && (
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-4 line-clamp-2">
                    {definition.description}
                  </p>
                )}

                <div className="flex gap-2 mt-auto">
                  <button
                    onClick={() => router.push(`/playbooks/definitions/${definition.id}`)}
                    className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm"
                  >
                    <Play className="w-4 h-4" />
                    Run
                  </button>
                  <button
                    onClick={() => router.push(`/playbooks/definitions/${definition.id}/edit`)}
                    className="p-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                  >
                    <Edit className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                  </button>
                  <button
                    onClick={() => handleDelete(definition.id)}
                    disabled={deletingId === definition.id}
                    className="p-2 border border-red-300 dark:border-red-800 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors disabled:opacity-50"
                  >
                    <Trash2 className="w-4 h-4 text-red-600 dark:text-red-400" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
