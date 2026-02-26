/** Dify configuration modal component */

import { useState, useEffect } from 'react';
import { Settings, X, Globe, Key, Eye, EyeOff, Download, RefreshCw, CheckCircle, XCircle } from 'lucide-react';
import type { DifyConfig, DifyConfigForm } from '../types';

interface DifyConfigModalProps {
  show: boolean;
  config: DifyConfig | null;
  onClose: () => void;
  onSave: (config: DifyConfigForm) => Promise<void>;
  onTest: () => Promise<void>;
  t: any;
}

export function DifyConfigModal({
  show,
  config,
  onClose,
  onSave,
  onTest,
  t
}: DifyConfigModalProps) {
  const [formData, setFormData] = useState<DifyConfigForm>({
    difyApiUrl: "",
    difyApiKey: "",
    difyWorkspaceId: ""
  });
  const [showApiKey, setShowApiKey] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [configSuccess, setConfigSuccess] = useState<string | null>(null);
  const [configError, setConfigError] = useState<string | null>(null);

  // Initialize form with current config
  useEffect(() => {
    if (config) {
      setFormData({
        difyApiUrl: config.api_url || "",
        difyApiKey: config.api_key || "",
        difyWorkspaceId: config.workspace_id || ""
      });
    }
  }, [config]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setConfigError(null);
    setConfigSuccess(null);

    try {
      await onSave(formData);
      setConfigSuccess("Configuration saved successfully!");
      await new Promise(resolve => setTimeout(resolve, 1500));
      onClose();
    } catch (e: unknown) {
      setConfigError((e as Error)?.message || "Failed to save configuration");
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    setConfigError(null);
    setConfigSuccess(null);

    try {
      await onTest();
      setConfigSuccess("Successfully connected to Dify!");
    } catch (e: unknown) {
      setConfigError((e as Error)?.message || "Connection test failed");
    } finally {
      setTesting(false);
    }
  };

  if (!show) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <Settings className="w-5 h-5 text-blue-600" />
              {t('configModal.title')}
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              {t('configModal.description')}
            </p>
          </div>
          <button
            onClick={() => {
              onClose();
              setConfigError(null);
              setConfigSuccess(null);
            }}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Error/Success Messages */}
        {configError && (
          <div className="mx-6 mt-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 px-4 py-3 rounded-lg">
            {configError}
          </div>
        )}
        {configSuccess && (
          <div className="mx-6 mt-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 text-green-700 dark:text-green-300 px-4 py-3 rounded-lg">
            {configSuccess}
          </div>
        )}

        {/* Configuration Form */}
        <form onSubmit={handleSave} className="p-6 overflow-y-auto max-h-[60vh] space-y-6">
          {/* Current Configuration Display */}
          {config && config.configured && (
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
              <h4 className="text-sm font-semibold text-blue-900 dark:text-blue-100 mb-3">{t('configModal.currentConfig')}</h4>
              <div className="space-y-2 text-sm">
                <div className="flex items-center gap-2">
                  <span className="text-gray-600 dark:text-gray-400">{t('configModal.apiUrl')}:</span>
                  <code className="px-2 py-1 bg-white dark:bg-gray-700 rounded text-blue-600 dark:text-blue-400">{config.api_url || t('notConfigured')}</code>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-gray-600 dark:text-gray-400">{t('configModal.apiKey')}:</span>
                  <code className="px-2 py-1 bg-white dark:bg-gray-700 rounded text-blue-600 dark:text-blue-400">{config.api_key || t('notConfigured')}</code>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-gray-600 dark:text-gray-400">{t('configModal.status')}:</span>
                  {config.connected ? (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-green-100 text-green-700 rounded-full text-xs">
                      <CheckCircle className="w-3 h-3" />
                      {t('configModal.connected')}
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-red-100 text-red-700 rounded-full text-xs">
                      <XCircle className="w-3 h-3" />
                      {t('configModal.notConnected')}
                    </span>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* API URL */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              <div className="flex items-center gap-2">
                <Globe className="w-4 h-4" />
                {t('configModal.apiUrl')}
              </div>
            </label>
            <input
              type="url"
              value={formData.difyApiUrl}
              onChange={(e) => setFormData(prev => ({ ...prev, difyApiUrl: e.target.value }))}
              placeholder={t('configModal.apiUrlPlaceholder')}
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
              required
            />
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              {t('configModal.apiUrlHelp')}
            </p>
          </div>

          {/* API Key */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              <div className="flex items-center gap-2">
                <Key className="w-4 h-4" />
                {t('configModal.apiKey')}
              </div>
            </label>
            <div className="relative">
              <input
                type={showApiKey ? "text" : "password"}
                value={formData.difyApiKey}
                onChange={(e) => setFormData(prev => ({ ...prev, difyApiKey: e.target.value }))}
                placeholder={t('configModal.apiKeyPlaceholder')}
                className="w-full px-4 py-2 pr-20 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
              />
              <button
                type="button"
                onClick={() => setShowApiKey(!showApiKey)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
              >
                {showApiKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              {t('configModal.apiKeyHelp')}
            </p>
            {config && config.api_key && (
              <p className="mt-1 text-xs text-green-600 dark:text-green-400">
                {t('configModal.currentKey', { key: config.api_key })}
              </p>
            )}
          </div>

          {/* Workspace ID */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              {t('configModal.workspaceId')}
            </label>
            <input
              type="text"
              value={formData.difyWorkspaceId}
              onChange={(e) => setFormData(prev => ({ ...prev, difyWorkspaceId: e.target.value }))}
              placeholder={t('configModal.workspaceIdPlaceholder')}
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
            />
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              {t('configModal.workspaceIdHelp')}
            </p>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <button
              type="submit"
              disabled={saving}
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Download className="w-4 h-4" />
              {saving ? t('savingConfig') : t('saveConfig')}
            </button>
            <button
              type="button"
              onClick={handleTest}
              disabled={testing}
              className="inline-flex items-center gap-2 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${testing ? "animate-spin" : ""}`} />
              {testing ? t('testingConnection') : t('testConnection')}
            </button>
          </div>
        </form>

        {/* Footer */}
        <div className="p-6 border-t border-gray-200 dark:border-gray-700 flex justify-end">
          <button
            type="button"
            onClick={() => {
              onClose();
              setConfigError(null);
              setConfigSuccess(null);
            }}
            className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          >
            {t('cancel')}
          </button>
        </div>
      </div>
    </div>
  );
}
