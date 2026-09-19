"use client";

import { FixedSizeList } from "react-window";
import { useFormatter } from "next-intl";

import { getStatusCodeClass, getMethodClass } from "../utils";
import type { AuditLog } from "../types";

interface VirtualAuditTableProps {
  logs: AuditLog[];
  height?: number;
  rowHeight?: number;
  isFetching?: boolean;
}

const HEADER_HEIGHT = 56;
const ROW_HEIGHT = 64;

function AuditLogRow({ log, style }: { log: AuditLog; style: React.CSSProperties }) {
  const format = useFormatter();
  return (
    <div
      style={style}
      className="flex items-center border-b border-border-subtle dark:border-border-strong hover:bg-surface-card dark:hover:bg-surface-active w-full overflow-hidden"
    >
      {/* Time */}
      <div className="w-36 lg:w-40 shrink-0 px-3 lg:px-4 py-3 whitespace-nowrap text-sm text-text-tertiary dark:text-text-muted">
        {format.dateTime(new Date(log.created_at), { dateStyle: "medium", timeStyle: "medium" })}
      </div>
      {/* User */}
      <div className="hidden sm:block w-24 lg:w-28 shrink-0 px-3 lg:px-4 py-3 whitespace-nowrap text-sm text-text-primary dark:text-white truncate">
        {log.username || <span className="text-text-muted italic">System</span>}
      </div>
      {/* Client IP */}
      <div className="hidden md:block w-28 lg:w-32 shrink-0 px-3 lg:px-4 py-3 whitespace-nowrap text-xs text-text-tertiary dark:text-text-muted font-mono truncate">
        {log.ip_address || <span className="text-text-muted italic">—</span>}
      </div>
      {/* Action */}
      <div className="w-40 lg:w-48 shrink-0 px-3 lg:px-4 py-3 text-sm text-text-primary dark:text-white truncate">
        <code className="text-xs bg-surface-hover dark:bg-surface-active px-2 py-0.5 rounded font-mono truncate inline-block max-w-full">
          {log.action}
        </code>
      </div>
      {/* Method */}
      <div className="w-16 lg:w-20 shrink-0 px-2 lg:px-3 py-3 whitespace-nowrap text-center">
        <span className={`px-2 py-1 text-xs font-semibold rounded ${getMethodClass(log.method)}`}>
          {log.method}
        </span>
      </div>
      {/* Path */}
      <div className="flex-1 min-w-[220px] px-3 lg:px-4 py-3 text-sm text-text-secondary dark:text-text-muted font-mono">
        <div className="truncate" title={log.path}>
          {log.path}
        </div>
      </div>
      {/* Status */}
      <div className="w-16 lg:w-20 shrink-0 px-2 lg:px-3 py-3 whitespace-nowrap text-center">
        <span
          className={`px-2 py-1 text-xs font-semibold rounded ${getStatusCodeClass(log.status_code)}`}
        >
          {log.status_code}
        </span>
      </div>
      {/* Duration */}
      <div className="hidden md:block w-16 lg:w-20 shrink-0 px-3 lg:px-4 py-3 whitespace-nowrap text-xs text-text-tertiary dark:text-text-muted text-right font-mono">
        {log.duration_ms !== null ? (
          `${log.duration_ms}ms`
        ) : (
          <span className="text-text-muted">—</span>
        )}
      </div>
      {/* Target */}
      <div className="hidden lg:block w-28 lg:w-36 shrink-0 px-3 lg:px-4 py-3 whitespace-nowrap text-xs text-text-secondary dark:text-text-muted truncate">
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
      </div>
    </div>
  );
}

export function VirtualAuditTable({
  logs,
  height = 600,
  rowHeight = ROW_HEIGHT,
  isFetching = false,
}: VirtualAuditTableProps) {
  const Row = ({ index, style }: { index: number; style: React.CSSProperties }) => {
    const log = logs[index];
    return <AuditLogRow key={log.id} log={log} style={style} />;
  };

  return (
    <div
      className={`bg-white dark:bg-surface-card rounded-lg shadow overflow-hidden flex flex-col relative transition-opacity duration-150 ${
        isFetching ? "opacity-75" : "opacity-100"
      }`}
      style={{ minHeight: height, height }}
    >
      {isFetching && (
        <div className="absolute top-0 left-0 right-0 h-0.5 bg-blue-500 animate-pulse z-20" />
      )}
      <div className="overflow-hidden flex-1 flex flex-col">
        {/* Table Header */}
        <div
          className="flex items-center bg-surface-card dark:bg-surface-active sticky top-0 z-10 shrink-0 border-b border-border-subtle dark:border-gray-600"
          style={{ height: HEADER_HEIGHT }}
        >
          <div className="w-36 lg:w-40 shrink-0 px-3 lg:px-4 py-3 text-left text-xs font-medium text-text-tertiary dark:text-text-muted uppercase tracking-wider">
            Time
          </div>
          <div className="hidden sm:block w-24 lg:w-28 shrink-0 px-3 lg:px-4 py-3 text-left text-xs font-medium text-text-tertiary dark:text-text-muted uppercase tracking-wider">
            User
          </div>
          <div className="hidden md:block w-28 lg:w-32 shrink-0 px-3 lg:px-4 py-3 text-left text-xs font-medium text-text-tertiary dark:text-text-muted uppercase tracking-wider">
            IP
          </div>
          <div className="w-40 lg:w-48 shrink-0 px-3 lg:px-4 py-3 text-left text-xs font-medium text-text-tertiary dark:text-text-muted uppercase tracking-wider">
            Action
          </div>
          <div className="w-16 lg:w-20 shrink-0 px-2 lg:px-3 py-3 text-center text-xs font-medium text-text-tertiary dark:text-text-muted uppercase tracking-wider">
            Method
          </div>
          <div className="flex-1 min-w-[220px] px-3 lg:px-4 py-3 text-left text-xs font-medium text-text-tertiary dark:text-text-muted uppercase tracking-wider">
            Path
          </div>
          <div className="w-16 lg:w-20 shrink-0 px-2 lg:px-3 py-3 text-center text-xs font-medium text-text-tertiary dark:text-text-muted uppercase tracking-wider">
            Status
          </div>
          <div className="hidden md:block w-16 lg:w-20 shrink-0 px-3 lg:px-4 py-3 text-right text-xs font-medium text-text-tertiary dark:text-text-muted uppercase tracking-wider">
            Duration
          </div>
          <div className="hidden lg:block w-28 lg:w-36 shrink-0 px-3 lg:px-4 py-3 text-left text-xs font-medium text-text-tertiary dark:text-text-muted uppercase tracking-wider">
            Target
          </div>
        </div>

        {/* Virtual List or Centered Empty State */}
        {logs.length === 0 ? (
          <div className="flex-1 flex items-center justify-center p-8 text-center">
            <p className="text-text-tertiary dark:text-text-muted">No audit logs found.</p>
          </div>
        ) : (
          <FixedSizeList
            height={height - HEADER_HEIGHT}
            itemCount={logs.length}
            itemSize={rowHeight}
            width="100%"
            className="custom-scrollbar"
            style={{ overflowX: "hidden" }}
          >
            {Row}
          </FixedSizeList>
        )}
      </div>
    </div>
  );
}

export default VirtualAuditTable;
