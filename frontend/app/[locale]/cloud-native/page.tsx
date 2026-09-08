"use client";

import { useState, useEffect } from "react";
import { useRouter } from "@/i18n/navigation";
import { useFormatter, useTranslations } from "next-intl";
import { api } from "@/lib/api";
import { loadAuthState } from "@/lib/auth";
import { PageHeader } from "@/components/common/PageHeader";
import { useToast } from "@/components/Toast";
import { cn } from "@/lib/utils";
import {
  Cloud,
  Container,
  Shield,
  Server,
  AlertTriangle,
  CheckCircle,
  Scan,
  Search,
  Activity,
  XCircle,
} from "lucide-react";

interface CloudDashboard {
  total_containers: number;
  running_containers: number;
  total_images: number;
  vulnerable_images: number;
  recent_vulnerabilities: Array<{ image: string; severity: string; cve: string }>;
  top_mitre_techniques?: Array<{ technique: string; count: number }>;
  overview?: {
    connected_clusters: number;
    connected_clouds: number;
    total_resources: number;
    active_alerts: number;
    total_containers: number;
    vulnerable_images: number;
  };
  security_summary?: {
    critical_findings: number;
    high_findings: number;
    medium_findings: number;
    low_findings: number;
  };
  compliance?: {
    cis_benchmark: number;
    last_scan?: string;
  };
}

interface CloudConnection {
  provider: string;
  status: string;
}

interface CVEItem {
  cve_id: string;
  severity: string;
  title: string;
  package_name: string;
  installed_version: string;
  fixed_version: string | null;
  description: string;
  /** Optional advisory link from the scanner; falls back to NVD. */
  url?: string;
}

interface TrivyScanResult {
  image: string;
  scan_time: string;
  total_vulnerabilities: number;
  severity_counts: Record<string, number>;
  vulnerabilities: CVEItem[];
}

interface FalcoStats {
  time_window_hours: number;
  total_alerts: number;
  today_total: number;
  today_high_critical: number;
  severity_breakdown: Record<string, number>;
  top_rules: Array<{ rule: string; count: number }>;
  top_hosts: Array<{ hostname: string; count: number }>;
}

export default function CloudNativePage() {
  const router = useRouter();
  const t = useTranslations("cloudNative");
  const format = useFormatter();
  const { showToast } = useToast();
  const [mounted, setMounted] = useState(false);
  const [dashboard, setDashboard] = useState<CloudDashboard | null>(null);
  const [connections, setConnections] = useState<CloudConnection[]>([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);

  // ── Image scanning state ──
  const [imageInput, setImageInput] = useState("nginx:1.21");
  const [scanResult, setScanResult] = useState<TrivyScanResult | null>(null);
  const [scanError, setScanError] = useState("");

  // ── Falco state ──
  const [falcoStats, setFalcoStats] = useState<FalcoStats | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "trivy" | "falco">("overview");

  useEffect(() => {
    setMounted(true);
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [dashRes, connRes, falcoRes] = await Promise.all([
        api.get("/api/cloud-native/dashboard"),
        api.get("/api/cloud-native/cloud/connections"),
        api.get("/api/cloud-native/falco-alerts/stats?hours=24").catch(() => null),
      ]);

      setDashboard(dashRes as unknown as CloudDashboard);
      setConnections((connRes as unknown as { connections: CloudConnection[] }).connections);
      if (falcoRes) setFalcoStats(falcoRes as FalcoStats);
    } catch (e) {
      console.error("Failed to load data:", e);
    } finally {
      setLoading(false);
    }
  };

  const scanContainer = async () => {
    if (!imageInput.trim()) return;
    setScanning(true);
    setScanError("");
    setScanResult(null);

    try {
      const response = await api.post("/api/cloud-native/containers/trivy-scan", {
        image: imageInput.trim(),
        force_rescan: false,
      });
      setScanResult(response as unknown as TrivyScanResult);
    } catch (e: any) {
      setScanError(e?.message || t("scanFailed"));
      console.error("Scan failed:", e);
    } finally {
      setScanning(false);
    }
  };

  // ── Legacy scan (keep for backward compat) ──
  const scanContainerLegacy = async () => {
    setScanning(true);
    try {
      const response = await api.post("/api/cloud-native/containers/scan", {
        image: "nginx",
        tag: "1.21",
      });
      const vulnCount = (response as unknown as { total_vulnerabilities: number })
        .total_vulnerabilities;
      showToast(
        `${t("scanComplete")} - ${t("foundVulnerabilities", { count: vulnCount })}`,
        "info"
      );
    } catch (e) {
      console.error("Scan failed:", e);
    } finally {
      setScanning(false);
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity?.toLowerCase()) {
      case "critical":
        return "text-red-600 bg-red-50 dark:bg-red-900/30";
      case "high":
        return "text-orange-600 bg-orange-50 dark:bg-orange-900/30";
      case "medium":
        return "text-yellow-600 bg-yellow-50 dark:bg-yellow-900/30";
      default:
        return "text-blue-600 bg-blue-50 dark:bg-blue-900/30";
    }
  };

  const getSeverityBadge = (severity: string) => {
    const colors: Record<string, string> = {
      CRITICAL: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
      HIGH: "bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-300",
      MEDIUM: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300",
      LOW: "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300",
    };
    return `px-2 py-0.5 rounded text-xs font-medium ${colors[severity?.toUpperCase()] || colors.LOW}`;
  };

  if (!mounted) return null;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <PageHeader title={t("title")} subtitle={t("subtitle")} />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Demo data notice: K8s/cloud insights come from sample data until
            cluster/cloud integrations are configured; Trivy & Falco are real */}
        <div className="rounded-lg border border-amber-300 bg-amber-50 dark:border-amber-700 dark:bg-amber-900/30 px-4 py-3 text-sm text-amber-800 dark:text-amber-200">
          {t("demoNotice")}
        </div>

        {/* Stats */}
        {dashboard && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {t("connectedClusters")}
                  </p>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {dashboard.overview?.connected_clusters ?? 0}
                  </p>
                </div>
                <Server className="w-8 h-8 text-blue-500" />
              </div>
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400">{t("cloudProviders")}</p>
                  <p className="text-2xl font-bold text-blue-600">
                    {dashboard.overview?.connected_clouds ?? 0}
                  </p>
                </div>
                <Cloud className="w-8 h-8 text-blue-500" />
              </div>
            </div>

            {/* Falco Today Stats */}
            <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {t("falcoAlertsToday")}
                  </p>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {falcoStats?.today_total ?? "—"}
                  </p>
                </div>
                <Activity className="w-8 h-8 text-purple-500" />
              </div>
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {t("falcoHighCritical")}
                  </p>
                  <p className="text-2xl font-bold text-red-600">
                    {falcoStats?.today_high_critical ?? "—"}
                  </p>
                </div>
                <AlertTriangle className="w-8 h-8 text-red-500" />
              </div>
            </div>
          </div>
        )}

        {/* Tab Navigation */}
        <div className="flex gap-2 mb-6 border-b border-gray-200 dark:border-gray-700">
          {(["overview", "trivy", "falco"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab
                  ? "border-blue-500 text-blue-600 dark:text-blue-400"
                  : "border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
              }`}
            >
              {tab === "overview"
                ? t("securityOverview")
                : tab === "trivy"
                  ? t("imageScanning")
                  : t("falcoAlerts")}
            </button>
          ))}
        </div>

        {/* ── OVERVIEW TAB ── */}
        {activeTab === "overview" && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2">
              {dashboard && (
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 mb-6">
                  <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                    <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                      <Shield className="w-5 h-5 text-blue-500" />
                      {t("securityOverview")}
                    </h2>
                  </div>
                  <div className="p-4">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      {[
                        {
                          key: "critical_findings",
                          labelKey: "critical",
                          bg: "bg-danger-500/10 border border-danger-500/20",
                          text: "text-danger-600 dark:text-danger-400",
                        },
                        {
                          key: "high_findings",
                          labelKey: "high",
                          bg: "bg-warning-500/10 border border-warning-500/20",
                          text: "text-warning-600 dark:text-warning-400",
                        },
                        {
                          key: "medium_findings",
                          labelKey: "medium",
                          bg: "bg-amber-500/10 border border-amber-500/20",
                          text: "text-amber-600 dark:text-amber-400",
                        },
                        {
                          key: "low_findings",
                          labelKey: "low",
                          bg: "bg-accent-500/10 border border-accent-500/20",
                          text: "text-accent-600 dark:text-accent-400",
                        },
                      ].map(({ key, labelKey, bg, text }) => (
                        <div key={key} className={cn("text-center p-4 rounded-xl shadow-xs", bg)}>
                          <p className={cn("text-2xl font-bold tracking-tight tabular-nums", text)}>
                            {(dashboard.security_summary as any)?.[key] ?? 0}
                          </p>
                          <p
                            className={cn(
                              "text-xs font-semibold uppercase tracking-wider mt-1",
                              text
                            )}
                          >
                            {t(labelKey)}
                          </p>
                        </div>
                      ))}
                    </div>

                    <div className="mt-6 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium text-gray-900 dark:text-white">
                          {t("cisCompliance")}
                        </span>
                        <span className="text-lg font-bold text-green-600">
                          {dashboard.compliance?.cis_benchmark ?? 0}%
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                        <div
                          className="bg-green-500 h-2 rounded-full transition-all"
                          style={{ width: `${dashboard.compliance?.cis_benchmark ?? 0}%` }}
                        ></div>
                      </div>
                      <p className="text-xs text-gray-500 mt-1">
                        {t("lastScan")}:{" "}
                        {dashboard.compliance?.last_scan
                          ? format.dateTime(new Date(dashboard.compliance.last_scan), {
                              dateStyle: "medium",
                              timeStyle: "medium",
                            })
                          : "-"}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Quick Actions */}
              <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
                <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                  <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                    {t("quickActions")}
                  </h2>
                </div>
                <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                  <button
                    onClick={() => setActiveTab("trivy")}
                    className="p-4 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg hover:border-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors text-left"
                  >
                    <Scan className="w-8 h-8 text-blue-500 mb-2" />
                    <h3 className="font-medium text-gray-900 dark:text-white">{t("scanImage")}</h3>
                    <p className="text-sm text-gray-500">{t("detectVulnerabilities")}</p>
                  </button>

                  <button
                    onClick={() => showToast(t("k8sScanRequiresCluster"), "warning")}
                    className="p-4 border-2 border-dashed border-border-subtle rounded-xl hover:border-accent-500 hover:bg-accent-500/10 transition-colors text-left"
                  >
                    <Server className="w-8 h-8 text-green-500 mb-2" />
                    <h3 className="font-medium text-gray-900 dark:text-white">
                      {t("scanKubernetes")}
                    </h3>
                    <p className="text-sm text-gray-500">{t("cisBenchmark")}</p>
                  </button>
                </div>
              </div>
            </div>

            {/* Sidebar */}
            <div className="space-y-6">
              <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4">
                <h3 className="font-semibold text-gray-900 dark:text-white mb-4">
                  {t("cloudConnectionStatus")}
                </h3>
                <div className="space-y-3">
                  {[
                    { key: "aws", name: "AWS" },
                    { key: "azure", name: "Azure" },
                    { key: "gcp", name: "GCP" },
                    { key: "alicloud", name: "AliCloud" },
                  ].map((provider) => {
                    const connected = connections.some((c) => c.provider === provider.key);
                    return (
                      <div key={provider.key} className="flex items-center justify-between">
                        <span className="text-gray-700 dark:text-gray-300">{provider.name}</span>
                        {connected ? (
                          <span className="flex items-center gap-1 text-green-600 text-sm">
                            <CheckCircle className="w-4 h-4" />
                            {t("connected")}
                          </span>
                        ) : (
                          <span className="text-gray-400 text-sm">{t("notConfigured")}</span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              {dashboard && dashboard.recent_vulnerabilities.length > 0 && (
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4">
                  <h3 className="font-semibold text-gray-900 dark:text-white mb-4">
                    {t("recentVulnerabilities")}
                  </h3>
                  <div className="space-y-3">
                    {dashboard.recent_vulnerabilities.map((vuln, index) => (
                      <div
                        key={index}
                        className="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800"
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-medium text-red-900 dark:text-red-100">
                            {vuln.image}
                          </span>
                          <span
                            className={`px-2 py-0.5 rounded text-xs font-medium ${getSeverityColor(vuln.severity)}`}
                          >
                            {vuln.severity}
                          </span>
                        </div>
                        <p className="text-sm text-red-700 dark:text-red-300">{vuln.cve}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="bg-gradient-to-br from-sky-50 to-blue-50 dark:from-sky-900/20 dark:to-blue-900/20 rounded-xl p-4 border border-sky-200 dark:border-sky-800">
                <h4 className="font-medium text-sky-900 dark:text-sky-100 mb-2">
                  {t("supportedCloudProviders")}
                </h4>
                <ul className="text-sm text-sky-800 dark:text-sky-200 space-y-1">
                  <li>• {t("aws")}</li>
                  <li>• {t("azure")}</li>
                  <li>• {t("gcp")}</li>
                  <li>• {t("alicloud")}</li>
                </ul>
              </div>
            </div>
          </div>
        )}

        {/* ── TRIVY TAB ── */}
        {activeTab === "trivy" && (
          <div className="space-y-6">
            {/* Scan Input */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <Scan className="w-5 h-5 text-blue-500" />
                {t("imageScanning")} — Trivy
              </h2>
              <div className="flex gap-3">
                <div className="flex-1">
                  <input
                    type="text"
                    value={imageInput}
                    onChange={(e) => setImageInput(e.target.value)}
                    placeholder="nginx:1.21, alpine:latest, python:3.11-slim..."
                    className="w-full px-4 py-2.5 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    onKeyDown={(e) => e.key === "Enter" && scanContainer()}
                  />
                </div>
                <button
                  onClick={scanContainer}
                  disabled={scanning || !imageInput.trim()}
                  className="px-6 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 font-medium"
                >
                  {scanning ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      {t("scanningImage")}
                    </>
                  ) : (
                    <>
                      <Search className="w-4 h-4" />
                      {t("scanImage")}
                    </>
                  )}
                </button>
              </div>
              {scanError && (
                <div className="mt-3 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-300 text-sm flex items-center gap-2">
                  <XCircle className="w-4 h-4 flex-shrink-0" />
                  {scanError}
                </div>
              )}
            </div>

            {/* Scan Results */}
            {scanResult && (
              <div className="space-y-4">
                {/* Summary Cards */}
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                  {[
                    {
                      label: "CRITICAL",
                      count: scanResult.severity_counts?.CRITICAL ?? 0,
                      color: "red",
                    },
                    {
                      label: "HIGH",
                      count: scanResult.severity_counts?.HIGH ?? 0,
                      color: "orange",
                    },
                    {
                      label: "MEDIUM",
                      count: scanResult.severity_counts?.MEDIUM ?? 0,
                      color: "yellow",
                    },
                    { label: "LOW", count: scanResult.severity_counts?.LOW ?? 0, color: "blue" },
                    { label: "TOTAL", count: scanResult.total_vulnerabilities, color: "gray" },
                  ].map(({ label, count, color }) => (
                    <div
                      key={label}
                      className={`bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-${color}-200 dark:border-${color}-800 text-center`}
                    >
                      <p className={`text-2xl font-bold text-${color}-600 dark:text-${color}-400`}>
                        {count}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{label}</p>
                    </div>
                  ))}
                </div>

                {/* CVE Table */}
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
                  <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                    <h3 className="font-semibold text-gray-900 dark:text-white">
                      {t("vulnerabilityDetails")} — {scanResult.image}
                    </h3>
                    <p className="text-xs text-gray-500 mt-1">
                      {t("scannedAt")}:{" "}
                      {format.dateTime(new Date(scanResult.scan_time), {
                        dateStyle: "medium",
                        timeStyle: "medium",
                      })}
                    </p>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="bg-gray-50 dark:bg-gray-700 text-left">
                          <th className="px-4 py-3 font-medium text-gray-600 dark:text-gray-300">
                            CVE ID
                          </th>
                          <th className="px-4 py-3 font-medium text-gray-600 dark:text-gray-300">
                            {t("severity")}
                          </th>
                          <th className="px-4 py-3 font-medium text-gray-600 dark:text-gray-300">
                            {t("packageName")}
                          </th>
                          <th className="px-4 py-3 font-medium text-gray-600 dark:text-gray-300">
                            {t("installedVersion")}
                          </th>
                          <th className="px-4 py-3 font-medium text-gray-600 dark:text-gray-300">
                            {t("fixedVersion")}
                          </th>
                          <th className="px-4 py-3 font-medium text-gray-600 dark:text-gray-300">
                            {t("description")}
                          </th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                        {scanResult.vulnerabilities.map((vuln, idx) => (
                          <tr key={idx} className="hover:bg-gray-50 dark:hover:bg-gray-750">
                            <td className="px-4 py-3 font-mono text-xs text-blue-600 dark:text-blue-400 whitespace-nowrap">
                              <a
                                href={vuln.url || `https://nvd.nist.gov/vuln/detail/${vuln.cve_id}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="hover:underline"
                              >
                                {vuln.cve_id}
                              </a>
                            </td>
                            <td className="px-4 py-3">
                              <span className={getSeverityBadge(vuln.severity)}>
                                {vuln.severity}
                              </span>
                            </td>
                            <td className="px-4 py-3 font-mono text-xs text-gray-700 dark:text-gray-300">
                              {vuln.package_name}
                            </td>
                            <td className="px-4 py-3 font-mono text-xs text-gray-500 dark:text-gray-400">
                              {vuln.installed_version}
                            </td>
                            <td className="px-4 py-3 font-mono text-xs">
                              {vuln.fixed_version ? (
                                <span className="text-green-600 dark:text-green-400">
                                  {vuln.fixed_version}
                                </span>
                              ) : (
                                <span className="text-gray-400">—</span>
                              )}
                            </td>
                            <td className="px-4 py-3 text-xs text-gray-600 dark:text-gray-400 max-w-xs truncate">
                              {vuln.description || vuln.title}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}

            {!scanResult && !scanError && (
              <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-12 text-center">
                <Search className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
                <p className="text-gray-500 dark:text-gray-400">{t("enterImageToScan")}</p>
                <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                  {t("scanExamples")}: nginx:1.21, alpine:3.18, python:3.11-slim
                </p>
              </div>
            )}
          </div>
        )}

        {/* ── FALCO TAB ── */}
        {activeTab === "falco" && (
          <div className="space-y-6">
            {/* Falco Stats Cards */}
            {falcoStats && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700 text-center">
                  <p className="text-3xl font-bold text-gray-900 dark:text-white">
                    {falcoStats.total_alerts}
                  </p>
                  <p className="text-sm text-gray-500 mt-1">{t("totalAlerts24h")}</p>
                </div>
                <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-red-200 dark:border-red-800 text-center">
                  <p className="text-3xl font-bold text-red-600">
                    {falcoStats.severity_breakdown?.critical ?? 0}
                  </p>
                  <p className="text-sm text-red-500 mt-1">{t("critical")}</p>
                </div>
                <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-orange-200 dark:border-orange-800 text-center">
                  <p className="text-3xl font-bold text-orange-600">
                    {falcoStats.severity_breakdown?.high ?? 0}
                  </p>
                  <p className="text-sm text-orange-500 mt-1">{t("high")}</p>
                </div>
                <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700 text-center">
                  <p className="text-3xl font-bold text-gray-900 dark:text-white">
                    {falcoStats.today_total}
                  </p>
                  <p className="text-sm text-gray-500 mt-1">{t("today")}</p>
                </div>
              </div>
            )}

            {/* Top Falco Rules */}
            {falcoStats && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
                  <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                    <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                      <Activity className="w-5 h-5 text-purple-500" />
                      {t("topFalcoRules")}
                    </h3>
                  </div>
                  <div className="p-4">
                    <div className="space-y-2">
                      {falcoStats.top_rules?.map((item, idx) => (
                        <div
                          key={idx}
                          className="flex items-center justify-between py-2 border-b border-gray-50 dark:border-gray-700 last:border-0"
                        >
                          <div className="flex items-center gap-3 min-w-0">
                            <span className="text-xs font-mono text-gray-400 w-5">#{idx + 1}</span>
                            <span className="text-sm text-gray-700 dark:text-gray-300 truncate">
                              {item.rule}
                            </span>
                          </div>
                          <span className="text-sm font-semibold text-gray-900 dark:text-white ml-4">
                            {item.count}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
                  <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                    <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                      <Server className="w-5 h-5 text-green-500" />
                      {t("topFalcoHosts")}
                    </h3>
                  </div>
                  <div className="p-4">
                    <div className="space-y-2">
                      {falcoStats.top_hosts?.map((item, idx) => (
                        <div
                          key={idx}
                          className="flex items-center justify-between py-2 border-b border-gray-50 dark:border-gray-700 last:border-0"
                        >
                          <div className="flex items-center gap-3 min-w-0">
                            <span className="text-xs font-mono text-gray-400 w-5">#{idx + 1}</span>
                            <span className="text-sm text-gray-700 dark:text-gray-300 font-mono truncate">
                              {item.hostname}
                            </span>
                          </div>
                          <span className="text-sm font-semibold text-gray-900 dark:text-white ml-4">
                            {item.count}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Falco Config Info */}
            {!falcoStats && (
              <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-12 text-center">
                <Activity className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
                <p className="text-gray-500 dark:text-gray-400">{t("falcoNotConfigured")}</p>
                <p className="text-xs text-gray-400 dark:text-gray-500 mt-1 max-w-md mx-auto">
                  {t("falcoSetupHint")}
                </p>
              </div>
            )}

            {/* Falco webhook setup card */}
            <div className="bg-gradient-to-br from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20 rounded-xl p-4 border border-purple-200 dark:border-purple-800">
              <h4 className="font-medium text-purple-900 dark:text-purple-100 mb-2 flex items-center gap-2">
                <Shield className="w-4 h-4" />
                {t("falcoSetupTitle")}
              </h4>
              <p className="text-sm text-purple-800 dark:text-purple-200 mb-2">
                {t("falcoSetupDesc")}
              </p>
              <code className="block p-2 bg-purple-100 dark:bg-purple-900/30 rounded text-xs text-purple-900 dark:text-purple-200 font-mono break-all">
                falcosidekick --url http://your-host/api/cloud-native/falco-alerts
              </code>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
