/** Chat header component with workspace branding and action buttons */

"use client";

import { Brain, Plus, PanelLeft, Sparkles } from "lucide-react";

interface ChatHeaderProps {
  t: (key: string) => string;
  tCommon: (key: string) => string;
  onClearChat: () => void;
  onToggleHistory: () => void;
  showHistory?: boolean;
  loading: boolean;
  thinking: boolean;
  isStreaming: boolean;
  currentTitle?: string | null;
  activeModelName?: string | null;
}

export function ChatHeader({
  t,
  tCommon,
  onClearChat,
  onToggleHistory,
  showHistory = false,
  loading,
  thinking,
  isStreaming,
  currentTitle,
  activeModelName,
}: ChatHeaderProps) {
  const isBusy = loading || thinking || isStreaming;

  return (
    <div className="h-13 px-4 border-b border-border-subtle flex items-center justify-between bg-surface-card sticky top-0 z-20 flex-shrink-0">
      <div className="flex items-center gap-2.5 min-w-0">
        {/* Toggle History Sidebar Button (only visible when sidebar is collapsed) */}
        {!showHistory && (
          <>
            <button
              onClick={onToggleHistory}
              className="p-1.5 rounded-lg transition-colors cursor-pointer text-text-secondary hover:text-text-primary hover:bg-surface-hover"
              title={`${t("history.expandHistory") || "展开历史"} (⌘/)`}
              aria-label={t("history.expandHistory") || "展开历史"}
            >
              <PanelLeft className="w-4 h-4" />
            </button>
            <div className="h-4 w-px bg-border-subtle" aria-hidden="true" />
          </>
        )}

        <div className="flex items-center gap-2 min-w-0">
          <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-ai/10 text-ai-fg border border-ai/20">
            <Brain className="w-3.5 h-3.5" />
          </div>
          <span className="text-xs sm:text-sm font-semibold text-text-primary truncate max-w-[200px] sm:max-w-[320px]">
            {currentTitle || t("title") || "安全研判会话"}
          </span>
          {activeModelName && (
            <span className="hidden md:inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-surface-hover text-text-secondary border border-border-subtle">
              <Sparkles className="w-2.5 h-2.5 text-ai-fg" />
              {activeModelName}
            </span>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        {/* New Chat Button */}
        <button
          onClick={onClearChat}
          disabled={isBusy}
          className="flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-lg border border-border-subtle bg-surface-card hover:bg-surface-hover text-xs font-medium text-text-primary hover:border-border-default shadow-subtle transition-all active:scale-95 disabled:opacity-50 cursor-pointer"
          title="新建研判对话 (⌘N)"
        >
          <Plus className="w-3.5 h-3.5 text-text-secondary" />
          <span className="hidden sm:inline">{t("history.newChat") || "新对话"}</span>
          <kbd className="hidden lg:inline text-[9px] px-1 py-0.5 bg-surface-hover text-text-muted rounded border border-border-subtle font-mono">
            ⌘N
          </kbd>
        </button>
      </div>
    </div>
  );
}
