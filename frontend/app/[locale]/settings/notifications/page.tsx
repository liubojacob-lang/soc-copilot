"use client";

import { useState, useEffect } from "react";
import { useRouter } from "@/i18n/navigation";
import { useTranslations, useLocale } from "next-intl";
import { loadAuthState, authFetchJSON, isAdmin } from "@/lib/auth";
import { PageHeader } from "@/components/common/PageHeader";
import {
  Bell,
  MessageSquare,
  Mail,
  Send,
  CheckCircle,
  XCircle,
  Loader2,
  AlertCircle,
  ExternalLink,
} from "lucide-react";

interface ChannelStatus {
  feishu: boolean;
  slack: boolean;
  email: boolean;
}

interface TestResult {
  channel: string;
  success: boolean;
  message: string;
}

interface QueueStats {
  critical?: { length?: number; pending?: number };
  high?: { length?: number; pending?: number };
  medium?: { length?: number; pending?: number };
  low?: { length?: number; pending?: number };
}

interface NotificationHealth {
  redis: boolean;
  streams: boolean;
  channels: Record<string, boolean>;
  error?: string;
}

export default function NotificationSettingsPage() {
  const router = useRouter();
  const locale = useLocale();
  const t = useTranslations("notificationSettings");
  const [channels, setChannels] = useState<ChannelStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [testing, setTesting] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [queueStats, setQueueStats] = useState<QueueStats | null>(null);
  const [health, setHealth] = useState<NotificationHealth | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    const authState = loadAuthState();
    if (!authState?.isAuthenticated) {
      router.push("/login");
      return;
    }
    if (!isAdmin(authState.user)) {
      router.push("/");
      return;
    }
    fetchData();
  }, [router]);

  const fetchData = async () => {
    try {
      const [channelsData, queueData, healthData] = await Promise.all([
        authFetchJSON<ChannelStatus>("/api/v1/notifications/channels").catch(() => null),
        authFetchJSON<QueueStats>("/api/v1/notifications/queue/stats").catch(() => null),
        authFetchJSON<NotificationHealth>("/api/v1/notifications/health").catch(() => null),
      ]);
      setChannels(channelsData);
      setQueueStats(queueData);
      setHealth(healthData);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t("failedToLoad"));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const refreshData = async () => {
    setRefreshing(true);
    await fetchData();
  };

  const testChannel = async (channel: string) => {
    setTesting(channel);
    setTestResult(null);
    try {
      const result = await authFetchJSON<TestResult>(`/api/v1/notifications/test`, {
        method: "POST",
        body: JSON.stringify({ channels: [channel] }),
      });
      setTestResult(result);
    } catch (err: unknown) {
      setTestResult({
        channel,
        success: false,
        message: err instanceof Error ? err.message : "Test failed",
      });
    } finally {
      setTesting(null);
    }
  };

  const testAllChannels = async () => {
    setTesting("all");
    setTestResult(null);
    try {
      const result = await authFetchJSON<Record<string, boolean>>("/api/v1/notifications/test", {
        method: "POST",
      });
      const allSuccess = Object.values(result).every((v) => v);
      setTestResult({
        channel: "all",
        success: allSuccess,
        message: allSuccess ? "All notifications sent successfully" : "Some notifications failed",
      });
    } catch (err: unknown) {
      setTestResult({
        channel: "all",
        success: false,
        message: err instanceof Error ? err.message : "Test failed",
      });
    } finally {
      setTesting(null);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-surface-ground">
        <PageHeader title={t("title")} subtitle={t("subtitle")} />
        <main className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-text-tertiary" />
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-surface-ground">
      <PageHeader title={t("title")} subtitle={t("subtitle")} />

      <main className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {error && (
          <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
          </div>
        )}

        {testResult && (
          <div
            className={`mb-6 p-4 rounded-lg border ${testResult.success ? "bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800" : "bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800"}`}
          >
            <p
              className={`text-sm ${testResult.success ? "text-green-700 dark:text-green-400" : "text-red-600 dark:text-red-400"}`}
            >
              {testResult.success ? (
                <CheckCircle className="w-4 h-4 inline mr-2" />
              ) : (
                <XCircle className="w-4 h-4 inline mr-2" />
              )}
              {testResult.message}
            </p>
          </div>
        )}

        {/* Test All Button */}
        <div className="mb-6 flex justify-between items-center">
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Notification Runtime Status
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={refreshData}
              disabled={refreshing}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 flex items-center gap-2"
            >
              {refreshing ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Bell className="w-4 h-4" />
              )}
              Refresh
            </button>
            <button
              onClick={testAllChannels}
              disabled={testing !== null}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
            >
              {testing === "all" ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
              {t("testAll")}
            </button>
          </div>
        </div>

        {/* Queue Stats */}
        <div className="mb-6 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Queue Stats</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            {(["critical", "high", "medium", "low"] as const).map((level) => (
              <div key={level} className="p-3 rounded border border-gray-200 dark:border-gray-700">
                <div className="font-medium capitalize text-gray-700 dark:text-gray-200">
                  {level}
                </div>
                <div className="text-gray-500 dark:text-gray-400">
                  pending: {queueStats?.[level]?.pending ?? 0}
                </div>
                <div className="text-gray-500 dark:text-gray-400">
                  length: {queueStats?.[level]?.length ?? 0}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Health */}
        <div className="mb-6 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
            {t("serviceHealth")}
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
            <HealthCell label={t("redis")} healthy={!!health?.redis} />
            <HealthCell label={t("streams")} healthy={!!health?.streams} />
            <HealthCell
              label={t("channelsConfigured")}
              healthy={!!health?.channels && Object.values(health.channels).some(Boolean)}
            />
          </div>
          {health?.error && (
            <p className="mt-3 text-sm text-red-600 dark:text-red-400">{health.error}</p>
          )}
        </div>

        {/* Notification Channels */}
        <div className="space-y-4">
          {/* Feishu */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
                  <MessageSquare className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                </div>
                <div>
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                    {t("feishu")}
                  </h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400">{t("feishuDesc")}</p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                {channels?.feishu ? (
                  <span className="flex items-center gap-1 text-green-700 dark:text-green-400">
                    <CheckCircle className="w-5 h-5" />
                    {t("configured")}
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-text-tertiary">
                    <XCircle className="w-5 h-5" />
                    {t("notConfigured")}
                  </span>
                )}
                <button
                  onClick={() => testChannel("feishu")}
                  disabled={testing !== null || !channels?.feishu}
                  className="px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 flex items-center gap-2"
                >
                  {testing === "feishu" ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Send className="w-4 h-4" />
                  )}
                  {t("test")}
                </button>
              </div>
            </div>
          </div>

          {/* Slack */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center">
                  <MessageSquare className="w-6 h-6 text-purple-600 dark:text-purple-400" />
                </div>
                <div>
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                    {t("slack")}
                  </h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400">{t("slackDesc")}</p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                {channels?.slack ? (
                  <span className="flex items-center gap-1 text-green-700 dark:text-green-400">
                    <CheckCircle className="w-5 h-5" />
                    {t("configured")}
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-text-tertiary">
                    <XCircle className="w-5 h-5" />
                    {t("notConfigured")}
                  </span>
                )}
                <button
                  onClick={() => testChannel("slack")}
                  disabled={testing !== null || !channels?.slack}
                  className="px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 flex items-center gap-2"
                >
                  {testing === "slack" ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Send className="w-4 h-4" />
                  )}
                  {t("test")}
                </button>
              </div>
            </div>
          </div>

          {/* Email */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center">
                  <Mail className="w-6 h-6 text-green-700 dark:text-green-400" />
                </div>
                <div>
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                    {t("email")}
                  </h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400">{t("emailDesc")}</p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                {channels?.email ? (
                  <span className="flex items-center gap-1 text-green-700 dark:text-green-400">
                    <CheckCircle className="w-5 h-5" />
                    {t("configured")}
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-text-tertiary">
                    <XCircle className="w-5 h-5" />
                    {t("notConfigured")}
                  </span>
                )}
                <button
                  onClick={() => testChannel("email")}
                  disabled={testing !== null || !channels?.email}
                  className="px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 flex items-center gap-2"
                >
                  {testing === "email" ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Send className="w-4 h-4" />
                  )}
                  {t("test")}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Info Box */}
        <div className="mt-8 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-blue-600 dark:text-blue-400 mt-0.5" />
            <div>
              <h4 className="text-sm font-medium text-blue-800 dark:text-blue-300">
                {t("configInfoTitle")}
              </h4>
              <p className="text-sm text-blue-700 dark:text-blue-400 mt-1">{t("configInfoDesc")}</p>
              <div className="mt-2 text-xs text-blue-700 dark:text-blue-400 space-y-1">
                <p>
                  •{" "}
                  <code className="bg-blue-100 dark:bg-blue-900/50 px-1 rounded">
                    FEISHU_WEBHOOK_URL
                  </code>
                </p>
                <p>
                  •{" "}
                  <code className="bg-blue-100 dark:bg-blue-900/50 px-1 rounded">
                    SLACK_WEBHOOK_URL
                  </code>
                </p>
                <p>
                  •{" "}
                  <code className="bg-blue-100 dark:bg-blue-900/50 px-1 rounded">
                    ALERT_EMAIL_TO
                  </code>
                </p>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

function HealthCell({ label, healthy }: { label: string; healthy: boolean }) {
  return (
    <div className="p-3 rounded border border-gray-200 dark:border-gray-700 flex items-center justify-between">
      <span className="text-gray-700 dark:text-gray-300">{label}</span>
      {healthy ? (
        <span className="text-green-700 dark:text-green-400 flex items-center gap-1">
          <CheckCircle className="w-4 h-4" />
          OK
        </span>
      ) : (
        <span className="text-red-600 dark:text-red-400 flex items-center gap-1">
          <XCircle className="w-4 h-4" />
          Down
        </span>
      )}
    </div>
  );
}
