"use client";

import React from "react";
import { Edit2, Trash2, Check } from "lucide-react";
import type { ChatConversation } from "@/hooks/useChatHistory";

interface ConversationItemProps {
  conv: ChatConversation;
  isActive: boolean;
  isEditing: boolean;
  editTitle: string;
  inputRef: React.RefObject<HTMLInputElement | null>;
  onSelect: (conv: ChatConversation) => void;
  onStartEdit: () => void;
  onEditTitleChange: (title: string) => void;
  onEditKeyDown: (e: React.KeyboardEvent) => void;
  onSaveEdit: () => void;
  onCancelEdit: () => void;
  onDelete: () => void;
  formatTimeAgo: (dateStr: string) => string;
  getInitial: (title: string) => string;
  getColor: (id: string) => string;
  t: (key: string) => string;
}

export const ConversationItem = React.memo(function ConversationItem({
  conv,
  isActive,
  isEditing,
  editTitle,
  inputRef,
  onSelect,
  onStartEdit,
  onEditTitleChange,
  onEditKeyDown,
  onSaveEdit,
  onCancelEdit,
  onDelete,
  formatTimeAgo,
  getInitial,
  getColor,
  t,
}: ConversationItemProps) {
  return (
    <div className="px-2">
      {isEditing ? (
        <div
          className="p-2 bg-blue-50 dark:bg-blue-900/20 rounded-xl
                        border border-blue-200 dark:border-blue-800"
        >
          <input
            ref={inputRef}
            type="text"
            value={editTitle}
            onChange={(e) => onEditTitleChange(e.target.value)}
            onKeyDown={onEditKeyDown}
            placeholder={t("renamePlaceholder")}
            aria-label={t("renamePlaceholder")}
            className="w-full px-3 py-2 text-sm
                       border border-gray-300 dark:border-gray-600
                       rounded-lg bg-white dark:bg-gray-800
                       text-gray-900 dark:text-white
                       focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <div className="flex gap-2 mt-2">
            <button
              onClick={onSaveEdit}
              aria-label={t("saveRename")}
              className="flex-1 flex items-center justify-center gap-1 px-3 py-1.5
                         text-xs font-medium text-white bg-blue-600 hover:bg-blue-700
                         rounded-lg transition-colors"
            >
              <Check className="w-3.5 h-3.5" />
              {t("saveRename")}
            </button>
            <button
              onClick={onCancelEdit}
              aria-label={t("cancelRename")}
              className="flex-1 px-3 py-1.5 text-xs font-medium
                         text-gray-600 dark:text-gray-400
                         bg-gray-100 dark:bg-gray-700
                         hover:bg-gray-200 dark:hover:bg-gray-600
                         rounded-lg transition-colors"
            >
              {t("cancelRename")}
            </button>
          </div>
        </div>
      ) : (
        <div
          className={`
            group relative flex items-start gap-3 px-3 py-2.5 rounded-xl cursor-pointer transition-all
            ${
              isActive
                ? "bg-blue-100 dark:bg-blue-900/40 ring-1 ring-blue-200 dark:ring-blue-800"
                : "hover:bg-gray-100 dark:hover:bg-gray-800/70"
            }
          `}
          onClick={() => onSelect(conv)}
          onDoubleClick={(e) => {
            e.stopPropagation();
            onStartEdit();
          }}
        >
          {isActive && (
            <div
              className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8
                            bg-blue-600 dark:bg-blue-400 rounded-r-full"
            />
          )}

          <div
            className={`
            flex-shrink-0 w-9 h-9 rounded-lg flex items-center justify-center text-sm font-medium
            ${
              isActive
                ? "bg-blue-200 dark:bg-blue-800 text-blue-700 dark:text-blue-300"
                : getColor(conv.id)
            }
          `}
          >
            {getInitial(conv.title)}
          </div>

          <div className="flex-1 min-w-0 py-0.5">
            <p
              className={`text-sm font-medium truncate
                           ${isActive ? "text-blue-900 dark:text-blue-100" : "text-gray-800 dark:text-gray-200"}`}
            >
              {conv.title}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 flex items-center gap-1.5">
              <span>{formatTimeAgo(conv.updatedAt)}</span>
              <span className="w-1 h-1 rounded-full bg-gray-300 dark:bg-gray-600" />
              <span>
                {conv.messages.length}
                {t("messages")}
              </span>
            </p>
          </div>

          <div
            className={`
            flex items-center gap-0.5 flex-shrink-0
            opacity-0 group-hover:opacity-100 transition-opacity
            ${isActive ? "opacity-100" : ""}
          `}
          >
            <button
              onClick={(e) => {
                e.stopPropagation();
                onStartEdit();
              }}
              aria-label={t("rename")}
              className="p-1.5 text-gray-400 hover:text-blue-600 dark:hover:text-blue-400
                         hover:bg-blue-100 dark:hover:bg-blue-900/30 rounded-lg transition-colors"
              title={t("rename")}
            >
              <Edit2 className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete();
              }}
              aria-label={t("delete")}
              className="p-1.5 text-gray-400 hover:text-red-600 dark:hover:text-red-400
                         hover:bg-red-100 dark:hover:bg-red-900/30 rounded-lg transition-colors"
              title={t("delete")}
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
});
