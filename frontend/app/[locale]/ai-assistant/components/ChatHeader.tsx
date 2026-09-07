/** Chat header component with workspace branding and action buttons */

"use client";

import { Brain, RefreshCw, History } from "lucide-react";

interface ChatHeaderProps {
  t: (key: string) => string;
  tCommon: (key: string) => string;
  onClearChat: () => void;
  onToggleHistory: () => void;
  loading: boolean;
  thinking: boolean;
  isStreaming: boolean;
}

export function ChatHeader({
  t,
  tCommon,
  onClearChat,
  onToggleHistory,
  loading,
  thinking,
  isStreaming,
}: ChatHeaderProps) {
  const isBusy = loading || thinking || isStreaming;

  return (
    <div className="h-14 px-4 sm:px-6 border-b border-gray-200/80 dark:border-gray-800/80 flex items-center justify-between bg-white/90 dark:bg-gray-850/90 backdrop-blur-md sticky top-0 z-20 flex-shrink-0">
      <div className="flex items-center gap-2.5">
        <div className="p-1.5 bg-gradient-to-tr from-blue-600 via-indigo-600 to-purple-600 rounded-lg shadow-sm text-white">
          <Brain className="w-4 h-4 text-white" />
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-gray-900 dark:text-white">SOC Copilot</span>
          <span className="hidden sm:inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-purple-50 dark:bg-purple-950/60 text-purple-600 dark:text-purple-300 border border-purple-200/60 dark:border-purple-800/60">
            实战研判工作台
          </span>
        </div>
      </div>

      <div className="flex items-center gap-2">
        {/* New Chat Button */}
        <button
          onClick={onClearChat}
          disabled={isBusy}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-750 text-xs font-medium text-gray-700 dark:text-gray-200 shadow-sm transition-all active:scale-95 disabled:opacity-50"
          title="新建对话 (⌘+N)"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-gray-500 ${isBusy ? "animate-spin" : ""}`} />
          <span className="hidden sm:inline">新对话</span>
        </button>

        {/* History Drawer Toggle */}
        <button
          onClick={onToggleHistory}
          className="p-2 rounded-xl text-gray-600 hover:text-gray-900 dark:text-gray-300 dark:hover:text-white border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-750 shadow-sm transition-all"
          title="历史记录 (⌘+/)"
        >
          <History className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
