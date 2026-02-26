'use client';

/**
 * AlertActions Component
 * 告警响应动作按钮
 */

import React, { useState } from 'react';
import { CheckCircle, XCircle, AlertTriangle, UserPlus, RotateCcw, Play, Ban } from 'lucide-react';
import { AlertStatus } from '@/components/AlertStatusBadge';

interface AlertActionsProps {
  alertId: string;
  currentStatus: AlertStatus;
  canResolve?: boolean;
  canAssign?: boolean;
  canEscalate?: boolean;
  onAction?: (action: string, data?: any) => void;
}

type Action = 'resolve' | 'false_positive' | 'assign' | 'escalate' | 'reopen' | 'isolate_host' | 'block_ip';

const ACTION_CONFIG = {
  resolve: {
    label: 'Resolve',
    icon: CheckCircle,
    color: 'bg-green-100 text-green-800 hover:bg-green-200 dark:bg-green-900/30 dark:hover:bg-green-900/50 dark:text-green-300',
    description: 'Mark this alert as resolved',
  },
  false_positive: {
    label: 'False Positive',
    icon: XCircle,
    color: 'bg-gray-100 text-gray-800 hover:bg-gray-200 dark:bg-gray-900/30 dark:hover:bg-gray-900/50 dark:text-gray-300',
    description: 'Mark this alert as a false positive',
  },
  assign: {
    label: 'Assign',
    icon: UserPlus,
    color: 'bg-blue-100 text-blue-800 hover:bg-blue-200 dark:bg-blue-900/30 dark:hover:bg-blue-900/50 dark:text-blue-300',
    description: 'Assign this alert to a user',
  },
  escalate: {
    label: 'Escalate',
    icon: AlertTriangle,
    color: 'bg-orange-100 text-orange-800 hover:bg-orange-200 dark:bg-orange-900/30 dark:hover:bg-orange-900/50 dark:text-orange-300',
    description: 'Escalate to higher level',
  },
  reopen: {
    label: 'Reopen',
    icon: RotateCcw,
    color: 'bg-yellow-100 text-yellow-800 hover:bg-yellow-200 dark:bg-yellow-900/30 dark:hover:bg-yellow-900/50 dark:text-yellow-300',
    description: 'Reopen this alert',
  },
  isolate_host: {
    label: 'Isolate Host',
    icon: Ban,
    color: 'bg-red-100 text-red-800 hover:bg-red-200 dark:bg-red-900/30 dark:hover:bg-red-900/50 dark:text-red-300',
    description: 'Isolate the affected host from network',
  },
  block_ip: {
    label: 'Block IP',
    icon: Ban,
    color: 'bg-red-100 text-red-800 hover:bg-red-200 dark:bg-red-900/30 dark:hover:bg-red-900/50 dark:text-red-300',
    description: 'Block the IP address on firewall',
  },
};

export function AlertActions({
  alertId,
  currentStatus,
  canResolve = true,
  canAssign = true,
  canEscalate = true,
  onAction,
}: AlertActionsProps) {
  const [selectedAction, setSelectedAction] = useState<Action | null>(null);
  const [showDialog, setShowDialog] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleActionClick = (action: Action) => {
    setSelectedAction(action);
    setShowDialog(true);
  };

  const handleConfirm = async (data?: any) => {
    if (!selectedAction) return;

    setLoading(true);
    try {
      await onAction?.(selectedAction, data);
      setShowDialog(false);
      setSelectedAction(null);
    } catch (error) {
      console.error('Action failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const isResolved = currentStatus === 'resolved' || currentStatus === 'false_positive';

  const availableActions: Action[] = [];

  if (isResolved) {
    availableActions.push('reopen');
  } else {
    if (canResolve) {
      availableActions.push('resolve', 'false_positive');
    }
    if (canAssign) {
      availableActions.push('assign');
    }
    if (canEscalate) {
      availableActions.push('escalate');
    }
    // 自动化响应动作
    availableActions.push('isolate_host', 'block_ip');
  }

  return (
    <>
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
            Response Actions
          </h4>
          {selectedAction && (
            <span className="text-xs text-gray-500 dark:text-gray-400">
              Ready to: {ACTION_CONFIG[selectedAction].label}
            </span>
          )}
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {availableActions.map((action) => {
            const config = ACTION_CONFIG[action];
            const Icon = config.icon;

            return (
              <button
                key={action}
                onClick={() => handleActionClick(action)}
                disabled={loading}
                className={`
                  flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium
                  transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed
                  ${config.color}
                `}
                title={config.description}
              >
                <Icon className="w-4 h-4 flex-shrink-0" />
                <span className="truncate">{config.label}</span>
              </button>
            );
          })}
        </div>

        {/* Quick Actions */}
        <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
          <div className="flex items-start gap-2">
            <Play className="w-4 h-4 text-blue-600 dark:text-blue-400 mt-0.5" />
            <div className="flex-1">
              <div className="text-sm font-medium text-blue-900 dark:text-blue-300">
                Quick Actions
              </div>
              <div className="mt-2 flex flex-wrap gap-2">
                <button
                  onClick={() => handleActionClick('resolve')}
                  className="px-3 py-1.5 bg-white dark:bg-gray-800 text-blue-700 dark:text-blue-300 text-xs font-medium rounded hover:bg-blue-50 dark:hover:bg-gray-700 transition-colors"
                >
                  Auto-Resolve
                </button>
                <button
                  onClick={() => handleActionClick('assign')}
                  className="px-3 py-1.5 bg-white dark:bg-gray-800 text-blue-700 dark:text-blue-300 text-xs font-medium rounded hover:bg-blue-50 dark:hover:bg-gray-700 transition-colors"
                >
                  Assign to Me
                </button>
                <button
                  onClick={() => handleActionClick('escalate')}
                  className="px-3 py-1.5 bg-white dark:bg-gray-800 text-blue-700 dark:text-blue-300 text-xs font-medium rounded hover:bg-blue-50 dark:hover:bg-gray-700 transition-colors"
                >
                  Escalate
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Action Dialog */}
      {showDialog && selectedAction && (
        <ActionDialog
          action={selectedAction}
          alertId={alertId}
          config={ACTION_CONFIG[selectedAction]}
          onConfirm={handleConfirm}
          onCancel={() => {
            setShowDialog(false);
            setSelectedAction(null);
          }}
          loading={loading}
        />
      )}
    </>
  );
}

// Action Dialog Component
interface ActionDialogProps {
  action: Action;
  alertId: string;
  config: typeof ACTION_CONFIG[keyof typeof ACTION_CONFIG];
  onConfirm: (data?: any) => void;
  onCancel: () => void;
  loading: boolean;
}

function ActionDialog({ action, alertId, config, onConfirm, onCancel, loading }: ActionDialogProps) {
  const [note, setNote] = useState('');
  const [assignTo, setAssignTo] = useState('');

  const handleConfirm = () => {
    const data: any = {};

    if (action === 'resolve' || action === 'false_positive') {
      data.resolution_note = note;
      data.resolution_type = action === 'false_positive' ? 'false_positive' : 'resolved';
    }

    if (action === 'assign') {
      data.assigned_to = assignTo;
      data.note = note;
    }

    if (action === 'escalate') {
      data.escalated_to = assignTo;
      data.reason = note;
    }

    onConfirm(data);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2">
            <config.icon className="w-5 h-5 text-gray-600 dark:text-gray-400" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              {config.label}
            </h3>
          </div>
          <button
            onClick={onCancel}
            disabled={loading}
            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
          >
            <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="px-4 py-4">
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            {config.description}
          </p>

          {(action === 'assign' || action === 'escalate') && (
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {action === 'assign' ? 'Assign to' : 'Escalate to'}
              </label>
              <input
                type="text"
                value={assignTo}
                onChange={(e) => setAssignTo(e.target.value)}
                placeholder="Enter username or role"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
              />
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Note {action === 'resolve' || action === 'false_positive' ? '(required)' : '(optional)'}
            </label>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Add a note..."
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
            />
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 px-4 py-3 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={onCancel}
            disabled={loading}
            className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={loading || (action === 'resolve' && !note.trim())}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Processing...' : config.label}
          </button>
        </div>
      </div>
    </div>
  );
}
