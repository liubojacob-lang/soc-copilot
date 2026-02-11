"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api, PlaybookRunResponse, PlaybookMetadata } from "@/lib/api";
import { loadAuthState, logout, isAdmin, type User } from "@/lib/auth";
import Navigation from "@/components/Navigation";
import { api_v74 } from "@/lib/api";

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-gray-100 text-gray-700",
  running: "bg-blue-100 text-blue-700",
  success: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
  partial: "bg-amber-100 text-amber-700",
  skipped: "bg-gray-100 text-gray-500",
  queued: "bg-purple-100 text-purple-700",  // v0.7.4: queued status
};

const MODE_COLORS: Record<string, string> = {
  dry_run: "bg-purple-50 text-purple-700",
  apply: "bg-red-50 text-red-700",
};

export default function PlaybooksPage() {
  const router = useRouter();
  const [runs, setRuns] = useState<PlaybookRunResponse[]>([]);
  const [playbooks, setPlaybooks] = useState<Record<string, PlaybookMetadata>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>("");
  const [filterPlaybook, setFilterPlaybook] = useState<string>("");
  const [user, setUser] = useState<User | null>(null);
  const [mounted, setMounted] = useState(false);
  // v0.7.4: Queue stats
  const [queueStats, setQueueStats] = useState<{ running: number; queued: number; max_concurrent: number } | null>(null);

  useEffect(() => {
    setMounted(true);

    // Check authentication
    const authState = loadAuthState();
    if (!authState?.isAuthenticated) {
      router.push("/login");
      return;
    }
    setUser(authState.user);

    loadData();
    // v0.7.4: Poll queue stats every 10 seconds
    loadQueueStats();
    const interval = setInterval(loadQueueStats, 10000);
    return () => clearInterval(interval);
  }, [router, filterStatus, filterPlaybook]);

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  // v0.7.4: Load queue stats
  async function loadQueueStats() {
    try {
      const stats = await api_v74.getQueueStats();
      setQueueStats(stats);
    } catch (e) {
      // Silently fail for queue stats
    }
  }

  if (!mounted) return null;

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const [runsResponse, playbooksData] = await Promise.all([
        api.listPlaybookRuns({
          status: filterStatus || undefined,
          playbook_name: filterPlaybook || undefined,
          page_size: 50,
        }),
        api.getAvailablePlaybooks(),
      ]);
      setRuns(runsResponse.items);
      setPlaybooks(playbooksData);
    } catch (e: unknown) {
      setError((e as Error)?.message ?? "Failed to load playbook runs");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Navigation */}
      <Navigation title="Playbook Runs" subtitle="Execute and monitor automated security playbooks" />

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

        {/* Filters */}
        <div className="bg-white rounded-lg border border-slate-200 p-4 mb-6">
          {/* v0.7.4: Queue Status */}
          {queueStats && (
            <div className="mb-4 p-3 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <svg className="w-5 h-5 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span className="text-sm font-medium text-blue-900 dark:text-blue-300">Run Queue</span>
                  </div>
                  <div className="flex items-center gap-4 text-sm">
                    <span className="flex items-center gap-1">
                      <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                      <span className="text-gray-700 dark:text-gray-300">Running: <strong>{queueStats.running}</strong></span>
                    </span>
                    <span className="flex items-center gap-1">
                      <span className="w-2 h-2 bg-purple-500 rounded-full"></span>
                      <span className="text-gray-700 dark:text-gray-300">Queued: <strong>{queueStats.queued}</strong></span>
                    </span>
                    <span className="text-gray-500 dark:text-gray-400">Max: {queueStats.max_concurrent}</span>
                  </div>
                </div>
              </div>
            </div>
          )}
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Filters</h2>
          <div className="flex gap-4">
            <div className="flex-1">
              <label className="block text-xs font-medium text-slate-600 mb-1">Playbook</label>
              <select
                value={filterPlaybook}
                onChange={(e) => setFilterPlaybook(e.target.value)}
                className="w-full p-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-soc-500"
              >
                <option value="">All Playbooks</option>
                {Object.entries(playbooks).map(([key, pb]) => (
                  <option key={key} value={key}>{pb.name}</option>
                ))}
              </select>
            </div>
            <div className="flex-1">
              <label className="block text-xs font-medium text-slate-600 mb-1">Status</label>
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="w-full p-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-soc-500"
              >
                <option value="">All Statuses</option>
                <option value="running">Running</option>
                <option value="success">Success</option>
                <option value="failed">Failed</option>
                <option value="partial">Partial</option>
              </select>
            </div>
            <div className="flex items-end">
              <button
                onClick={loadData}
                className="px-4 py-2 bg-soc-600 text-white font-medium rounded-lg hover:bg-soc-700"
              >
                Refresh
              </button>
            </div>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-800 text-sm">{error}</p>
          </div>
        )}

        {loading ? (
          <div className="text-center py-12">
            <p className="text-slate-600">Loading playbook runs...</p>
          </div>
        ) : runs.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-lg border border-slate-200">
            <p className="text-slate-600">No playbook runs found</p>
          </div>
        ) : (
          <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
            <table className="w-full">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-600 uppercase tracking-wider">
                    Playbook
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-600 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-600 uppercase tracking-wider">
                    Mode
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-600 uppercase tracking-wider">
                    Started
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-600 uppercase tracking-wider">
                    Duration
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-slate-600 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {runs.map((run) => {
                  const duration = run.finished_at
                    ? Math.round((new Date(run.finished_at).getTime() - new Date(run.started_at).getTime()) / 1000)
                    : null;

                  return (
                    <tr key={run.id} className="hover:bg-slate-50">
                      <td className="px-6 py-4">
                        <div>
                          <div className="font-medium text-slate-900">
                            {playbooks[run.playbook_name]?.name || run.playbook_name}
                          </div>
                          <div className="text-xs text-slate-500">{run.id}</div>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${STATUS_COLORS[run.status]}`}>
                          {run.status}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${MODE_COLORS[run.mode]}`}>
                          {run.mode}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-slate-600">
                        {new Date(run.started_at).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 text-sm text-slate-600">
                        {duration !== null ? `${duration}s` : "-"}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <a
                          href={`/playbooks/${run.id}`}
                          className="text-soc-600 hover:text-soc-700 text-sm font-medium"
                        >
                          View Details
                        </a>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Available Playbooks */}
        <div className="mt-8">
          <h2 className="text-xl font-semibold text-slate-900 mb-4">Available Playbooks</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {Object.entries(playbooks).map(([key, pb]) => (
              <div key={key} className="bg-white rounded-lg border border-slate-200 p-4">
                <h3 className="font-semibold text-slate-900">{pb.name}</h3>
                <p className="text-sm text-slate-600 mt-1">{pb.description}</p>
                <div className="flex items-center justify-between mt-3">
                  <span className="text-xs text-slate-500">v{pb.version} • ~{pb.estimated_duration_seconds}s</span>
                  <span className="text-xs text-slate-500">{pb.steps.length} steps</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
