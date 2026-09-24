"use client";

import { useState, useEffect, useRef } from "react";
import { useTranslations } from "next-intl";
import {
  Plus,
  Search,
  MessageSquare,
  AlertTriangle,
  ChevronRight,
  ChevronLeft,
  MoreHorizontal,
} from "lucide-react";
import type { ChatConversation } from "@/hooks/useChatHistory";
import { ConversationItem } from "@/components/chat/ConversationItem";
import { getInitial, getColor, useGroupedConversations } from "@/components/chat/chatHelpers";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";

interface ChatHistorySidebarProps {
  isOpen: boolean;
  onClose: () => void;
  conversations: ChatConversation[];
  currentId: string | null;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  onSelect: (conv: ChatConversation) => void;
  onDelete: (id: string) => void;
  onRename: (id: string, newTitle: string) => void;
  onNewChat: () => void;
  formatTimeAgo: (dateStr: string) => string;
}

export function ChatHistorySidebar({
  isOpen,
  onClose,
  conversations,
  currentId,
  searchQuery,
  onSearchChange,
  onSelect,
  onDelete,
  onRename,
  onNewChat,
  formatTimeAgo,
}: ChatHistorySidebarProps) {
  const t = useTranslations("aiAssistant.history");

  const [isCollapsed, setIsCollapsed] = useState(true);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [mounted, setMounted] = useState(false);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [hoveredConvId, setHoveredConvId] = useState<string | null>(null);

  const inputRef = useRef<HTMLInputElement>(null);
  const sidebarRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (editingId && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editingId]);

  const groupedConversations = useGroupedConversations(conversations, t, mounted);

  const startEditing = (conv: ChatConversation) => {
    setEditingId(conv.id);
    setEditTitle(conv.title);
  };

  const saveRename = () => {
    if (editingId && editTitle.trim()) {
      onRename(editingId, editTitle.trim());
    }
    setEditingId(null);
    setEditTitle("");
  };

  const cancelRename = () => {
    setEditingId(null);
    setEditTitle("");
  };

  const handleEditKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      saveRename();
    } else if (e.key === "Escape") {
      e.preventDefault();
      cancelRename();
    }
  };

  const confirmDelete = () => {
    if (deleteConfirmId) {
      onDelete(deleteConfirmId);
      setDeleteConfirmId(null);
    }
  };

  const handleSelect = (conv: ChatConversation) => {
    onSelect(conv);
    setIsCollapsed(true);
  };

  if (!isOpen) return null;

  // Collapsed sidebar - icons only
  if (isCollapsed) {
    return (
      <>
        <div className="fixed inset-0 bg-black/20 z-40 lg:hidden" onClick={onClose} />

        <aside
          ref={sidebarRef}
          className="fixed left-0 top-0 h-screen w-[60px] bg-gray-50/95 dark:bg-gray-900/95
                     border-r border-gray-200/60 dark:border-gray-700/60 z-50
                     flex flex-col backdrop-blur-sm transition-all duration-300"
        >
          <div className="p-2 border-b border-gray-200/60 dark:border-gray-700/60">
            <button
              onClick={onNewChat}
              aria-label={t("newChat")}
              className="w-11 h-11 flex items-center justify-center rounded-xl
                         bg-gradient-to-br from-blue-500 to-indigo-600 text-white
                         hover:from-blue-600 hover:to-indigo-700 shadow-md hover:shadow-lg
                         transition-all duration-200 hover:scale-105"
              title={t("newChat")}
            >
              <Plus className="w-5 h-5" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto py-2 space-y-1">
            {conversations.slice(0, 10).map((conv) => (
              <div
                key={conv.id}
                className="relative px-2"
                onMouseEnter={() => setHoveredConvId(conv.id)}
                onMouseLeave={() => setHoveredConvId(null)}
              >
                <button
                  onClick={() => handleSelect(conv)}
                  aria-label={`${conv.title} - ${formatTimeAgo(conv.updatedAt)}, ${conv.messages.length} ${t("messages")}`}
                  className={`
                    w-11 h-11 rounded-xl flex items-center justify-center text-sm font-medium
                    transition-all duration-200
                    ${
                      conv.id === currentId
                        ? "bg-blue-100 dark:bg-blue-900/40 ring-2 ring-blue-400 dark:ring-blue-600 text-blue-700 dark:text-blue-300"
                        : `bg-white dark:bg-gray-800 hover:scale-105 shadow-sm hover:shadow ${getColor(conv.id)}`
                    }
                  `}
                  title={conv.title}
                >
                  {getInitial(conv.title)}
                </button>

                {conv.id === currentId && (
                  <div
                    className="absolute -right-0.5 top-1/2 -translate-y-1/2 w-1.5 h-6
                                  bg-blue-500 dark:bg-blue-400 rounded-l-full"
                  />
                )}

                {hoveredConvId === conv.id && (
                  <div className="absolute left-full ml-2 top-1/2 -translate-y-1/2 z-50">
                    <div
                      className="bg-gray-900 dark:bg-gray-800 text-white text-xs px-3 py-1.5
                                    rounded-lg whitespace-nowrap shadow-lg"
                    >
                      <div className="font-medium max-w-[200px] truncate">{conv.title}</div>
                      <div className="text-text-tertiary text-[10px] mt-0.5">
                        {formatTimeAgo(conv.updatedAt)} · {conv.messages.length} {t("messages")}
                      </div>
                    </div>
                    <div
                      className="absolute left-0 top-1/2 -translate-x-1 -translate-y-1/2
                                    w-2 h-2 bg-gray-900 dark:bg-gray-800 rotate-45"
                    />
                  </div>
                )}
              </div>
            ))}

            {conversations.length > 10 && (
              <div className="px-2 pt-1">
                <button
                  onClick={() => setIsCollapsed(false)}
                  aria-label={t("showMore")}
                  className="w-11 h-11 rounded-xl flex items-center justify-center
                             bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400
                             hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                  title={t("showMore")}
                >
                  <MoreHorizontal className="w-5 h-5" />
                </button>
              </div>
            )}
          </div>

          <div className="p-2 border-t border-gray-200/60 dark:border-gray-700/60">
            <button
              onClick={() => setIsCollapsed(false)}
              aria-label={t("expandHistory")}
              className="w-11 h-11 flex items-center justify-center rounded-xl
                         text-gray-500 dark:text-gray-400
                         hover:bg-gray-200 dark:hover:bg-gray-800 hover:text-gray-700 dark:hover:text-gray-200
                         transition-all duration-200"
              title={t("expandHistory")}
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>
        </aside>
      </>
    );
  }

  // Expanded sidebar - full view
  return (
    <>
      <div
        className="fixed inset-0 bg-black/30 backdrop-blur-sm z-40"
        onClick={() => setIsCollapsed(true)}
      />

      <aside
        ref={sidebarRef}
        className="fixed left-0 top-0 h-screen w-[300px] bg-white dark:bg-gray-900
                   border-r border-gray-200 dark:border-gray-700 z-50
                   flex flex-col shadow-2xl animate-in slide-in-from-left-2 duration-300"
      >
        {/* Header */}
        <header
          className="flex items-center justify-between px-4 py-3
                           border-b border-gray-200 dark:border-gray-700
                           bg-gradient-to-r from-gray-50 to-white dark:from-gray-800 dark:to-gray-900"
        >
          <div className="flex items-center gap-2">
            <div className="p-1.5 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
              <MessageSquare className="w-4 h-4 text-blue-600 dark:text-blue-400" />
            </div>
            <h2 className="font-semibold text-gray-900 dark:text-white">{t("title")}</h2>
            <span className="text-xs text-text-tertiary bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded-full">
              {conversations.length}
            </span>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setIsCollapsed(true)}
              aria-label={t("collapse")}
              className="p-1.5 text-text-tertiary hover:text-gray-600 dark:hover:text-gray-300
                         hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors"
              title={t("collapse")}
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              onClick={onClose}
              aria-label="Close sidebar"
              className="p-1.5 text-text-tertiary hover:text-gray-600 dark:hover:text-gray-300
                         hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors"
            >
              <span className="sr-only">Close</span>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
        </header>

        {/* New Chat */}
        <div className="p-3 border-b border-gray-100 dark:border-gray-800">
          <button
            onClick={onNewChat}
            aria-label={t("newChat")}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5
                       text-sm font-medium text-white
                       bg-gradient-to-r from-blue-600 to-indigo-600
                       hover:from-blue-700 hover:to-indigo-700
                       rounded-xl transition-all shadow-md hover:shadow-lg"
          >
            <Plus className="w-4 h-4" />
            {t("newChat")}
          </button>
        </div>

        {/* Search */}
        <div className="p-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-tertiary" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder={t("search")}
              aria-label={t("search")}
              className="w-full pl-10 pr-3 py-2.5 text-sm
                         border border-gray-200 dark:border-gray-700
                         rounded-xl bg-gray-50 dark:bg-gray-800
                         text-gray-900 dark:text-white
                         placeholder-gray-500 dark:placeholder-gray-400
                         focus:ring-2 focus:ring-blue-500 focus:border-transparent
                         transition-all"
            />
          </div>
        </div>

        {/* Conversation List */}
        <div className="flex-1 overflow-y-auto">
          {conversations.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 px-6">
              <div
                className="w-16 h-16 rounded-2xl bg-gradient-to-br from-gray-100 to-gray-200
                              dark:from-gray-800 dark:to-gray-700
                              flex items-center justify-center mb-4"
              >
                <MessageSquare className="w-8 h-8 text-text-tertiary dark:text-gray-500" />
              </div>
              <p className="text-gray-700 dark:text-gray-300 font-medium text-center mb-1">
                {t("emptyTitle")}
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400 text-center mb-5">
                {t("emptyHint")}
              </p>
              <button
                onClick={onNewChat}
                aria-label={t("newChat")}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium
                           text-blue-600 dark:text-blue-400
                           bg-blue-50 dark:bg-blue-900/30
                           hover:bg-blue-100 dark:hover:bg-blue-900/50
                           rounded-xl transition-colors"
              >
                <Plus className="w-4 h-4" />
                {t("newChat")}
              </button>
            </div>
          ) : (
            <div className="py-2">
              {groupedConversations.map(({ label, conversations: groupConvs }) => (
                <div key={label} className="mb-2">
                  <div
                    className="px-4 py-1.5 text-[11px] font-semibold text-text-tertiary dark:text-gray-500
                                  uppercase tracking-wider flex items-center gap-2"
                  >
                    {label}
                    <span className="text-gray-300 dark:text-gray-600 font-normal">
                      ({groupConvs.length})
                    </span>
                  </div>
                  {groupConvs.map((conv) => (
                    <ConversationItem
                      key={conv.id}
                      conv={conv}
                      isActive={conv.id === currentId}
                      isEditing={conv.id === editingId}
                      editTitle={editTitle}
                      inputRef={inputRef}
                      onSelect={handleSelect}
                      onStartEdit={() => startEditing(conv)}
                      onEditTitleChange={setEditTitle}
                      onEditKeyDown={handleEditKeyDown}
                      onSaveEdit={saveRename}
                      onCancelEdit={cancelRename}
                      onDelete={() => setDeleteConfirmId(conv.id)}
                      formatTimeAgo={formatTimeAgo}
                      getInitial={getInitial}
                      getColor={getColor}
                      t={t}
                    />
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div
          className="px-4 py-3 border-t border-gray-200 dark:border-gray-700
                        bg-gray-50/80 dark:bg-gray-800/50"
        >
          <div className="flex items-center justify-between text-[11px] text-text-tertiary dark:text-gray-500">
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 bg-gray-200 dark:bg-gray-700 rounded text-[10px] font-mono">
                ⌘N
              </kbd>
              <span>{t("shortcuts.new")}</span>
            </span>
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 bg-gray-200 dark:bg-gray-700 rounded text-[10px] font-mono">
                ESC
              </kbd>
              <span>{t("shortcuts.close")}</span>
            </span>
          </div>
        </div>
      </aside>

      {/* Delete Confirmation Modal */}
      <ConfirmDialog
        open={!!deleteConfirmId}
        title={t("deleteConfirm")}
        description={t("deleteWarning")}
        confirmText={t("delete")}
        cancelText={t("cancelRename")}
        variant="danger"
        onConfirm={confirmDelete}
        onCancel={() => setDeleteConfirmId(null)}
      />
    </>
  );
}
