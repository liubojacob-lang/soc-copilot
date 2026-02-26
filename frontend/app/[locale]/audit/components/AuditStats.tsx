/** Audit logs statistics cards component */

import type { AuditLogStats } from '../types';

interface AuditStatsProps {
  stats: AuditLogStats | null;
}

export function AuditStats({ stats }: AuditStatsProps) {
  if (!stats) return null;

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
        <p className="text-sm text-gray-600 dark:text-gray-400">Total Logs</p>
        <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats.total_requests}</p>
      </div>
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
        <p className="text-sm text-gray-600 dark:text-gray-400">Last 24 Hours</p>
        <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">{stats.last_24h_requests}</p>
      </div>
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
        <p className="text-sm text-gray-600 dark:text-gray-400">Failed Requests</p>
        <p className="text-2xl font-bold text-red-600 dark:text-red-400">{stats.failed_requests}</p>
      </div>
    </div>
  );
}
