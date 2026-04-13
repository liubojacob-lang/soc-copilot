"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { useTranslations, useLocale } from "next-intl";
import { api, api_ai_models, type AIModel, type TestModelResponse } from "@/lib/api";
import { loadAuthState } from "@/lib/auth";
import Navigation from "@/components/Navigation";
import { useChatHistory, type ChatConversation } from "@/hooks/useChatHistory";
import { ChatHistorySidebar } from "@/components/ChatHistorySidebar";
import { ChatHeader, ChatInput, ChatMessages, QuickActions } from "./components";
import { useAIChat } from "./hooks/useAIChat";
import { getErrorMessage, cleanModelName, convertToHistoryMessage } from "./utils";
import type { QuickAction } from "./types";
import { AlertTriangle, Lightbulb, FileText, Brain, Zap } from "lucide-react";

export default function AIAssistantPage() {
  const router = useRouter();
  const locale = useLocale();
  const t = useTranslations("aiAssistant");
  const tCommon = useTranslations("common");
  const [mounted, setMounted] = useState(false);

  // Welcome message
  const getWelcomeMessage = () => {
    return `${t("welcome.greeting")}

${t("welcome.capabilities")}

${t("welcome.features.alertAnalysis")}
${t("welcome.features.playbookRecommend")}
${t("welcome.features.naturalLanguage")}
${t("welcome.features.reportGeneration")}

${t("welcome.prompt")}`;
  };

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
  const [showHistoryPanel, setShowHistoryPanel] = useState(false);
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
    setMessages,
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
      router.push(`/${locale}/login`);
      return;
    }
    void loadAIStatus();
    void loadModels();

    // Set initial welcome message
    setMessages([
      {
        role: "assistant",
        content: getWelcomeMessage(),
        timestamp: new Date(),
      },
    ]);
  }, [router, locale]);

  // Auto-save conversation when messages change
  useEffect(() => {
    if (!historyLoaded || messages.length <= 1) return;
    if (skipAutoSaveRef.current) {
      skipAutoSaveRef.current = false;
      return;
    }
    const hasUserMessages = messages.some((m) => m.role === "user");
    if (hasUserMessages) {
      const historyMessages = messages.map(convertToHistoryMessage) as any[];
      saveConversation(historyMessages, selectedModel?.id, selectedModel?.display_name);
    }
  }, [messages, historyLoaded, selectedModel, saveConversation]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "n") {
        e.preventDefault();
        handleNewChat();
      }
      if ((e.ctrlKey || e.metaKey) && e.key === "/") {
        e.preventDefault();
        setShowHistoryPanel((prev) => !prev);
      }
      if (e.key === "Escape" && showHistoryPanel) {
        setShowHistoryPanel(false);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [showHistoryPanel]);

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
      setShowHistoryPanel(false);
    },
    [models, loadConversation, loadChatConversation]
  );

  // New chat handler
  const handleNewChat = useCallback(() => {
    clearChat(getWelcomeMessage());
    createNewConversation();
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

    if (!input) return;

    setInputValue("");
    await sendMessage(input, messages);
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

  const quickActions: QuickAction[] = [
    {
      icon: AlertTriangle,
      label: t("quickActions.analyzeAlert.label"),
      query: t("quickActions.analyzeAlert.query"),
      color: "red",
    },
    {
      icon: Lightbulb,
      label: t("quickActions.recommendPlaybook.label"),
      query: t("quickActions.recommendPlaybook.query"),
      color: "amber",
    },
    {
      icon: FileText,
      label: t("quickActions.generateReport.label"),
      query: t("quickActions.generateReport.query"),
      color: "blue",
    },
    {
      icon: Brain,
      label: t("quickActions.threatHunt.label"),
      query: t("quickActions.threatHunt.query"),
      color: "purple",
    },
  ];

  if (!mounted) return null;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
      <Navigation title={t("title")} subtitle={t("subtitle")} />

      <main className="max-w-6xl mx-auto px-4 py-6">
        {errorMessage && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/20 dark:text-red-300">
            {errorMessage}
          </div>
        )}

        <div className="bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm rounded-2xl shadow-xl border border-gray-200/50 dark:border-gray-700/50 overflow-hidden">
          <div className="flex flex-col lg:flex-row h-[calc(100vh-180px)] min-h-[600px]">
            {/* Chat Area */}
            <div className="flex-1 flex flex-col">
              <ChatHeader
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
                onClearChat={handleNewChat}
                onToggleHistory={() => setShowHistoryPanel(!showHistoryPanel)}
                loading={loading}
                thinking={thinking}
                isStreaming={isStreaming}
              />

              <ChatMessages
                messages={messages}
                streamingMessage={streamingMessage}
                thinking={thinking}
                copiedIndex={copiedIndex}
                onCopy={copyToClipboard}
                t={t}
              />

              <QuickActions
                actions={quickActions}
                onActionClick={(query) => {
                  setInputValue(query);
                }}
                loading={loading}
                thinking={thinking}
                isStreaming={isStreaming}
                t={t}
              />

              <ChatInput
                input={inputValue}
                setInput={setInputValue}
                onSend={handleSubmit}
                loading={loading}
                thinking={thinking}
                isStreaming={isStreaming}
                t={t}
                tCommon={tCommon}
              />
            </div>

            {/* Sidebar */}
            <div className="hidden lg:block w-72 border-l border-gray-200/50 dark:border-gray-700/50 bg-gray-50/30 dark:bg-gray-800/30">
              <div className="p-4 space-y-4">
                <div>
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
                    <Zap className="w-4 h-4 text-amber-500" />
                    {t("sidebar.capabilities")}
                  </h3>
                  <div className="space-y-2">
                    {[
                      { name: t("quickActions.analyzeAlert.label"), colorClass: "bg-red-500" },
                      {
                        name: t("quickActions.recommendPlaybook.label"),
                        colorClass: "bg-blue-500",
                      },
                      { name: t("quickActions.generateReport.label"), colorClass: "bg-purple-500" },
                      { name: t("quickActions.threatHunt.label"), colorClass: "bg-green-500" },
                    ].map((item, i) => (
                      <div
                        key={i}
                        className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400"
                      >
                        <div className={`w-2 h-2 rounded-full ${item.colorClass}`}></div>
                        <span>{item.name}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-xl p-4">
                  <h4 className="text-sm font-medium text-blue-900 dark:text-blue-100 mb-2 flex items-center gap-2">
                    💡 {t("sidebar.usageTips")}
                  </h4>
                  <ul className="text-xs text-blue-800 dark:text-blue-200 space-y-1.5">
                    <li>• {t("sidebar.tips.naturalLanguage")}</li>
                    <li>• {t("sidebar.tips.alertAnalysis")}</li>
                    <li>• {t("sidebar.tips.securityReports")}</li>
                    <li>• {t("sidebar.tips.recommendations")}</li>
                  </ul>
                </div>

                {selectedModel && (
                  <div className="bg-white dark:bg-gray-700 rounded-xl p-4 border border-gray-200 dark:border-gray-600">
                    <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">
                      {t("sidebar.currentModel")}
                    </div>
                    <div className="font-medium text-gray-900 dark:text-white">
                      {cleanModelName(selectedModel.display_name, selectedModel.provider)}
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      {t(`providers.${selectedModel.provider}`) || selectedModel.provider}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </main>

      <ChatHistorySidebar
        isOpen={showHistoryPanel}
        onClose={() => setShowHistoryPanel(false)}
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
    </div>
  );
}
