"use client";

import { useState, useRef, useEffect, useMemo } from "react";
import { useTranslations } from "next-intl";
import {
  Plus,
  Search,
  MessageSquare,
  PanelLeftClose,
  Edit2,
  Trash2,
  Check,
  X,
  AlertTriangle,
  History,
} from "lucide-react";
import type { ChatConversation } from "@/hooks/useChatHistory";

interface ChatHistoryPanelProps {
  isOpen: boolean;
  onToggle: () => void;
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

interface GroupedConversations {
  label: string;
  conversations: ChatConversation[];
}

export function ChatHistoryPanel({
  isOpen,
  onToggle,
  conversations,
  currentId,
  searchQuery,
  onSearchChange,
  onSelect,
  onDelete,
  onRename,
  onNewChat,
  formatTimeAgo,
}: ChatHistoryPanelProps) {
  const t = useTranslations("aiAssistant.history");

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (editingId && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editingId]);

  // Group conversations into today, yesterday, past 7 days, older
  const groupedConversations = useMemo<GroupedConversations[]>(() => {
    if (!mounted) return [];

    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today.getTime() - 86400000);
    const weekAgo = new Date(today.getTime() - 7 * 86400000);

    const groups: Record<string, ChatConversation[]> = {
      [t("today")]: [],
      [t("yesterday")]: [],
      [t("past7Days")]: [],
      [t("older")]: [],
    };

    conversations.forEach((conv) => {
      const date = new Date(conv.updatedAt);
      if (date >= today) {
        groups[t("today")].push(conv);
      } else if (date >= yesterday) {
        groups[t("yesterday")].push(conv);
      } else if (date >= weekAgo) {
        groups[t("past7Days")].push(conv);
      } else {
        groups[t("older")].push(conv);
      }
    });

    return [
      { label: t("today"), conversations: groups[t("today")] },
      { label: t("yesterday"), conversations: groups[t("yesterday")] },
      { label: t("past7Days"), conversations: groups[t("past7Days")] },
      { label: t("older"), conversations: groups[t("older")] },
    ].filter((group) => group.conversations.length > 0);
  }, [conversations, t, mounted]);

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

  const content = (
    <div className="flex flex-col h-full min-h-0 select-none">
      {/* Sidebar Header */}
      <div className="h-14 px-3.5 border-b border-gray-200/80 dark:border-gray-800/80 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-2">
          <div className="p-1 rounded-lg bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400">
            <History className="w-3.5 h-3.5" />
          </div>
          <span className="text-xs font-semibold text-gray-800 dark:text-gray-200">
            {t("title")}
          </span>
          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 font-medium">
            {conversations.length}
          </span>
        </div>

        {/* Collapse button */}
        <button
          onClick={onToggle}
          className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
          title="收起侧栏 (⌘+/)"
        >
          <PanelLeftClose className="w-4 h-4" />
        </button>
      </div>

      {/* New Chat & Search Controls */}
      <div className="p-2.5 space-y-2 border-b border-gray-100 dark:border-gray-800/60 flex-shrink-0">
        <button
          onClick={onNewChat}
          className="w-full flex items-center justify-between px-3 py-2 text-xs font-medium text-blue-700 dark:text-blue-300 bg-blue-50/80 hover:bg-blue-100/90 dark:bg-blue-950/50 dark:hover:bg-blue-900/60 border border-blue-200/60 dark:border-blue-800/50 rounded-xl transition-all shadow-xs active:scale-[0.98]"
        >
          <div className="flex items-center gap-1.5">
            <Plus className="w-3.5 h-3.5" />
            <span>新建研判</span>
          </div>
          <kbd className="text-[10px] px-1.5 py-0.2 bg-blue-100 dark:bg-blue-900/60 rounded text-blue-600 dark:text-blue-400 font-mono">
            ⌘N
          </kbd>
        </button>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="搜索研判历史..."
            className="w-full pl-8 pr-7 py-1.5 text-xs bg-white dark:bg-gray-800/70 border border-gray-200/80 dark:border-gray-700/80 rounded-lg text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-500 transition-all"
          />
          {searchQuery && (
            <button
              onClick={() => onSearchChange("")}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 p-0.5"
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>

      {/* Conversation List */}
      <div className="flex-1 min-h-0 overflow-y-auto px-2 py-2 space-y-3">
        {conversations.length === 0 ? (
          <div className="py-12 text-center">
            <div className="w-10 h-10 mx-auto rounded-xl bg-gray-100 dark:bg-gray-800 flex items-center justify-center mb-2.5 text-gray-400">
              <MessageSquare className="w-5 h-5" />
            </div>
            <p className="text-xs font-medium text-gray-600 dark:text-gray-400">
              {searchQuery ? "未搜索到匹配记录" : t("emptyTitle")}
            </p>
            <p className="text-[11px] text-gray-400 dark:text-gray-500 mt-1">
              {searchQuery ? "请尝试其他关键词" : t("emptyHint")}
            </p>
          </div>
        ) : (
          groupedConversations.map(({ label, conversations: groupConvs }) => (
            <div key={label} className="space-y-0.5">
              <div className="px-2 py-1 text-[10px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider flex items-center justify-between">
                <span>{label}</span>
                <span className="text-gray-300 dark:text-gray-600 font-normal">
                  {groupConvs.length}
                </span>
              </div>

              {groupConvs.map((conv) => {
                const isActive = conv.id === currentId;
                const isEditing = conv.id === editingId;

                if (isEditing) {
                  return (
                    <div
                      key={conv.id}
                      className="p-1.5 bg-blue-50 dark:bg-blue-950/40 rounded-xl border border-blue-200 dark:border-blue-800"
                    >
                      <input
                        ref={inputRef}
                        type="text"
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        onKeyDown={handleEditKeyDown}
                        placeholder={t("renamePlaceholder")}
                        className="w-full px-2 py-1 text-xs border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                      />
                      <div className="flex gap-1.5 mt-1.5">
                        <button
                          onClick={saveRename}
                          className="flex-1 flex items-center justify-center gap-1 py-1 text-[10px] font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors"
                        >
                          <Check className="w-3 h-3" />
                          <span>{t("saveRename")}</span>
                        </button>
                        <button
                          onClick={cancelRename}
                          className="flex-1 py-1 text-[10px] font-medium text-gray-600 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-md transition-colors"
                        >
                          {t("cancelRename")}
                        </button>
                      </div>
                    </div>
                  );
                }

                return (
                  <div
                    key={conv.id}
                    onClick={() => onSelect(conv)}
                    onDoubleClick={() => startEditing(conv)}
                    className={`group relative flex items-center justify-between px-2.5 py-2 rounded-xl text-xs cursor-pointer transition-all ${
                      isActive
                        ? "bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 font-medium border border-blue-200/60 dark:border-blue-800/60 shadow-xs"
                        : "hover:bg-gray-100/90 dark:hover:bg-gray-800/70 text-gray-700 dark:text-gray-300 border border-transparent"
                    }`}
                  >
                    <div className="flex items-center gap-2 min-w-0 pr-1">
                      {isActive ? (
                        <span className="w-1.5 h-1.5 rounded-full bg-blue-600 dark:bg-blue-400 flex-shrink-0 animate-pulse" />
                      ) : (
                        <MessageSquare className="w-3.5 h-3.5 text-gray-400 dark:text-gray-500 flex-shrink-0" />
                      )}
                      <span className="truncate" title={conv.title}>
                        {conv.title}
                      </span>
                    </div>

                    {/* Action buttons on hover/active */}
                    <div
                      className={`flex items-center gap-0.5 flex-shrink-0 transition-opacity ${
                        isActive ? "opacity-100" : "opacity-0 group-hover:opacity-100"
                      }`}
                    >
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          startEditing(conv);
                        }}
                        className="p-1 text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-blue-100/60 dark:hover:bg-blue-900/40 rounded transition-colors"
                        title={t("rename")}
                      >
                        <Edit2 className="w-3 h-3" />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setDeleteConfirmId(conv.id);
                        }}
                        className="p-1 text-gray-400 hover:text-rose-600 dark:hover:text-rose-400 hover:bg-rose-100/60 dark:hover:bg-rose-900/40 rounded transition-colors"
                        title={t("delete")}
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          ))
        )}
      </div>

      {/* Footer */}
      <div className="px-3 py-2 border-t border-gray-200/70 dark:border-gray-800/70 text-[10px] text-gray-400 dark:text-gray-500 flex items-center justify-between flex-shrink-0 bg-gray-50/50 dark:bg-gray-900/30">
        <span>⌘+N 新对话</span>
        <span>⌘+/ 折叠</span>
      </div>

      {/* Delete Confirmation Modal (Constrained to Card) */}
      {deleteConfirmId && (
        <div className="absolute inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl border border-gray-200 dark:border-gray-700 max-w-[240px] w-full p-4 animate-in zoom-in-95 duration-150">
            <div className="flex items-center gap-2.5 text-rose-600 dark:text-rose-400 mb-2">
              <AlertTriangle className="w-4 h-4 flex-shrink-0" />
              <h4 className="text-xs font-semibold text-gray-900 dark:text-white">
                {t("deleteConfirm")}
              </h4>
            </div>
            <p className="text-[11px] text-gray-500 dark:text-gray-400 mb-3">
              {t("deleteWarning")}
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setDeleteConfirmId(null)}
                className="flex-1 py-1.5 text-xs text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
              >
                {t("cancelRename")}
              </button>
              <button
                onClick={confirmDelete}
                className="flex-1 py-1.5 text-xs text-white bg-rose-600 hover:bg-rose-700 rounded-lg transition-colors font-medium shadow-xs"
              >
                {t("delete")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );

  return (
    <>
      {/* Desktop Column: Smooth inline width transition inside card */}
      <aside
        className={`hidden md:flex flex-col h-full bg-gray-50/70 dark:bg-gray-900/40 border-r border-gray-200/80 dark:border-gray-800/80 flex-shrink-0 transition-[width,opacity] duration-300 ease-in-out relative ${
          isOpen
            ? "w-64 lg:w-72 opacity-100"
            : "w-0 border-r-0 opacity-0 pointer-events-none overflow-hidden"
        }`}
      >
        <div className="w-64 lg:w-72 h-full min-h-0 flex flex-col">{content}</div>
      </aside>

      {/* Mobile Drawer: Slides over inside the card container */}
      {isOpen && (
        <div className="md:hidden">
          <div className="absolute inset-0 bg-black/30 backdrop-blur-xs z-30" onClick={onToggle} />
          <aside className="absolute inset-y-0 left-0 z-40 w-72 bg-white dark:bg-gray-850 shadow-2xl border-r border-gray-200 dark:border-gray-800 animate-in slide-in-from-left duration-200">
            {content}
          </aside>
        </div>
      )}
    </>
  );
}
