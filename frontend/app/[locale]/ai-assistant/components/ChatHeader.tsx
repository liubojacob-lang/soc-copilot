/** Chat header component with model selector and actions */

import { useRef, useEffect } from 'react';
import { Brain, ChevronDown, RefreshCw, History, Check, Loader, Wifi, WifiOff, Settings } from 'lucide-react';
import { cleanModelName } from '../utils';
import type { AIModel } from '@/lib/api';
import type { TestModelResponse } from '@/lib/api';

interface ChatHeaderProps {
  t: any;
  tCommon: any;
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
  onClearChat: () => void;
  onToggleHistory: () => void;
  loading: boolean;
  thinking: boolean;
  isStreaming: boolean;
}

export function ChatHeader({
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
  onClearChat,
  onToggleHistory,
  loading,
  thinking,
  isStreaming
}: ChatHeaderProps) {
  const modelPanelRef = useRef<HTMLDivElement>(null);

  // Close model panel when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (modelPanelRef.current && !modelPanelRef.current.contains(event.target as Node)) {
        setShowModelPanel(false);
      }
    };
    if (showModelPanel) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showModelPanel, setShowModelPanel]);

  const enabledModels = models.filter(m => m.enabled);

  return (
    <div className="px-6 py-4 border-b border-gray-200/50 dark:border-gray-700/50 flex items-center justify-between bg-white/50 dark:bg-gray-800/50">
      <div className="flex items-center gap-3">
        <div className="p-2 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl shadow-lg">
          <Brain className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-lg font-bold text-gray-900 dark:text-white">
            {t('welcome.title')}
          </h1>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {t('subtitle')}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2" ref={modelPanelRef}>
        {/* Model Selector */}
        <div className="relative">
          <button
            onClick={() => setShowModelPanel(!showModelPanel)}
            className="flex items-center gap-2 px-3 py-2 text-sm bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/30 dark:to-purple-900/30 hover:from-blue-100 hover:to-purple-100 dark:hover:from-blue-900/50 dark:hover:to-purple-900/50 border border-blue-200/50 dark:border-blue-700/50 rounded-lg transition-all group"
          >
            <div className="flex items-center gap-2">
              {selectedModel ? (
                <>
                  <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                  <span className="text-gray-700 dark:text-gray-300 font-medium max-w-[120px] truncate">
                    {cleanModelName(selectedModel.display_name, selectedModel.provider)}
                  </span>
                </>
              ) : (
                <span className="text-gray-500 dark:text-gray-400">{t('model.select')}</span>
              )}
            </div>
            <ChevronDown className={`w-4 h-4 text-gray-500 transition-transform duration-200 ${showModelPanel ? 'rotate-180' : ''}`} />
          </button>

          {showModelPanel && (
            <div className="absolute right-0 mt-2 w-80 bg-white dark:bg-gray-800 rounded-xl shadow-2xl border border-gray-200 dark:border-gray-700 z-50 overflow-hidden">
              <div className="p-3 border-b border-gray-100 dark:border-gray-700">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-gray-900 dark:text-white">{t('model.select')}</span>
                  <button
                    onClick={onRefreshModels}
                    className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                    title={tCommon('refresh')}
                  >
                    <RefreshCw className="w-3.5 h-3.5 text-gray-500" />
                  </button>
                </div>
              </div>

              <div className="max-h-64 overflow-y-auto p-2">
                {enabledModels.length === 0 ? (
                  <div className="text-center py-4 text-sm text-gray-500">{t('model.noModels')}</div>
                ) : (
                  <div className="space-y-1">
                    {enabledModels.map(model => (
                      <button
                        key={model.id}
                        onClick={() => onModelSelect(model)}
                        className={`w-full p-3 rounded-lg text-left transition-all ${
                          selectedModel?.id === model.id
                            ? 'bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/30 dark:to-purple-900/30 border border-blue-300 dark:border-blue-700'
                            : 'hover:bg-gray-50 dark:hover:bg-gray-700/50 border border-transparent'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium text-gray-900 dark:text-white">
                            {cleanModelName(model.display_name, model.provider)}
                          </span>
                          {selectedModel?.id === model.id && (
                            <Check className="w-4 h-4 text-blue-600 dark:text-blue-400 flex-shrink-0" />
                          )}
                        </div>
                        <div className="text-xs text-gray-500 dark:text-gray-400 mt-1 flex items-center gap-1">
                          <span className="w-1.5 h-1.5 rounded-full bg-purple-400"></span>
                          {t(`providers.${model.provider}`) || model.provider}
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              <div className="p-3 border-t border-gray-100 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-700/30">
                <div className="flex gap-2">
                  <button
                    onClick={() => selectedModel && onTestModel(selectedModel)}
                    disabled={!selectedModel || testingModel !== null}
                    className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-gray-700 dark:text-gray-300"
                  >
                    {testingModel ? (
                      <Loader className="w-3.5 h-3.5 animate-spin text-blue-600" />
                    ) : testResult?.model_id === selectedModel?.id ? (
                      testResult?.success ? (
                        <><Wifi className="w-3.5 h-3.5 text-green-600" /><span className="text-green-600">{testResult.latency_ms?.toFixed(0)}ms</span></>
                      ) : (
                        <WifiOff className="w-3.5 h-3.5 text-red-600" />
                      )
                    ) : (
                      <span>🔌</span>
                    )}
                    <span>{testingModel ? t('model.testing') : t('model.testConnection')}</span>
                  </button>

                  <button
                    onClick={() => selectedModel && onSetDefault(selectedModel)}
                    disabled={!selectedModel || selectedModel.id === defaultModel?.id}
                    className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-lg hover:from-blue-600 hover:to-purple-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                  >
                    <Settings className="w-3.5 h-3.5" />
                    <span>{selectedModel?.id === defaultModel?.id ? t('model.isDefault') : t('model.setDefault')}</span>
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* History Toggle */}
        <button
          onClick={onToggleHistory}
          className="p-2 rounded-lg transition-colors text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700"
          title={t('history.title')}
        >
          <History className="w-5 h-5" />
        </button>

        {/* Clear Chat */}
        <button
          onClick={onClearChat}
          disabled={loading || thinking || isStreaming}
          className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg disabled:opacity-50 transition-colors"
          title={t('actions.clearChat')}
        >
          <RefreshCw className={`w-5 h-5 ${loading || thinking || isStreaming ? 'animate-spin' : ''}`} />
        </button>
      </div>
    </div>
  );
}
