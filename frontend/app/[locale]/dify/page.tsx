"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from 'next-intl';
import { loadAuthState } from "@/lib/auth";
import Navigation from "@/components/Navigation";
import { DifyConfigModal, DifyWorkflowList, ManualImportModal } from './components';
import { useDifyWorkflows } from './hooks/useDifyWorkflows';
import { RefreshCw, Plus, Settings, Zap, CheckCircle, XCircle, ExternalLink } from 'lucide-react';
import type { DifyConfigForm } from './types';

export default function DifyIntegrationPage() {
  const router = useRouter();
  const t = useTranslations('difyPage');
  const [mounted, setMounted] = useState(false);

  // UI state
  const [refreshing, setRefreshing] = useState(false);
  const [importing, setImporting] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [showManualImport, setShowManualImport] = useState(false);
  const [manualImporting, setManualImporting] = useState(false);

  // Use custom hook
  const {
    workflows,
    config,
    loading,
    error,
    loadData,
    importWorkflow,
    deleteWorkflow
  } = useDifyWorkflows();

  useEffect(() => {
    setMounted(true);
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadData();
    setRefreshing(false);
  };

  const handleImport = async (workflow: any) => {
    setImporting(workflow.id);
    try {
      await importWorkflow(workflow);
    } finally {
      setImporting(null);
    }
  };

  const handleDelete = async (workflow: any) => {
    if (!confirm(t('modal.deleteConfirm', { name: workflow.name }))) {
      return;
    }
    setDeleting(workflow.id);
    try {
      await deleteWorkflow(workflow);
    } finally {
      setDeleting(null);
    }
  };

  const handleManualImport = async (appId: string) => {
    setManualImporting(true);
    try {
      const token = localStorage.getItem("access_token");
      const response = await fetch(`/api/dify/workflows/${appId.trim()}/import`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Import failed");
      }

      const result = await response.json();
      setShowManualImport(false);
      router.push(`/playbooks/definitions/${result.definition_id}`);
    } catch (e: unknown) {
      console.error(e);
    } finally {
      setManualImporting(false);
    }
  };

  const handleSaveConfig = async (formData: DifyConfigForm) => {
    const token = localStorage.getItem("access_token");
    const response = await fetch("/api/admin/settings", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({
        dify_api_url: formData.difyApiUrl,
        dify_api_key: formData.difyApiKey,
        dify_workspace_id: formData.difyWorkspaceId,
      }),
    });

    if (!response.ok) {
      let errorMessage = "Failed to save settings";
      try {
        const err = await response.json();
        errorMessage = err.detail || errorMessage;
      } catch {
        const text = await response.text();
        errorMessage = text || `HTTP ${response.status}: ${response.statusText}`;
      }
      throw new Error(errorMessage);
    }

    await loadData();
  };

  const handleTestConnection = async () => {
    const token = localStorage.getItem("access_token");
    const response = await fetch("/api/dify/test-connection", {
      method: "GET",
      headers: { "Authorization": `Bearer ${token}` }
    });

    if (!response.ok) {
      let errorMessage = "Failed to test connection";
      try {
        const err = await response.json();
        errorMessage = err.detail || errorMessage;
      } catch {
        const text = await response.text();
        errorMessage = text || `HTTP ${response.status}: ${response.statusText}`;
      }
      throw new Error(errorMessage);
    }

    const data = await response.json();
    if (!data.connected) {
      throw new Error("Could not connect to Dify. Please check your configuration.");
    }

    await loadData();
  };

  if (!mounted) return null;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Navigation title={t('title')} subtitle={t('subtitle')} />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 mb-6">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                <Zap className="w-6 h-6 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{t('header')}</h1>
                <p className="text-gray-600 dark:text-gray-400 mt-1">
                  {t('description')}
                </p>
              </div>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => setShowManualImport(true)}
                className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
              >
                <Plus className="w-4 h-4" />
                {t('importById')}
              </button>
              <button
                onClick={() => setShowConfigModal(true)}
                className="flex items-center gap-2 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              >
                <Settings className="w-4 h-4" />
                {t('config')}
              </button>
              <button
                onClick={handleRefresh}
                disabled={refreshing}
                className="flex items-center gap-2 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} />
                {t('refresh')}
              </button>
            </div>
          </div>

          {/* Connection Status */}
          {config && (
            <div className="mt-4 flex items-center gap-6">
              <div className="flex items-center gap-2">
                {config.connected ? (
                  <>
                    <CheckCircle className="w-5 h-5 text-green-500" />
                    <span className="text-sm text-gray-700 dark:text-gray-300">
                      {t('connected')}
                    </span>
                  </>
                ) : (
                  <>
                    <XCircle className="w-5 h-5 text-red-500" />
                    <span className="text-sm text-gray-700 dark:text-gray-300">
                      {t('notConnected')}
                    </span>
                  </>
                )}
              </div>
              <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                <ExternalLink className="w-4 h-4" />
                <a href="https://dify.ai" target="_blank" rel="noopener noreferrer" className="hover:underline">
                  {t('whatIsDify')}
                </a>
              </div>
            </div>
          )}
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 px-4 py-3 rounded-lg mb-6">
            {error}
          </div>
        )}

        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
            <p className="mt-4 text-gray-600 dark:text-gray-400">{t('loading')}</p>
          </div>
        ) : workflows.length === 0 ? (
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-12 text-center">
            <div className="max-w-md mx-auto">
              <div className="w-16 h-16 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-4">
                <Zap className="w-8 h-8 text-gray-400" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                {t('noWorkflows')}
              </h3>
              <p className="text-gray-600 dark:text-gray-400 mb-6">
                {!config?.configured
                  ? t('notConfigured')
                  : t('noWorkspaces')}
              </p>
              <button
                onClick={() => setShowConfigModal(true)}
                className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                <Settings className="w-4 h-4" />
                {t('configure')}
              </button>
            </div>
          </div>
        ) : (
          <DifyWorkflowList
            workflows={workflows}
            importing={importing}
            deleting={deleting}
            onImport={handleImport}
            onDelete={handleDelete}
            t={t}
          />
        )}

        {/* Quick Start Guide */}
        <div className="mt-8 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-blue-900 dark:text-blue-100 mb-3">
            {t('quickStart.title')}
          </h3>
          <div className="space-y-3 text-sm text-blue-800 dark:text-blue-200">
            <p dangerouslySetInnerHTML={{ __html: t.raw('quickStart.step1') }} />
            <p dangerouslySetInnerHTML={{ __html: t.raw('quickStart.step2') }} />
            <p dangerouslySetInnerHTML={{ __html: t.raw('quickStart.step3') }} />
            <p dangerouslySetInnerHTML={{ __html: t.raw('quickStart.step4') }} />
          </div>
        </div>
      </main>

      {/* Modals */}
      <ManualImportModal
        show={showManualImport}
        importing={manualImporting}
        onImport={handleManualImport}
        onClose={() => setShowManualImport(false)}
        t={t}
      />

      <DifyConfigModal
        show={showConfigModal}
        config={config}
        onClose={() => setShowConfigModal(false)}
        onSave={handleSaveConfig}
        onTest={handleTestConnection}
        t={t}
      />
    </div>
  );
}
