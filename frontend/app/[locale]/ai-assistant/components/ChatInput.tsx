/** Chat input component with floating glassmorphic card, auto-resizing textarea, model selector pill, and send button */

"use client";

import { useRef, useEffect } from "react";
import {
  Loader,
  X,
  ArrowUp,
  ChevronUp,
  Check,
  Wifi,
  WifiOff,
  Settings,
  RefreshCw,
} from "lucide-react";
import { cleanModelName } from "../utils";
import type { AIModel, TestModelResponse } from "@/lib/api";

interface ChatInputProps {
  input: string;
  setInput: (value: string) => void;
  onSend: () => void;
  loading: boolean;
  thinking: boolean;
  isStreaming: boolean;
  t: (key: string) => string;
  tCommon: (key: string) => string;
  selectedModel: AIModel | null;
  models: AIModel[];
  defaultModel: AIModel | null;
  testResult: TestModelResponse | null;
  testingModel: string | null;
  showModelPanel: boolean;
  setShowModelPanel: (show: boolean) => void;
  onModelSelect: (model: AIModel) => void;
  onTestModel: (model: AIModel) => void;
  onSetDefault: (model: AIModel) => void;
  onRefreshModels: () => void;
}

export function ChatInput({
  input,
  setInput,
  onSend,
  loading,
  thinking,
  isStreaming,
  t,
  tCommon,
  selectedModel,
  models,
  defaultModel,
  testResult,
  testingModel,
  showModelPanel,
  setShowModelPanel,
  onModelSelect,
  onTestModel,
  onSetDefault,
  onRefreshModels,
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const modelPanelRef = useRef<HTMLDivElement>(null);

  // Auto-resize textarea based on content
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  }, [input]);

  // Focus textarea on mount
  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  // Close model panel when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (modelPanelRef.current && !modelPanelRef.current.contains(event.target as Node)) {
        setShowModelPanel(false);
      }
    };
    if (showModelPanel) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [showModelPanel, setShowModelPanel]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!loading && !thinking && !isStreaming && input.trim()) {
        onSend();
      }
    }
  };

  const isBusy = loading || thinking || isStreaming;

  const enabledModels = models.filter((m) => m.enabled);
  const autoModel = enabledModels.find((m) => m.id === "auto" || m.provider === "auto");
  const manualModels = enabledModels.filter((m) => m.id !== "auto" && m.provider !== "auto");

  return (
    <div className="w-full max-w-4xl mx-auto px-4 pb-4 pt-1 flex-shrink-0">
      {/* Floating Card Container */}
      <div className="relative bg-surface-card border border-border-subtle shadow-xl hover:shadow-2xl focus-within:border-ai/80 focus-within:ring-4 focus-within:ring-ai/10 rounded-2xl transition-all p-3 flex flex-col gap-2">
        {/* Text Input */}
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            t("inputPlaceholder") ||
            "输入安全告警、可疑IP/载荷、逆向代码或研判指令，按 Shift+Enter 换行..."
          }
          className="w-full bg-transparent text-text-primary placeholder:text-text-muted text-sm focus:outline-none resize-none min-h-[44px] max-h-[180px] leading-relaxed px-1"
          disabled={isBusy}
          rows={1}
        />

        {/* Action & Status Row */}
        <div className="flex items-center justify-between pt-1 border-t border-border-subtle">
          {/* Left: Model Pill & Key Hint */}
          <div className="flex items-center gap-2 relative" ref={modelPanelRef}>
            {/* Pop-up Model Selector Menu (Bottom to Top) */}
            {showModelPanel && (
              <div className="absolute bottom-full mb-2 left-0 w-56 bg-surface-card rounded-xl shadow-2xl border border-border-default shadow-slate-900/15 dark:shadow-black/60 z-50 overflow-hidden animate-fadeIn p-1.5">
                {/* Compact Menu Title */}
                <div className="px-2 py-0.5 flex items-center justify-between text-[10px] font-medium text-text-muted">
                  <span>研判模型</span>
                  <button
                    type="button"
                    onClick={onRefreshModels}
                    className="p-0.5 hover:text-text-primary rounded transition-colors"
                    title={tCommon("refresh")}
                  >
                    <RefreshCw className="w-2.5 h-2.5" />
                  </button>
                </div>

                {/* Auto-Route Option */}
                {autoModel &&
                  (() => {
                    const isAutoSelected =
                      selectedModel?.id === autoModel.id ||
                      (!selectedModel && autoModel.id === "auto");
                    return (
                      <button
                        type="button"
                        onClick={() => {
                          onModelSelect(autoModel);
                          setShowModelPanel(false);
                        }}
                        className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs transition-colors cursor-pointer group ${
                          isAutoSelected
                            ? "bg-purple-50 dark:bg-purple-950/50 text-purple-700 dark:text-purple-300 font-medium"
                            : "hover:bg-surface-hover text-text-secondary hover:text-text-primary"
                        }`}
                      >
                        <div className="flex items-center gap-2 min-w-0 flex-1">
                          <span className="w-2 h-2 rounded-full bg-purple-500 animate-pulse shrink-0" />
                          <span className="truncate">自动分配</span>
                        </div>
                        <div className="flex items-center gap-2 shrink-0 ml-2">
                          <span className="text-[10px] px-1.5 py-0.5 leading-none rounded font-medium bg-purple-100/80 text-purple-700 dark:bg-purple-900/60 dark:text-purple-300">
                            推荐
                          </span>
                          <div className="w-3.5 h-3.5 flex items-center justify-center shrink-0">
                            {isAutoSelected && (
                              <Check className="w-3.5 h-3.5 text-purple-600 dark:text-purple-400" />
                            )}
                          </div>
                        </div>
                      </button>
                    );
                  })()}

                {/* Divider */}
                <div className="my-1 border-t border-border-subtle" />

                {/* Manual Models Selection */}
                <div className="space-y-0.5">
                  {manualModels.map((model) => {
                    const isSelected = selectedModel?.id === model.id;
                    let shortName = "Llama 3.2 11B";
                    let tagText = "极速";
                    let tagColor =
                      "text-emerald-700 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-950/60";
                    let dotColor = "bg-emerald-500";

                    if (model.id.includes("llama-3.2")) {
                      shortName = "Llama 3.2 11B";
                      tagText = "极速";
                      tagColor =
                        "text-emerald-700 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-950/60";
                      dotColor = "bg-emerald-500";
                    } else if (model.id.includes("nemotron")) {
                      shortName = "Nemotron 30B";
                      tagText = "推理";
                      tagColor =
                        "text-indigo-700 dark:text-indigo-300 bg-indigo-50 dark:bg-indigo-950/60";
                      dotColor = "bg-indigo-500";
                    } else if (model.id.includes("glm-4")) {
                      shortName = "GLM-4.7 Flash";
                      tagText = "长文";
                      tagColor =
                        "text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-950/60";
                      dotColor = "bg-amber-500";
                    } else {
                      shortName = cleanModelName(model.display_name, model.provider);
                      tagText = "";
                    }

                    return (
                      <button
                        type="button"
                        key={model.id}
                        onClick={() => {
                          onModelSelect(model);
                          setShowModelPanel(false);
                        }}
                        className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs transition-colors cursor-pointer group ${
                          isSelected
                            ? "bg-accent-50 dark:bg-accent-950/50 text-accent-700 dark:text-accent-300 font-medium"
                            : "hover:bg-surface-hover text-text-secondary hover:text-text-primary"
                        }`}
                      >
                        <div className="flex items-center gap-2 min-w-0 flex-1">
                          <span className={`w-2 h-2 rounded-full ${dotColor} shrink-0`} />
                          <span className="truncate">{shortName}</span>
                        </div>
                        <div className="flex items-center gap-2 shrink-0 ml-2">
                          {tagText && (
                            <span
                              className={`text-[10px] px-1.5 py-0.5 leading-none rounded font-medium ${tagColor}`}
                            >
                              {tagText}
                            </span>
                          )}
                          <div className="w-3.5 h-3.5 flex items-center justify-center shrink-0">
                            {isSelected && (
                              <Check className="w-3.5 h-3.5 text-accent-600 dark:text-accent-400" />
                            )}
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>

                {/* Compact Micro-toolbar */}
                <div className="pt-1 mt-1 border-t border-border-subtle flex items-center justify-between px-1.5 text-[10px]">
                  <button
                    type="button"
                    onClick={() => selectedModel && onTestModel(selectedModel)}
                    disabled={!selectedModel || testingModel !== null}
                    className="inline-flex items-center gap-1 text-text-muted hover:text-text-primary transition-colors disabled:opacity-50"
                    title="测试当前模型网络延迟"
                  >
                    {testingModel ? (
                      <Loader className="w-2.5 h-2.5 animate-spin text-accent-500" />
                    ) : testResult?.model_id === selectedModel?.id ? (
                      testResult?.success ? (
                        <>
                          <Wifi className="w-2.5 h-2.5 text-emerald-500" />
                          <span className="text-emerald-600 dark:text-emerald-400 font-medium">
                            {testResult.latency_ms?.toFixed(0)}ms
                          </span>
                        </>
                      ) : (
                        <>
                          <WifiOff className="w-2.5 h-2.5 text-rose-500" />
                          <span className="text-rose-500">异常</span>
                        </>
                      )
                    ) : (
                      <>
                        <Wifi className="w-2.5 h-2.5" />
                        <span>测速</span>
                      </>
                    )}
                  </button>

                  <button
                    type="button"
                    onClick={() => selectedModel && onSetDefault(selectedModel)}
                    disabled={!selectedModel || selectedModel.id === defaultModel?.id}
                    className="inline-flex items-center gap-1 text-text-muted hover:text-accent-600 dark:hover:text-accent-400 transition-colors disabled:opacity-40 disabled:hover:text-text-muted"
                    title="将当前选择设为默认"
                  >
                    <Settings className="w-2.5 h-2.5" />
                    <span>{selectedModel?.id === defaultModel?.id ? "已默认" : "设为默认"}</span>
                  </button>
                </div>
              </div>
            )}

            {/* Model Pill Trigger Button */}
            <button
              type="button"
              onClick={() => setShowModelPanel(!showModelPanel)}
              className={`inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-xs font-medium transition-all shadow-subtle border ${
                selectedModel?.id === "auto"
                  ? "bg-ai/10 hover:bg-ai/15 text-ai-fg border-ai/20"
                  : "bg-surface-hover hover:bg-surface-active text-text-primary border-border-subtle"
              }`}
              title="切换 AI 研判模型"
            >
              <span
                className={`w-2 h-2 rounded-full ${
                  selectedModel?.id === "auto"
                    ? "bg-purple-500 animate-pulse"
                    : selectedModel?.id.includes("nemotron")
                      ? "bg-indigo-500"
                      : selectedModel?.id.includes("glm")
                        ? "bg-amber-500"
                        : "bg-emerald-500"
                }`}
              />
              <span className="max-w-[120px] truncate">
                {selectedModel
                  ? selectedModel.id === "auto"
                    ? "⚡ 自动分配"
                    : selectedModel.id.includes("llama-3.2")
                      ? "Llama 3.2 11B"
                      : selectedModel.id.includes("nemotron")
                        ? "Nemotron 30B"
                        : selectedModel.id.includes("glm-4")
                          ? "GLM-4.7 Flash"
                          : cleanModelName(selectedModel.display_name, selectedModel.provider)
                  : t("model.select")}
              </span>
              <ChevronUp
                className={`w-3.5 h-3.5 text-text-muted transition-transform duration-200 ${
                  showModelPanel ? "rotate-180" : ""
                }`}
              />
            </button>

            <span className="hidden sm:inline-block text-[11px] text-text-muted select-none">
              ↵ 发送 · Shift+↵ 换行
            </span>
          </div>

          {/* Right: Clear & Submit Button */}
          <div className="flex items-center gap-2">
            {input && !isBusy && (
              <button
                type="button"
                className="p-1.5 text-text-muted hover:text-text-primary hover:bg-surface-hover rounded-lg transition-colors"
                title={tCommon("clear")}
                onClick={() => setInput("")}
              >
                <X className="w-4 h-4" />
              </button>
            )}

            <button
              type="button"
              onClick={onSend}
              disabled={isBusy || !input.trim()}
              className="px-4 py-2 bg-gradient-to-r from-accent-600 via-indigo-600 to-purple-600 hover:from-accent-700 hover:via-indigo-700 hover:to-purple-700 text-white rounded-xl disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-md hover:shadow-lg flex items-center gap-1.5 text-xs font-medium active:scale-95"
            >
              {isBusy ? (
                <>
                  <Loader className="w-3.5 h-3.5 animate-spin" />
                  <span>研判中...</span>
                </>
              ) : (
                <>
                  <ArrowUp className="w-3.5 h-3.5" />
                  <span>发送</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Safety & Compliance Disclaimer */}
      <p className="text-[11px] text-text-muted text-center mt-2 select-none">
        AI 分析结论由大模型生成，涉及网络阻断等高危处置前请经 SOC 专家复核确认。
      </p>
    </div>
  );
}
