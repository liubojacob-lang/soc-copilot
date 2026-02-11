"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { loadAuthState } from "@/lib/auth";
import Navigation from "@/components/Navigation";
import { 
  Search, 
  Target, 
  Play, 
  FileText,
  Shield,
  Clock,
  CheckCircle,
  AlertTriangle,
  Download
} from "lucide-react";

export default function ThreatHuntingPage() {
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
  const [hypotheses, setHypotheses] = useState<any[]>([]);
  const [results, setResults] = useState<any[]>([]);
  const [dashboard, setDashboard] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [executing, setExecuting] = useState<string | null>(null);

  useEffect(() => {
    setMounted(true);
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [hypRes, resultRes, dashRes] = await Promise.all([
        api.get("/api/threat-hunting/hypotheses"),
        api.get("/api/threat-hunting/results?limit=10"),
        api.get("/api/threat-hunting/dashboard")
      ]);
      
      setHypotheses(hypRes.data);
      setResults(resultRes.data);
      setDashboard(dashRes.data);
    } catch (e) {
      console.error("Failed to load data:", e);
    } finally {
      setLoading(false);
    }
  };

  const executeHunt = async (hypothesisId: string) => {
    setExecuting(hypothesisId);
    try {
      await api.post("/api/threat-hunting/execute", {
        hypothesis_id: hypothesisId,
        time_range_hours: 24
      });
      // Reload results
      const resultRes = await api.get("/api/threat-hunting/results?limit=10");
      setResults(resultRes.data);
    } catch (e) {
      console.error("Failed to execute hunt:", e);
    } finally {
      setExecuting(null);
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "critical": return "text-red-600 bg-red-50";
      case "high": return "text-orange-600 bg-orange-50";
      case "medium": return "text-yellow-600 bg-yellow-50";
      default: return "text-blue-600 bg-blue-50";
    }
  };

  if (!mounted) return null;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Navigation />
      
      <main className="pt-16 pb-8">
        <div className="max-w-7xl mx-auto px-4">
          {/* Header */}
          <div className="mb-8">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-gradient-to-br from-green-500 to-teal-600 rounded-xl">
                <Target className="w-8 h-8 text-white" />
              </div>
              <div>
                <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                  威胁狩猎
                </h1>
                <p className="text-gray-600 dark:text-gray-400">
                  Proactive Threat Hunting - 主动发现并应对威胁
                </p>
              </div>
            </div>
          </div>

          {/* Stats */}
          {dashboard && (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
              <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
                <p className="text-sm text-gray-600 dark:text-gray-400">总狩猎次数</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {dashboard.summary.total_hunts_executed}
                </p>
              </div>
              <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
                <p className="text-sm text-gray-600 dark:text-gray-400">发现威胁</p>
                <p className="text-2xl font-bold text-green-600">
                  {dashboard.summary.total_findings}
                </p>
              </div>
              <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
                <p className="text-sm text-gray-600 dark:text-gray-400">严重发现</p>
                <p className="text-2xl font-bold text-red-600">
                  {dashboard.summary.critical_findings}
                </p>
              </div>
              <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
                <p className="text-sm text-gray-600 dark:text-gray-400">成功率</p>
                <p className="text-2xl font-bold text-blue-600">
                  {dashboard.hunt_effectiveness.success_rate}
                </p>
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Hunt Hypotheses */}
            <div className="lg:col-span-2">
              <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
                <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                  <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                    <Shield className="w-5 h-5 text-green-500" />
                    狩猎假设库 (MITRE ATT&CK)
                  </h2>
                </div>
                <div className="p-4">
                  {loading ? (
                    <div className="text-center py-8 text-gray-500">加载中...</div>
                  ) : (
                    <div className="space-y-4">
                      {hypotheses.map((hypothesis) => (
                        <div 
                          key={hypothesis.id}
                          className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:shadow-md transition-shadow"
                        >
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-2">
                                <h3 className="font-semibold text-gray-900 dark:text-white">
                                  {hypothesis.name}
                                </h3>
                                <span className={`px-2 py-0.5 rounded text-xs font-medium ${getSeverityColor(hypothesis.severity)}`}>
                                  {hypothesis.severity === 'critical' ? '严重' : 
                                   hypothesis.severity === 'high' ? '高危' : 
                                   hypothesis.severity === 'medium' ? '中危' : '低危'}
                                </span>
                                {hypothesis.verified && (
                                  <CheckCircle className="w-4 h-4 text-green-500" />
                                )}
                              </div>
                              <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                                {hypothesis.description}
                              </p>
                              <div className="flex items-center gap-4 text-xs text-gray-500">
                                <span>MITRE: {hypothesis.mitre_techniques.join(", ")}</span>
                                <span>数据源: {hypothesis.data_sources.join(", ")}</span>
                              </div>
                            </div>
                            <button
                              onClick={() => executeHunt(hypothesis.id)}
                              disabled={executing === hypothesis.id}
                              className="ml-4 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 flex items-center gap-2"
                            >
                              {executing === hypothesis.id ? (
                                <>
                                  <Clock className="w-4 h-4 animate-spin" />
                                  执行中...
                                </>
                              ) : (
                                <>
                                  <Play className="w-4 h-4" />
                                  执行
                                </>
                              )}
                            </button>
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
              {/* Recent Results */}
              <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
                <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                  <h3 className="font-semibold text-gray-900 dark:text-white">
                    最近狩猎结果
                  </h3>
                </div>
                <div className="p-4">
                  {results.slice(0, 5).map((result, index) => (
                    <div 
                      key={index}
                      className="flex items-center justify-between py-3 border-b border-gray-100 dark:border-gray-700 last:border-0"
                    >
                      <div>
                        <p className="font-medium text-gray-900 dark:text-white text-sm">
                          {result.hunt_name}
                        </p>
                        <p className="text-xs text-gray-500">
                          {new Date(result.started_at).toLocaleString()}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        {result.findings_count > 0 ? (
                          <span className="px-2 py-1 bg-red-100 text-red-600 rounded text-xs">
                            {result.findings_count} 发现
                          </span>
                        ) : (
                          <span className="px-2 py-1 bg-green-100 text-green-600 rounded text-xs">
                            正常
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Top MITRE Techniques */}
              {dashboard && (
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4">
                  <h3 className="font-semibold text-gray-900 dark:text-white mb-4">
                    常用技术 (MITRE)
                  </h3>
                  <div className="space-y-3">
                    {dashboard.top_mitre_techniques.map((tech: any, index: number) => (
                      <div key={index} className="flex items-center justify-between">
                        <div>
                          <p className="text-sm font-medium text-gray-900 dark:text-white">
                            {tech.technique}
                          </p>
                          <p className="text-xs text-gray-500">{tech.name}</p>
                        </div>
                        <span className="text-sm text-gray-600">
                          {tech.count} 次
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* IOC Hunt */}
              <div className="bg-gradient-to-br from-green-50 to-teal-50 dark:from-green-900/20 dark:to-teal-900/20 rounded-xl p-4 border border-green-200 dark:border-green-800">
                <h4 className="font-medium text-green-900 dark:text-green-100 mb-2 flex items-center gap-2">
                  <Search className="w-4 h-4" />
                  IOC 狩猎
                </h4>
                <p className="text-sm text-green-800 dark:text-green-200 mb-3">
                  在历史数据中搜索已知的 IOC（IP、域名、哈希值）
                </p>
                <button 
                  onClick={() => alert("IOC狩猎功能开发中...")}
                  className="w-full py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm"
                >
                  开始 IOC 狩猎
                </button>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
