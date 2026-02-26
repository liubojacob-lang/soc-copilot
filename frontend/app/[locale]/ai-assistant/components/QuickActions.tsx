/** Quick actions for common AI tasks */

import { AlertTriangle, Lightbulb, FileText, Brain } from 'lucide-react';
import type { QuickAction } from '../types';

interface QuickActionsProps {
  actions: QuickAction[];
  onActionClick: (query: string) => void;
  loading: boolean;
  thinking: boolean;
  isStreaming: boolean;
  t: any;
}

export function QuickActions({
  actions,
  onActionClick,
  loading,
  thinking,
  isStreaming,
  t
}: QuickActionsProps) {
  return (
    <div className="px-6 py-3 border-t border-gray-200/50 dark:border-gray-700/50 bg-gray-50/50 dark:bg-gray-800/50">
      <div className="flex items-center gap-2 overflow-x-auto pb-1">
        <span className="text-xs text-gray-500 dark:text-gray-400 flex-shrink-0">{t('actions.quickActions')}</span>
        {actions.map((action, index) => (
          <button
            key={index}
            onClick={() => onActionClick(action.query)}
            disabled={loading || thinking || isStreaming}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-full whitespace-nowrap transition-all hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed ${
              action.color === 'red' ? 'bg-red-100 text-red-700 hover:bg-red-200 dark:bg-red-900/30 dark:text-red-400' :
              action.color === 'amber' ? 'bg-amber-100 text-amber-700 hover:bg-amber-200 dark:bg-amber-900/30 dark:text-amber-400' :
              action.color === 'blue' ? 'bg-blue-100 text-blue-700 hover:bg-blue-200 dark:bg-blue-900/30 dark:text-blue-400' :
              'bg-purple-100 text-purple-700 hover:bg-purple-200 dark:bg-purple-900/30 dark:text-purple-400'
            }`}
          >
            <action.icon className="w-3.5 h-3.5" />
            {action.label}
          </button>
        ))}
      </div>
    </div>
  );
}
