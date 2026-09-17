"use client";

import { useState, useEffect } from "react";
import { useRouter } from "@/i18n/navigation";
import { useFormatter, useTranslations } from "next-intl";
import { apiClient } from "@/lib/api";
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
  Layers,
  ChevronRight,
  ChevronLeft,
  ExternalLink,
  X,
  RefreshCw,
  Info,
  Check,
  Terminal,
  Cpu,
  HardDrive,
  Filter,
  Copy,
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

interface K8sCluster {
  name: string;
  provider: string;
  region: string;
  version: string;
  status: string;
  nodes_count: number;
  pods_count: number;
  namespaces: string[];
  created_at: string;
}

interface K8sResourceItem {
  name: string;
  namespace: string;
  kind: string;
  labels: Record<string, string>;
  annotations?: Record<string, string>;
  spec?: Record<string, any>;
  status: Record<string, any>;
}

interface K8sFinding {
  id: string;
  resource_name: string;
  namespace: string;
  kind: string;
  severity: string;
  category: string;
  title: string;
  description: string;
  remediation: string;
  detected_at?: string;
}

interface ComplianceReport {
  scan_date: string;
  cluster?: string;
  total_findings: number;
  severity_breakdown: Record<string, number>;
  cis_compliance: {
    total_checks: number;
    passed: number;
    failed: number;
    skipped: number;
    compliance_percentage: number;
  };
  findings: Array<{
    id: string;
    resource: string;
    namespace: string;
    severity: string;
    category: string;
    title: string;
    remediation: string;
  }>;
}

interface ContainerItem {
  id: string;
  name: string;
  pod_name: string;
  namespace: string;
  cluster_name: string;
  image: string;
  status: "running" | "warning" | "terminated" | string;
  state_reason?: string | null;
  restart_count: number;
  cpu_usage: string;
  memory_usage: string;
  ip_address: string;
  ports: string[];
  privileged: boolean;
  run_as_root: boolean;
  readonly_rootfs: boolean;
  vulnerabilities_count: number;
  critical_vulns: number;
  high_vulns: number;
  created_at: string;
  node_name?: string;
  remediation?: string | null;
  command?: string[];
  mounts?: string[];
  env_vars?: Record<string, string>;
}

interface ContainerListResponse {
  total: number;
  filtered_total: number;
  page: number;
  page_size: number;
  total_pages: number;
  running: number;
  warning: number;
  terminated: number;
  vulnerable: number;
  containers: ContainerItem[];
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
  const [activeTab, setActiveTab] = useState<"overview" | "containers" | "trivy" | "falco">("overview");

  // ── Containers state ──
  const [containers, setContainers] = useState<ContainerItem[]>([]);
  const [containersStats, setContainersStats] = useState<{
    total: number;
    running: number;
    warning: number;
    terminated: number;
    vulnerable: number;
  }>({ total: 45, running: 42, warning: 2, terminated: 1, vulnerable: 9 });
  const [loadingContainers, setLoadingContainers] = useState(false);
  const [containerSearch, setContainerSearch] = useState("");
  const [containerStatusFilter, setContainerStatusFilter] = useState("all");
  const [containerNsFilter, setContainerNsFilter] = useState("");
  const [containerClusterFilter, setContainerClusterFilter] = useState("");
  const [containerPage, setContainerPage] = useState(1);
  const [containerPageSize, setContainerPageSize] = useState(10);
  const [containerTotalPages, setContainerTotalPages] = useState(1);
  const [containerFilteredTotal, setContainerFilteredTotal] = useState(45);
  const [selectedContainer, setSelectedContainer] = useState<ContainerItem | null>(null);
  const [containerDetailModalOpen, setContainerDetailModalOpen] = useState(false);
  const [loadingContainerDetail, setLoadingContainerDetail] = useState(false);

  // ── K8s Cluster & Resource state ──
  const [clusterModalOpen, setClusterModalOpen] = useState(false);
  const [clusters, setClusters] = useState<K8sCluster[]>([]);
  const [selectedCluster, setSelectedCluster] = useState<K8sCluster | null>(null);
  const [activeResourceType, setActiveResourceType] = useState<
    "pods" | "deployments" | "services" | "secrets" | "configmaps"
  >("pods");
  const [selectedNamespace, setSelectedNamespace] = useState("");
  const [clusterResources, setClusterResources] = useState<K8sResourceItem[]>([]);
  const [loadingResources, setLoadingResources] = useState(false);
  const [k8sScanning, setK8sScanning] = useState(false);
  const [k8sScanFindings, setK8sScanFindings] = useState<K8sFinding[] | null>(null);

  // ── CIS Compliance Modal state ──
  const [complianceModalOpen, setComplianceModalOpen] = useState(false);
  const [complianceReport, setComplianceReport] = useState<ComplianceReport | null>(null);
  const [loadingCompliance, setLoadingCompliance] = useState(false);

  // ── Findings Detail Modal state ──
  const [findingsModalOpen, setFindingsModalOpen] = useState(false);
  const [findingsFilter, setFindingsFilter] = useState<string>("all");
  const [allFindings, setAllFindings] = useState<K8sFinding[]>([]);

  // ── Cloud Provider Modal state ──
  const [cloudModalOpen, setCloudModalOpen] = useState(false);
  const [selectedCloudProvider, setSelectedCloudProvider] = useState<string | null>(null);
  const [cloudEvents, setCloudEvents] = useState<any[]>([]);
  const [loadingCloudEvents, setLoadingCloudEvents] = useState(false);

  useEffect(() => {
    setMounted(true);
    loadData();
    loadContainers();
  }, []);

  const loadData = async () => {
    try {
      const [dashRes, connRes, falcoRes] = await Promise.all([
        apiClient.get<CloudDashboard>("/api/cloud-native/dashboard"),
        apiClient.get<{ connections: CloudConnection[] }>("/api/cloud-native/cloud/connections"),
        apiClient.get<FalcoStats>("/api/cloud-native/falco-alerts/stats?hours=24").catch(() => null),
      ]);

      setDashboard(dashRes);
      setConnections(connRes?.connections || []);
      if (falcoRes) setFalcoStats(falcoRes);
    } catch (e) {
      console.error("Failed to load data:", e);
    } finally {
      setLoading(false);
    }
  };

  const loadContainers = async (params?: {
    search?: string;
    status?: string;
    namespace?: string;
    cluster?: string;
    page?: number;
    pageSize?: number;
  }) => {
    setLoadingContainers(true);
    try {
      const q = new URLSearchParams();
      const sVal = params?.search !== undefined ? params.search : containerSearch;
      if (sVal.trim()) q.set("search", sVal.trim());
      const stVal = params?.status !== undefined ? params.status : containerStatusFilter;
      if (stVal && stVal !== "all") q.set("status", stVal);
      const nsVal = params?.namespace !== undefined ? params.namespace : containerNsFilter;
      if (nsVal) q.set("namespace", nsVal);
      const clVal = params?.cluster !== undefined ? params.cluster : containerClusterFilter;
      if (clVal) q.set("cluster", clVal);

      const targetPage = params?.page !== undefined ? params.page : containerPage;
      const targetPageSize = params?.pageSize !== undefined ? params.pageSize : containerPageSize;
      q.set("page", String(targetPage));
      q.set("page_size", String(targetPageSize));

      const qs = q.toString() ? `?${q.toString()}` : "";
      const res = await apiClient.get<ContainerListResponse>(`/api/cloud-native/containers${qs}`);
      if (res?.containers) {
        setContainers(res.containers);
        setContainerPage(res.page || targetPage);
        setContainerPageSize(res.page_size || targetPageSize);
        setContainerTotalPages(res.total_pages || 1);
        setContainerFilteredTotal(res.filtered_total ?? res.total);
        setContainersStats({
          total: res.total,
          running: res.running,
          warning: res.warning,
          terminated: res.terminated,
          vulnerable: res.vulnerable,
        });
      }
    } catch (e) {
      console.error("Failed to load containers:", e);
    } finally {
      setLoadingContainers(false);
    }
  };

  const openContainerInspector = async (containerId: string) => {
    setContainerDetailModalOpen(true);
    setLoadingContainerDetail(true);
    try {
      const res = await apiClient.get<ContainerItem>(
        `/api/cloud-native/containers/${encodeURIComponent(containerId)}`
      );
      setSelectedContainer(res);
    } catch (e) {
      console.error("Failed to load container detail:", e);
    } finally {
      setLoadingContainerDetail(false);
    }
  };

  const scanContainerFromList = (imageName: string) => {
    setImageInput(imageName);
    setActiveTab("trivy");
    setScanResult(null);
    setScanError("");
    setContainerDetailModalOpen(false);
  };

  const scanContainer = async () => {
    if (!imageInput.trim()) return;
    setScanning(true);
    setScanError("");
    setScanResult(null);

    try {
      const response = await apiClient.post<TrivyScanResult>("/api/cloud-native/containers/trivy-scan", {
        image: imageInput.trim(),
        force_rescan: false,
      });
      setScanResult(response);
    } catch (e: any) {
      setScanError(e?.message || t("scanFailed"));
      console.error("Scan failed:", e);
    } finally {
      setScanning(false);
    }
  };

  const openClusterModal = async (clusterName?: string) => {
    setClusterModalOpen(true);
    try {
      const res = await apiClient.get<{ clusters: K8sCluster[] }>("/api/cloud-native/kubernetes/clusters");
      if (res?.clusters?.length) {
        setClusters(res.clusters);
        const target = clusterName
          ? res.clusters.find((c: K8sCluster) => c.name === clusterName) || res.clusters[0]
          : res.clusters[0];
        setSelectedCluster(target);
        loadResources(target.name, activeResourceType, selectedNamespace);
      } else {
        const defaultClusters: K8sCluster[] = [
          {
            name: "k8s-prod-cluster",
            provider: "AWS EKS",
            region: "ap-east-1",
            version: "v1.28.2",
            status: "healthy",
            nodes_count: 12,
            pods_count: 36,
            namespaces: ["production", "ingress-nginx", "monitoring", "kube-system"],
            created_at: new Date().toISOString(),
          },
          {
            name: "k8s-staging-cluster",
            provider: "AliCloud ACK",
            region: "cn-hangzhou",
            version: "v1.27.4",
            status: "warning",
            nodes_count: 4,
            pods_count: 9,
            namespaces: ["staging", "kube-system", "default"],
            created_at: new Date().toISOString(),
          },
        ];
        setClusters(defaultClusters);
        setSelectedCluster(defaultClusters[0]);
        loadResources(defaultClusters[0].name, activeResourceType, selectedNamespace);
      }
    } catch (e) {
      console.error("Failed to load clusters", e);
    }
  };

  const loadResources = async (clusterName: string, type: string, ns: string = "") => {
    setLoadingResources(true);
    try {
      const query = ns ? `?namespace=${encodeURIComponent(ns)}` : "";
      const res = await apiClient.get<{ resources: K8sResourceItem[] }>(
        `/api/cloud-native/kubernetes/resources/${type}${query}`
      );
      setClusterResources(res?.resources || []);
    } catch (e) {
      console.error("Failed to load resources", e);
      setClusterResources([]);
    } finally {
      setLoadingResources(false);
    }
  };

  const runClusterScan = async (clusterName: string, ns?: string) => {
    setK8sScanning(true);
    setK8sScanFindings(null);
    try {
      const res = await apiClient.post<{ findings: K8sFinding[] }>("/api/cloud-native/kubernetes/scan", {
        cluster_name: clusterName,
        namespace: ns || undefined,
      });
      setK8sScanFindings(res?.findings || []);
      showToast(t("scanClusterSuccess"), "success");
    } catch (e) {
      console.error("Failed to scan cluster", e);
      showToast(t("scanFailed"), "error");
    } finally {
      setK8sScanning(false);
    }
  };

  const openComplianceModal = async () => {
    setComplianceModalOpen(true);
    setLoadingCompliance(true);
    try {
      const res = await apiClient.get<ComplianceReport>("/api/cloud-native/compliance/report");
      setComplianceReport(res);
    } catch (e) {
      console.error("Failed to load compliance report", e);
    } finally {
      setLoadingCompliance(false);
    }
  };

  const openFindingsModal = async (severity: string = "all") => {
    setFindingsFilter(severity.toLowerCase());
    setFindingsModalOpen(true);
    try {
      const res = await apiClient.get<ComplianceReport>("/api/cloud-native/compliance/report");
      if (res?.findings) {
        setAllFindings(
          res.findings.map((f: ComplianceReport["findings"][number]) => ({
            id: f.id,
            resource_name: f.resource,
            namespace: f.namespace,
            kind: f.resource.split("/")[0] || "Resource",
            severity: f.severity,
            category: f.category,
            title: f.title,
            description: `Violation in ${f.resource} (${f.namespace})`,
            remediation: f.remediation,
            detected_at: res.scan_date,
          }))
        );
      }
    } catch (e) {
      console.error("Failed to load findings", e);
    }
  };

  const openCloudModal = async (provider: string) => {
    setSelectedCloudProvider(provider);
    setCloudModalOpen(true);
    setLoadingCloudEvents(true);
    try {
      const res = await apiClient.get<{ events: any[] }>(
        `/api/cloud-native/cloud/events/${provider}?hours=24`
      );
      setCloudEvents(res?.events || []);
    } catch (e) {
      console.error("Failed to load cloud events", e);
      setCloudEvents([]);
    } finally {
      setLoadingCloudEvents(false);
    }
  };

  // ── Legacy scan (keep for backward compat) ──
  const scanContainerLegacy = async () => {
    setScanning(true);
    try {
      const response = await apiClient.post<{ total_vulnerabilities: number }>("/api/cloud-native/containers/scan", {
        image: "nginx",
        tag: "1.21",
      });
      const vulnCount = response?.total_vulnerabilities || 0;
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

      <main className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Demo data notice: K8s/cloud insights come from sample data until
            cluster/cloud integrations are configured; Trivy & Falco are real */}
        <div className="rounded-lg border border-amber-300 bg-amber-50 dark:border-amber-700 dark:bg-amber-900/30 px-4 py-3 text-sm text-amber-800 dark:text-amber-200">
          {t("demoNotice")}
        </div>

        {/* Stats - 6 Responsive Interactive Cards */}
        {dashboard && (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
            {/* 1. Connected Clusters */}
            <div
              onClick={() => openClusterModal()}
              className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm border border-gray-200 dark:border-gray-700 hover:border-blue-500 hover:shadow-md transition-all cursor-pointer group"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                  {t("connectedClusters")}
                </span>
                <Server className="w-5 h-5 text-blue-500 group-hover:scale-110 transition-transform" />
              </div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {dashboard.overview?.connected_clusters ?? 2}
              </p>
              <p className="text-xs text-blue-600 dark:text-blue-400 mt-2 flex items-center gap-1 group-hover:underline">
                {t("clickToViewDetails")} <ChevronRight className="w-3 h-3" />
              </p>
            </div>

            {/* 2. Total Containers */}
            <div
              onClick={() => {
                setActiveTab("containers");
                loadContainers({ page: 1 });
              }}
              className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm border border-gray-200 dark:border-gray-700 hover:border-emerald-500 hover:shadow-md transition-all cursor-pointer group"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                  {t("totalContainers")}
                </span>
                <Container className="w-5 h-5 text-emerald-500 group-hover:scale-110 transition-transform" />
              </div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {dashboard.overview?.total_containers ?? 45}
              </p>
              <p className="text-xs text-emerald-600 dark:text-emerald-400 mt-2 flex items-center gap-1 group-hover:underline">
                {t("clickToViewContainers")} <ChevronRight className="w-3 h-3" />
              </p>
            </div>

            {/* 3. Vulnerable Images */}
            <div
              onClick={() => setActiveTab("trivy")}
              className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm border border-gray-200 dark:border-gray-700 hover:border-amber-500 hover:shadow-md transition-all cursor-pointer group"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                  {t("vulnerableImages")}
                </span>
                <AlertTriangle className="w-5 h-5 text-amber-500 group-hover:scale-110 transition-transform" />
              </div>
              <p className="text-2xl font-bold text-amber-600 dark:text-amber-400">
                {dashboard.overview?.vulnerable_images ?? 8}
              </p>
              <p className="text-xs text-amber-600 dark:text-amber-400 mt-2 flex items-center gap-1 group-hover:underline">
                {t("clickToScan")} <ChevronRight className="w-3 h-3" />
              </p>
            </div>

            {/* 4. Cloud Providers */}
            <div
              onClick={() => openCloudModal("aws")}
              className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm border border-gray-200 dark:border-gray-700 hover:border-sky-500 hover:shadow-md transition-all cursor-pointer group"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                  {t("cloudProviders")}
                </span>
                <Cloud className="w-5 h-5 text-sky-500 group-hover:scale-110 transition-transform" />
              </div>
              <p className="text-2xl font-bold text-sky-600 dark:text-sky-400">
                {dashboard.overview?.connected_clouds ?? connections.length}
              </p>
              <p className="text-xs text-sky-600 dark:text-sky-400 mt-2 flex items-center gap-1 group-hover:underline">
                {t("clickToViewDetails")} <ChevronRight className="w-3 h-3" />
              </p>
            </div>

            {/* 5. Falco Today Stats */}
            <div
              onClick={() => setActiveTab("falco")}
              className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm border border-gray-200 dark:border-gray-700 hover:border-purple-500 hover:shadow-md transition-all cursor-pointer group"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                  {t("falcoAlertsToday")}
                </span>
                <Activity className="w-5 h-5 text-purple-500 group-hover:scale-110 transition-transform" />
              </div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {falcoStats?.today_total ?? "—"}
              </p>
              <p className="text-xs text-purple-600 dark:text-purple-400 mt-2 flex items-center gap-1 group-hover:underline">
                {t("clickToViewDetails")} <ChevronRight className="w-3 h-3" />
              </p>
            </div>

            {/* 6. Falco High/Critical */}
            <div
              onClick={() => setActiveTab("falco")}
              className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm border border-gray-200 dark:border-gray-700 hover:border-red-500 hover:shadow-md transition-all cursor-pointer group"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                  {t("falcoHighCritical")}
                </span>
                <AlertTriangle className="w-5 h-5 text-red-500 group-hover:scale-110 transition-transform" />
              </div>
              <p className="text-2xl font-bold text-red-600 dark:text-red-400">
                {falcoStats?.today_high_critical ?? "—"}
              </p>
              <p className="text-xs text-red-600 dark:text-red-400 mt-2 flex items-center gap-1 group-hover:underline">
                {t("clickToViewDetails")} <ChevronRight className="w-3 h-3" />
              </p>
            </div>
          </div>
        )}

        {/* Tab Navigation */}
        <div className="flex gap-2 mb-6 border-b border-gray-200 dark:border-gray-700 overflow-x-auto">
          {(["overview", "containers", "trivy", "falco"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => {
                setActiveTab(tab);
                if (tab === "containers" && containers.length === 0) {
                  loadContainers({ page: 1 });
                }
              }}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 whitespace-nowrap ${
                activeTab === tab
                  ? "border-blue-500 text-blue-600 dark:text-blue-400 font-semibold"
                  : "border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
              }`}
            >
              {tab === "overview" && <Shield className="w-4 h-4" />}
              {tab === "containers" && <Container className="w-4 h-4" />}
              {tab === "trivy" && <Scan className="w-4 h-4" />}
              {tab === "falco" && <Activity className="w-4 h-4" />}
              {tab === "overview"
                ? t("securityOverview")
                : tab === "containers"
                  ? `${t("containersList")} (${dashboard?.overview?.total_containers ?? containersStats.total})`
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
                          bg: "bg-danger-500/10 border border-danger-500/20 hover:border-danger-500/50",
                          text: "text-danger-600 dark:text-danger-400",
                        },
                        {
                          key: "high_findings",
                          labelKey: "high",
                          bg: "bg-warning-500/10 border border-warning-500/20 hover:border-warning-500/50",
                          text: "text-warning-600 dark:text-warning-400",
                        },
                        {
                          key: "medium_findings",
                          labelKey: "medium",
                          bg: "bg-amber-500/10 border border-amber-500/20 hover:border-amber-500/50",
                          text: "text-amber-600 dark:text-amber-400",
                        },
                        {
                          key: "low_findings",
                          labelKey: "low",
                          bg: "bg-accent-500/10 border border-accent-500/20 hover:border-accent-500/50",
                          text: "text-accent-600 dark:text-accent-400",
                        },
                      ].map(({ key, labelKey, bg, text }) => (
                        <div
                          key={key}
                          onClick={() => openFindingsModal(labelKey)}
                          className={cn(
                            "text-center p-4 rounded-xl shadow-subtle cursor-pointer transition-all hover:scale-[1.03] group",
                            bg
                          )}
                          title={t("clickToViewDetails")}
                        >
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
                          <p className="text-[10px] text-gray-400 dark:text-gray-500 mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
                            {t("clickToViewDetails")}
                          </p>
                        </div>
                      ))}
                    </div>

                    {/* Clickable CIS Compliance Section */}
                    <div
                      onClick={() => openComplianceModal()}
                      className="mt-6 p-4 bg-gray-50 dark:bg-gray-700/60 rounded-xl border border-transparent hover:border-green-400/50 cursor-pointer transition-all group"
                      title={t("clickToViewReport")}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium text-gray-900 dark:text-white flex items-center gap-2">
                          <CheckCircle className="w-4 h-4 text-green-500" />
                          {t("cisCompliance")}
                        </span>
                        <div className="flex items-center gap-2">
                          <span className="text-lg font-bold text-green-600">
                            {dashboard.compliance?.cis_benchmark ?? 0}%
                          </span>
                          <span className="text-xs text-green-600 dark:text-green-400 flex items-center gap-1 group-hover:underline">
                            {t("clickToViewReport")} <ExternalLink className="w-3 h-3" />
                          </span>
                        </div>
                      </div>
                      <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                        <div
                          className="bg-green-500 h-2 rounded-full transition-all"
                          style={{ width: `${dashboard.compliance?.cis_benchmark ?? 0}%` }}
                        ></div>
                      </div>
                      <p className="text-xs text-gray-500 mt-1.5 flex items-center justify-between">
                        <span>
                          {t("lastScan")}:{" "}
                          {dashboard.compliance?.last_scan
                            ? format.dateTime(new Date(dashboard.compliance.last_scan), {
                                dateStyle: "medium",
                                timeStyle: "medium",
                              })
                            : "-"}
                        </span>
                        <span className="text-gray-400 group-hover:text-green-600 dark:group-hover:text-green-400 transition-colors text-[11px]">
                          100项基准已审计 (85通过 / 10未通过)
                        </span>
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
                    className="p-4 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg hover:border-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors text-left group"
                  >
                    <Scan className="w-8 h-8 text-blue-500 mb-2 group-hover:scale-110 transition-transform" />
                    <h3 className="font-medium text-gray-900 dark:text-white flex items-center gap-1">
                      {t("scanImage")} <ChevronRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </h3>
                    <p className="text-sm text-gray-500">{t("detectVulnerabilities")}</p>
                  </button>

                  <button
                    onClick={() => openClusterModal()}
                    className="p-4 border-2 border-dashed border-border-subtle rounded-xl hover:border-accent-500 hover:bg-accent-500/10 transition-colors text-left group"
                  >
                    <Server className="w-8 h-8 text-green-500 mb-2 group-hover:scale-110 transition-transform" />
                    <h3 className="font-medium text-gray-900 dark:text-white flex items-center gap-1">
                      {t("scanKubernetes")} <ChevronRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </h3>
                    <p className="text-sm text-gray-500">{t("cisBenchmark")} — 点击打开集群审计</p>
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
                <div className="space-y-2">
                  {[
                    { key: "aws", name: "AWS" },
                    { key: "azure", name: "Azure" },
                    { key: "gcp", name: "GCP" },
                    { key: "alicloud", name: "AliCloud" },
                  ].map((provider) => {
                    const connected = connections.some((c) => c.provider === provider.key);
                    return (
                      <div
                        key={provider.key}
                        onClick={() => openCloudModal(provider.key)}
                        className="flex items-center justify-between p-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer transition-colors group"
                        title={t("clickToViewDetails")}
                      >
                        <span className="text-gray-700 dark:text-gray-300 font-medium group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                          {provider.name}
                        </span>
                        {connected ? (
                          <span className="flex items-center gap-1 text-green-600 text-sm">
                            <CheckCircle className="w-4 h-4" />
                            {t("connected")}
                          </span>
                        ) : (
                          <span className="text-gray-400 text-xs flex items-center gap-1">
                            {t("notConfigured")}
                            <ChevronRight className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              {dashboard && dashboard.recent_vulnerabilities.length > 0 && (
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4">
                  <h3 className="font-semibold text-gray-900 dark:text-white mb-4 flex items-center justify-between">
                    <span>{t("recentVulnerabilities")}</span>
                    <span className="text-xs text-gray-400 font-normal">点击重新扫描</span>
                  </h3>
                  <div className="space-y-3">
                    {dashboard.recent_vulnerabilities.map((vuln, index) => (
                      <div
                        key={index}
                        onClick={() => {
                          setImageInput(vuln.image);
                          setActiveTab("trivy");
                        }}
                        className="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800 cursor-pointer hover:border-red-400 hover:shadow-sm transition-all group"
                        title={t("clickToScan")}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-medium text-red-900 dark:text-red-100 group-hover:underline flex items-center gap-1">
                            {vuln.image}
                            <ChevronRight className="w-3 h-3 text-red-500 opacity-0 group-hover:opacity-100" />
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

        {/* ── CONTAINERS TAB ── */}
        {activeTab === "containers" && (
          <div className="space-y-6">
            {/* 1. Status Filter Pills / Overview Cards */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
              <button
                onClick={() => {
                  setContainerStatusFilter("all");
                  setContainerPage(1);
                  loadContainers({ status: "all", page: 1 });
                }}
                className={`p-3.5 rounded-xl border text-left transition-all ${
                  containerStatusFilter === "all"
                    ? "bg-blue-50/80 border-blue-500 dark:bg-blue-900/30 dark:border-blue-400 ring-2 ring-blue-500/20"
                    : "bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:border-gray-300"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-500 dark:text-gray-400 font-medium">全部容器资产</span>
                  <Container className="w-4 h-4 text-blue-500" />
                </div>
                <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
                  {containersStats.total}
                </p>
                <p className="text-[11px] text-gray-500 dark:text-gray-400 mt-0.5">跨 2 集群 / 6 命名空间</p>
              </button>

              <button
                onClick={() => {
                  setContainerStatusFilter("running");
                  setContainerPage(1);
                  loadContainers({ status: "running", page: 1 });
                }}
                className={`p-3.5 rounded-xl border text-left transition-all ${
                  containerStatusFilter === "running"
                    ? "bg-emerald-50/80 border-emerald-500 dark:bg-emerald-900/30 dark:border-emerald-400 ring-2 ring-emerald-500/20"
                    : "bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:border-gray-300"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-500 dark:text-gray-400 font-medium">运行正常</span>
                  <CheckCircle className="w-4 h-4 text-emerald-500" />
                </div>
                <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-1">
                  {containersStats.running}
                </p>
                <p className="text-[11px] text-emerald-600/80 dark:text-emerald-400/80 mt-0.5">健康率 93.3%</p>
              </button>

              <button
                onClick={() => {
                  setContainerStatusFilter("warning");
                  setContainerPage(1);
                  loadContainers({ status: "warning", page: 1 });
                }}
                className={`p-3.5 rounded-xl border text-left transition-all ${
                  containerStatusFilter === "warning"
                    ? "bg-amber-50/80 border-amber-500 dark:bg-amber-900/30 dark:border-amber-400 ring-2 ring-amber-500/20"
                    : "bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:border-gray-300"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-500 dark:text-gray-400 font-medium">异常 / 警告</span>
                  <AlertTriangle className="w-4 h-4 text-amber-500" />
                </div>
                <p className="text-2xl font-bold text-amber-600 dark:text-amber-400 mt-1">
                  {containersStats.warning}
                </p>
                <p className="text-[11px] text-amber-600/80 dark:text-amber-400/80 mt-0.5">重启或安全策略违规</p>
              </button>

              <button
                onClick={() => {
                  setContainerStatusFilter("terminated");
                  setContainerPage(1);
                  loadContainers({ status: "terminated", page: 1 });
                }}
                className={`p-3.5 rounded-xl border text-left transition-all ${
                  containerStatusFilter === "terminated"
                    ? "bg-gray-100 border-gray-500 dark:bg-gray-700/50 dark:border-gray-400 ring-2 ring-gray-500/20"
                    : "bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:border-gray-300"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-500 dark:text-gray-400 font-medium">已结束 / 停止</span>
                  <XCircle className="w-4 h-4 text-gray-400" />
                </div>
                <p className="text-2xl font-bold text-gray-700 dark:text-gray-300 mt-1">
                  {containersStats.terminated}
                </p>
                <p className="text-[11px] text-gray-500 dark:text-gray-400 mt-0.5">已完成的批处理任务</p>
              </button>

              <button
                onClick={() => {
                  setContainerSearch("vuln");
                  setContainerPage(1);
                  loadContainers({ search: "vuln", page: 1 });
                }}
                className="p-3.5 rounded-xl border text-left transition-all bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:border-red-400 group"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-500 dark:text-gray-400 font-medium">含已知漏洞</span>
                  <Shield className="w-4 h-4 text-red-500 group-hover:scale-110 transition-transform" />
                </div>
                <p className="text-2xl font-bold text-red-600 dark:text-red-400 mt-1">
                  {containersStats.vulnerable}
                </p>
                <p className="text-[11px] text-red-500/80 dark:text-red-400/80 mt-0.5">建议执行 Trivy 漏洞加固</p>
              </button>
            </div>

            {/* 2. Search & Filters Bar */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4">
              <div className="flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
                {/* Search input */}
                <div className="relative flex-1">
                  <Search className="w-4 h-4 text-gray-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={containerSearch}
                    onChange={(e) => {
                      setContainerSearch(e.target.value);
                      setContainerPage(1);
                      loadContainers({ search: e.target.value, page: 1 });
                    }}
                    placeholder={t("searchContainers")}
                    className="w-full pl-10 pr-9 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                  />
                  {containerSearch && (
                    <button
                      onClick={() => {
                        setContainerSearch("");
                        setContainerPage(1);
                        loadContainers({ search: "", page: 1 });
                      }}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>

                {/* Filters */}
                <div className="flex flex-wrap items-center gap-2">
                  {/* Status filter */}
                  <select
                    value={containerStatusFilter}
                    onChange={(e) => {
                      setContainerStatusFilter(e.target.value);
                      setContainerPage(1);
                      loadContainers({ status: e.target.value, page: 1 });
                    }}
                    className="px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg text-xs text-gray-700 dark:text-gray-200 focus:outline-none focus:border-blue-500"
                  >
                    <option value="all">{t("allStatuses")}</option>
                    <option value="running">{t("running")}</option>
                    <option value="warning">{t("warning")}</option>
                    <option value="terminated">{t("terminated")}</option>
                  </select>

                  {/* Namespace filter */}
                  <select
                    value={containerNsFilter}
                    onChange={(e) => {
                      setContainerNsFilter(e.target.value);
                      setContainerPage(1);
                      loadContainers({ namespace: e.target.value, page: 1 });
                    }}
                    className="px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg text-xs text-gray-700 dark:text-gray-200 focus:outline-none focus:border-blue-500"
                  >
                    <option value="">{t("allNamespaces")}</option>
                    <option value="production">production</option>
                    <option value="staging">staging</option>
                    <option value="ingress-nginx">ingress-nginx</option>
                    <option value="monitoring">monitoring</option>
                    <option value="kube-system">kube-system</option>
                    <option value="default">default</option>
                  </select>

                  {/* Cluster filter */}
                  <select
                    value={containerClusterFilter}
                    onChange={(e) => {
                      setContainerClusterFilter(e.target.value);
                      setContainerPage(1);
                      loadContainers({ cluster: e.target.value, page: 1 });
                    }}
                    className="px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg text-xs text-gray-700 dark:text-gray-200 focus:outline-none focus:border-blue-500"
                  >
                    <option value="">全部集群</option>
                    <option value="k8s-prod-cluster">k8s-prod-cluster (36)</option>
                    <option value="k8s-staging-cluster">k8s-staging-cluster (9)</option>
                  </select>

                  {/* Refresh */}
                  <button
                    onClick={() => loadContainers({ page: containerPage })}
                    disabled={loadingContainers}
                    className="p-2 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-300 transition-colors"
                    title="刷新列表"
                  >
                    <RefreshCw className={`w-4 h-4 ${loadingContainers ? "animate-spin text-blue-500" : ""}`} />
                  </button>
                </div>
              </div>
            </div>

            {/* 3. Containers Table */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Container className="w-5 h-5 text-emerald-500" />
                  <h3 className="font-semibold text-gray-900 dark:text-white">
                    {t("containersList")}
                  </h3>
                  <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300 rounded-full text-xs font-semibold">
                    {containers.length} 个实例
                  </span>
                </div>
                <span className="text-xs text-gray-400">
                  点击任意容器行查看端口映射、挂载卷、环境与安全上下文
                </span>
              </div>

              {/* Table Body Area with preserved height to prevent scroll jumping */}
              <div className="relative min-h-[420px]">
                {/* Overlay loading indicator during pagination or filter refresh */}
                {loadingContainers && containers.length > 0 && (
                  <div className="absolute inset-0 bg-white/60 dark:bg-gray-800/60 z-10 flex items-center justify-center backdrop-blur-[1px] transition-all">
                    <div className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 shadow-md rounded-lg text-xs font-medium text-gray-700 dark:text-gray-200">
                      <div className="w-4 h-4 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
                      <span>正在加载第 {containerPage} 页数据...</span>
                    </div>
                  </div>
                )}

                {loadingContainers && containers.length === 0 ? (
                  <div className="py-24 text-center text-sm text-gray-400 flex items-center justify-center gap-2">
                    <div className="w-5 h-5 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
                    正在加载容器资产列表...
                  </div>
                ) : containers.length === 0 ? (
                  <div className="py-20 text-center text-sm text-gray-400 space-y-2">
                    <Container className="w-8 h-8 text-gray-300 dark:text-gray-600 mx-auto" />
                    <p>{t("noContainersFound")}</p>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="bg-gray-50/80 dark:bg-gray-750/80 text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700">
                        <th className="py-3 px-4 font-semibold">{t("containerName")}</th>
                        <th className="py-3 px-3 font-semibold">{t("status")}</th>
                        <th className="py-3 px-3 font-semibold">集群 / 命名空间</th>
                        <th className="py-3 px-4 font-semibold">{t("image")}</th>
                        <th className="py-3 px-3 font-semibold">{t("securityContext")}</th>
                        <th className="py-3 px-3 font-semibold">已知漏洞</th>
                        <th className="py-3 px-3 font-semibold">资源配额</th>
                        <th className="py-3 px-4 font-semibold text-right">操作</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100 dark:divide-gray-700/60">
                      {containers.map((cnt) => (
                        <tr
                          key={cnt.id}
                          className="hover:bg-blue-50/40 dark:hover:bg-blue-900/10 transition-colors group cursor-pointer"
                          onClick={() => openContainerInspector(cnt.id)}
                        >
                          {/* Container Name & ID */}
                          <td className="py-3 px-4">
                            <div className="flex items-center gap-2">
                              <span className="font-semibold text-gray-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                                {cnt.name}
                              </span>
                            </div>
                            <div className="flex items-center gap-1.5 mt-0.5 text-gray-400 font-mono text-[11px]">
                              <span>ID: {cnt.id}</span>
                              <span>·</span>
                              <span>Pod: {cnt.pod_name}</span>
                            </div>
                          </td>

                          {/* Status */}
                          <td className="py-3 px-3 whitespace-nowrap">
                            {cnt.status === "running" ? (
                              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300">
                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                                {t("running")}
                              </span>
                            ) : cnt.status === "warning" ? (
                              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300">
                                <AlertTriangle className="w-3 h-3 text-amber-600 dark:text-amber-400" />
                                {cnt.state_reason || t("warning")}
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300">
                                <span className="w-1.5 h-1.5 rounded-full bg-gray-400" />
                                {cnt.state_reason || t("terminated")}
                              </span>
                            )}
                          </td>

                          {/* Cluster & Namespace */}
                          <td className="py-3 px-3 whitespace-nowrap">
                            <div className="text-gray-900 dark:text-gray-200 font-medium text-[11px]">
                              {cnt.cluster_name}
                            </div>
                            <span className="inline-block mt-0.5 px-2 py-0.2 rounded bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 text-[10px] font-mono">
                              {cnt.namespace}
                            </span>
                          </td>

                          {/* Image */}
                          <td className="py-3 px-4">
                            <div className="font-mono text-gray-800 dark:text-gray-200 text-[11px] max-w-[220px] truncate" title={cnt.image}>
                              {cnt.image}
                            </div>
                            {cnt.ports && cnt.ports.length > 0 ? (
                              <div className="text-gray-400 text-[10px] font-mono mt-0.5">
                                Ports: {cnt.ports.join(", ")}
                              </div>
                            ) : (
                              <div className="text-gray-400 text-[10px] mt-0.5">无暴露端口</div>
                            )}
                          </td>

                          {/* Security Context Badges */}
                          <td className="py-3 px-3">
                            <div className="flex flex-wrap gap-1">
                              {cnt.privileged ? (
                                <span className="px-1.5 py-0.5 rounded bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300 text-[10px] font-semibold flex items-center gap-0.5">
                                  <AlertTriangle className="w-2.5 h-2.5" /> 特权容器
                                </span>
                              ) : (
                                <span className="px-1.5 py-0.5 rounded bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300 text-[10px]">
                                  非特权
                                </span>
                              )}

                              {cnt.run_as_root ? (
                                <span className="px-1.5 py-0.5 rounded bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-300 text-[10px] font-medium">
                                  Root运行
                                </span>
                              ) : (
                                <span className="px-1.5 py-0.5 rounded bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-300 text-[10px]">
                                  非Root
                                </span>
                              )}

                              {cnt.readonly_rootfs && (
                                <span className="px-1.5 py-0.5 rounded bg-purple-50 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300 text-[10px]">
                                  只读FS
                                </span>
                              )}
                            </div>
                          </td>

                          {/* Vulnerabilities */}
                          <td className="py-3 px-3 whitespace-nowrap">
                            {cnt.vulnerabilities_count > 0 ? (
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  scanContainerFromList(cnt.image);
                                }}
                                className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300 hover:bg-red-200 transition-colors flex items-center gap-1"
                                title="点击直接进入 Trivy 扫描该镜像"
                              >
                                <AlertTriangle className="w-3 h-3" />
                                {cnt.vulnerabilities_count} 个已知漏洞
                              </button>
                            ) : (
                              <span className="inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-400 text-[11px]">
                                <CheckCircle className="w-3 h-3" />
                                安全
                              </span>
                            )}
                          </td>

                          {/* Resources */}
                          <td className="py-3 px-3 whitespace-nowrap font-mono text-gray-600 dark:text-gray-400 text-[11px]">
                            <div>CPU: {cnt.cpu_usage}</div>
                            <div>MEM: {cnt.memory_usage}</div>
                          </td>

                          {/* Actions */}
                          <td className="py-3 px-4 text-right whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                            <div className="flex items-center justify-end gap-2">
                              <button
                                onClick={() => openContainerInspector(cnt.id)}
                                className="px-2.5 py-1 bg-gray-100 hover:bg-blue-50 text-gray-700 hover:text-blue-600 dark:bg-gray-700 dark:hover:bg-gray-600 dark:text-gray-200 rounded text-xs font-medium transition-colors flex items-center gap-1"
                              >
                                <Info className="w-3 h-3" />
                                {t("viewDetails")}
                              </button>
                              <button
                                onClick={() => scanContainerFromList(cnt.image)}
                                className="px-2.5 py-1 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:hover:bg-emerald-900/50 dark:text-emerald-300 rounded text-xs font-medium transition-colors flex items-center gap-1"
                                title={t("scanImageAction")}
                              >
                                <Scan className="w-3 h-3" />
                                扫描
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              </div>

              {/* Pagination Controls */}
              <div className="px-6 py-3.5 border-t border-gray-200 dark:border-gray-700 bg-gray-50/70 dark:bg-gray-800/60 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-gray-600 dark:text-gray-300">
                <div className="flex items-center gap-3">
                  <span>
                    {t("showingPagination", {
                      start: containerFilteredTotal > 0 ? (containerPage - 1) * containerPageSize + 1 : 0,
                      end: Math.min(containerPage * containerPageSize, containerFilteredTotal),
                      total: containerFilteredTotal,
                    })}
                    {containerFilteredTotal !== containersStats.total && (
                      <span className="text-gray-400 ml-1">
                        {t("filteredFromTotal", { total: containersStats.total })}
                      </span>
                    )}
                  </span>

                  <div className="flex items-center gap-1.5 border-l border-gray-200 dark:border-gray-700 pl-3">
                    <span className="text-gray-500">{t("perPage")}:</span>
                    <select
                      value={containerPageSize}
                      onChange={(e) => {
                        const newSize = Number(e.target.value);
                        setContainerPageSize(newSize);
                        setContainerPage(1);
                        loadContainers({ page: 1, pageSize: newSize });
                      }}
                      className="px-2 py-1 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded text-xs text-gray-700 dark:text-gray-200 focus:outline-none focus:border-blue-500 cursor-pointer"
                    >
                      <option value={10}>10 条/页</option>
                      <option value={20}>20 条/页</option>
                      <option value={50}>50 条/页</option>
                    </select>
                  </div>
                </div>

                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={(e) => {
                      e.preventDefault();
                      if (containerPage > 1) {
                        const p = containerPage - 1;
                        setContainerPage(p);
                        loadContainers({ page: p });
                      }
                    }}
                    disabled={containerPage <= 1 || loadingContainers}
                    className="px-2.5 py-1.5 rounded border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1 transition-colors"
                    title={t("prevPage")}
                  >
                    <ChevronLeft className="w-3.5 h-3.5" />
                    <span>{t("prevPage")}</span>
                  </button>

                  <div className="flex items-center gap-1 px-1">
                    {Array.from({ length: containerTotalPages }, (_, i) => i + 1).map((p) => {
                      if (
                        containerTotalPages > 7 &&
                        p !== 1 &&
                        p !== containerTotalPages &&
                        Math.abs(p - containerPage) > 1
                      ) {
                        if (p === 2 || p === containerTotalPages - 1) {
                          return (
                            <span key={p} className="px-1 text-gray-400">
                              ...
                            </span>
                          );
                        }
                        return null;
                      }

                      return (
                        <button
                          key={p}
                          type="button"
                          onClick={(e) => {
                            e.preventDefault();
                            if (p !== containerPage) {
                              setContainerPage(p);
                              loadContainers({ page: p });
                            }
                          }}
                          disabled={loadingContainers}
                          className={`min-w-[28px] h-7 px-2 rounded text-xs font-medium transition-colors ${
                            containerPage === p
                              ? "bg-blue-600 text-white font-semibold shadow-sm"
                              : "bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-600"
                          }`}
                        >
                          {p}
                        </button>
                      );
                    })}
                  </div>

                  <button
                    type="button"
                    onClick={(e) => {
                      e.preventDefault();
                      if (containerPage < containerTotalPages) {
                        const p = containerPage + 1;
                        setContainerPage(p);
                        loadContainers({ page: p });
                      }
                    }}
                    disabled={containerPage >= containerTotalPages || loadingContainers}
                    className="px-2.5 py-1.5 rounded border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1 transition-colors"
                    title={t("nextPage")}
                  >
                    <span>{t("nextPage")}</span>
                    <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                </div>
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

        {/* ══════════════════════════════════════════════════════════════ */}
        {/* ── MODAL 1: K8S CLUSTERS & RESOURCE EXPLORER ── */}
        {/* ══════════════════════════════════════════════════════════════ */}
        {clusterModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-white dark:bg-gray-800 rounded-2xl max-w-5xl w-full max-h-[90vh] flex flex-col shadow-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
              {/* Modal Header */}
              <div className="p-6 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between bg-gray-50/50 dark:bg-gray-750">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 bg-blue-100 dark:bg-blue-900/40 rounded-xl text-blue-600 dark:text-blue-400">
                    <Server className="w-6 h-6" />
                  </div>
                  <div>
                    <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                      {t("clusterDetails")}
                    </h2>
                    <p className="text-xs text-gray-500 mt-0.5">
                      查看集群拓扑、资源详情及执行 CIS 基准安全扫描
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setClusterModalOpen(false)}
                  className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Modal Body */}
              <div className="p-6 overflow-y-auto space-y-6 flex-1">
                {/* Cluster Selectors */}
                <div>
                  <label className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 block mb-2">
                    {t("clusterList")} ({clusters.length})
                  </label>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {clusters.map((cluster) => {
                      const isSelected = selectedCluster?.name === cluster.name;
                      return (
                        <div
                          key={cluster.name}
                          onClick={() => {
                            setSelectedCluster(cluster);
                            loadResources(cluster.name, activeResourceType, selectedNamespace);
                          }}
                          className={cn(
                            "p-4 rounded-xl border-2 transition-all cursor-pointer flex items-center justify-between",
                            isSelected
                              ? "border-blue-500 bg-blue-50/40 dark:bg-blue-900/20 shadow-sm"
                              : "border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600"
                          )}
                        >
                          <div className="space-y-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="font-semibold text-gray-900 dark:text-white truncate">
                                {cluster.name}
                              </span>
                              <span
                                className={cn(
                                  "px-2 py-0.5 rounded text-[11px] font-medium",
                                  cluster.status === "healthy"
                                    ? "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300"
                                    : "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300"
                                )}
                              >
                                {cluster.status === "healthy" ? t("healthy") : t("warning")}
                              </span>
                            </div>
                            <p className="text-xs text-gray-500 dark:text-gray-400">
                              {cluster.provider} • {cluster.region} • {cluster.version}
                            </p>
                          </div>
                          <div className="text-right flex-shrink-0 pl-3">
                            <p className="text-sm font-bold text-gray-900 dark:text-white">
                              {cluster.nodes_count} {t("nodes")} / {cluster.pods_count} Pods
                            </p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Selected Cluster Toolbar & Actions */}
                {selectedCluster && (
                  <div className="bg-gray-50 dark:bg-gray-750 p-4 rounded-xl border border-gray-200 dark:border-gray-700 flex flex-wrap items-center justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                        {t("namespace")}:
                      </span>
                      <select
                        value={selectedNamespace}
                        onChange={(e) => {
                          setSelectedNamespace(e.target.value);
                          loadResources(selectedCluster.name, activeResourceType, e.target.value);
                        }}
                        className="text-xs px-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                      >
                        <option value="">{t("allNamespaces")}</option>
                        {selectedCluster.namespaces.map((ns) => (
                          <option key={ns} value={ns}>
                            {ns}
                          </option>
                        ))}
                      </select>
                    </div>

                    <button
                      onClick={() => runClusterScan(selectedCluster.name, selectedNamespace)}
                      disabled={k8sScanning}
                      className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-xs font-medium flex items-center gap-2 transition-colors disabled:opacity-50"
                    >
                      {k8sScanning ? (
                        <>
                          <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                          {t("clusterScanning")}
                        </>
                      ) : (
                        <>
                          <Shield className="w-3.5 h-3.5" />
                          {t("runClusterScan")}
                        </>
                      )}
                    </button>
                  </div>
                )}

                {/* Cluster Scan Findings Output (if scanned) */}
                {k8sScanFindings && (
                  <div className="p-4 bg-amber-50/50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-800/40 rounded-xl space-y-3">
                    <div className="flex items-center justify-between">
                      <h3 className="text-sm font-bold text-amber-900 dark:text-amber-200 flex items-center gap-2">
                        <AlertTriangle className="w-4 h-4 text-amber-600" />
                        安全扫描发现 ({k8sScanFindings.length} 项隐患)
                      </h3>
                      <span className="text-xs text-gray-500">已完成 CIS 基准比对</span>
                    </div>
                    <div className="space-y-2">
                      {k8sScanFindings.map((f, idx) => (
                        <div
                          key={idx}
                          className="p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 text-xs space-y-1.5"
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-semibold text-gray-900 dark:text-white">
                              [{f.category}] {f.title}
                            </span>
                            <span className={getSeverityBadge(f.severity)}>{f.severity}</span>
                          </div>
                          <p className="text-gray-600 dark:text-gray-400">
                            资源: <code className="font-mono text-blue-600 dark:text-blue-400">{f.kind}/{f.resource_name}</code> (ns: {f.namespace})
                          </p>
                          <p className="text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/30 p-2 rounded">
                            <strong>加固建议:</strong> {f.remediation}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* K8s Resource Explorer Section */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                      <Layers className="w-4 h-4 text-blue-500" />
                      {t("resourceViewer")}
                    </h3>
                    <div className="flex gap-1 bg-gray-100 dark:bg-gray-700/60 p-1 rounded-lg">
                      {(["pods", "deployments", "services", "secrets", "configmaps"] as const).map(
                        (rtype) => (
                          <button
                            key={rtype}
                            onClick={() => {
                              setActiveResourceType(rtype);
                              if (selectedCluster) {
                                loadResources(selectedCluster.name, rtype, selectedNamespace);
                              }
                            }}
                            className={cn(
                              "px-2.5 py-1 text-xs font-medium rounded-md transition-all capitalize",
                              activeResourceType === rtype
                                ? "bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 shadow-sm"
                                : "text-gray-600 dark:text-gray-400 hover:text-gray-900"
                            )}
                          >
                            {rtype}
                          </button>
                        )
                      )}
                    </div>
                  </div>

                  {/* Resources Table */}
                  <div className="border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden">
                    {loadingResources ? (
                      <div className="p-8 text-center text-xs text-gray-400 flex items-center justify-center gap-2">
                        <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                        正在加载集群资源...
                      </div>
                    ) : clusterResources.length === 0 ? (
                      <div className="p-8 text-center text-xs text-gray-400">
                        当前命名空间下未找到 {activeResourceType} 资源
                      </div>
                    ) : (
                      <table className="w-full text-left text-xs">
                        <thead className="bg-gray-50 dark:bg-gray-750 text-gray-600 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700">
                          <tr>
                            <th className="px-4 py-2.5 font-medium">{t("resourceName")}</th>
                            <th className="px-4 py-2.5 font-medium">{t("namespace")}</th>
                            <th className="px-4 py-2.5 font-medium">{t("resourceType")}</th>
                            <th className="px-4 py-2.5 font-medium">{t("status")}</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100 dark:divide-gray-700/60 font-mono">
                          {clusterResources.map((res, idx) => (
                            <tr key={idx} className="hover:bg-gray-50 dark:hover:bg-gray-750/50">
                              <td className="px-4 py-2.5 text-gray-900 dark:text-white font-medium">
                                {res.name}
                              </td>
                              <td className="px-4 py-2.5 text-gray-500">{res.namespace}</td>
                              <td className="px-4 py-2.5">
                                <span className="px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-[11px] text-gray-700 dark:text-gray-300">
                                  {res.kind}
                                </span>
                              </td>
                              <td className="px-4 py-2.5">
                                <span className="inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-400">
                                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                                  {res.status?.phase || (res.status?.readyReplicas ? `${res.status.readyReplicas} Ready` : "Active")}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>
                </div>
              </div>

              {/* Modal Footer */}
              <div className="p-4 border-t border-gray-200 dark:border-gray-700 flex justify-end bg-gray-50 dark:bg-gray-750">
                <button
                  onClick={() => setClusterModalOpen(false)}
                  className="px-5 py-2 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-800 dark:text-white rounded-lg text-xs font-medium transition-colors"
                >
                  {t("close")}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════ */}
        {/* ── MODAL 2: CIS COMPLIANCE REPORT MODAL ── */}
        {/* ══════════════════════════════════════════════════════════════ */}
        {complianceModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-white dark:bg-gray-800 rounded-2xl max-w-4xl w-full max-h-[90vh] flex flex-col shadow-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
              <div className="p-6 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between bg-gray-50/50 dark:bg-gray-750">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 bg-green-100 dark:bg-green-900/40 rounded-xl text-green-600 dark:text-green-400">
                    <CheckCircle className="w-6 h-6" />
                  </div>
                  <div>
                    <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                      {t("cisComplianceReport")}
                    </h2>
                    <p className="text-xs text-gray-500 mt-0.5">
                      CIS Kubernetes Benchmark 100 项安全合规基线检查详情
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setComplianceModalOpen(false)}
                  className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="p-6 overflow-y-auto space-y-6 flex-1">
                {loadingCompliance ? (
                  <div className="py-16 text-center text-sm text-gray-400 flex items-center justify-center gap-2">
                    <div className="w-5 h-5 border-2 border-green-500 border-t-transparent rounded-full animate-spin" />
                    正在生成 CIS 合规审计报告...
                  </div>
                ) : (
                  <>
                    {/* Compliance Stats Cards */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      <div className="p-4 bg-gray-50 dark:bg-gray-750 rounded-xl text-center border border-gray-200 dark:border-gray-700">
                        <p className="text-2xl font-bold text-gray-900 dark:text-white">
                          {complianceReport?.cis_compliance?.total_checks ?? 100}
                        </p>
                        <p className="text-xs text-gray-500 mt-1">{t("totalChecks")}</p>
                      </div>
                      <div className="p-4 bg-green-50/60 dark:bg-green-900/20 rounded-xl text-center border border-green-200 dark:border-green-800">
                        <p className="text-2xl font-bold text-green-600">
                          {complianceReport?.cis_compliance?.passed ?? 85}
                        </p>
                        <p className="text-xs text-green-600 dark:text-green-400 mt-1">{t("passed")}</p>
                      </div>
                      <div className="p-4 bg-red-50/60 dark:bg-red-900/20 rounded-xl text-center border border-red-200 dark:border-red-800">
                        <p className="text-2xl font-bold text-red-600">
                          {complianceReport?.cis_compliance?.failed ?? 10}
                        </p>
                        <p className="text-xs text-red-600 dark:text-red-400 mt-1">{t("failed")}</p>
                      </div>
                      <div className="p-4 bg-blue-50/60 dark:bg-blue-900/20 rounded-xl text-center border border-blue-200 dark:border-blue-800">
                        <p className="text-2xl font-bold text-blue-600">
                          {complianceReport?.cis_compliance?.compliance_percentage ?? 85}%
                        </p>
                        <p className="text-xs text-blue-600 dark:text-blue-400 mt-1">
                          {t("compliancePercentage")}
                        </p>
                      </div>
                    </div>

                    {/* Failed Items & Remediation */}
                    <div className="space-y-3">
                      <h3 className="text-sm font-bold text-gray-900 dark:text-white">
                        {t("failedChecksAndRemediation")}
                      </h3>
                      <div className="space-y-2">
                        {complianceReport?.findings?.map((item) => (
                          <div
                            key={item.id}
                            className="p-4 bg-gray-50 dark:bg-gray-750 border border-gray-200 dark:border-gray-700 rounded-xl text-xs space-y-2"
                          >
                            <div className="flex items-center justify-between">
                              <span className="font-semibold text-gray-900 dark:text-white text-sm">
                                [{item.category}] {item.title}
                              </span>
                              <span className={getSeverityBadge(item.severity)}>{item.severity}</span>
                            </div>
                            <p className="text-gray-500">受影响资源: <code className="font-mono text-gray-800 dark:text-gray-200">{item.resource}</code> (namespace: {item.namespace})</p>
                            <div className="p-2.5 bg-emerald-50 dark:bg-emerald-950/30 text-emerald-800 dark:text-emerald-300 rounded-lg">
                              <strong>加固指导:</strong> {item.remediation}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </>
                )}
              </div>

              <div className="p-4 border-t border-gray-200 dark:border-gray-700 flex justify-end bg-gray-50 dark:bg-gray-750">
                <button
                  onClick={() => setComplianceModalOpen(false)}
                  className="px-5 py-2 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-800 dark:text-white rounded-lg text-xs font-medium transition-colors"
                >
                  {t("close")}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════ */}
        {/* ── MODAL 3: SECURITY FINDINGS DETAILS MODAL ── */}
        {/* ══════════════════════════════════════════════════════════════ */}
        {findingsModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-white dark:bg-gray-800 rounded-2xl max-w-4xl w-full max-h-[90vh] flex flex-col shadow-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
              <div className="p-6 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between bg-gray-50/50 dark:bg-gray-750">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 bg-red-100 dark:bg-red-900/40 rounded-xl text-red-600 dark:text-red-400">
                    <Shield className="w-6 h-6" />
                  </div>
                  <div>
                    <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                      {t("securityFindings")}
                    </h2>
                    <p className="text-xs text-gray-500 mt-0.5">
                      按严重程度筛选查看云原生与容器安全风险细节
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setFindingsModalOpen(false)}
                  className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Filter Tabs */}
              <div className="px-6 py-3 border-b border-gray-200 dark:border-gray-700 flex items-center gap-2 bg-gray-50/30">
                <span className="text-xs font-semibold text-gray-500">{t("filterBySeverity")}:</span>
                {(["all", "critical", "high", "medium", "low"] as const).map((sev) => (
                  <button
                    key={sev}
                    onClick={() => setFindingsFilter(sev)}
                    className={cn(
                      "px-3 py-1 rounded-lg text-xs font-medium transition-all capitalize",
                      findingsFilter === sev
                        ? "bg-blue-600 text-white shadow-sm"
                        : "bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200"
                    )}
                  >
                    {sev}
                  </button>
                ))}
              </div>

              <div className="p-6 overflow-y-auto space-y-3 flex-1">
                {allFindings
                  .filter(
                    (f) => findingsFilter === "all" || f.severity.toLowerCase() === findingsFilter
                  )
                  .map((f, idx) => (
                    <div
                      key={idx}
                      className="p-4 bg-gray-50 dark:bg-gray-750 border border-gray-200 dark:border-gray-700 rounded-xl text-xs space-y-2"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-gray-900 dark:text-white text-sm">
                          [{f.category}] {f.title}
                        </span>
                        <span className={getSeverityBadge(f.severity)}>{f.severity}</span>
                      </div>
                      <p className="text-gray-500">
                        涉及资源: <code className="font-mono text-blue-600 dark:text-blue-400">{f.resource_name}</code> (namespace: {f.namespace})
                      </p>
                      <p className="text-gray-600 dark:text-gray-300">{f.description}</p>
                      <div className="p-2.5 bg-emerald-50 dark:bg-emerald-950/30 text-emerald-800 dark:text-emerald-300 rounded-lg">
                        <strong>加固方案:</strong> {f.remediation}
                      </div>
                    </div>
                  ))}
              </div>

              <div className="p-4 border-t border-gray-200 dark:border-gray-700 flex justify-end bg-gray-50 dark:bg-gray-750">
                <button
                  onClick={() => setFindingsModalOpen(false)}
                  className="px-5 py-2 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-800 dark:text-white rounded-lg text-xs font-medium transition-colors"
                >
                  {t("close")}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════ */}
        {/* ── MODAL 4: CLOUD PROVIDER DETAILS MODAL ── */}
        {/* ══════════════════════════════════════════════════════════════ */}
        {cloudModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-white dark:bg-gray-800 rounded-2xl max-w-3xl w-full max-h-[90vh] flex flex-col shadow-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
              <div className="p-6 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between bg-gray-50/50 dark:bg-gray-750">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 bg-sky-100 dark:bg-sky-900/40 rounded-xl text-sky-600 dark:text-sky-400">
                    <Cloud className="w-6 h-6" />
                  </div>
                  <div>
                    <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                      {t("cloudProviderDetails")} — {selectedCloudProvider?.toUpperCase()}
                    </h2>
                    <p className="text-xs text-gray-500 mt-0.5">
                      多云环境凭据配置与云端安全事件监控
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setCloudModalOpen(false)}
                  className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="p-6 overflow-y-auto space-y-5 flex-1">
                {/* Configuration guide card */}
                <div className="p-4 bg-sky-50/50 dark:bg-sky-900/10 border border-sky-200 dark:border-sky-800 rounded-xl text-xs space-y-2">
                  <h3 className="font-semibold text-sky-900 dark:text-sky-200 flex items-center gap-2">
                    <Info className="w-4 h-4" />
                    {t("configureGuide")}
                  </h3>
                  <p className="text-sky-800 dark:text-sky-300">
                    在后端运行环境或 Docker compose 文件中设置以下环境变量以点亮此连接：
                  </p>
                  <code className="block p-2.5 bg-sky-100/60 dark:bg-sky-950/40 rounded text-sky-900 dark:text-sky-200 font-mono text-[11px]">
                    {selectedCloudProvider === "aws" && "AWS_ACCESS_KEY_ID=your-key\nAWS_SECRET_ACCESS_KEY=your-secret"}
                    {selectedCloudProvider === "alicloud" && "ALICLOUD_ACCESS_KEY=your-key\nALICLOUD_SECRET_KEY=your-secret"}
                    {selectedCloudProvider === "azure" && "AZURE_SUBSCRIPTION_ID=your-sub-id"}
                    {selectedCloudProvider === "gcp" && "GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json"}
                  </code>
                </div>

                {/* Cloud security events list */}
                <div className="space-y-3">
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-white flex items-center justify-between">
                    <span>云安全审计事件 (近 24 小时)</span>
                    <span className="text-xs text-gray-400 font-normal">CloudTrail / Activity Logs</span>
                  </h3>
                  {loadingCloudEvents ? (
                    <div className="py-8 text-center text-xs text-gray-400 flex items-center justify-center gap-2">
                      <div className="w-4 h-4 border-2 border-sky-500 border-t-transparent rounded-full animate-spin" />
                      正在加载云端事件...
                    </div>
                  ) : cloudEvents.length === 0 ? (
                    <div className="p-8 text-center text-xs text-gray-400 bg-gray-50 dark:bg-gray-750 rounded-xl border border-dashed border-gray-200 dark:border-gray-700">
                      暂无未处理的云安全事件。连接凭证配置后将自动实时同步。
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {cloudEvents.map((evt, idx) => (
                        <div
                          key={idx}
                          className="p-3 bg-gray-50 dark:bg-gray-750 border border-gray-200 dark:border-gray-700 rounded-lg text-xs space-y-1"
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-semibold text-gray-900 dark:text-white">
                              [{evt.service}] {evt.event_type}
                            </span>
                            <span className={getSeverityBadge(evt.severity)}>{evt.severity}</span>
                          </div>
                          <p className="text-gray-600 dark:text-gray-300">{evt.description}</p>
                          <p className="text-gray-400 text-[11px] font-mono">Resource: {evt.resource_id}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              <div className="p-4 border-t border-gray-200 dark:border-gray-700 flex justify-end bg-gray-50 dark:bg-gray-750">
                <button
                  onClick={() => setCloudModalOpen(false)}
                  className="px-5 py-2 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-800 dark:text-white rounded-lg text-xs font-medium transition-colors"
                >
                  {t("close")}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════ */}
        {/* ── MODAL 5: CONTAINER INSPECTOR MODAL ── */}
        {/* ══════════════════════════════════════════════════════════════ */}
        {containerDetailModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-white dark:bg-gray-800 rounded-2xl max-w-4xl w-full max-h-[90vh] flex flex-col shadow-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
              {/* Modal Header */}
              <div className="p-6 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between bg-gray-50/50 dark:bg-gray-750">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 bg-emerald-100 dark:bg-emerald-900/40 rounded-xl text-emerald-600 dark:text-emerald-400">
                    <Container className="w-6 h-6" />
                  </div>
                  <div>
                    <h2 className="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                      {selectedContainer?.name || t("containerDetails")}
                      {selectedContainer && (
                        <span className={`text-xs px-2.5 py-0.5 rounded-full font-medium ${
                          selectedContainer.status === "running"
                            ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300"
                            : selectedContainer.status === "warning"
                            ? "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300"
                            : "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300"
                        }`}>
                          {selectedContainer.status}
                        </span>
                      )}
                    </h2>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {selectedContainer?.cluster_name} · 命名空间: {selectedContainer?.namespace} · Pod: {selectedContainer?.pod_name}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setContainerDetailModalOpen(false)}
                  className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Modal Body */}
              <div className="p-6 overflow-y-auto space-y-6 flex-1 text-xs">
                {loadingContainerDetail ? (
                  <div className="py-20 text-center text-sm text-gray-400 flex items-center justify-center gap-2">
                    <div className="w-5 h-5 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
                    正在拉取容器配置与安全详情...
                  </div>
                ) : selectedContainer ? (
                  <>
                    {/* Security Context & Compliance Warnings */}
                    <div className="bg-gradient-to-r from-gray-50 to-gray-100 dark:from-gray-750 dark:to-gray-800 p-4 rounded-xl border border-gray-200 dark:border-gray-700 space-y-3">
                      <div className="flex items-center gap-2 text-sm font-bold text-gray-900 dark:text-white">
                        <Shield className="w-4 h-4 text-blue-500" />
                        安全上下文与合规策略核查
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                        <div className={`p-3 rounded-lg border ${
                          selectedContainer.privileged
                            ? "bg-red-50 border-red-200 text-red-800 dark:bg-red-900/20 dark:border-red-800 dark:text-red-300"
                            : "bg-green-50 border-green-200 text-green-800 dark:bg-green-900/20 dark:border-green-800 dark:text-green-300"
                        }`}>
                          <div className="font-semibold">特权容器 (Privileged)</div>
                          <div className="mt-1 text-xs">
                            {selectedContainer.privileged ? "⚠️ 允许特权模式 (存在逃逸风险)" : "✓ 已禁用 (合规)"}
                          </div>
                        </div>

                        <div className={`p-3 rounded-lg border ${
                          selectedContainer.run_as_root
                            ? "bg-amber-50 border-amber-200 text-amber-800 dark:bg-amber-900/20 dark:border-amber-800 dark:text-amber-300"
                            : "bg-green-50 border-green-200 text-green-800 dark:bg-green-900/20 dark:border-green-800 dark:text-green-300"
                        }`}>
                          <div className="font-semibold">用户权限 (RunAsUser)</div>
                          <div className="mt-1 text-xs">
                            {selectedContainer.run_as_root ? "⚠️ 以 Root 身份执行" : "✓ 非 Root 用户执行 (合规)"}
                          </div>
                        </div>

                        <div className={`p-3 rounded-lg border ${
                          selectedContainer.readonly_rootfs
                            ? "bg-green-50 border-green-200 text-green-800 dark:bg-green-900/20 dark:border-green-800 dark:text-green-300"
                            : "bg-gray-50 border-gray-200 text-gray-700 dark:bg-gray-700/50 dark:border-gray-600 dark:text-gray-300"
                        }`}>
                          <div className="font-semibold">只读根文件系统</div>
                          <div className="mt-1 text-xs">
                            {selectedContainer.readonly_rootfs ? "✓ ReadOnlyRootFS 已开启" : "未开启 (建议加固开启)"}
                          </div>
                        </div>
                      </div>

                      {selectedContainer.remediation && (
                        <div className="mt-2 p-3 bg-amber-50/80 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-800 rounded-lg text-amber-800 dark:text-amber-200 flex items-start gap-2">
                          <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                          <div>
                            <span className="font-semibold">安全建议：</span>
                            {selectedContainer.remediation}
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Basic & Runtime Specs Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {/* Left: General Info */}
                      <div className="bg-gray-50 dark:bg-gray-750 p-4 rounded-xl border border-gray-200 dark:border-gray-700 space-y-2.5">
                        <h4 className="font-bold text-gray-900 dark:text-white flex items-center gap-1.5 text-xs">
                          <HardDrive className="w-4 h-4 text-indigo-500" />
                          基础运行时规格
                        </h4>
                        <div className="grid grid-cols-2 gap-2 text-[11px]">
                          <div>
                            <span className="text-gray-400">容器 ID:</span>
                            <p className="font-mono text-gray-800 dark:text-gray-200 mt-0.5">{selectedContainer.id}</p>
                          </div>
                          <div>
                            <span className="text-gray-400">内部 IP:</span>
                            <p className="font-mono text-gray-800 dark:text-gray-200 mt-0.5">{selectedContainer.ip_address}</p>
                          </div>
                          <div>
                            <span className="text-gray-400">工作节点:</span>
                            <p className="font-mono text-gray-800 dark:text-gray-200 mt-0.5">{selectedContainer.node_name || "node-worker-01"}</p>
                          </div>
                          <div>
                            <span className="text-gray-400">重启次数:</span>
                            <p className="font-mono text-gray-800 dark:text-gray-200 mt-0.5">{selectedContainer.restart_count} 次</p>
                          </div>
                          <div>
                            <span className="text-gray-400">CPU 占用:</span>
                            <p className="font-mono text-gray-800 dark:text-gray-200 mt-0.5">{selectedContainer.cpu_usage}</p>
                          </div>
                          <div>
                            <span className="text-gray-400">内存占用:</span>
                            <p className="font-mono text-gray-800 dark:text-gray-200 mt-0.5">{selectedContainer.memory_usage}</p>
                          </div>
                        </div>
                      </div>

                      {/* Right: Network Ports & Image */}
                      <div className="bg-gray-50 dark:bg-gray-750 p-4 rounded-xl border border-gray-200 dark:border-gray-700 space-y-2.5">
                        <h4 className="font-bold text-gray-900 dark:text-white flex items-center gap-1.5 text-xs">
                          <Scan className="w-4 h-4 text-emerald-500" />
                          镜像与网络端口
                        </h4>
                        <div>
                          <span className="text-gray-400 text-[11px]">容器镜像:</span>
                          <p className="font-mono text-gray-900 dark:text-white text-xs font-semibold mt-0.5 break-all">
                            {selectedContainer.image}
                          </p>
                        </div>
                        <div>
                          <span className="text-gray-400 text-[11px]">暴露端口:</span>
                          <div className="flex flex-wrap gap-1.5 mt-1">
                            {selectedContainer.ports && selectedContainer.ports.length > 0 ? (
                              selectedContainer.ports.map((p, idx) => (
                                <span key={idx} className="px-2 py-0.5 bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300 rounded font-mono text-[11px]">
                                  {p}
                                </span>
                              ))
                            ) : (
                              <span className="text-gray-400 text-xs">无端口映射</span>
                            )}
                          </div>
                        </div>
                        <div>
                          <span className="text-gray-400 text-[11px]">已知漏洞状态:</span>
                          <p className="mt-0.5">
                            {selectedContainer.vulnerabilities_count > 0 ? (
                              <span className="text-red-600 dark:text-red-400 font-semibold">
                                检测到 {selectedContainer.vulnerabilities_count} 个漏洞 (含高危: {selectedContainer.high_vulns})
                              </span>
                            ) : (
                              <span className="text-emerald-600 dark:text-emerald-400 font-semibold">
                                未检测到已知 CVE 漏洞
                              </span>
                            )}
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* Entrypoint Command */}
                    {selectedContainer.command && selectedContainer.command.length > 0 && (
                      <div>
                        <h4 className="font-bold text-gray-900 dark:text-white mb-2 flex items-center gap-1.5 text-xs">
                          <Terminal className="w-4 h-4 text-gray-500" />
                          启动命令 (Entrypoint / Command)
                        </h4>
                        <div className="bg-gray-900 text-emerald-400 p-3 rounded-xl font-mono text-xs overflow-x-auto">
                          $ {selectedContainer.command.join(" ")}
                        </div>
                      </div>
                    )}

                    {/* Mounts */}
                    {selectedContainer.mounts && selectedContainer.mounts.length > 0 && (
                      <div>
                        <h4 className="font-bold text-gray-900 dark:text-white mb-2 flex items-center gap-1.5 text-xs">
                          <HardDrive className="w-4 h-4 text-purple-500" />
                          存储卷挂载 (Volume Mounts)
                        </h4>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                          {selectedContainer.mounts.map((m, idx) => (
                            <div key={idx} className="p-2 bg-gray-50 dark:bg-gray-750 border border-gray-200 dark:border-gray-700 rounded-lg font-mono text-[11px] text-gray-700 dark:text-gray-300">
                              📂 {m}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Environment Variables */}
                    {selectedContainer.env_vars && Object.keys(selectedContainer.env_vars).length > 0 && (
                      <div>
                        <h4 className="font-bold text-gray-900 dark:text-white mb-2 text-xs">
                          环境变量 (Environment Variables)
                        </h4>
                        <div className="bg-gray-50 dark:bg-gray-750 border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden divide-y divide-gray-200 dark:divide-gray-700">
                          {Object.entries(selectedContainer.env_vars).map(([k, v]) => (
                            <div key={k} className="p-2.5 flex items-center justify-between text-[11px] font-mono">
                              <span className="text-gray-500 dark:text-gray-400 font-semibold">{k}</span>
                              <span className="text-gray-800 dark:text-gray-200 bg-white dark:bg-gray-800 px-2 py-0.5 rounded border border-gray-200 dark:border-gray-700">{v}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </>
                ) : null}
              </div>

              {/* Modal Footer */}
              <div className="p-4 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between bg-gray-50 dark:bg-gray-750">
                {selectedContainer && (
                  <button
                    onClick={() => scanContainerFromList(selectedContainer.image)}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 shadow-sm"
                  >
                    <Scan className="w-4 h-4" />
                    对此镜像执行 Trivy 漏洞扫描
                  </button>
                )}
                <button
                  onClick={() => setContainerDetailModalOpen(false)}
                  className="px-5 py-2 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-800 dark:text-white rounded-lg text-xs font-medium transition-colors ml-auto"
                >
                  {t("close")}
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
