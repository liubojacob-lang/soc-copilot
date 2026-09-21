/** Audit logs table component */

import { useFormatter } from "next-intl";

import { getStatusCodeClass, getMethodClass } from "../utils";
import type { AuditLog } from "../types";

interface AuditTableProps {
  logs: AuditLog[];
}

export function AuditTable({ logs }: AuditTableProps) {
  const format = useFormatter();
  if (logs.length === 0) {
    return (
      <div className="bg-white dark:bg-surface-card rounded-lg shadow overflow-hidden">
        <div className="p-8 text-center">
          <p className="text-text-tertiary dark:text-text-muted">No audit logs found.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-surface-card rounded-lg shadow overflow-hidden">
      <div className="overflow-hidden">
        <table className="w-full table-fixed divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-surface-card dark:bg-surface-active">
            <tr>
              <th className="w-36 lg:w-40 px-3 lg:px-4 py-3 text-left text-xs font-medium text-text-tertiary dark:text-text-muted uppercase tracking-wider">
                Time
              </th>
              <th className="hidden sm:table-cell w-24 lg:w-28 px-3 lg:px-4 py-3 text-left text-xs font-medium text-text-tertiary dark:text-text-muted uppercase tracking-wider">
                User
              </th>
              <th className="hidden md:table-cell w-28 lg:w-32 px-3 lg:px-4 py-3 text-left text-xs font-medium text-text-tertiary dark:text-text-muted uppercase tracking-wider">
                IP
              </th>
              <th className="w-40 lg:w-48 px-3 lg:px-4 py-3 text-left text-xs font-medium text-text-tertiary dark:text-text-muted uppercase tracking-wider">
                Action
              </th>
              <th className="w-16 lg:w-20 px-2 lg:px-3 py-3 text-center text-xs font-medium text-text-tertiary dark:text-text-muted uppercase tracking-wider">
                Method
              </th>
              <th className="px-3 lg:px-4 py-3 text-left text-xs font-medium text-text-tertiary dark:text-text-muted uppercase tracking-wider">
                Path
              </th>
              <th className="w-16 lg:w-20 px-2 lg:px-3 py-3 text-center text-xs font-medium text-text-tertiary dark:text-text-muted uppercase tracking-wider">
                Status
              </th>
              <th className="hidden md:table-cell w-16 lg:w-20 px-3 lg:px-4 py-3 text-right text-xs font-medium text-text-tertiary dark:text-text-muted uppercase tracking-wider">
                Duration
              </th>
              <th className="hidden lg:table-cell w-28 lg:w-36 px-3 lg:px-4 py-3 text-left text-xs font-medium text-text-tertiary dark:text-text-muted uppercase tracking-wider">
                Target
              </th>
            </tr>
          </thead>
          <tbody className="bg-white dark:bg-surface-card divide-y divide-gray-200 dark:divide-gray-700">
            {logs.map((log) => (
              <tr key={log.id} className="hover:bg-surface-card dark:hover:bg-gray-750">
                <td className="px-3 lg:px-4 py-3 whitespace-nowrap text-sm text-text-tertiary dark:text-text-muted">
                  {format.dateTime(new Date(log.created_at), {
                    dateStyle: "medium",
                    timeStyle: "medium",
                  })}
                </td>
                <td className="hidden sm:table-cell px-3 lg:px-4 py-3 whitespace-nowrap text-sm text-text-primary dark:text-white truncate">
                  {log.username || <span className="text-text-muted italic">System</span>}
                </td>
                <td className="hidden md:table-cell px-3 lg:px-4 py-3 whitespace-nowrap text-xs text-text-tertiary dark:text-text-muted font-mono truncate">
                  {log.ip_address || <span className="text-text-muted italic">—</span>}
                </td>
                <td className="px-3 lg:px-4 py-3 text-sm text-text-primary dark:text-white truncate">
                  <code className="text-xs bg-surface-hover dark:bg-surface-active px-2 py-0.5 rounded font-mono truncate inline-block max-w-full">
                    {log.action}
                  </code>
                </td>
                <td className="px-2 lg:px-3 py-3 whitespace-nowrap text-center">
                  <span
                    className={`px-2 py-1 text-xs font-semibold rounded ${getMethodClass(log.method)}`}
                  >
                    {log.method}
                  </span>
                </td>
                <td
                  className="px-3 lg:px-4 py-3 text-sm text-text-secondary dark:text-text-muted font-mono truncate"
                  title={log.path}
                >
                  {log.path}
                </td>
                <td className="px-2 lg:px-3 py-3 whitespace-nowrap text-center">
                  <span
                    className={`px-2 py-1 text-xs font-semibold rounded ${getStatusCodeClass(log.status_code)}`}
                  >
                    {log.status_code}
                  </span>
                </td>
                <td className="hidden md:table-cell px-3 lg:px-4 py-3 whitespace-nowrap text-xs text-text-tertiary dark:text-text-muted text-right font-mono">
                  {log.duration_ms !== null ? (
                    `${log.duration_ms}ms`
                  ) : (
                    <span className="text-text-muted">—</span>
                  )}
                </td>
                <td className="hidden lg:table-cell px-3 lg:px-4 py-3 whitespace-nowrap text-xs text-text-secondary dark:text-text-muted truncate">
                  {log.target_type ? (
                    <span
                      className="px-1.5 py-0.5 rounded bg-surface-hover dark:bg-surface-active font-mono text-[11px]"
                      title={`${log.target_type}:${log.target_id}`}
                    >
                      {log.target_type}:{log.target_id}
                    </span>
                  ) : (
                    <span className="text-text-muted dark:text-text-tertiary">—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
