/** Dify workflow list component */

import { Download, Trash2, Clock, Zap } from 'lucide-react';
import type { DifyWorkflow } from '../types';

interface DifyWorkflowListProps {
  workflows: DifyWorkflow[];
  importing: string | null;
  deleting: string | null;
  onImport: (workflow: DifyWorkflow) => void;
  onDelete: (workflow: DifyWorkflow) => void;
  t: any;
}

export function DifyWorkflowList({
  workflows,
  importing,
  deleting,
  onImport,
  onDelete,
  t
}: DifyWorkflowListProps) {
  if (workflows.length === 0) return null;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
          {t('availableWorkflows', { count: workflows.length })}
        </h2>
      </div>
      <div className="divide-y divide-gray-200 dark:divide-gray-700">
        {workflows.map((workflow) => (
          <div
            key={workflow.id}
            className="px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
          >
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
                    <Zap className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900 dark:text-white">
                      {workflow.name}
                    </h3>
                    {workflow.description && (
                      <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                        {workflow.description}
                      </p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-4 mt-2 text-sm text-gray-500 dark:text-gray-400">
                  <span className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded">
                    {workflow.mode}
                  </span>
                  <span>•</span>
                  <span>ID: {workflow.id}</span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => onImport(workflow)}
                  disabled={importing === workflow.id || deleting === workflow.id}
                  className="flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 text-sm"
                >
                  {importing === workflow.id ? (
                    <>
                      <Clock className="w-4 h-4 animate-spin" />
                      {t('importing')}
                    </>
                  ) : (
                    <>
                      <Download className="w-4 h-4" />
                      {t('import')}
                    </>
                  )}
                </button>
                <button
                  onClick={() => onDelete(workflow)}
                  disabled={deleting === workflow.id}
                  className="flex items-center gap-2 px-3 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 text-sm"
                >
                  {deleting === workflow.id ? (
                    <>
                      <Clock className="w-4 h-4 animate-spin" />
                      {t('deleting')}
                    </>
                  ) : (
                    <>
                      <Trash2 className="w-4 h-4" />
                      {t('delete')}
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
