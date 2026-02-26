"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";
import { loadAuthState } from "@/lib/auth";
import Navigation from "@/components/Navigation";
import {
  Cloud,
  Container,
  Shield,
  Server,
  AlertTriangle,
  CheckCircle,
  Scan
} from "lucide-react";

export default function CloudNativePage() {
  const router = useRouter();
  const t = useTranslations('cloudNative');
  const [mounted, setMounted] = useState(false);
  const [dashboard, setDashboard] = useState<any>(null);
  const [connections, setConnections] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);

  useEffect(() => {
    setMounted(true);
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [dashRes, connRes] = await Promise.all([
        api.get("/api/cloud-native/dashboard"),
        api.get("/api/cloud-native/cloud/connections")
      ]);

      setDashboard(dashRes as any);
      setConnections((connRes as any).connections);
    } catch (e) {
      console.error("Failed to load data:", e);
    } finally {
      setLoading(false);
    }
  };

  const scanContainer = async () => {
    setScanning(true);
    try {
      const response = await api.post("/api/cloud-native/containers/scan", {
        image: "nginx",
        tag: "1.21"
      });
      const vulnCount = (response as any).total_vulnerabilities;
      alert(`${t('scanComplete')}\n${t('foundVulnerabilities', { count: vulnCount })}`);
    } catch (e) {
      console.error("Scan failed:", e);
    } finally {
      setScanning(false);
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
      <Navigation title={t('title')} subtitle={t('subtitle')} />
      
      <main className="pt-16 pb-8">
        <div className="max-w-7xl mx-auto px-4">
          {/* Header */}
          <div className="mb-8">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-gradient-to-br from-sky-500 to-blue-600 rounded-xl">
                <Cloud className="w-8 h-8 text-white" />
              </div>
              <div>
                <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                  {t('title')}
                </h1>
                <p className="text-gray-600 dark:text-gray-400">
                  {t('subtitle')}
                </p>
              </div>
            </div>
          </div>

          {/* Stats */}
          {dashboard && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
              <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600 dark:text-gray-400">{t('connectedClusters')}</p>
                    <p className="text-2xl font-bold text-gray-900 dark:text-white">
                      {dashboard.overview.connected_clusters}
                    </p>
                  </div>
                  <Server className="w-8 h-8 text-blue-500" />
                </div>
              </div>

              <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600 dark:text-gray-400">{t('cloudProviders')}</p>
                    <p className="text-2xl font-bold text-blue-600">
                      {dashboard.overview.connected_clouds}
                    </p>
                  </div>
                  <Cloud className="w-8 h-8 text-blue-500" />
                </div>
              </div>

              <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600 dark:text-gray-400">{t('totalContainers')}</p>
                    <p className="text-2xl font-bold text-gray-900 dark:text-white">
                      {dashboard.overview.total_containers}
                    </p>
                  </div>
                  <Container className="w-8 h-8 text-green-500" />
                </div>
              </div>

              <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600 dark:text-gray-400">{t('vulnerableImages')}</p>
                    <p className="text-2xl font-bold text-orange-600">
                      {dashboard.overview.vulnerable_images}
                    </p>
                  </div>
                  <AlertTriangle className="w-8 h-8 text-orange-500" />
                </div>
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Security Summary */}
            <div className="lg:col-span-2">
              {dashboard && (
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 mb-6">
                  <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                    <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                      <Shield className="w-5 h-5 text-blue-500" />
                      {t('securityOverview')}
                    </h2>
                  </div>
                  <div className="p-4">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div className="text-center p-4 bg-red-50 dark:bg-red-900/20 rounded-lg">
                        <p className="text-2xl font-bold text-red-600">
                          {dashboard.security_summary.critical_findings}
                        </p>
                        <p className="text-sm text-red-600">{t('critical')}</p>
                      </div>
                      <div className="text-center p-4 bg-orange-50 dark:bg-orange-900/20 rounded-lg">
                        <p className="text-2xl font-bold text-orange-600">
                          {dashboard.security_summary.high_findings}
                        </p>
                        <p className="text-sm text-orange-600">{t('high')}</p>
                      </div>
                      <div className="text-center p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
                        <p className="text-2xl font-bold text-yellow-600">
                          {dashboard.security_summary.medium_findings}
                        </p>
                        <p className="text-sm text-yellow-600">{t('medium')}</p>
                      </div>
                      <div className="text-center p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                        <p className="text-2xl font-bold text-blue-600">
                          {dashboard.security_summary.low_findings}
                        </p>
                        <p className="text-sm text-blue-600">{t('low')}</p>
                      </div>
                    </div>

                    {/* Compliance */}
                    <div className="mt-6 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium text-gray-900 dark:text-white">
                          {t('cisCompliance')}
                        </span>
                        <span className="text-lg font-bold text-green-600">
                          {dashboard.compliance.cis_benchmark}%
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                        <div
                          className="bg-green-500 h-2 rounded-full transition-all"
                          style={{ width: `${dashboard.compliance.cis_benchmark}%` }}
                        ></div>
                      </div>
                      <p className="text-xs text-gray-500 mt-1">
                        {t('lastScan')}: {new Date(dashboard.compliance.last_scan).toLocaleString()}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Quick Actions */}
              <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
                <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                  <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                    {t('quickActions')}
                  </h2>
                </div>
                <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                  <button
                    onClick={scanContainer}
                    disabled={scanning}
                    className="p-4 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg hover:border-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors text-left"
                  >
                    <Scan className="w-8 h-8 text-blue-500 mb-2" />
                    <h3 className="font-medium text-gray-900 dark:text-white">
                      {scanning ? t('scanningImage') : t('scanImage')}
                    </h3>
                    <p className="text-sm text-gray-500">
                      {t('detectVulnerabilities')}
                    </p>
                  </button>

                  <button
                    onClick={() => alert(t('k8sScanComingSoon'))}
                    className="p-4 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg hover:border-green-500 hover:bg-green-50 dark:hover:bg-green-900/20 transition-colors text-left"
                  >
                    <Server className="w-8 h-8 text-green-500 mb-2" />
                    <h3 className="font-medium text-gray-900 dark:text-white">
                      {t('scanKubernetes')}
                    </h3>
                    <p className="text-sm text-gray-500">
                      {t('cisBenchmark')}
                    </p>
                  </button>
                </div>
              </div>
            </div>

            {/* Sidebar */}
            <div className="space-y-6">
              {/* Cloud Connections */}
              <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4">
                <h3 className="font-semibold text-gray-900 dark:text-white mb-4">
                  {t('cloudConnectionStatus')}
                </h3>
                <div className="space-y-3">
                  {[
                    { key: 'aws', name: 'AWS' },
                    { key: 'azure', name: 'Azure' },
                    { key: 'gcp', name: 'GCP' },
                    { key: 'alicloud', name: 'AliCloud' }
                  ].map((provider) => {
                    const connected = connections.some(
                      (c: any) => c.provider === provider.key
                    );
                    return (
                      <div key={provider.key} className="flex items-center justify-between">
                        <span className="text-gray-700 dark:text-gray-300">{provider.name}</span>
                        {connected ? (
                          <span className="flex items-center gap-1 text-green-600 text-sm">
                            <CheckCircle className="w-4 h-4" />
                            {t('connected')}
                          </span>
                        ) : (
                          <span className="text-gray-400 text-sm">{t('notConfigured')}</span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Recent Vulnerabilities */}
              {dashboard && dashboard.recent_vulnerabilities.length > 0 && (
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4">
                  <h3 className="font-semibold text-gray-900 dark:text-white mb-4">
                    {t('recentVulnerabilities')}
                  </h3>
                  <div className="space-y-3">
                    {dashboard.recent_vulnerabilities.map((vuln: any, index: number) => (
                      <div key={index} className="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-medium text-red-900 dark:text-red-100">
                            {vuln.image}
                          </span>
                          <span className={`px-2 py-0.5 rounded text-xs font-medium ${getSeverityColor(vuln.severity)}`}>
                            {vuln.severity}
                          </span>
                        </div>
                        <p className="text-sm text-red-700 dark:text-red-300">
                          {vuln.cve}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Info */}
              <div className="bg-gradient-to-br from-sky-50 to-blue-50 dark:from-sky-900/20 dark:to-blue-900/20 rounded-xl p-4 border border-sky-200 dark:border-sky-800">
                <h4 className="font-medium text-sky-900 dark:text-sky-100 mb-2">
                  {t('supportedCloudProviders')}
                </h4>
                <ul className="text-sm text-sky-800 dark:text-sky-200 space-y-1">
                  <li>• {t('aws')}</li>
                  <li>• {t('azure')}</li>
                  <li>• {t('gcp')}</li>
                  <li>• {t('alicloud')}</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
