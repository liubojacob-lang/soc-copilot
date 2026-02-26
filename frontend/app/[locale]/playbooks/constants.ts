/** Playbooks page types and constants */

export interface PlaybookRun {
  id: string;
  playbook_name: string;
  status: string;
  mode: string;
  started_at: string;
  finished_at: string | null;
}

export interface PlaybookMetadata {
  name: string;
  description: string;
  version: string;
  estimated_duration_seconds: number;
  steps: any[];
}

export interface QueueStats {
  running: number;
  queued: number;
  max_concurrent: number;
}

export const STATUS_COLORS: Record<string, string> = {
  pending: "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300",
  running: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300",
  success: "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300",
  failed: "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300",
  partial: "bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300",
  skipped: "bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400",
  queued: "bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300",
};

export const MODE_COLORS: Record<string, string> = {
  dry_run: "bg-purple-50 text-purple-700 dark:bg-purple-900/50 dark:text-purple-300",
  apply: "bg-red-50 text-red-700 dark:bg-red-900/50 dark:text-red-300",
};
