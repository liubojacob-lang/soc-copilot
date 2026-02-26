'use client';

import { ReactNode } from "react";
import { FileText, AlertTriangle, Search, Inbox } from "lucide-react";

interface EmptyStateProps {
  icon?: 'file' | 'alert' | 'search' | 'inbox' | 'custom';
  title: string;
  description?: string;
  action?: ReactNode;
  customIcon?: ReactNode;
}

const ICONS = {
  file: FileText,
  alert: AlertTriangle,
  search: Search,
  inbox: Inbox,
};

export function EmptyState({ icon = 'inbox', title, description, action, customIcon }: EmptyStateProps) {
  const IconComponent = !customIcon ? ICONS[icon] : null;

  return (
    <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
      {customIcon ? (
        <div className="mb-4">{customIcon}</div>
      ) : (
        <div className="w-16 h-16 mb-4 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
          <IconComponent className="w-8 h-8 text-gray-400" />
        </div>
      )}
      <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-1">
        {title}
      </h3>
      {description && (
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-4 max-w-sm">
          {description}
        </p>
      )}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
