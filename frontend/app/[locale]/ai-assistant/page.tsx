"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "@/i18n/navigation";
import { useTranslations, useLocale } from "next-intl";
import { api, api_ai_models, type AIModel, type TestModelResponse } from "@/lib/api";
import { loadAuthState } from "@/lib/auth";
import { PageHeader } from "@/components/common/PageHeader";
import { useChatHistory, type ChatConversation } from "@/hooks/useChatHistory";
import { ChatHeader, ChatInput, ChatMessages, HeroPrompts, ChatHistoryPanel } from "./components";
import { useAIChat } from "./hooks/useAIChat";
import { getErrorMessage, convertToHistoryMessage } from "./utils";
import { X } from "lucide-react";

export default function AIAssistantPage() {
  const router = useRouter();
  const locale = useLocale();
  const t = useTranslations("aiAssistant");
  const tCommon = useTranslations("common");
  const [mounted, setMounted] = useState(false);

  // Model state
  const [models, setModels] = useState<AIModel[]>([]);
  const [selectedModel, setSelectedModel] = useState<AIModel | null>(null);
  const [defaultModel, setDefaultModel] = useState<AIModel | null>(null);
  const [testingModel, setTestingModel] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<TestModelResponse | null>(null);
  const [showModelPanel, setShowModelPanel] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  // UI state
  const [showHistoryPanel, setShowHistoryPanel] = useState(true);
  const skipAutoSaveRef = useRef(false);
  const [inputValue, setInputValue] = useState("");

  // Chat history hook
  const {
    conversations,
    filteredConversations,
    currentId,
    searchQuery,
    setSearchQuery,
    isLoaded: historyLoaded,
    createNewConversation,
    saveConversation,
    loadConversation,
    deleteConversation,
    renameConversation,
  } = useChatHistory();

  // AI Chat hook
  const {
    messages,
    loading,
    thinking,
    isStreaming,
    streamingMessage,
    sendMessage,
    loadConversation: loadChatConversation,
    clearChat,
  } = useAIChat({
    selectedModelId: selectedModel?.id,
    onConversationSave: saveConversation,
  });

  // Authentication & initialization
  useEffect(() => {
    setMounted(true);
    const authState = loadAuthState();
    if (!authState?.isAuthenticated) {
      router.push("/login");
      return;
    }
    void loadAIStatus();
    void loadModels();
  }, [router, locale]);

  // Auto-save conversation when messages change
  useEffect(() => {
    if (!historyLoaded || messages.length === 0) return;
    if (skipAutoSaveRef.current) {
      skipAutoSaveRef.current = false;
      return;
    }
    // Don't auto-save during typewriter streaming
    if (isStreaming || messages.some((m) => m.isStreaming)) return;

    const hasUserMessages = messages.some((m) => m.role === "user");
    if (hasUserMessages) {
      const validMessages = messages.filter(
        (m) => m && m.role && typeof m.content === "string" && m.content.trim() && !m.isStreaming
      );
      if (validMessages.length > 0) {
        const historyMessages = validMessages.map(convertToHistoryMessage) as any[];
        saveConversation(historyMessages, selectedModel?.id, selectedModel?.display_name);
      }
    }
  }, [messages, historyLoaded, isStreaming, selectedModel, saveConversation]);

  // Restore sidebar open preference on mount
  useEffect(() => {
    try {
      const saved = localStorage.getItem("chatHistorySidebarOpen");
      if (saved !== null) {
        setShowHistoryPanel(saved === "true");
      } else if (window.innerWidth < 1024) {
        setShowHistoryPanel(false);
      }
    } catch {}
  }, []);

  const handleToggleHistory = useCallback(() => {
    setShowHistoryPanel((prev) => {
      const next = !prev;
      try {
        localStorage.setItem("chatHistorySidebarOpen", String(next));
      } catch {}
      return next;
    });
  }, []);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "n") {
        e.preventDefault();
        handleNewChat();
      }
      if ((e.ctrlKey || e.metaKey) && e.key === "/") {
        e.preventDefault();
        handleToggleHistory();
      }
      if (e.key === "Escape" && showHistoryPanel && window.innerWidth < 768) {
        setShowHistoryPanel(false);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [showHistoryPanel, handleToggleHistory]);

  // Load conversation handler
  const handleLoadConversation = useCallback(
    (conv: ChatConversation) => {
      skipAutoSaveRef.current = true;
      loadConversation(conv.id);
      loadChatConversation(conv, models);

      if (conv.modelId) {
        const model = models.find((m) => m.id === conv.modelId);
        if (model) setSelectedModel(model);
      }
      if (typeof window !== "undefined" && window.innerWidth < 768) {
        setShowHistoryPanel(false);
      }
    },
    [models, loadConversation, loadChatConversation]
  );

  // New chat handler
  const handleNewChat = useCallback(() => {
    clearChat();
    createNewConversation();
    setInputValue("");
  }, [clearChat, createNewConversation]);

  const loadAIStatus = async () => {
    try {
      await api.get("/api/ai/status");
    } catch (error) {
      console.error("Failed to check AI status:", error);
    }
  };

  const loadModels = async () => {
    try {
      const response = await api_ai_models.listModels();
      setModels(response.models);
      const enabledModels = response.models.filter((m) => m.enabled);
      const resolvedDefaultModel = response.default_model_id
        ? (response.models.find((m) => m.id === response.default_model_id) ?? null)
        : null;

      setDefaultModel(resolvedDefaultModel);

      const savedModelId = localStorage.getItem("selectedModelId");
      const savedModel = savedModelId ? enabledModels.find((m) => m.id === savedModelId) : null;

      setSelectedModel((prevSelected) => {
        if (savedModel) return savedModel;
        if (resolvedDefaultModel?.enabled) return resolvedDefaultModel;
        if (prevSelected && enabledModels.some((m) => m.id === prevSelected.id))
          return prevSelected;
        return enabledModels[0] ?? null;
      });
      setTestResult(null);
    } catch (error) {
      console.error("Failed to load models:", error);
      setErrorMessage(getErrorMessage(error, t("errors.loadModelsFailed"), t));
    }
  };

  const testModelConnectivity = async (model: AIModel) => {
    setTestingModel(model.id);
    setTestResult(null);
    try {
      const result = await api_ai_models.testModel({ model_id: model.id });
      setTestResult(result);
    } catch (error) {
      setTestResult({
        success: false,
        model_id: model.id,
        error_message: getErrorMessage(error, t("errors.serviceFailed", { message: "" }), t),
      });
    } finally {
      setTestingModel(null);
    }
  };

  const setModelAsDefault = async (model: AIModel) => {
    try {
      await api_ai_models.setDefaultModel({ model_id: model.id });
      setDefaultModel(model);
    } catch (error) {
      setErrorMessage(getErrorMessage(error, t("errors.setDefaultFailed"), t));
    }
  };

  const handleModelSelect = (model: AIModel) => {
    setSelectedModel(model);
    localStorage.setItem("selectedModelId", model.id);
    setShowModelPanel(false);
  };

  const handleSubmit = async (e?: React.FormEvent) => {
    e?.preventDefault();
    const input = inputValue.trim();

    if (!input || loading || thinking || isStreaming) return;

    setInputValue("");
    await sendMessage(input, messages);
  };

  const handleSelectPrompt = async (prompt: string) => {
    setInputValue("");
    await sendMessage(prompt, messages);
  };

  const copyToClipboard = async (text: string, index: number) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedIndex(index);
      setTimeout(() => setCopiedIndex(null), 2000);
    } catch (error) {
      setErrorMessage(getErrorMessage(error, t("errors.copyFailed"), t));
    }
  };

  const formatTimeAgo = useCallback(
    (dateStr: string) => {
      const date = new Date(dateStr);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMs / 3600000);
      const diffDays = Math.floor(diffMs / 86400000);

      if (diffMins < 1) return t("history.justNow");
      if (diffMins < 60) return t("history.minutesAgo", { count: diffMins });
      if (diffHours < 24) return t("history.hoursAgo", { count: diffHours });
      return t("history.daysAgo", { count: diffDays });
    },
    [t]
  );

  if (!mounted) return null;

  const hasMessages = messages.length > 0;

  return (
    <div className="h-[calc(100vh-4rem)] max-h-[calc(100vh-4rem)] bg-surface-ground flex flex-col overflow-hidden">
      <PageHeader
        title={t("title")}
        subtitle={t("subtitle")}
        className="w-full flex-shrink-0 pt-3 sm:pt-4 pb-1"
      />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-3 sm:pb-4 flex-1 min-h-0 w-full flex flex-col overflow-hidden">
        {/* Floating Error Toast */}
        {errorMessage && (
          <div className="mb-3 flex-shrink-0 rounded-xl border border-rose-200 bg-rose-50/95 dark:border-rose-900/60 dark:bg-rose-950/90 backdrop-blur px-4 py-2 text-xs text-rose-700 dark:text-rose-300 shadow-sm flex items-center justify-between">
            <span>{errorMessage}</span>
            <button
              onClick={() => setErrorMessage(null)}
              className="p-1 hover:bg-rose-100 dark:hover:bg-rose-900/50 rounded"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* AI Workspace Card (Embedded 2-Column Flex Container) */}
        <div className="bg-white dark:bg-gray-850/90 border border-gray-200/80 dark:border-gray-700/80 rounded-2xl shadow-sm flex flex-1 min-h-0 h-full max-h-full overflow-hidden relative">
          {/* Embedded Left History Sidebar */}
          <ChatHistoryPanel
            isOpen={showHistoryPanel}
            onToggle={handleToggleHistory}
            conversations={filteredConversations}
            currentId={currentId}
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
            onSelect={handleLoadConversation}
            onDelete={deleteConversation}
            onRename={renameConversation}
            onNewChat={handleNewChat}
            formatTimeAgo={formatTimeAgo}
          />

          {/* Right Main Chat Column */}
          <div className="flex-1 flex flex-col min-w-0 min-h-0 h-full overflow-hidden relative">
            {/* Card Top Chat Header */}
            <ChatHeader
              t={t}
              tCommon={tCommon}
              onClearChat={handleNewChat}
              onToggleHistory={handleToggleHistory}
              showHistory={showHistoryPanel}
              loading={loading}
              thinking={thinking}
              isStreaming={isStreaming}
            />

            {/* Dynamic Content: Empty State Hero vs Active Chat Thread */}
            <div className="flex-1 min-h-0 overflow-hidden flex flex-col relative">
              {!hasMessages ? (
                <div className="flex-1 min-h-0 overflow-y-auto flex flex-col justify-center py-6">
                  <HeroPrompts
                    onSelectPrompt={handleSelectPrompt}
                    disabled={loading || thinking || isStreaming}
                  />
                </div>
              ) : (
                <ChatMessages
                  messages={messages}
                  streamingMessage={streamingMessage}
                  thinking={thinking}
                  copiedIndex={copiedIndex}
                  onCopy={copyToClipboard}
                  t={t}
                />
              )}
            </div>

            {/* Mainstream Floating Glassmorphic Input with integrated Model Selector */}
            <ChatInput
              input={inputValue}
              setInput={setInputValue}
              onSend={handleSubmit}
              loading={loading}
              thinking={thinking}
              isStreaming={isStreaming}
              t={t}
              tCommon={tCommon}
              selectedModel={selectedModel}
              models={models}
              defaultModel={defaultModel}
              testResult={testResult}
              testingModel={testingModel}
              showModelPanel={showModelPanel}
              setShowModelPanel={setShowModelPanel}
              onModelSelect={handleModelSelect}
              onTestModel={testModelConnectivity}
              onSetDefault={setModelAsDefault}
              onRefreshModels={loadModels}
            />
          </div>
        </div>
      </main>
    </div>
  );
}
