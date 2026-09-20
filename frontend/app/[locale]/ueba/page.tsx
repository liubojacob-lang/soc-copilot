"use client";

import { useState, useEffect } from "react";
import { useRouter } from "@/i18n/navigation";
import { useFormatter, useTranslations, useLocale } from "next-intl";
import { api } from "@/lib/api";
import { loadAuthState } from "@/lib/auth";
import { PageHeader } from "@/components/common/PageHeader";
import { ErrorDisplay } from "@/components/common/ErrorDisplay";
import { Users, AlertTriangle, TrendingUp, Shield, Activity } from "lucide-react";

interface UEBADashboard {
  total_users: number;
  high_risk_count: number;
  anomaly_count_24h: number;
  avg_risk_score: number;
  top_risk_factors: Array<{ factor: string; count: number }>;
  recent_anomalies: Array<{
    username: string;
    user: string;
    type: string;
    severity: string;
    timestamp: string;
    detected_at: string;
    description: string;
  }>;
  summary: {
    total_users_monitored: number;
    high_risk_users: number;
    anomalies_detected_24h: number;
    critical_alerts: number;
  };
}

interface UEBARiskUser {
  username: string;
  risk_score: number;
  risk_level: string;
  department: string;
  last_activity: string;
  anomalies: number;
  anomaly_count: number;
}

export default function UEBAPage() {
  const router = useRouter();
  const locale = useLocale();
  const t = useTranslations("uebaPage");
  const format = useFormatter();
  const tCommon = useTranslations("common");
  const tRiskFactors = useTranslations("uebaPage.riskFactors");
  const tRiskLevel = useTranslations("uebaPage.riskLevel");
  const [mounted, setMounted] = useState(false);
  const [dashboard, setDashboard] = useState<UEBADashboard | null>(null);
  const [loadError, setLoadError] = useState<Error | null>(null);
  const [highRiskUsers, setHighRiskUsers] = useState<UEBARiskUser[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setMounted(true);
    loadDashboard();
    loadHighRiskUsers();
  }, []);

  const loadDashboard = async () => {
    try {
      const response = await api.get("/api/ueba/dashboard");
      setDashboard(response as UEBADashboard);
      setLoadError(null);
    } catch (e) {
      console.error("Failed to load dashboard:", e);
      setLoadError(e instanceof Error ? e : new Error(String(e)));
    }
  };

  const loadHighRiskUsers = async () => {
    try {
      const response = await api.get("/api/ueba/high-risk-users?limit=10");
      setHighRiskUsers((response as { users: UEBARiskUser[] }).users || []);
    } catch (e) {
      console.error("Failed to load high risk users:", e);
    } finally {
      setLoading(false);
    }
  };

  /**
   * 风险分档样式 —— 单一数据源。
   *
   * ⚠️ 文字色与底色**分开定义**，不要再用 `getRiskColor(score).split(" ")[0]`
   * 去取文字色：那只拿到第一个 token（浅色值），`dark:text-*` 会被一起丢掉。
   * 在硬编码的 `dark:bg-gray-700` 卡片上，浅色的 `text-red-700` 实测只有 1.59:1。
   *
   * 浅色值按最不利底色校准（黄档要 600，绿档同）—— 不要为了"整齐"统一成 600，
   * 它们贴在各自的 `bg-*-50` 上，同色系浅底比白底更难达标。
   */
  const RISK_TIERS = [
    { min: 80, text: "text-red-700 dark:text-red-300", bg: "bg-red-50 dark:bg-red-900/30" },
    {
      min: 60,
      text: "text-orange-700 dark:text-orange-300",
      bg: "bg-orange-50 dark:bg-orange-900/30",
    },
    {
      min: 30,
      text: "text-yellow-600 dark:text-yellow-300",
      bg: "bg-yellow-50 dark:bg-yellow-900/30",
    },
    { min: 0, text: "text-green-600 dark:text-green-300", bg: "bg-green-50 dark:bg-green-900/30" },
  ];
  const riskTier = (score: number) =>
    RISK_TIERS.find((t) => score >= t.min) ?? RISK_TIERS[RISK_TIERS.length - 1];
  const getRiskTextColor = (score: number) => riskTier(score).text;
  const getRiskColor = (score: number) => `${riskTier(score).text} ${riskTier(score).bg}`;

  if (!mounted) return null;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <PageHeader title={t("title")} subtitle={t("subtitle")} />

      <main className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {loadError && <ErrorDisplay error={loadError} onRetry={loadDashboard} compact />}

        {/* Stats Cards */}
        {dashboard && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400">{t("monitoredUsers")}</p>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {dashboard.summary.total_users_monitored}
                  </p>
                </div>
                <Users className="w-8 h-8 text-blue-500" />
              </div>
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400">{t("highRiskUsers")}</p>
                  <p className="text-2xl font-bold text-red-600">
                    {dashboard.summary.high_risk_users}
                  </p>
                </div>
                <AlertTriangle className="w-8 h-8 text-red-500" />
              </div>
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400">{t("anomalies24h")}</p>
                  <p className="text-2xl font-bold text-orange-600">
                    {dashboard.summary.anomalies_detected_24h}
                  </p>
                </div>
                <Activity className="w-8 h-8 text-orange-500" />
              </div>
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400">{t("criticalAlerts")}</p>
                  <p className="text-2xl font-bold text-red-600">
                    {dashboard.summary.critical_alerts}
                  </p>
                </div>
                <Shield className="w-8 h-8 text-red-500" />
              </div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* High Risk Users */}
          <div className="lg:col-span-2">
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
              <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5 text-red-500" />
                  {t("highRiskUsersSection")}
                </h2>
              </div>
              <div className="p-4">
                {loading ? (
                  <div className="text-center py-8 text-text-tertiary dark:text-text-muted">
                    {tCommon("loading")}
                  </div>
                ) : highRiskUsers.length === 0 ? (
                  <div className="text-center py-8 text-text-tertiary dark:text-text-muted">
                    {t("noHighRiskUsers")}
                  </div>
                ) : (
                  <div className="space-y-3">
                    {highRiskUsers.map((user, index) => (
                      <div
                        key={index}
                        className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700 rounded-lg"
                      >
                        <div className="flex items-center gap-4">
                          <div className="w-10 h-10 rounded-full bg-gray-300 dark:bg-gray-600 flex items-center justify-center">
                            <span className="text-gray-600 dark:text-gray-300 font-semibold">
                              {user.username.charAt(0).toUpperCase()}
                            </span>
                          </div>
                          <div>
                            <p className="font-medium text-gray-900 dark:text-white">
                              {user.username}
                            </p>
                            <p className="text-sm text-text-tertiary dark:text-gray-300">
                              {t("anomalousBehaviors", { count: user.anomaly_count })}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-4">
                          <div className="text-right">
                            <p className={`text-lg font-bold ${getRiskTextColor(user.risk_score)}`}>
                              {user.risk_score.toFixed(1)}
                            </p>
                            <p className="text-xs text-text-tertiary dark:text-gray-300">
                              {t("riskScore")}
                            </p>
                          </div>
                          <span
                            className={`px-3 py-1 rounded-full text-sm font-medium ${getRiskColor(user.risk_score)}`}
                          >
                            {user.risk_level === "high"
                              ? tRiskLevel("high")
                              : user.risk_level === "medium"
                                ? tRiskLevel("medium")
                                : tRiskLevel("low")}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Top Risk Factors */}
            {dashboard && (
              <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4">
                <h3 className="font-semibold text-gray-900 dark:text-white mb-4">
                  {t("topRiskFactors")}
                </h3>
                <div className="space-y-3">
                  {dashboard.top_risk_factors.map((factor, index) => (
                    <div key={index} className="flex items-center justify-between">
                      <span className="text-sm text-gray-600 dark:text-gray-400">
                        {factor.factor === "off_hours_login"
                          ? t("offHoursLogin")
                          : factor.factor === "unusual_data_access"
                            ? tRiskFactors("unusualDataAccess")
                            : factor.factor === "geolocation_anomaly"
                              ? tRiskFactors("geolocationAnomaly")
                              : factor.factor}
                      </span>
                      <span className="text-sm font-medium text-gray-900 dark:text-white">
                        {factor.count} {t("times")}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Recent Anomalies */}
            {dashboard && dashboard.recent_anomalies.length > 0 && (
              <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4">
                <h3 className="font-semibold text-gray-900 dark:text-white mb-4">
                  {t("recentAnomalies")}
                </h3>
                <div className="space-y-3">
                  {dashboard.recent_anomalies.map((anomaly, index) => (
                    <div
                      key={index}
                      className="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800"
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <AlertTriangle className="w-4 h-4 text-red-500" />
                        <span className="font-medium text-red-900 dark:text-red-100">
                          {anomaly.username}
                        </span>
                      </div>
                      <p className="text-sm text-red-700 dark:text-red-300">
                        {anomaly.type === "off_hours_login" ? t("offHoursLogin") : anomaly.type}
                      </p>
                      <p className="text-xs text-red-700 dark:text-red-400 mt-1">
                        {format.dateTime(new Date(anomaly.detected_at), {
                          dateStyle: "medium",
                          timeStyle: "medium",
                        })}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* ML Info */}
            <div className="bg-gradient-to-br from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20 rounded-xl p-4 border border-purple-200 dark:border-purple-800">
              <h4 className="font-medium text-purple-900 dark:text-purple-100 mb-2 flex items-center gap-2">
                <TrendingUp className="w-4 h-4" />
                {t("mlPowered.title")}
              </h4>
              <p className="text-sm text-purple-800 dark:text-purple-200">
                {t("mlPowered.description")}
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
