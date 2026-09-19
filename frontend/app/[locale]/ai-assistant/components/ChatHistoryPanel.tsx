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
      <div className="h-13 px-3.5 border-b border-border-subtle flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-2">
          <div className="p-1 rounded-lg bg-ai/10 text-ai border border-ai/20">
            <History className="w-3.5 h-3.5" />
          </div>
          <span className="text-xs font-semibold text-text-primary">
            {t("title") || "研判记录"}
          </span>
          <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-surface-hover text-text-tertiary font-medium">
            {conversations.length}
          </span>
        </div>

        {/* Collapse button */}
        <button
          onClick={onToggle}
          className="p-1.5 text-text-tertiary hover:text-text-primary hover:bg-surface-hover rounded-lg transition-colors cursor-pointer"
          title={`${t("collapse") || "收起"} (⌘/)`}
          aria-label={t("collapse") || "收起"}
        >
          <PanelLeftClose className="w-4 h-4" />
        </button>
      </div>

      {/* New Chat & Search Controls */}
      <div className="p-2.5 space-y-2 border-b border-border-subtle flex-shrink-0 bg-surface-card">
        <button
          onClick={onNewChat}
          className="w-full flex items-center justify-between px-3 py-2 text-xs font-medium text-accent-700 dark:text-accent-300 bg-accent-50/80 hover:bg-accent-100/90 dark:bg-accent-950/50 dark:hover:bg-accent-900/60 border border-accent-200/60 dark:border-accent-800/50 rounded-xl transition-all shadow-subtle active:scale-[0.98] cursor-pointer"
        >
          <div className="flex items-center gap-1.5">
            <Plus className="w-3.5 h-3.5" />
            <span>新建研判会话</span>
          </div>
          <kbd className="text-[10px] px-1.5 py-0.2 bg-accent-100 dark:bg-accent-900/60 rounded text-accent-700 dark:text-accent-300 font-mono">
            ⌘N
          </kbd>
        </button>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-text-muted" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="搜索研判历史..."
            className="w-full pl-8 pr-7 py-1.5 text-xs bg-surface-ground border border-border-subtle rounded-lg text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-accent-500 transition-all"
          />
          {searchQuery && (
            <button
              onClick={() => onSearchChange("")}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary p-0.5"
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
            <div className="w-10 h-10 mx-auto rounded-xl bg-surface-hover flex items-center justify-center mb-2.5 text-text-muted">
              <MessageSquare className="w-5 h-5" />
            </div>
            <p className="text-xs font-medium text-text-secondary">
              {searchQuery ? "未搜索到匹配记录" : t("emptyTitle") || "暂无研判记录"}
            </p>
            <p className="text-[11px] text-text-muted mt-1">
              {searchQuery ? "请尝试其他关键词" : t("emptyHint") || "发起提问将自动归档"}
            </p>
          </div>
        ) : (
          groupedConversations.map(({ label, conversations: groupConvs }) => (
            <div key={label} className="space-y-0.5">
              <div className="px-2 py-1 text-[10px] font-semibold text-text-tertiary uppercase tracking-wider flex items-center justify-between">
                <span>{label}</span>
                <span className="text-text-muted font-normal">{groupConvs.length}</span>
              </div>

              {groupConvs.map((conv) => {
                const isActive = conv.id === currentId;
                const isEditing = conv.id === editingId;

                if (isEditing) {
                  return (
                    <div
                      key={conv.id}
                      className="p-1.5 bg-accent-50/50 dark:bg-accent-950/40 rounded-xl border border-accent-200 dark:border-accent-800"
                    >
                      <input
                        ref={inputRef}
                        type="text"
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        onKeyDown={handleEditKeyDown}
                        className="w-full px-2 py-1 text-xs bg-surface-card border border-border-default rounded-md text-text-primary focus:outline-none focus:ring-1 focus:ring-accent-500"
                        placeholder="输入会话标题..."
                      />
                      <div className="flex justify-end gap-1 mt-1.5">
                        <button
                          onClick={cancelRename}
                          className="p-1 text-text-muted hover:text-text-primary rounded"
                          title="取消"
                        >
                          <X className="w-3 h-3" />
                        </button>
                        <button
                          onClick={saveRename}
                          className="p-1 text-accent-600 dark:text-accent-400 hover:text-accent-700 rounded"
                          title="保存"
                        >
                          <Check className="w-3 h-3" />
                        </button>
                      </div>
                    </div>
                  );
                }

                return (
                  <div
                    key={conv.id}
                    onClick={() => onSelect(conv)}
                    className={`group relative flex items-center justify-between px-2.5 py-2 rounded-xl text-xs transition-colors cursor-pointer ${
                      isActive
                        ? "bg-accent-50 dark:bg-accent-950/50 text-accent-700 dark:text-accent-300 font-medium"
                        : "text-text-secondary hover:text-text-primary hover:bg-surface-hover"
                    }`}
                  >
                    <div className="flex items-center gap-2 min-w-0 flex-1 pr-1">
                      <MessageSquare
                        className={`w-3.5 h-3.5 shrink-0 ${isActive ? "text-accent-600 dark:text-accent-400" : "text-text-muted group-hover:text-text-secondary"}`}
                      />
                      <span className="truncate">{conv.title || "未命名会话"}</span>
                    </div>

                    <div className="flex items-center gap-1 shrink-0">
                      <span
                        className={`text-[10px] tabular-nums ${isActive ? "text-accent-600/80 dark:text-accent-400/80" : "text-text-muted group-hover:hidden"}`}
                      >
                        {formatTimeAgo(conv.updatedAt)}
                      </span>

                      {/* Hover Actions */}
                      <div className="hidden group-hover:flex items-center gap-0.5">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            startEditing(conv);
                          }}
                          className="p-1 text-text-muted hover:text-text-primary rounded hover:bg-surface-active transition-colors"
                          title="重命名"
                        >
                          <Edit2 className="w-3 h-3" />
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setDeleteConfirmId(conv.id);
                          }}
                          className="p-1 text-text-muted hover:text-rose-600 dark:hover:text-rose-400 rounded hover:bg-surface-active transition-colors"
                          title="删除"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          ))
        )}
      </div>

      {/* Delete Confirmation Modal */}
      {deleteConfirmId && (
        <div className="absolute inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-surface-card rounded-2xl shadow-xl border border-border-subtle max-w-[240px] w-full p-4 animate-in zoom-in-95 duration-150">
            <div className="flex items-center gap-2.5 text-rose-600 dark:text-rose-400 mb-2">
              <AlertTriangle className="w-4 h-4 flex-shrink-0" />
              <h4 className="text-xs font-semibold text-text-primary">
                {t("deleteConfirm") || "确认删除会话？"}
              </h4>
            </div>
            <p className="text-[11px] text-text-muted mb-3">
              {t("deleteWarning") || "此操作将永久删除此条研判记录，不可撤回。"}
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setDeleteConfirmId(null)}
                className="flex-1 py-1.5 text-xs text-text-secondary hover:bg-surface-hover rounded-lg transition-colors cursor-pointer"
              >
                {t("cancelRename") || "取消"}
              </button>
              <button
                onClick={confirmDelete}
                className="flex-1 py-1.5 text-xs text-white bg-rose-600 hover:bg-rose-700 rounded-lg transition-colors font-medium shadow-subtle cursor-pointer"
              >
                {t("delete") || "删除"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );

  return (
    <>
      {/* Desktop Column: Flush Sub-Sidebar with main navigation */}
      <aside
        className={`hidden md:flex flex-col h-full bg-surface-card border-r border-border-subtle flex-shrink-0 transition-[width,opacity] duration-300 ease-in-out relative ${
          isOpen
            ? "w-64 lg:w-72 opacity-100"
            : "w-0 border-r-0 opacity-0 pointer-events-none overflow-hidden"
        }`}
      >
        <div className="w-64 lg:w-72 h-full min-h-0 flex flex-col">{content}</div>
      </aside>

      {/* Mobile Drawer */}
      {isOpen && (
        <div className="md:hidden">
          <div className="fixed inset-0 bg-black/40 backdrop-blur-xs z-40" onClick={onToggle} />
          <aside className="fixed inset-y-0 left-0 z-50 w-72 bg-surface-card shadow-2xl border-r border-border-subtle animate-in slide-in-from-left duration-200">
            {content}
          </aside>
        </div>
      )}
    </>
  );
}
