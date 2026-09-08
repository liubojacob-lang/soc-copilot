"use client";

import { FixedSizeList } from "react-window";
import { useFormatter } from "next-intl";

import { getStatusCodeClass, getMethodClass } from "../utils";
import type { AuditLog } from "../types";

interface VirtualAuditTableProps {
  logs: AuditLog[];
  height?: number;
  rowHeight?: number;
}

const HEADER_HEIGHT = 56;
const ROW_HEIGHT = 64;

function AuditLogRow({ log, style }: { log: AuditLog; style: React.CSSProperties }) {
  const format = useFormatter();
  return (
    <div
      style={style}
      className="flex items-center border-b border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700"
    >
      <div className="px-4 py-3 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400 w-40">
        {format.dateTime(new Date(log.created_at), { dateStyle: "medium", timeStyle: "medium" })}
      </div>
      <div className="hidden md:block px-4 py-3 whitespace-nowrap text-sm text-gray-900 dark:text-white w-28">
        {log.username || <span className="text-gray-400 italic">System</span>}
      </div>
      <div className="px-4 py-3 text-sm text-gray-900 dark:text-white w-32">
        <code className="text-xs bg-gray-100 dark:bg-gray-700 px-1.5 py-0.5 rounded">
          {log.action}
        </code>
      </div>
      <div className="px-4 py-3 whitespace-nowrap w-20">
        <span className={`px-2 py-1 text-xs font-semibold rounded ${getMethodClass(log.method)}`}>
          {log.method}
        </span>
      </div>
      <div className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400 font-mono flex-1">
        <div className="truncate max-w-xs" title={log.path}>
          {log.path}
        </div>
      </div>
      <div className="px-4 py-3 whitespace-nowrap w-20">
        <span
          className={`px-2 py-1 text-xs font-semibold rounded ${getStatusCodeClass(log.status_code)}`}
        >
          {log.status_code}
        </span>
      </div>
      <div className="hidden md:block px-4 py-3 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400 w-32">
        {log.target_type && (
          <span>
            {log.target_type}:{log.target_id}
          </span>
        )}
      </div>
      <div className="hidden md:block px-4 py-3 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400 w-20">
        {log.duration_ms !== null ? `${log.duration_ms}ms` : "-"}
      </div>
    </div>
  );
}

export function VirtualAuditTable({
  logs,
  height = 600,
  rowHeight = ROW_HEIGHT,
}: VirtualAuditTableProps) {
  const emptyComponent = (
    <div className="p-8 text-center">
      <p className="text-gray-500 dark:text-gray-400">No audit logs found.</p>
    </div>
  );

  if (logs.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
        {emptyComponent}
      </div>
    );
  }

  const Row = ({ index, style }: { index: number; style: React.CSSProperties }) => {
    const log = logs[index];
    return <AuditLogRow key={log.id} log={log} style={style} />;
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
      <div className="overflow-x-auto">
        {/* Table Header */}
        <div
          className="flex items-center bg-gray-50 dark:bg-gray-700 sticky top-0 z-10"
          style={{ height: HEADER_HEIGHT }}
        >
          <div className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider w-40">
            Time
          </div>
          <div className="hidden md:block px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider w-28">
            User
          </div>
          <div className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider w-32">
            Action
          </div>
          <div className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider w-20">
            Method
          </div>
          <div className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider flex-1">
            Path
          </div>
          <div className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider w-20">
            Status
          </div>
          <div className="hidden md:block px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider w-32">
            Target
          </div>
          <div className="hidden md:block px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider w-20">
            Duration
          </div>
        </div>

        {/* Virtual List */}
        <FixedSizeList
          height={height - HEADER_HEIGHT}
          itemCount={logs.length}
          itemSize={rowHeight}
          width="100%"
          className="scrollbar-thin"
        >
          {Row}
        </FixedSizeList>
      </div>
    </div>
  );
}

export default VirtualAuditTable;
