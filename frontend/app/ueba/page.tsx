"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { loadAuthState } from "@/lib/auth";
import Navigation from "@/components/Navigation";
import { 
  Users, 
  AlertTriangle, 
  TrendingUp, 
  Shield,
  Activity
} from "lucide-react";

export default function UEBAPage() {
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
  const [dashboard, setDashboard] = useState<any>(null);
  const [highRiskUsers, setHighRiskUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setMounted(true);
    loadDashboard();
    loadHighRiskUsers();
  }, []);

  const loadDashboard = async () => {
    try {
      const response = await api.get("/api/ueba/dashboard");
      setDashboard(response.data);
    } catch (e) {
      console.error("Failed to load dashboard:", e);
    }
  };

  const loadHighRiskUsers = async () => {
    try {
      const response = await api.get("/api/ueba/high-risk-users?limit=10");
      setHighRiskUsers(response.data.users || []);
    } catch (e) {
      console.error("Failed to load high risk users:", e);
    } finally {
      setLoading(false);
    }
  };

  const getRiskColor = (score: number) => {
    if (score >= 80) return "text-red-600 bg-red-50";
    if (score >= 60) return "text-orange-600 bg-orange-50";
    if (score >= 30) return "text-yellow-600 bg-yellow-50";
    return "text-green-600 bg-green-50";
  };

  if (!mounted) return null;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Navigation title="UEBA" />
      
      <main className="pt-16 pb-8">
        <div className="max-w-7xl mx-auto px-4">
          {/* Header */}
          <div className="mb-8">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-gradient-to-br from-purple-500 to-pink-600 rounded-xl">
                <Users className="w-8 h-8 text-white" />
              </div>
              <div>
                <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                  UEBA
                </h1>
                <p className="text-gray-600 dark:text-gray-400">
                  User and Entity Behavior Analytics - Detect insider threats and anomalous behavior
                </p>
              </div>
            </div>
          </div>

          {/* Stats Cards */}
          {dashboard && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
              <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600 dark:text-gray-400">Monitored Users</p>
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
                    <p className="text-sm text-gray-600 dark:text-gray-400">High Risk Users</p>
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
                    <p className="text-sm text-gray-600 dark:text-gray-400">24h Anomalies</p>
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
                    <p className="text-sm text-gray-600 dark:text-gray-400">Critical Alerts</p>
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
                    High Risk Users
                  </h2>
                </div>
                <div className="p-4">
                  {loading ? (
                    <div className="text-center py-8 text-gray-500">Loading...</div>
                  ) : highRiskUsers.length === 0 ? (
                    <div className="text-center py-8 text-gray-500">No high risk users found</div>
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
                              <p className="text-sm text-gray-500 dark:text-gray-400">
                                {user.anomaly_count} anomalous behaviors
                              </p>
                            </div>
                          </div>
                          <div className="flex items-center gap-4">
                            <div className="text-right">
                              <p className={`text-lg font-bold ${getRiskColor(user.risk_score).split(' ')[0]}`}>
                                {user.risk_score.toFixed(1)}
                              </p>
                              <p className="text-xs text-gray-500">Risk Score</p>
                            </div>
                            <span className={`px-3 py-1 rounded-full text-sm font-medium ${getRiskColor(user.risk_score)}`}>
                              {user.risk_level === 'high' ? 'High' : user.risk_level === 'medium' ? 'Medium' : 'Low'}
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
                    Top Risk Factors
                  </h3>
                  <div className="space-y-3">
                    {dashboard.top_risk_factors.map((factor: any, index: number) => (
                      <div key={index} className="flex items-center justify-between">
                        <span className="text-sm text-gray-600 dark:text-gray-400">
                          {factor.factor === 'off_hours_login' ? 'Off-hours Login' :
                           factor.factor === 'unusual_data_access' ? 'Unusual Data Access' :
                           factor.factor === 'geolocation_anomaly' ? 'Geolocation Anomaly' :
                           factor.factor}
                        </span>
                        <span className="text-sm font-medium text-gray-900 dark:text-white">
                          {factor.count} times
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
                    Recent Anomalies
                  </h3>
                  <div className="space-y-3">
                    {dashboard.recent_anomalies.map((anomaly: any, index: number) => (
                      <div key={index} className="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
                        <div className="flex items-center gap-2 mb-1">
                          <AlertTriangle className="w-4 h-4 text-red-500" />
                          <span className="font-medium text-red-900 dark:text-red-100">
                            {anomaly.username}
                          </span>
                        </div>
                        <p className="text-sm text-red-700 dark:text-red-300">
                          {anomaly.type === 'off_hours_login' ? 'Off-hours Login' : anomaly.type}
                        </p>
                        <p className="text-xs text-red-600 dark:text-red-400 mt-1">
                          {new Date(anomaly.detected_at).toLocaleString()}
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
                  ML Powered
                </h4>
                <p className="text-sm text-purple-800 dark:text-purple-200">
                  Using Isolation Forest algorithm to detect anomalous behavior, automatically learning normal patterns and identifying deviations.
                </p>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
