"use client";

import { useState, useEffect } from "react";
import { TabButton, TabList } from "@/components/ui/Tabs";
import { useRouter } from "@/i18n/navigation";
import { useFormatter, useTranslations, useLocale } from "next-intl";
import { loadAuthState, authFetchJSON, isAdmin, isAnalystOrAdmin } from "@/lib/auth";
import { PageHeader } from "@/components/common/PageHeader";
import { ErrorDisplay } from "@/components/common/ErrorDisplay";
import { getLocalizedRule, matchesRuleSearch } from "@/lib/correlationRulesI18n";
import {
  Link,
  Search,
  Plus,
  RefreshCw,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Loader2,
  Filter,
  ChevronLeft,
  ChevronRight,
  Shield,
  Clock,
  Activity,
  Eye,
  Edit2,
  Trash2,
  Lock,
  Sparkles,
} from "lucide-react";
import { RuleDetailsDrawer, CorrelationRule } from "./components/RuleDetailsDrawer";
import { RuleFormModal } from "./components/RuleFormModal";
import {
  IncidentDetailsDrawer,
  type Incident,
} from "./components/IncidentDetailsDrawer";

interface Stats {
  total_incidents: number;
  open_incidents: number;
  resolved_incidents: number;
  total_rules: number;
  enabled_rules: number;
  total_correlations_performed: number;
}

const SEVERITY_COLORS = {
  critical: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  high: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
  medium: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
  low: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
};

const STATUS_COLORS = {
  open: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  investigating: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
  resolved: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  closed: "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-400",
};

export default function CorrelationPage() {
  const router = useRouter();
  const locale = useLocale();
  const t = useTranslations("correlation");
  const format = useFormatter();
  const tCommon = useTranslations("common");

  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [rules, setRules] = useState<CorrelationRule[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<Error | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState<"incidents" | "rules">("incidents");
  const [search, setSearch] = useState("");
  const [severityFilter, setSeverityFilter] = useState("all");
  const [ruleSearch, setRuleSearch] = useState("");
  const [ruleStatusFilter, setRuleStatusFilter] = useState<"all" | "enabled" | "disabled">("all");
  const [togglingRuleId, setTogglingRuleId] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  // Detail Drawer & Create/Edit Modal State
  const [selectedRule, setSelectedRule] = useState<CorrelationRule | null>(null);
  const [isDetailsOpen, setIsDetailsOpen] = useState(false);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<CorrelationRule | null>(null);
  const [deletingRuleId, setDeletingRuleId] = useState<string | null>(null);

  // Incident Detail Drawer State
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [isIncidentDetailsOpen, setIsIncidentDetailsOpen] = useState(false);

  useEffect(() => {
    const authState = loadAuthState();
    if (!authState?.isAuthenticated) {
      router.push("/login");
      return;
    }
    fetchData();
  }, [router]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [incidentsData, rulesData, statsData] = await Promise.all([
        authFetchJSON<{ items?: Incident[]; total?: number } | Incident[]>(
          `/api/correlation/incidents?page=${page}&page_size=20`
        ).catch(() => []),
        authFetchJSON<{ rules?: CorrelationRule[]; count?: number } | CorrelationRule[]>(
          "/api/correlation/rules"
        ).catch(() => []),
        authFetchJSON<any>("/api/correlation/stats").catch(() => null),
      ]);

      const resolvedIncidents: Incident[] = Array.isArray(incidentsData)
        ? incidentsData
        : Array.isArray((incidentsData as any)?.items)
          ? (incidentsData as any).items
          : [];

      const resolvedRules: CorrelationRule[] = Array.isArray(rulesData)
        ? rulesData
        : Array.isArray((rulesData as any)?.rules)
          ? (rulesData as any).rules
          : [];

      const normalizedStats: Stats = {
        total_incidents:
          statsData?.total_incidents ?? statsData?.incidents?.total ?? resolvedIncidents.length,
        open_incidents: statsData?.open_incidents ?? statsData?.incidents?.by_status?.open ?? 0,
        resolved_incidents:
          statsData?.resolved_incidents ?? statsData?.incidents?.by_status?.resolved ?? 0,
        total_rules: statsData?.total_rules ?? statsData?.rules?.total ?? resolvedRules.length,
        enabled_rules:
          statsData?.enabled_rules ??
          statsData?.rules?.active ??
          resolvedRules.filter((r) => r.enabled).length,
        total_correlations_performed:
          statsData?.total_correlations_performed ??
          statsData?.rules?.total_correlations_performed ??
          0,
      };

      setIncidents(resolvedIncidents);
      setRules(resolvedRules);
      setStats(normalizedStats);

      const totalIncidentsCount = Array.isArray(incidentsData)
        ? incidentsData.length
        : ((incidentsData as any)?.total ?? resolvedIncidents.length);
      setTotalPages(Math.max(1, Math.ceil(totalIncidentsCount / 20)));
      setLoadError(null);
    } catch (err) {
      console.error("Failed to fetch correlation data:", err);
      setLoadError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setLoading(false);
    }
  };

  const handleToggleRule = async (ruleId: string) => {
    setTogglingRuleId(ruleId);
    try {
      const res = await authFetchJSON<{ success: boolean; rule_id: string; enabled: boolean }>(
        `/api/correlation/rules/${ruleId}/toggle`,
        { method: "POST" }
      );
      if (res && res.success) {
        setRules((prev) => prev.map((r) => (r.id === ruleId ? { ...r, enabled: res.enabled } : r)));
        setSelectedRule((prev) =>
          prev && prev.id === ruleId ? { ...prev, enabled: res.enabled } : prev
        );
      }
    } catch (err) {
      console.error("Failed to toggle rule:", err);
    } finally {
      setTogglingRuleId(null);
    }
  };

  const handleViewRule = (rule: CorrelationRule) => {
    setSelectedRule(rule);
    setIsDetailsOpen(true);
  };

  const handleCreateRule = () => {
    setEditingRule(null);
    setIsFormOpen(true);
  };

  const handleEditRule = (rule: CorrelationRule) => {
    setEditingRule(rule);
    setIsDetailsOpen(false);
    setIsFormOpen(true);
  };

  const handleDeleteRule = async (ruleId: string) => {
    if (!window.confirm(t("deleteRuleConfirm"))) return;
    setDeletingRuleId(ruleId);
    try {
      await authFetchJSON(`/api/correlation/rules/${ruleId}`, { method: "DELETE" });
      setRules((prev) => prev.filter((r) => r.id !== ruleId));
      if (selectedRule?.id === ruleId) {
        setIsDetailsOpen(false);
        setSelectedRule(null);
      }
    } catch (err) {
      console.error("Failed to delete rule:", err);
    } finally {
      setDeletingRuleId(null);
    }
  };

  useEffect(() => {
    fetchData();
  }, [page]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchData();
    setRefreshing(false);
  };

  const handleViewIncident = (incident: Incident) => {
    setSelectedIncident(incident);
    setIsIncidentDetailsOpen(true);
  };

  const handleUpdateIncidentStatus = async (incidentId: string, newStatus: string) => {
    await authFetchJSON(
      `/api/correlation/incidents/${incidentId}/status?status=${encodeURIComponent(newStatus)}`,
      { method: "PUT" }
    );
    // Update local state
    setIncidents((prev) =>
      prev.map((item) => (item.id === incidentId ? { ...item, status: newStatus } : item))
    );
    if (selectedIncident && selectedIncident.id === incidentId) {
      setSelectedIncident((prev) => (prev ? { ...prev, status: newStatus } : null));
    }
  };

  const filteredIncidents = incidents.filter((incident) => {
    const matchesSearch =
      !search ||
      incident.title.toLowerCase().includes(search.toLowerCase()) ||
      incident.description?.toLowerCase().includes(search.toLowerCase());
    const matchesSeverity = severityFilter === "all" || incident.severity === severityFilter;
    return matchesSearch && matchesSeverity;
  });

  const filteredRules = rules.filter((rule) => {
    const matchesSearch = matchesRuleSearch(rule, ruleSearch, locale);
    const matchesStatus =
      ruleStatusFilter === "all" ||
      (ruleStatusFilter === "enabled" && rule.enabled) ||
      (ruleStatusFilter === "disabled" && !rule.enabled);
    return matchesSearch && matchesStatus;
  });

  if (loading) {
    return (
      <div className="min-h-screen bg-surface-ground">
        <PageHeader title={t("title")} subtitle={t("subtitle")} />
        <main className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="animate-pulse space-y-3">
            <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/3" />
            <div className="h-32 bg-gray-200 dark:bg-gray-700 rounded" />
            <div className="h-32 bg-gray-200 dark:bg-gray-700 rounded" />
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-surface-ground">
      <PageHeader title={t("title")} subtitle={t("subtitle")} />

      <main className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {loadError && (
          <div className="mb-4">
            <ErrorDisplay error={loadError} onRetry={fetchData} compact />
          </div>
        )}
        <div className="flex justify-between items-center mb-6">
          <TabList>
            <TabButton
              active={activeTab === "incidents"}
              onClick={() => setActiveTab("incidents")}
              label={t("incidents")}
            />
            <TabButton
              active={activeTab === "rules"}
              onClick={() => setActiveTab("rules")}
              label={t("rules")}
            />
          </TabList>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center gap-2 px-4 py-2 bg-accent-600 text-white rounded-lg hover:bg-accent-700 disabled:opacity-50 text-sm font-medium transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} />
            {t("refresh")}
          </button>
        </div>

        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-surface-card rounded-xl p-4 shadow-sm border border-border-subtle">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-purple-50 dark:bg-purple-950/50 rounded-lg">
                  <Link className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                </div>
                <div>
                  <p className="text-sm text-text-secondary">{t("totalIncidents")}</p>
                  <p className="text-2xl font-bold text-text-primary">{stats.total_incidents}</p>
                </div>
              </div>
            </div>
            <div className="bg-surface-card rounded-xl p-4 shadow-sm border border-border-subtle">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-rose-50 dark:bg-rose-950/50 rounded-lg">
                  <AlertTriangle className="w-5 h-5 text-rose-600 dark:text-rose-400" />
                </div>
                <div>
                  <p className="text-sm text-text-secondary">{t("openIncidents")}</p>
                  <p className="text-2xl font-bold text-rose-600 dark:text-rose-400">
                    {stats.open_incidents}
                  </p>
                </div>
              </div>
            </div>
            <div className="bg-surface-card rounded-xl p-4 shadow-sm border border-border-subtle">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-emerald-50 dark:bg-emerald-950/50 rounded-lg">
                  <CheckCircle className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
                </div>
                <div>
                  <p className="text-sm text-text-secondary">{t("resolvedIncidents")}</p>
                  <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">
                    {stats.resolved_incidents}
                  </p>
                </div>
              </div>
            </div>
            <div className="bg-surface-card rounded-xl p-4 shadow-sm border border-border-subtle">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-accent-50 dark:bg-accent-950/50 rounded-lg">
                  <Activity className="w-5 h-5 text-accent-600 dark:text-accent-400" />
                </div>
                <div>
                  <p className="text-sm text-text-secondary">{t("totalCorrelations")}</p>
                  <p className="text-2xl font-bold text-accent-600 dark:text-accent-400">
                    {stats.total_correlations_performed}
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab Content */}
        {activeTab === "incidents" ? (
          <>
            {/* Filters */}
            <div className="bg-surface-card rounded-xl shadow-sm border border-border-subtle p-4 mb-4">
              <div className="flex gap-4 flex-wrap">
                <div className="flex-1 min-w-[200px] relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
                  <input
                    type="text"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder={t("searchIncidents")}
                    className="w-full pl-10 pr-4 py-2 border border-border-subtle rounded-lg bg-surface-ground text-text-primary placeholder:text-text-muted text-sm focus:outline-none focus:border-accent-500 transition-colors"
                  />
                </div>
                <select
                  value={severityFilter}
                  onChange={(e) => setSeverityFilter(e.target.value)}
                  className="px-4 py-2 border border-border-subtle rounded-lg bg-surface-ground text-text-primary text-sm focus:outline-none focus:border-accent-500 transition-colors"
                >
                  <option value="all">{t("allSeverity")}</option>
                  <option value="critical">{t("critical")}</option>
                  <option value="high">{t("high")}</option>
                  <option value="medium">{t("medium")}</option>
                  <option value="low">{t("low")}</option>
                </select>
              </div>
            </div>

            {/* Incidents Table */}
            <div className="bg-surface-card rounded-xl shadow-sm border border-border-subtle overflow-hidden">
              {filteredIncidents.length === 0 ? (
                <div className="p-12 text-center">
                  <Link className="w-12 h-12 text-text-muted mx-auto mb-4 opacity-40" />
                  <p className="text-text-secondary text-sm font-medium">{t("noIncidents")}</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-border-subtle">
                    <thead className="bg-surface-hover/50">
                      <tr>
                        <th className="px-6 py-3.5 text-left text-xs font-semibold text-text-secondary uppercase tracking-wider">
                          {t("incident")}
                        </th>
                        <th className="px-6 py-3.5 text-left text-xs font-semibold text-text-secondary uppercase tracking-wider">
                          {t("severity")}
                        </th>
                        <th className="px-6 py-3.5 text-left text-xs font-semibold text-text-secondary uppercase tracking-wider">
                          {t("status")}
                        </th>
                        <th className="px-6 py-3.5 text-left text-xs font-semibold text-text-secondary uppercase tracking-wider">
                          {t("events")}
                        </th>
                        <th className="px-6 py-3.5 text-left text-xs font-semibold text-text-secondary uppercase tracking-wider">
                          {t("confidence")}
                        </th>
                        <th className="px-6 py-3.5 text-left text-xs font-semibold text-text-secondary uppercase tracking-wider">
                          {t("created")}
                        </th>
                        <th className="px-6 py-3.5 text-right text-xs font-semibold text-text-secondary uppercase tracking-wider">
                          {t("actions")}
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border-subtle">
                      {filteredIncidents.map((incident) => (
                        <tr
                          key={incident.id}
                          onClick={() => handleViewIncident(incident)}
                          className="hover:bg-surface-hover/50 transition-colors cursor-pointer group"
                          title="点击查看关联事件研判详情"
                        >
                          <td className="px-6 py-4">
                            <div>
                              <p className="text-sm font-medium text-text-primary group-hover:text-accent-600 transition-colors">
                                {incident.title}
                              </p>
                              {incident.description && (
                                <p className="text-xs text-text-secondary mt-1 line-clamp-1">
                                  {incident.description}
                                </p>
                              )}
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span
                              className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${SEVERITY_COLORS[incident.severity as keyof typeof SEVERITY_COLORS] || SEVERITY_COLORS.low}`}
                            >
                              {incident.severity}
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span
                              className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[incident.status as keyof typeof STATUS_COLORS] || STATUS_COLORS.open}`}
                            >
                              {incident.status}
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-text-secondary font-mono">
                            {incident.raw_event_count}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-text-secondary font-mono">
                            {(incident.confidence_score * 100).toFixed(0)}%
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-text-secondary">
                            {format.dateTime(new Date(incident.created_at), {
                              dateStyle: "medium",
                              timeStyle: "medium",
                            })}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleViewIncident(incident);
                              }}
                              title={t("viewIncident")}
                              className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-accent-600 dark:text-accent-400 bg-accent-50 dark:bg-accent-950/40 rounded-lg hover:bg-accent-100 dark:hover:bg-accent-900/60 transition-colors"
                            >
                              <Eye className="w-3.5 h-3.5" />
                              <span>{t("viewIncident")}</span>
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="px-6 py-4 border-t border-border-subtle flex items-center justify-between">
                  <p className="text-sm text-text-secondary">{t("pageOf", { page, totalPages })}</p>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page === 1}
                      className="px-3 py-1 border border-border-subtle rounded hover:bg-surface-hover text-text-secondary disabled:opacity-50 transition-colors"
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                      disabled={page === totalPages}
                      className="px-3 py-1 border border-border-subtle rounded hover:bg-surface-hover text-text-secondary disabled:opacity-50 transition-colors"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          </>
        ) : (
          /* Rules Tab */
          <>
            {/* Rules Filter Toolbar */}
            <div className="bg-surface-card rounded-xl shadow-sm border border-border-subtle p-4 mb-4">
              <div className="flex gap-4 flex-wrap items-center justify-between">
                <div className="flex-1 min-w-[240px] relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
                  <input
                    type="text"
                    value={ruleSearch}
                    onChange={(e) => setRuleSearch(e.target.value)}
                    placeholder={t("searchRulesPlaceholder")}
                    className="w-full pl-10 pr-4 py-2 border border-border-subtle rounded-lg bg-surface-ground text-text-primary placeholder:text-text-muted text-sm focus:outline-none focus:border-accent-500 transition-colors"
                  />
                </div>
                <div className="flex items-center gap-3">
                  <select
                    value={ruleStatusFilter}
                    onChange={(e) => setRuleStatusFilter(e.target.value as any)}
                    className="px-3.5 py-2 border border-border-subtle rounded-lg bg-surface-ground text-text-primary text-sm focus:outline-none focus:border-accent-500 transition-colors"
                  >
                    <option value="all">{t("allStatus")}</option>
                    <option value="enabled">{t("enabled")}</option>
                    <option value="disabled">{t("disabled")}</option>
                  </select>
                  <span className="text-xs text-text-muted whitespace-nowrap">
                    {t("rulesCount", { count: filteredRules.length })}
                  </span>
                  <button
                    type="button"
                    onClick={handleCreateRule}
                    className="flex items-center gap-1.5 px-3.5 py-2 bg-accent-600 text-white rounded-lg hover:bg-accent-700 text-xs font-semibold shadow-sm transition-colors cursor-pointer"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    {t("createRule")}
                  </button>
                </div>
              </div>
            </div>

            {/* Rules Table */}
            <div className="bg-surface-card rounded-xl shadow-sm border border-border-subtle overflow-hidden">
              {filteredRules.length === 0 ? (
                <div className="p-12 text-center">
                  <Shield className="w-12 h-12 text-text-muted mx-auto mb-4 opacity-40" />
                  <p className="text-text-secondary text-sm font-medium">{t("noRules")}</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-border-subtle">
                    <thead className="bg-surface-hover/50">
                      <tr>
                        <th className="px-6 py-3.5 text-left text-xs font-semibold text-text-secondary uppercase tracking-wider">
                          {t("rule")}
                        </th>
                        <th className="px-6 py-3.5 text-left text-xs font-semibold text-text-secondary uppercase tracking-wider">
                          {t("category")}
                        </th>
                        <th className="px-6 py-3.5 text-left text-xs font-semibold text-text-secondary uppercase tracking-wider">
                          {t("ruleType")}
                        </th>
                        <th className="px-6 py-3.5 text-left text-xs font-semibold text-text-secondary uppercase tracking-wider">
                          {t("priority")}
                        </th>
                        <th className="px-6 py-3.5 text-left text-xs font-semibold text-text-secondary uppercase tracking-wider">
                          {t("timeWindow")}
                        </th>
                        <th className="px-6 py-3.5 text-left text-xs font-semibold text-text-secondary uppercase tracking-wider">
                          {t("status")}
                        </th>
                        <th className="px-6 py-3.5 text-left text-xs font-semibold text-text-secondary uppercase tracking-wider">
                          {t("correlations")}
                        </th>
                        <th className="px-6 py-3.5 text-right text-xs font-semibold text-text-secondary uppercase tracking-wider">
                          {t("actions")}
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border-subtle">
                      {filteredRules.map((rule) => {
                        const isToggling = togglingRuleId === rule.id;
                        const isDeleting = deletingRuleId === rule.id;
                        const { displayName, displayDescription, displayCategory } =
                          getLocalizedRule(rule, locale);
                        const isZh = locale.startsWith("zh");
                        const isBuiltin = rule.is_builtin ?? !rule.id.includes("custom");
                        const showEnglishAlias =
                          isZh &&
                          rule.name !== displayName &&
                          !rule.name.includes("Demo Correlation Rule");

                        return (
                          <tr key={rule.id} className="hover:bg-surface-hover/50 transition-colors">
                            <td className="px-6 py-4">
                              <div
                                onClick={() => handleViewRule(rule)}
                                className="cursor-pointer group"
                                title="点击查看规则详情"
                              >
                                <p className="text-sm font-semibold text-text-primary group-hover:text-accent-600 transition-colors">
                                  {displayName}
                                </p>
                                {displayDescription && (
                                  <p className="text-xs text-text-secondary mt-1 line-clamp-1">
                                    {displayDescription}
                                  </p>
                                )}
                                {showEnglishAlias && (
                                  <p className="text-[11px] font-mono text-text-muted mt-0.5">
                                    {rule.name}
                                  </p>
                                )}
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300 border border-blue-200/60 dark:border-blue-800/40">
                                {displayCategory}
                              </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              {isBuiltin ? (
                                <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded font-medium bg-purple-50 text-purple-700 dark:bg-purple-950/40 dark:text-purple-300 border border-purple-200/50">
                                  <Lock className="w-2.5 h-2.5" />
                                  {t("builtinRule")}
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded font-medium bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300 border border-amber-200/50">
                                  <Sparkles className="w-2.5 h-2.5" />
                                  {t("customRule")}
                                </span>
                              )}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-text-secondary font-mono">
                              {rule.priority}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-text-secondary font-mono">
                              {rule.time_window_seconds}s
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              {rule.enabled ? (
                                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                                  {t("enabled")}
                                </span>
                              ) : (
                                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-surface-hover text-text-muted border border-border-subtle">
                                  {t("disabled")}
                                </span>
                              )}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-text-secondary font-mono">
                              {rule.total_correlations}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-right">
                              <div className="flex items-center justify-end gap-1.5">
                                <button
                                  type="button"
                                  onClick={() => handleViewRule(rule)}
                                  className="px-2.5 py-1 text-xs font-medium rounded-lg border border-border-subtle text-text-secondary hover:text-text-primary hover:bg-surface-hover transition-colors inline-flex items-center gap-1 cursor-pointer"
                                  title={t("view")}
                                >
                                  <Eye className="w-3.5 h-3.5" />
                                  {t("view")}
                                </button>
                                {!isBuiltin && (
                                  <>
                                    <button
                                      type="button"
                                      onClick={() => handleEditRule(rule)}
                                      className="p-1.5 text-xs rounded-lg border border-border-subtle text-text-secondary hover:text-text-primary hover:bg-surface-hover transition-colors cursor-pointer"
                                      title={t("edit")}
                                    >
                                      <Edit2 className="w-3.5 h-3.5" />
                                    </button>
                                    <button
                                      type="button"
                                      disabled={isDeleting}
                                      onClick={() => handleDeleteRule(rule.id)}
                                      className="p-1.5 text-xs rounded-lg border border-rose-200 dark:border-rose-900/50 text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/40 transition-colors disabled:opacity-50 cursor-pointer"
                                      title={t("delete")}
                                    >
                                      {isDeleting ? (
                                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                      ) : (
                                        <Trash2 className="w-3.5 h-3.5" />
                                      )}
                                    </button>
                                  </>
                                )}
                                <button
                                  type="button"
                                  disabled={isToggling}
                                  onClick={() => handleToggleRule(rule.id)}
                                  className={`text-xs px-2.5 py-1 rounded-lg border font-medium transition-colors disabled:opacity-50 cursor-pointer ${
                                    rule.enabled
                                      ? "border-rose-200 text-rose-600 hover:bg-rose-50 dark:border-rose-900/50 dark:text-rose-400 dark:hover:bg-rose-950/50"
                                      : "border-emerald-200 text-emerald-600 hover:bg-emerald-50 dark:border-emerald-900/50 dark:text-emerald-400 dark:hover:bg-emerald-950/50"
                                  }`}
                                >
                                  {isToggling ? (
                                    <Loader2 className="w-3.5 h-3.5 animate-spin inline" />
                                  ) : rule.enabled ? (
                                    t("disable")
                                  ) : (
                                    t("enable")
                                  )}
                                </button>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </>
        )}
      </main>

      {/* Rule Details Drawer */}
      <RuleDetailsDrawer
        rule={selectedRule}
        isOpen={isDetailsOpen}
        onClose={() => setIsDetailsOpen(false)}
        onToggle={handleToggleRule}
        isToggling={togglingRuleId === selectedRule?.id}
        onEdit={handleEditRule}
        onDelete={handleDeleteRule}
        isDeleting={deletingRuleId === selectedRule?.id}
      />

      {/* Incident Details Drawer */}
      <IncidentDetailsDrawer
        incident={selectedIncident}
        isOpen={isIncidentDetailsOpen}
        onClose={() => setIsIncidentDetailsOpen(false)}
        onStatusChange={handleUpdateIncidentStatus}
      />

      {/* Create / Edit Rule Modal */}
      <RuleFormModal
        isOpen={isFormOpen}
        onClose={() => setIsFormOpen(false)}
        initialData={editingRule}
        onSuccess={fetchData}
      />
    </div>
  );
}
