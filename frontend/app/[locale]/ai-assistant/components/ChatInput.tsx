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
    <div className="w-full max-w-4xl mx-auto px-4 pb-4 pt-1">
      {/* Floating Card Container */}
      <div className="relative bg-white/95 dark:bg-gray-850/95 backdrop-blur-xl border border-gray-200/90 dark:border-gray-750 shadow-xl hover:shadow-2xl focus-within:border-indigo-500/80 dark:focus-within:border-indigo-400/80 focus-within:ring-4 focus-within:ring-indigo-500/10 rounded-2xl transition-all p-3 flex flex-col gap-2">
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
          className="w-full bg-transparent text-gray-900 dark:text-gray-100 placeholder:text-gray-400 dark:placeholder:text-gray-500 text-sm focus:outline-none resize-none min-h-[44px] max-h-[180px] leading-relaxed px-1"
          disabled={isBusy}
          rows={1}
        />

        {/* Action & Status Row */}
        <div className="flex items-center justify-between pt-1 border-t border-gray-100 dark:border-gray-800/80">
          {/* Left: Model Pill & Key Hint */}
          <div className="flex items-center gap-2 relative" ref={modelPanelRef}>
            {/* Pop-up Model Selector Menu (Bottom to Top) */}
            {showModelPanel && (
              <div className="absolute bottom-full mb-2 left-0 w-44 bg-white/95 dark:bg-[#181b24]/95 backdrop-blur-xl rounded-xl shadow-xl border border-gray-200/90 dark:border-gray-750 z-50 overflow-hidden animate-fadeIn p-1">
                {/* Compact Menu Title */}
                <div className="px-2 py-0.5 flex items-center justify-between text-[10px] font-medium text-gray-400 dark:text-gray-500">
                  <span>研判模型</span>
                  <button
                    type="button"
                    onClick={onRefreshModels}
                    className="p-0.5 hover:text-gray-700 dark:hover:text-gray-200 rounded transition-colors"
                    title={tCommon("refresh")}
                  >
                    <RefreshCw className="w-2.5 h-2.5" />
                  </button>
                </div>

                {/* Auto-Route Option */}
                {autoModel && (
                  <button
                    type="button"
                    onClick={() => {
                      onModelSelect(autoModel);
                      setShowModelPanel(false);
                    }}
                    className={`w-full flex items-center justify-between px-2 py-1.5 rounded-lg text-xs transition-colors ${
                      selectedModel?.id === autoModel.id
                        ? "bg-purple-50 dark:bg-purple-950/60 text-purple-700 dark:text-purple-300 font-medium"
                        : "hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300"
                    }`}
                  >
                    <div className="flex items-center gap-1.5 min-w-0">
                      <span className="w-1.5 h-1.5 rounded-full bg-purple-500 animate-pulse flex-shrink-0" />
                      <span className="font-semibold truncate">⚡ 自动分配</span>
                    </div>
                    <div className="flex items-center gap-1 flex-shrink-0 ml-1">
                      <span className="text-[10px] px-1 py-0.5 leading-none rounded bg-purple-100/80 dark:bg-purple-900/40 text-purple-600 dark:text-purple-300">
                        推荐
                      </span>
                      {selectedModel?.id === autoModel.id && (
                        <Check className="w-3 h-3 text-purple-600 dark:text-purple-400 flex-shrink-0" />
                      )}
                    </div>
                  </button>
                )}

                {/* Divider */}
                <div className="my-0.5 border-t border-gray-100 dark:border-gray-800" />

                {/* Manual Models Selection */}
                <div className="space-y-0.5">
                  {manualModels.map((model) => {
                    const isSelected = selectedModel?.id === model.id;
                    let shortName = "Llama 3.2 11B";
                    let tagText = "极速";
                    let tagColor =
                      "text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/50";
                    let dotColor = "bg-emerald-500";

                    if (model.id.includes("llama-3.2")) {
                      shortName = "Llama 3.2 11B";
                      tagText = "极速";
                      tagColor =
                        "text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/50";
                      dotColor = "bg-emerald-500";
                    } else if (model.id.includes("nemotron")) {
                      shortName = "Nemotron 30B";
                      tagText = "推理";
                      tagColor =
                        "text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-950/50";
                      dotColor = "bg-indigo-500";
                    } else if (model.id.includes("glm-4")) {
                      shortName = "GLM-4.7 Flash";
                      tagText = "长文";
                      tagColor =
                        "text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/50";
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
                        className={`w-full flex items-center justify-between px-2 py-1.5 rounded-lg text-xs transition-colors ${
                          isSelected
                            ? "bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 font-medium"
                            : "hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300"
                        }`}
                      >
                        <div className="flex items-center gap-1.5 min-w-0">
                          <span className={`w-1.5 h-1.5 rounded-full ${dotColor} flex-shrink-0`} />
                          <span className="truncate">{shortName}</span>
                        </div>
                        <div className="flex items-center gap-1 flex-shrink-0 ml-1">
                          {tagText && (
                            <span
                              className={`text-[10px] px-1 py-0.5 leading-none rounded ${tagColor}`}
                            >
                              {tagText}
                            </span>
                          )}
                          {isSelected && (
                            <Check className="w-3 h-3 text-blue-600 dark:text-blue-400 flex-shrink-0" />
                          )}
                        </div>
                      </button>
                    );
                  })}
                </div>

                {/* Compact Micro-toolbar */}
                <div className="pt-1 mt-1 border-t border-gray-100 dark:border-gray-800 flex items-center justify-between px-1.5 text-[10px]">
                  <button
                    type="button"
                    onClick={() => selectedModel && onTestModel(selectedModel)}
                    disabled={!selectedModel || testingModel !== null}
                    className="inline-flex items-center gap-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors disabled:opacity-50"
                    title="测试当前模型网络延迟"
                  >
                    {testingModel ? (
                      <Loader className="w-2.5 h-2.5 animate-spin text-blue-500" />
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
                    className="inline-flex items-center gap-1 text-gray-400 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors disabled:opacity-40 disabled:hover:text-gray-400"
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
              className={`inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-xs font-medium transition-all shadow-xs border ${
                selectedModel?.id === "auto"
                  ? "bg-purple-50 hover:bg-purple-100/80 dark:bg-purple-950/50 dark:hover:bg-purple-900/60 text-purple-700 dark:text-purple-300 border-purple-200/80 dark:border-purple-800/60"
                  : "bg-gray-100 hover:bg-gray-200/80 dark:bg-gray-800 dark:hover:bg-gray-750 text-gray-800 dark:text-gray-200 border-gray-200/80 dark:border-gray-750"
              }`}
              title="切换 AI 研判模型"
            >
              <span
                className={`w-2 h-2 rounded-full ${
                  selectedModel?.id === "auto"
                    ? "bg-purple-500 animate-pulse"
                    : "bg-emerald-500 animate-pulse"
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
                className={`w-3.5 h-3.5 text-gray-400 transition-transform duration-200 ${
                  showModelPanel ? "rotate-180" : ""
                }`}
              />
            </button>

            <span className="hidden sm:inline-block text-[11px] text-gray-400 dark:text-gray-500 select-none">
              ↵ 发送 · Shift+↵ 换行
            </span>
          </div>

          {/* Right: Clear & Submit Button */}
          <div className="flex items-center gap-2">
            {input && !isBusy && (
              <button
                type="button"
                className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
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
              className="px-4 py-2 bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 hover:from-blue-700 hover:via-indigo-700 hover:to-purple-700 text-white rounded-xl disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-md hover:shadow-lg flex items-center gap-1.5 text-xs font-medium active:scale-95"
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
      <p className="text-[11px] text-gray-400 dark:text-gray-500 text-center mt-2 select-none">
        AI 分析结论由大模型生成，涉及网络阻断等高危处置前请经 SOC 专家复核确认。
      </p>
    </div>
  );
}
