"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { loadAuthState, authFetchJSON } from "@/lib/auth";
import Navigation from "@/components/Navigation";

interface Definition {
  id: string;
  name: string;
  description: string | null;
  is_active: boolean;
}

interface CronTriggerResponse {
  id: string;
  definition_id: string;
  type: "cron";
  name: string | null;
  cron_expr: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  last_triggered_at: string | null;
}

// Common cron presets
const CRON_PRESETS: Record<string, { expr: string; description: string }> = {
  every_minute: { expr: "* * * * *", description: "Every minute" },
  every_5_minutes: { expr: "*/5 * * * *", description: "Every 5 minutes" },
  every_15_minutes: { expr: "*/15 * * * *", description: "Every 15 minutes" },
  every_30_minutes: { expr: "*/30 * * * *", description: "Every 30 minutes" },
  hourly: { expr: "0 * * * *", description: "Hourly (at minute 0)" },
  daily_midnight: { expr: "0 0 * * *", description: "Daily at midnight" },
  daily_noon: { expr: "0 12 * * *", description: "Daily at noon" },
  weekly_monday: { expr: "0 0 * * 1", description: "Weekly on Monday at midnight" },
  monthly: { expr: "0 0 1 * *", description: "Monthly on the 1st at midnight" },
};

export default function NewCronTriggerPage() {
  const router = useRouter();
  const [definitions, setDefinitions] = useState<Definition[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [createdTrigger, setCreatedTrigger] = useState<CronTriggerResponse | null>(null);

  const [formData, setFormData] = useState({
    definition_id: "",
    cron_expr: "",
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

  const fetchDefinitions = async () => {
    try {
      const data = await authFetchJSON<{items: any[], total: number}>("/api/playbook-definitions?page=1&page_size=100");
      setDefinitions(data.items.filter((d: Definition) => d.is_active));
    } catch (err: any) {
      setError(err.message || "Failed to load playbook definitions");
    } finally {
      setLoading(false);
    }
  };

  const handlePresetClick = (expr: string) => {
    setFormData({ ...formData, cron_expr: expr });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setError("");

    try {
      const response = await authFetchJSON<CronTriggerResponse>("/api/triggers/cron", {
        method: "POST",
        body: JSON.stringify(formData),
      });

      setCreatedTrigger(response);
      setShowSuccessModal(true);
    } catch (err: any) {
      setError(err.message || "Failed to create cron trigger");
    } finally {
      setCreating(false);
    }
  };

  const handleCloseModal = () => {
    setShowSuccessModal(false);
    router.push("/triggers");
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
      <Navigation title="New Cron Trigger" subtitle="Schedule automated playbook execution" />

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
              <label htmlFor="definition_id" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Playbook Definition *
              </label>
              <select
                id="definition_id"
                required
                value={formData.definition_id}
                onChange={(e) => setFormData({ ...formData, definition_id: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              >
                <option value="">Select a playbook...</option>
                {definitions.map((def) => (
                  <option key={def.id} value={def.id}>
                    {def.name} {def.description ? `- ${def.description}` : ""}
                  </option>
                ))}
              </select>
            </div>

            {/* Cron Expression */}
            <div>
              <label htmlFor="cron_expr" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Cron Expression *
              </label>
              <input
                id="cron_expr"
                type="text"
                required
                value={formData.cron_expr}
                onChange={(e) => setFormData({ ...formData, cron_expr: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white font-mono"
                placeholder="e.g., 0 0 * * * (daily at midnight)"
              />
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                Format: minute hour day month weekday (e.g., 0 0 * * * for daily at midnight)
              </p>
            </div>

            {/* Cron Presets */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Quick Presets
              </label>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                {Object.entries(CRON_PRESETS).map(([key, { expr, description }]) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => handlePresetClick(expr)}
                    className={`px-3 py-2 text-xs rounded-md border ${
                      formData.cron_expr === expr
                        ? "bg-purple-100 border-purple-500 text-purple-700 dark:bg-purple-900 dark:text-purple-300"
                        : "bg-gray-50 border-gray-300 text-gray-700 hover:bg-gray-100 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-300"
                    }`}
                  >
                    <div className="font-mono">{expr}</div>
                    <div className="text-[10px] opacity-75">{description}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* Trigger Name */}
            <div>
              <label htmlFor="name" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Trigger Name
              </label>
              <input
                id="name"
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                placeholder="e.g., Daily Security Scan"
              />
            </div>

            {/* Active Status */}
            <div className="flex items-center">
              <input
                id="is_active"
                type="checkbox"
                checked={formData.is_active}
                onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                className="h-4 w-4 text-purple-600 focus:ring-purple-500 border-gray-300 rounded"
              />
              <label htmlFor="is_active" className="ml-2 block text-sm text-gray-900 dark:text-white">
                Activate trigger immediately
              </label>
            </div>

            {/* Submit */}
            <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200 dark:border-gray-700">
              <button
                type="button"
                onClick={() => router.push("/triggers")}
                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={creating}
                className="px-4 py-2 text-sm font-medium text-white bg-purple-600 rounded-md hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {creating ? "Creating..." : "Create Cron Trigger"}
              </button>
            </div>
          </form>
        </div>

        {/* Info Box */}
        <div className="mt-6 p-4 bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-md">
          <h3 className="text-sm font-medium text-purple-800 dark:text-purple-300 mb-2">About Cron Triggers</h3>
          <ul className="text-sm text-purple-700 dark:text-purple-400 space-y-1 list-disc list-inside">
            <li>Cron triggers execute playbooks on a schedule using cron expressions</li>
            <li>The scheduler checks for due triggers every 30 seconds</li>
            <li>Trigger execution is logged in the audit log</li>
            <li>Use presets for common schedules or enter a custom cron expression</li>
          </ul>
        </div>
      </main>

      {/* Success Modal */}
      {showSuccessModal && createdTrigger && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4">
            <div className="mb-4">
              <div className="flex items-center justify-center w-12 h-12 bg-green-100 rounded-full mb-4">
                <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-gray-900 dark:text-white text-center">Cron Trigger Created</h3>
              <p className="text-sm text-gray-500 dark:text-gray-400 text-center mt-2">
                Your cron trigger has been created and will execute on schedule.
              </p>
            </div>

            <div className="mb-4 p-3 bg-gray-50 dark:bg-gray-700 rounded-md">
              <div className="text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Schedule:</span>
                  <span className="font-mono text-gray-900 dark:text-white">{createdTrigger.cron_expr}</span>
                </div>
                <div className="flex justify-between mt-1">
                  <span className="text-gray-600 dark:text-gray-400">Playbook:</span>
                  <span className="text-gray-900 dark:text-white">{definitions.find(d => d.id === createdTrigger.definition_id)?.name || createdTrigger.definition_id}</span>
                </div>
              </div>
            </div>

            <button
              onClick={handleCloseModal}
              className="w-full px-4 py-2 text-sm font-medium text-white bg-purple-600 rounded-md hover:bg-purple-700"
            >
              Done
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
