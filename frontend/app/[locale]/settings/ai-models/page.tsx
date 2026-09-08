"use client";

import { useFormatter, useTranslations } from "next-intl";
/**
 * AI Models Management Page
 * AI 模型管理 - 查看和管理可用的 AI 模型
 */

import { useEffect, useState } from "react";
import { PageHeader } from "@/components/common/PageHeader";
import { useToast } from "@/components/Toast";
import { authFetchJSON } from "@/lib/auth";
import {
  Brain,
  CheckCircle,
  XCircle,
  Zap,
  Settings,
  RefreshCw,
  Play,
  Star,
  Globe,
  Clock,
  MessageSquare,
  Code,
  Image as ImageIcon,
  FileText,
} from "lucide-react";

// Types
interface AIModel {
  id: string;
  name: string;
  provider: string;
  model_type: string;
  capabilities: string[];
  is_active: boolean;
  is_default: boolean;
  max_tokens: number;
  cost_per_1k_tokens: number;
  description?: string;
  last_used?: string;
  total_requests?: number;
  created_at: string;
  updated_at: string;
}

interface AIModelListResponse {
  models: AIModel[];
  total: number;
  default_model_id: string | null;
}

interface TestResult {
  success: boolean;
  response_time_ms?: number;
  response?: string;
  error?: string;
}

export default function AIModelsPage() {
  const t = useTranslations("aiModels");
  const format = useFormatter();
  const { showToast } = useToast();
  const [models, setModels] = useState<AIModel[]>([]);
  const [defaultModelId, setDefaultModelId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [testingModelId, setTestingModelId] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, TestResult>>({});
  const [settingDefault, setSettingDefault] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchModels = async () => {
    try {
      setLoading(true);
      const data: AIModelListResponse = await authFetchJSON("/api/ai/models");
      setModels(data.models || []);
      setDefaultModelId(data.default_model_id);
    } catch (error) {
      console.error("Failed to fetch models:", error);
    } finally {
      setLoading(false);
    }
  };

  const testModel = async (modelId: string) => {
    try {
      setTestingModelId(modelId);
      setTestResults((prev) => ({ ...prev, [modelId]: { success: false } }));

      const result = await authFetchJSON<{ response_time_ms?: number; response?: string }>(
        "/api/ai/models/test",
        {
          method: "POST",
          body: JSON.stringify({ model_id: modelId, prompt: "Hello, test connection." }),
        }
      );

      setTestResults((prev) => ({
        ...prev,
        [modelId]: {
          success: true,
          response_time_ms: result.response_time_ms,
          response: result.response,
        },
      }));
    } catch (error) {
      console.error("Failed to test model:", error);
      setTestResults((prev) => ({
        ...prev,
        [modelId]: {
          success: false,
          error: error instanceof Error ? error.message : t("testFailed"),
        },
      }));
    } finally {
      setTestingModelId(null);
    }
  };

  const setDefault = async (modelId: string) => {
    try {
      setSettingDefault(modelId);
      await authFetchJSON("/api/ai/models/default", {
        method: "POST",
        body: JSON.stringify({ model_id: modelId }),
      });
      await fetchModels();
      showToast("Default model updated", "success");
    } catch (error) {
      console.error("Failed to set default model:", error);
      showToast(t("setDefaultFailed"), "error");
    } finally {
      setSettingDefault(null);
    }
  };

  const refreshModels = async () => {
    try {
      setRefreshing(true);
      await authFetchJSON("/api/ai/models/refresh", { method: "POST" });
      await fetchModels();
    } catch (error) {
      console.error("Failed to refresh models:", error);
    } finally {
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchModels();
  }, []);

  const getProviderIcon = (provider: string) => {
    switch (provider.toLowerCase()) {
      case "openai":
        return <Zap className="w-5 h-5" />;
      case "anthropic":
        return <Brain className="w-5 h-5" />;
      case "google":
        return <Globe className="w-5 h-5" />;
      default:
        return <Settings className="w-5 h-5" />;
    }
  };

  const getProviderColor = (provider: string) => {
    switch (provider.toLowerCase()) {
      case "openai":
        return "text-green-600 bg-green-50 dark:bg-green-900/20 dark:text-green-400";
      case "anthropic":
        return "text-purple-600 bg-purple-50 dark:bg-purple-900/20 dark:text-purple-400";
      case "google":
        return "text-blue-600 bg-blue-50 dark:bg-blue-900/20 dark:text-blue-400";
      default:
        return "text-gray-600 bg-gray-50 dark:bg-gray-900/20 dark:text-gray-400";
    }
  };

  const getCapabilityIcon = (capability: string) => {
    switch (capability.toLowerCase()) {
      case "chat":
        return <MessageSquare className="w-4 h-4" />;
      case "code":
        return <Code className="w-4 h-4" />;
      case "image":
        return <ImageIcon className="w-4 h-4" />;
      case "text":
        return <FileText className="w-4 h-4" />;
      default:
        return <Zap className="w-4 h-4" />;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <PageHeader title={t("title")} subtitle={t("subtitle")} />
        <main className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex items-center justify-center min-h-[50vh]">
            <RefreshCw className="w-8 h-8 animate-spin text-blue-500" />
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <PageHeader
        title={t("title")}
        subtitle={t("subtitle")}
        actions={
          <button
            onClick={refreshModels}
            disabled={refreshing}
            className="px-3.5 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2 text-sm font-medium transition-colors shadow-sm"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} />
            <span>{t("refresh")}</span>
          </button>
        }
      />

      <main className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Models Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {models.map((model) => (
            <div
              key={model.id}
              className={`bg-white dark:bg-gray-800 rounded-lg shadow-sm border-2 transition-all ${
                model.id === defaultModelId
                  ? "border-blue-500 dark:border-blue-400"
                  : "border-gray-200 dark:border-gray-700"
              }`}
            >
              {/* Model Header */}
              <div className="p-6">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center space-x-3">
                    <div className={`p-2 rounded-lg ${getProviderColor(model.provider)}`}>
                      {getProviderIcon(model.provider)}
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center space-x-2">
                        <span>{model.name}</span>
                        {model.id === defaultModelId && (
                          <span className="px-2 py-0.5 text-xs bg-yellow-100 text-yellow-700 dark:bg-yellow-900/20 dark:text-yellow-400 rounded-full flex items-center">
                            <Star className="w-3 h-3 mr-1" />
                            {t("default")}
                          </span>
                        )}
                        {model.is_active ? (
                          <span className="px-2 py-0.5 text-xs bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400 rounded-full">
                            {t("active")}
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 text-xs bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400 rounded-full">
                            {t("inactive")}
                          </span>
                        )}
                      </h3>
                      <p className="text-sm text-gray-600 dark:text-gray-400">{model.provider}</p>
                    </div>
                  </div>
                </div>

                {/* Description */}
                {model.description && (
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                    {model.description}
                  </p>
                )}

                {/* Capabilities */}
                <div className="mb-4">
                  <div className="text-xs text-gray-500 dark:text-gray-400 mb-2">
                    {t("capabilities")}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {Array.isArray(model.capabilities) && model.capabilities.length > 0 ? (
                      model.capabilities.map((capability) => (
                        <span
                          key={capability}
                          className="px-2 py-1 text-xs bg-gray-100 text-gray-700 dark:bg-gray-900 dark:text-gray-300 rounded-md flex items-center space-x-1"
                        >
                          {getCapabilityIcon(capability)}
                          <span className="capitalize">{capability}</span>
                        </span>
                      ))
                    ) : (
                      <span className="text-xs text-gray-400">{t("noCapabilities")}</span>
                    )}
                  </div>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-3 gap-4 mb-4 text-sm">
                  <div className="bg-gray-50 dark:bg-gray-900/50 p-3 rounded-md">
                    <div className="text-gray-600 dark:text-gray-400 text-xs">{t("maxTokens")}</div>
                    <div className="font-semibold text-gray-900 dark:text-white">
                      {model.max_tokens != null ? format.number(model.max_tokens) : "N/A"}
                    </div>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-900/50 p-3 rounded-md">
                    <div className="text-gray-600 dark:text-gray-400 text-xs">{t("costPer1k")}</div>
                    <div className="font-semibold text-gray-900 dark:text-white">
                      ${model.cost_per_1k_tokens?.toFixed(4) || "0.0000"}
                    </div>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-900/50 p-3 rounded-md">
                    <div className="text-gray-600 dark:text-gray-400 text-xs">{t("requests")}</div>
                    <div className="font-semibold text-gray-900 dark:text-white">
                      {model.total_requests || 0}
                    </div>
                  </div>
                </div>

                {/* Test Result */}
                {testResults[model.id] && (
                  <div className="mb-4">
                    {testResults[model.id].success ? (
                      <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-md border border-green-200 dark:border-green-800">
                        <div className="flex items-center space-x-2 text-sm text-green-700 dark:text-green-400">
                          <CheckCircle className="w-4 h-4" />
                          <span>{t("connectionSuccess")}</span>
                        </div>
                        {testResults[model.id].response_time_ms !== undefined && (
                          <div className="text-xs text-green-600 dark:text-green-500 mt-1">
                            {t("responseTime")} {testResults[model.id].response_time_ms?.toFixed(2)}{" "}
                            ms
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="p-3 bg-red-50 dark:bg-red-900/20 rounded-md border border-red-200 dark:border-red-800">
                        <div className="flex items-center space-x-2 text-sm text-red-700 dark:text-red-400">
                          <XCircle className="w-4 h-4" />
                          <span>{t("testFailed")}</span>
                        </div>
                        {testResults[model.id].error && (
                          <div className="text-xs text-red-600 dark:text-red-500 mt-1">
                            {testResults[model.id].error}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {/* Actions */}
                <div className="flex items-center space-x-3">
                  <button
                    onClick={() => testModel(model.id)}
                    disabled={testingModelId === model.id || !model.is_active}
                    className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
                  >
                    {testingModelId === model.id ? (
                      <>
                        <RefreshCw className="w-4 h-4 animate-spin" />
                        <span>{t("testing")}</span>
                      </>
                    ) : (
                      <>
                        <Play className="w-4 h-4" />
                        <span>{t("testConnection")}</span>
                      </>
                    )}
                  </button>
                  {model.id !== defaultModelId && model.is_active && (
                    <button
                      onClick={() => setDefault(model.id)}
                      disabled={settingDefault === model.id}
                      className="flex-1 px-4 py-2 bg-yellow-600 text-white rounded-md hover:bg-yellow-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
                    >
                      {settingDefault === model.id ? (
                        <>
                          <RefreshCw className="w-4 h-4 animate-spin" />
                          <span>{t("setting")}</span>
                        </>
                      ) : (
                        <>
                          <Star className="w-4 h-4" />
                          <span>{t("setDefault")}</span>
                        </>
                      )}
                    </button>
                  )}
                </div>
              </div>

              {/* Footer */}
              {model.last_used && (
                <div className="px-6 py-3 bg-gray-50 dark:bg-gray-900/50 border-t border-gray-200 dark:border-gray-700">
                  <div className="flex items-center justify-between text-xs text-gray-600 dark:text-gray-400">
                    <span className="flex items-center space-x-1">
                      <Clock className="w-3 h-3" />
                      <span>
                        {t("lastUsed")}{" "}
                        {format.dateTime(new Date(model.last_used), {
                          dateStyle: "medium",
                          timeStyle: "medium",
                        })}
                      </span>
                    </span>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Empty State */}
        {models.length === 0 && (
          <div className="text-center py-12">
            <Brain className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              {t("emptyTitle")}
            </h3>
            <p className="text-gray-600 dark:text-gray-400 mb-4">{t("emptyDescription")}</p>
            <button
              onClick={refreshModels}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              Refresh Models
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
