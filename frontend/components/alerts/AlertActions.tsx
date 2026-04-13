"use client";

/**
 * AlertActions Component
 * 告警响应动作按钮
 */

import React, { useState } from "react";
import { CheckCircle, XCircle, AlertTriangle, UserPlus, RotateCcw, Play, Ban } from "lucide-react";
import { useTranslations } from "next-intl";
import { AlertStatus } from "@/components/AlertStatusBadge";

interface AlertActionsProps {
  alertId: string;
  currentStatus: AlertStatus;
  canResolve?: boolean;
  canAssign?: boolean;
  canEscalate?: boolean;
  onAction?: (action: string, data?: Record<string, unknown>) => void;
}

type Action =
  | "resolve"
  | "false_positive"
  | "assign"
  | "escalate"
  | "reopen"
  | "isolate_host"
  | "block_ip";

const ACTION_ICONS = {
  resolve: CheckCircle,
  false_positive: XCircle,
  assign: UserPlus,
  escalate: AlertTriangle,
  reopen: RotateCcw,
  isolate_host: Ban,
  block_ip: Ban,
};

const ACTION_COLORS = {
  resolve:
    "bg-green-100 text-green-800 hover:bg-green-200 dark:bg-green-900/30 dark:hover:bg-green-900/50 dark:text-green-300",
  false_positive:
    "bg-gray-100 text-gray-800 hover:bg-gray-200 dark:bg-gray-900/30 dark:hover:bg-gray-900/50 dark:text-gray-300",
  assign:
    "bg-blue-100 text-blue-800 hover:bg-blue-200 dark:bg-blue-900/30 dark:hover:bg-blue-900/50 dark:text-blue-300",
  escalate:
    "bg-orange-100 text-orange-800 hover:bg-orange-200 dark:bg-orange-900/30 dark:hover:bg-orange-900/50 dark:text-orange-300",
  reopen:
    "bg-yellow-100 text-yellow-800 hover:bg-yellow-200 dark:bg-yellow-900/30 dark:hover:bg-yellow-900/50 dark:text-yellow-300",
  isolate_host:
    "bg-red-100 text-red-800 hover:bg-red-200 dark:bg-red-900/30 dark:hover:bg-red-900/50 dark:text-red-300",
  block_ip:
    "bg-red-100 text-red-800 hover:bg-red-200 dark:bg-red-900/30 dark:hover:bg-red-900/50 dark:text-red-300",
};

export const AlertActions = React.memo(function AlertActions({
  alertId,
  currentStatus,
  canResolve = true,
  canAssign = true,
  canEscalate = true,
  onAction,
}: AlertActionsProps) {
  const t = useTranslations("alertActions");
  const [selectedAction, setSelectedAction] = useState<Action | null>(null);
  const [showDialog, setShowDialog] = useState(false);
  const [loading, setLoading] = useState(false);

  const getActionLabel = (action: Action) => {
    switch (action) {
      case "resolve":
        return t("actions.resolve.label");
      case "false_positive":
        return t("actions.falsePositive.label");
      case "assign":
        return t("actions.assign.label");
      case "escalate":
        return t("actions.escalate.label");
      case "reopen":
        return t("actions.reopen.label");
      case "isolate_host":
        return t("actions.isolateHost.label");
      case "block_ip":
        return t("actions.blockIp.label");
      default:
        return action;
    }
  };

  const getActionDescription = (action: Action) => {
    switch (action) {
      case "resolve":
        return t("actions.resolve.description");
      case "false_positive":
        return t("actions.falsePositive.description");
      case "assign":
        return t("actions.assign.description");
      case "escalate":
        return t("actions.escalate.description");
      case "reopen":
        return t("actions.reopen.description");
      case "isolate_host":
        return t("actions.isolateHost.description");
      case "block_ip":
        return t("actions.blockIp.description");
      default:
        return "";
    }
  };

  const handleActionClick = (action: Action) => {
    setSelectedAction(action);
    setShowDialog(true);
  };

  const handleConfirm = async (data?: Record<string, unknown>) => {
    if (!selectedAction) return;

    setLoading(true);
    try {
      await onAction?.(selectedAction, data);
      setShowDialog(false);
      setSelectedAction(null);
    } catch (error) {
      console.error("Action failed:", error);
    } finally {
      setLoading(false);
    }
  };

  const isResolved = currentStatus === "resolved" || currentStatus === "false_positive";

  const availableActions: Action[] = [];

  if (isResolved) {
    availableActions.push("reopen");
  } else {
    if (canResolve) {
      availableActions.push("resolve", "false_positive");
    }
    if (canAssign) {
      availableActions.push("assign");
    }
    if (canEscalate) {
      availableActions.push("escalate");
    }
    // 自动化响应动作
    availableActions.push("isolate_host", "block_ip");
  }

  return (
    <>
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-semibold text-gray-900 dark:text-white">{t("title")}</h4>
          {selectedAction && (
            <span className="text-xs text-gray-500 dark:text-gray-400">
              {t("readyTo")}: {getActionLabel(selectedAction)}
            </span>
          )}
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {availableActions.map((action) => {
            const Icon = ACTION_ICONS[action];

            return (
              <button
                key={action}
                onClick={() => handleActionClick(action)}
                disabled={loading}
                className={`
                  flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium
                  transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed
                  ${ACTION_COLORS[action]}
                `}
                title={getActionDescription(action)}
              >
                <Icon className="w-4 h-4 flex-shrink-0" />
                <span className="truncate">{getActionLabel(action)}</span>
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
                {t("quickActions")}
              </div>
              <div className="mt-2 flex flex-wrap gap-2">
                <button
                  onClick={() => handleActionClick("resolve")}
                  className="px-3 py-1.5 bg-white dark:bg-gray-800 text-blue-700 dark:text-blue-300 text-xs font-medium rounded hover:bg-blue-50 dark:hover:bg-gray-700 transition-colors"
                >
                  {t("autoResolve")}
                </button>
                <button
                  onClick={() => handleActionClick("assign")}
                  className="px-3 py-1.5 bg-white dark:bg-gray-800 text-blue-700 dark:text-blue-300 text-xs font-medium rounded hover:bg-blue-50 dark:hover:bg-gray-700 transition-colors"
                >
                  {t("assignToMe")}
                </button>
                <button
                  onClick={() => handleActionClick("escalate")}
                  className="px-3 py-1.5 bg-white dark:bg-gray-800 text-blue-700 dark:text-blue-300 text-xs font-medium rounded hover:bg-blue-50 dark:hover:bg-gray-700 transition-colors"
                >
                  {t("actions.escalate.label")}
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
          onConfirm={handleConfirm}
          onCancel={() => {
            setShowDialog(false);
            setSelectedAction(null);
          }}
          loading={loading}
          getActionLabel={getActionLabel}
        />
      )}
    </>
  );
});

interface ActionDialogProps {
  action: Action;
  alertId: string;
  onConfirm: (data?: Record<string, unknown>) => void;
  onCancel: () => void;
  loading: boolean;
  getActionLabel: (action: Action) => string;
}

function ActionDialog({ action, onConfirm, onCancel, loading, getActionLabel }: ActionDialogProps) {
  const t = useTranslations("alertActions");
  const tCommon = useTranslations("common");
  const [note, setNote] = useState("");
  const [assignee, setAssignee] = useState("");

  const needsAssignee = action === "assign" || action === "escalate";
  const needsNote = action === "false_positive" || action === "escalate";

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const data: Record<string, unknown> = {};
    if (needsAssignee && assignee) {
      data.assignee = assignee;
    }
    if (needsNote && note) {
      data.note = note;
    }
    onConfirm(data);
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          {getActionLabel(action)}
        </h3>

        <form onSubmit={handleSubmit}>
          {needsAssignee && (
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {action === "assign" ? t("dialog.assignTo") : t("dialog.escalateTo")}
              </label>
              <input
                type="text"
                value={assignee}
                onChange={(e) => setAssignee(e.target.value)}
                placeholder={t("dialog.placeholder.username")}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
            </div>
          )}

          {(needsNote || action === "resolve" || action === "reopen") && (
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {needsNote ? t("dialog.noteRequired") : t("dialog.noteOptional")}
              </label>
              <textarea
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder={t("dialog.placeholder.note")}
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
            </div>
          )}

          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={onCancel}
              disabled={loading}
              className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
            >
              {t("dialog.cancel")}
            </button>
            <button
              type="submit"
              disabled={loading || (needsNote && !note) || (needsAssignee && !assignee)}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors disabled:opacity-50"
            >
              {loading ? t("dialog.processing") : tCommon("confirm")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
