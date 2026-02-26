"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { loadAuthState, logout, authFetchJSON, isAdmin, isAnalystOrAdmin } from "@/lib/auth";
import Navigation from "@/components/Navigation";

interface AuditLog {
  id: string;
  user_id: string | null;
  username: string | null;
  action: string;
  method: string;
  path: string;
  status_code: number;
  target_type: string | null;
  target_id: string | null;
  ip_address: string | null;
  duration_ms: number | null;
  created_at: string;
}

interface AuditLogStats {
  total_requests: number;
  last_24h_requests: number;
  failed_requests: number;
}

export default function AuditLogsPage() {
  const router = useRouter();
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [stats, setStats] = useState<AuditLogStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize] = useState(50);
  const [total, setTotal] = useState(0);

  // Filters
  const [filterAction, setFilterAction] = useState("");
  const [filterPath, setFilterPath] = useState("");
  const [filterStatusCode, setFilterStatusCode] = useState("");
  const [filterDateFrom, setFilterDateFrom] = useState("");
  const [filterDateTo, setFilterDateTo] = useState("");
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [exporting, setExporting] = useState(false);
  const [showExportMenu, setShowExportMenu] = useState(false);

  // Helper function to format date for datetime-local input
  const formatDateForInput = (date: Date) => {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    return `${year}-${month}-${day}T${hours}:${minutes}`;
  };

  // Date range presets
  const datePresets = [
    {
      id: "15min",
      name: "🕐 15 min",
      label: "Last 15 minutes",
      getRange: () => {
        const now = new Date();
        const from = new Date(now.getTime() - 15 * 60 * 1000);
        return {
          from: formatDateForInput(from),
          to: formatDateForInput(now),
          display: "Last 15 minutes"
        };
      }
    },
    {
      id: "1hour",
      name: "🕐 1 hour",
      label: "Last hour",
      getRange: () => {
        const now = new Date();
        const from = new Date(now.getTime() - 60 * 60 * 1000);
        return {
          from: formatDateForInput(from),
          to: formatDateForInput(now),
          display: "Last hour"
        };
      }
    },
    {
      id: "today",
      name: "📅 Today",
      label: "Today",
      getRange: () => {
        const now = new Date();
        const from = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0);
        return {
          from: formatDateForInput(from),
          to: formatDateForInput(now),
          display: "Today"
        };
      }
    },
    {
      id: "yesterday",
      name: "📅 Yesterday",
      label: "Yesterday",
      getRange: () => {
        const now = new Date();
        const yesterday = new Date(now);
        yesterday.setDate(yesterday.getDate() - 1);
        const from = new Date(yesterday.getFullYear(), yesterday.getMonth(), yesterday.getDate(), 0, 0, 0);
        return {
          from: formatDateForInput(from),
          to: formatDateForInput(new Date(yesterday.getFullYear(), yesterday.getMonth(), yesterday.getDate(), 23, 59, 59)),
          display: "Yesterday"
        };
      }
    },
    {
      id: "7days",
      name: "📊 7 days",
      label: "Last 7 days",
      getRange: () => {
        const now = new Date();
        const from = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
        return {
          from: formatDateForInput(from),
          to: formatDateForInput(now),
          display: "Last 7 days"
        };
      }
    },
    {
      id: "30days",
      name: "📊 30 days",
      label: "Last 30 days",
      getRange: () => {
        const now = new Date();
        const from = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
        return {
          from: formatDateForInput(from),
          to: formatDateForInput(now),
          display: "Last 30 days"
        };
      }
    },
    {
      id: "thisWeek",
      name: "📊 This week",
      label: "This week",
      getRange: () => {
        const now = new Date();
        const dayOfWeek = now.getDay();
        // Calculate Monday of current week
        const daysFromMonday = dayOfWeek === 0 ? 6 : dayOfWeek - 1;
        const from = new Date(now);
        from.setDate(now.getDate() - daysFromMonday);
        from.setHours(0, 0, 0, 0);
        return {
          from: formatDateForInput(from),
          to: formatDateForInput(now),
          display: "This week"
        };
      }
    },
    {
      id: "thisMonth",
      name: "📊 This month",
      label: "This month",
      getRange: () => {
        const now = new Date();
        const from = new Date(now.getFullYear(), now.getMonth(), 1, 0, 0, 0);
        return {
          from: formatDateForInput(from),
          to: formatDateForInput(now),
          display: "This month"
        };
      }
    },
  ];

  // Simplified filter options - most commonly used
  const commonActions = [
    { value: "", label: "All Actions" },
    { value: "login:*", label: "Authentication" },
    { value: "users:*", label: "User Management" },
    { value: "playbook:*", label: "Playbooks" },
    { value: "assets:*", label: "Assets" },
    { value: "api_keys:*", label: "API Keys" },
  ];

  // Extended actions for advanced filters
  const extendedActions = [
    { value: "playbook_definitions:*", label: "Playbook Definitions" },
    { value: "ti:*", label: "Threat Intel" },
    { value: "ioc_hits:*", label: "IOC Hits" },
    { value: "alert:*", label: "Alert Analysis" },
    { value: "report:*", label: "Reports" },
    { value: "timeline:*", label: "Timelines" },
    { value: "audit_logs:*", label: "Audit Logs" },
    { value: "webhooks:*", label: "Webhooks" },
    { value: "history:*", label: "History" },
  ];

  const commonPaths = [
    { value: "", label: "All Paths" },
    { value: "/api/playbook*", label: "Playbooks" },
    { value: "/api/auth*", label: "Authentication" },
    { value: "/api/users*", label: "User Management" },
    { value: "/api/assets*", label: "Assets" },
  ];

  // Extended paths for advanced filters
  const extendedPaths = [
    { value: "/api/api-keys*", label: "API Keys" },
    { value: "/api/ti*", label: "Threat Intel" },
    { value: "/api/audit-logs*", label: "Audit Logs" },
    { value: "/api/webhooks*", label: "Webhooks" },
    { value: "/api/history*", label: "History" },
    { value: "/api/alert", label: "Alert Analysis" },
    { value: "/api/report", label: "Reports" },
    { value: "/api/timeline", label: "Timelines" },
  ];

  const statusCodes = [
    { value: "", label: "All Status" },
    { value: "success", label: "Success (2xx)" },
    { value: "error", label: "All Errors" },
    { value: "4xx", label: "Client Errors (4xx)" },
    { value: "5xx", label: "Server Errors (5xx)" },
  ];

  // Extended status codes for advanced filters
  const extendedStatusCodes = [
    { value: "200", label: "200 OK" },
    { value: "201", label: "201 Created" },
    { value: "204", label: "204 No Content" },
    { value: "400", label: "400 Bad Request" },
    { value: "401", label: "401 Unauthorized" },
    { value: "403", label: "403 Forbidden" },
    { value: "404", label: "404 Not Found" },
    { value: "422", label: "422 Unprocessable" },
    { value: "500", label: "500 Server Error" },
  ];

  // Simplified quick filter presets - most commonly used
  const quickFilters = [
    {
      name: "Errors",
      icon: "🔴",
      filter: { filterStatusCode: "error", filterAction: "", filterPath: "" },
      description: "Show only error responses"
    },
    {
      name: "Success",
      icon: "✅",
      filter: { filterStatusCode: "success", filterAction: "", filterPath: "" },
      description: "Only successful requests"
    },
    {
      name: "Login",
      icon: "🔐",
      filter: { filterAction: "login:*", filterStatusCode: "", filterPath: "" },
      description: "Login activity"
    },
    {
      name: "Users",
      icon: "👥",
      filter: { filterAction: "users:*", filterStatusCode: "", filterPath: "" },
      description: "User management"
    },
  ];

  useEffect(() => {
    const authState = loadAuthState();
    if (!authState?.isAuthenticated) {
      router.push("/login");
      return;
    }
    // Only admin and auditor can access audit logs
    if (!isAdmin(authState.user) && !isAnalystOrAdmin(authState.user)) {
      router.push("/");
      return;
    }
    // Initial load only
    if (loading) {
      fetchAuditLogs();
      fetchStats();
    }
  }, [router, page]);

  const fetchAuditLogs = async () => {
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
      });

      if (filterAction) params.append("action", filterAction);
      if (filterPath) params.append("path", filterPath);
      if (filterStatusCode) params.append("status_code", filterStatusCode);
      if (filterDateFrom) params.append("date_from", filterDateFrom);
      if (filterDateTo) params.append("date_to", filterDateTo);

      const data = await authFetchJSON<{ items: AuditLog[]; total: number }>(
        `/api/audit-logs?${params.toString()}`
      );

      setLogs(data.items);
      setTotal(data.total);
    } catch (err: any) {
      setError(err.message || "Failed to load audit logs");
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const data = await authFetchJSON<AuditLogStats>("/api/audit-logs/stats/summary");
      setStats(data);
    } catch (err: any) {
      console.error("Failed to load stats:", err);
    }
  };

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString();
  };

  const getStatusCodeClass = (statusCode: number) => {
    if (statusCode >= 200 && statusCode < 300) return "text-green-600 bg-green-100";
    if (statusCode >= 300 && statusCode < 400) return "text-blue-600 bg-blue-100";
    if (statusCode >= 400 && statusCode < 500) return "text-orange-600 bg-orange-100";
    if (statusCode >= 500) return "text-red-600 bg-red-100";
    return "text-gray-600 bg-gray-100";
  };

  const getMethodClass = (method: string) => {
    switch (method) {
      case "GET":
        return "bg-blue-100 text-blue-800";
      case "POST":
        return "bg-green-100 text-green-800";
      case "PUT":
        return "bg-yellow-100 text-yellow-800";
      case "PATCH":
        return "bg-purple-100 text-purple-800";
      case "DELETE":
        return "bg-red-100 text-red-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  const handleFilter = () => {
    setPage(1);
    fetchAuditLogs();
  };

  const handleClearFilters = () => {
    setFilterAction("");
    setFilterPath("");
    setFilterStatusCode("");
    setFilterDateFrom("");
    setFilterDateTo("");
    setPage(1);
    fetchAuditLogs();
  };

  const applyQuickFilter = (preset: typeof quickFilters[0]) => {
    setFilterAction(preset.filter.filterAction);
    setFilterPath(preset.filter.filterPath);
    setFilterStatusCode(preset.filter.filterStatusCode);
    setPage(1);
    fetchAuditLogs();
  };

  const applyDatePreset = (preset: typeof datePresets[0]) => {
    const range = preset.getRange();
    // Check if this preset is already selected - if so, toggle it off
    const isSelected = range.from === filterDateFrom && range.to === filterDateTo;

    if (isSelected) {
      // Toggle off - clear date filter
      setFilterDateFrom("");
      setFilterDateTo("");
      setPage(1);
      setTimeout(() => fetchAuditLogs(), 0);
    } else {
      // Apply the preset
      setFilterDateFrom(range.from);
      setFilterDateTo(range.to);
      setPage(1);
      setTimeout(() => fetchAuditLogs(), 0);
    }
  };

  const clearDateFilter = () => {
    setFilterDateFrom("");
    setFilterDateTo("");
    setPage(1);
    fetchAuditLogs();
  };

  const handleDateChange = (from: string, to: string) => {
    setFilterDateFrom(from);
    setFilterDateTo(to);
    // Don't auto-fetch on date change, wait for Apply Filters button
  };

  const getSelectedDateDisplay = () => {
    if (!filterDateFrom && !filterDateTo) return null;

    // Check if matches a preset
    const matchingPreset = datePresets.find(preset => {
      const range = preset.getRange();
      return range.from === filterDateFrom && range.to === filterDateTo;
    });

    if (matchingPreset) {
      return matchingPreset.name + " " + matchingPreset.label;
    }

    // Custom range display
    if (filterDateFrom && filterDateTo) {
      const fromDate = new Date(filterDateFrom);
      const toDate = new Date(filterDateTo);
      return `Custom: ${fromDate.toLocaleDateString()} - ${toDate.toLocaleDateString()}`;
    }
    if (filterDateFrom) {
      return `From ${new Date(filterDateFrom).toLocaleDateString()}`;
    }
    if (filterDateTo) {
      return `To ${new Date(filterDateTo).toLocaleDateString()}`;
    }
    return null;
  };

  const ActionFilterDropdown = () => (
    <div className="relative">
      <select
        id="filterAction"
        value={filterAction}
        onChange={(e) => setFilterAction(e.target.value)}
        className="w-full px-3 py-2 pr-10 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white appearance-none cursor-pointer"
      >
        <optgroup label="Common">
          {commonActions.map(action => (
            <option key={action.value} value={action.value}>
              {action.label}
            </option>
          ))}
        </optgroup>
        {showAdvancedFilters && (
          <optgroup label="More">
            {extendedActions.map(action => (
              <option key={action.value} value={action.value}>
                {action.label}
              </option>
            ))}
          </optgroup>
        )}
      </select>
      <div className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none">
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </div>
    </div>
  );

  const PathFilterDropdown = () => (
    <div className="relative">
      <select
        id="filterPath"
        value={filterPath}
        onChange={(e) => setFilterPath(e.target.value)}
        className="w-full px-3 py-2 pr-10 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white appearance-none cursor-pointer"
      >
        <optgroup label="Common">
          {commonPaths.map(path => (
            <option key={path.value} value={path.value}>
              {path.label}
            </option>
          ))}
        </optgroup>
        {showAdvancedFilters && (
          <optgroup label="More">
            {extendedPaths.map(path => (
              <option key={path.value} value={path.value}>
                {path.label}
              </option>
            ))}
          </optgroup>
        )}
      </select>
      <div className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none">
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </div>
    </div>
  );

  const StatusFilterDropdown = () => (
    <div className="relative">
      <select
        id="filterStatusCode"
        value={filterStatusCode}
        onChange={(e) => setFilterStatusCode(e.target.value)}
        className="w-full px-3 py-2 pr-10 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white appearance-none cursor-pointer"
      >
        <optgroup label="Categories">
          {statusCodes.map(status => (
            <option key={status.value} value={status.value}>
              {status.label}
            </option>
          ))}
        </optgroup>
        {showAdvancedFilters && (
          <optgroup label="Specific Codes">
            {extendedStatusCodes.map(status => (
              <option key={status.value} value={status.value}>
                {status.label}
              </option>
            ))}
          </optgroup>
        )}
      </select>
      <div className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none">
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </div>
    </div>
  );

  const exportLogs = async (format: 'csv' | 'json') => {
    setExporting(true);
    setShowExportMenu(false);
    try {
      const params = new URLSearchParams({ page_size: '10000' });
      if (filterAction) params.append("action", filterAction);
      if (filterPath) params.append("path", filterPath);
      if (filterStatusCode) params.append("status_code", filterStatusCode);
      if (filterDateFrom) params.append("date_from", filterDateFrom);
      if (filterDateTo) params.append("date_to", filterDateTo);

      const data = await authFetchJSON<{ items: AuditLog[]; total: number }>(
        `/api/audit-logs?${params.toString()}`
      );

      if (format === 'csv') {
        const headers = ['Timestamp', 'User', 'Action', 'Path', 'Method', 'Status Code', 'Duration (ms)', 'IP Address'];
        const rows = data.items.map(log => [
          new Date(log.created_at).toISOString(),
          log.username || log.user_id || 'N/A',
          log.action,
          log.path,
          log.method,
          log.status_code?.toString() || '',
          log.duration_ms?.toString() || '',
          log.ip_address || ''
        ]);
        const csv = [headers, ...rows].map(row => row.map(cell => `"${cell}"`).join(',')).join('\n');
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `audit-logs-${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        URL.revokeObjectURL(url);
      } else {
        const blob = new Blob([JSON.stringify(data.items, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `audit-logs-${new Date().toISOString().split('T')[0]}.json`;
        a.click();
        URL.revokeObjectURL(url);
      }
    } catch (err: any) {
      setError(err.message || "Failed to export logs");
    } finally {
      setExporting(false);
    }
  };

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (showExportMenu) setShowExportMenu(false);
    };
    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, [showExportMenu]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="text-gray-600 dark:text-gray-400">Loading...</div>
      </div>
    );
  }

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Navigation */}
      <Navigation title="Audit Logs" subtitle="View all system activity and operations" />

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Error Message */}
        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-md">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
              <p className="text-sm text-gray-600 dark:text-gray-400">Total Logs</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats.total_requests}</p>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
              <p className="text-sm text-gray-600 dark:text-gray-400">Last 24 Hours</p>
              <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">{stats.last_24h_requests}</p>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
              <p className="text-sm text-gray-600 dark:text-gray-400">Failed Requests</p>
              <p className="text-2xl font-bold text-red-600 dark:text-red-400">{stats.failed_requests}</p>
            </div>
          </div>
        )}

        {/* Filters - Compact Design */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow mb-6 overflow-hidden">
          {/* Quick Filters - Always Visible */}
          <div className="p-4 border-b border-gray-100 dark:border-gray-700">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-200 flex items-center gap-2">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                Quick Filters
              </h3>
              <button
                onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
                className="text-xs text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 flex items-center gap-1 transition-colors"
              >
                {showAdvancedFilters ? "Hide" : "Show"} Advanced
                <svg
                  className={`w-3 h-3 transition-transform ${showAdvancedFilters ? "rotate-180" : ""}`}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
            </div>
            <div className="flex flex-wrap gap-2">
              {quickFilters.map((preset) => (
                <button
                  key={preset.name}
                  onClick={() => applyQuickFilter(preset)}
                  className="px-4 py-2 text-sm font-medium bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 border border-gray-200 dark:border-gray-600 rounded-lg hover:border-blue-400 dark:hover:border-blue-500 hover:text-blue-600 dark:hover:text-blue-400 transition-all shadow-sm hover:shadow flex items-center gap-1.5"
                  title={preset.description}
                >
                  <span>{preset.icon}</span>
                  <span>{preset.name}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Advanced Filters - Collapsible */}
          {showAdvancedFilters && (
            <div className="p-4 bg-gray-50 dark:bg-gray-800/50 animate-fade-in">
              {/* Basic Filters */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                <div>
                  <label htmlFor="filterAction" className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Action
                  </label>
                  <ActionFilterDropdown />
                </div>
                <div>
                  <label htmlFor="filterPath" className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Path
                  </label>
                  <PathFilterDropdown />
                </div>
                <div>
                  <label htmlFor="filterStatusCode" className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Status Code
                  </label>
                  <StatusFilterDropdown />
                </div>
              </div>

              {/* Date Range - Simplified */}
              <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 flex items-center gap-2">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                    Date Range
                  </h4>
                  {(filterDateFrom || filterDateTo) && (
                    <button
                      onClick={clearDateFilter}
                      className="text-xs text-gray-500 hover:text-red-600 dark:text-gray-400 dark:hover:text-red-400 flex items-center gap-1 transition-colors"
                    >
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                      Clear
                    </button>
                  )}
                </div>

                {/* Date Presets - Compact */}
                <div className="grid grid-cols-4 md:grid-cols-7 gap-2 mb-3">
                  {datePresets.slice(0, 7).map((preset) => {
                    const range = preset.getRange();
                    const isSelected = range.from === filterDateFrom && range.to === filterDateTo;
                    return (
                      <button
                        key={preset.id}
                        onClick={() => applyDatePreset(preset)}
                        className={`px-2 py-2 text-xs font-medium rounded-lg transition-all ${
                          isSelected
                            ? 'bg-blue-600 text-white shadow-md'
                            : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 border border-gray-200 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-600'
                        }`}
                        title={preset.label}
                      >
                        {preset.name}
                      </button>
                    );
                  })}
                </div>

                {/* Custom Date Inputs */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label htmlFor="filterDateFrom" className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                      From
                    </label>
                    <input
                      id="filterDateFrom"
                      type="datetime-local"
                      value={filterDateFrom}
                      onChange={(e) => setFilterDateFrom(e.target.value)}
                      className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                    />
                  </div>
                  <div>
                    <label htmlFor="filterDateTo" className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                      To
                    </label>
                    <input
                      id="filterDateTo"
                      type="datetime-local"
                      value={filterDateTo}
                      onChange={(e) => setFilterDateTo(e.target.value)}
                      className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                    />
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex gap-2 mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                <button
                  onClick={handleFilter}
                  className="px-4 py-2 text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors flex items-center gap-2"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
                  </svg>
                  Apply Filters
                </button>
                <button
                  onClick={handleClearFilters}
                  className="px-4 py-2 text-sm font-medium bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200 rounded-md transition-colors flex items-center gap-2"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                  Clear All
                </button>
              </div>
            </div>
          )}

          {/* Date Range */}
            <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                  Date Range
                </h4>
                {(filterDateFrom || filterDateTo) && (
                  <button
                    onClick={clearDateFilter}
                    className="text-xs text-gray-500 hover:text-red-600 dark:text-gray-400 dark:hover:text-red-400 flex items-center gap-1 transition-colors"
                  >
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                    Clear
                  </button>
                )}
              </div>

              {/* Quick Presets - Enhanced with toggle feedback */}
              <div className="grid grid-cols-4 md:grid-cols-8 gap-2 mb-4">
                {datePresets.map((preset) => {
                  const range = preset.getRange();
                  const isSelected = range.from === filterDateFrom && range.to === filterDateTo;
                  return (
                    <button
                      key={preset.id}
                      onClick={() => applyDatePreset(preset)}
                      className={`relative px-2 py-2.5 text-xs font-medium rounded-lg transition-all duration-200 ${
                        isSelected
                          ? 'bg-gradient-to-r from-blue-600 to-blue-500 text-white shadow-md shadow-blue-200 dark:shadow-blue-900/30 scale-105'
                          : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 border border-gray-200 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600 hover:border-gray-300 dark:hover:border-gray-500'
                      }`}
                      title={isSelected ? `Click to deselect ${preset.label}` : preset.label}
                    >
                      <span className="relative z-10">{preset.name}</span>
                      {isSelected && (
                        <span className="absolute top-1 right-1 w-2 h-2 bg-white rounded-full animate-pulse"></span>
                      )}
                    </button>
                  );
                })}
              </div>

              {/* Selected Range Display - Enhanced */}
              {getSelectedDateDisplay() && (
                <div className="mb-4 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/30 dark:to-indigo-900/30 border border-blue-200 dark:border-blue-700 rounded-xl animate-fade-in">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-blue-100 dark:bg-blue-900/50 flex items-center justify-center">
                        <svg className="w-5 h-5 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                        </svg>
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-blue-800 dark:text-blue-300">Active Date Filter</p>
                        <p className="text-xs text-blue-600 dark:text-blue-400 mt-0.5">{getSelectedDateDisplay()}</p>
                      </div>
                    </div>
                    <button
                      onClick={clearDateFilter}
                      className="p-2 rounded-lg bg-white dark:bg-gray-700 text-gray-500 dark:text-gray-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-all shadow-sm"
                      title="Clear date filter"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                  {filterDateFrom && filterDateTo && (
                    <div className="mt-3 pt-3 border-t border-blue-200 dark:border-blue-700">
                      <div className="flex items-center gap-4 text-xs text-blue-700 dark:text-blue-300">
                        <div className="flex items-center gap-1.5">
                          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                          <span>From: {new Date(filterDateFrom).toLocaleString()}</span>
                        </div>
                        <svg className="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                        </svg>
                        <div className="flex items-center gap-1.5">
                          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                          <span>To: {new Date(filterDateTo).toLocaleString()}</span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Custom Range - Enhanced */}
              <div className="bg-gradient-to-br from-gray-50 to-blue-50 dark:from-gray-700/30 dark:to-blue-900/20 rounded-xl p-5 border border-gray-200 dark:border-gray-600">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-lg bg-blue-100 dark:bg-blue-900/50 flex items-center justify-center">
                      <svg className="w-4 h-4 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-5h2v5a2 2 0 002 2z" />
                      </svg>
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-gray-800 dark:text-gray-200">Custom Date Range</p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">Specify exact start and end times</p>
                    </div>
                  </div>
                  {(filterDateFrom || filterDateTo) && (
                    <button
                      onClick={() => {
                        setFilterDateFrom("");
                        setFilterDateTo("");
                      }}
                      className="px-3 py-1.5 text-xs font-medium text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors flex items-center gap-1"
                    >
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                      Clear Custom
                    </button>
                  )}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                  <div className="relative">
                    <label htmlFor="filterDateFrom" className="flex items-center gap-2 text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">
                      <span className="w-5 h-5 rounded-full bg-green-100 dark:bg-green-900/50 flex items-center justify-center">
                        <svg className="w-3 h-3 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                      </span>
                      Start Date & Time
                    </label>
                    <input
                      id="filterDateFrom"
                      type="datetime-local"
                      value={filterDateFrom}
                      onChange={(e) => setFilterDateFrom(e.target.value)}
                      className="w-full px-4 py-2.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white transition-all shadow-sm"
                    />
                    {filterDateFrom && (
                      <p className="mt-1.5 text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1">
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                        {new Date(filterDateFrom).toLocaleString()}
                      </p>
                    )}
                  </div>
                  <div className="relative">
                    <label htmlFor="filterDateTo" className="flex items-center gap-2 text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">
                      <span className="w-5 h-5 rounded-full bg-red-100 dark:bg-red-900/50 flex items-center justify-center">
                        <svg className="w-3 h-3 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                      </span>
                      End Date & Time
                    </label>
                    <input
                      id="filterDateTo"
                      type="datetime-local"
                      value={filterDateTo}
                      onChange={(e) => setFilterDateTo(e.target.value)}
                      className="w-full px-4 py-2.5 text-sm border border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white transition-all shadow-sm"
                    />
                    {filterDateTo && (
                      <p className="mt-1.5 text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1">
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                        {new Date(filterDateTo).toLocaleString()}
                      </p>
                    )}
                  </div>
                </div>

                {/* Quick preset shortcuts for custom range */}
                <div className="border-t border-gray-200 dark:border-gray-600 pt-4">
                  <p className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-2 flex items-center gap-1">
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                    Quick fill from now:
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {[
                      { label: "Last 30 min", minutes: 30 },
                      { label: "Last 2 hours", minutes: 120 },
                      { label: "Last 6 hours", minutes: 360 },
                      { label: "Last 12 hours", minutes: 720 },
                    ].map((shortcut) => (
                      <button
                        key={shortcut.label}
                        onClick={() => {
                          const now = new Date();
                          const from = new Date(now.getTime() - shortcut.minutes * 60 * 1000);
                          setFilterDateFrom(formatDateForInput(from));
                          setFilterDateTo(formatDateForInput(now));
                        }}
                        className="px-3 py-1.5 text-xs font-medium bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-blue-50 dark:hover:bg-blue-900/30 hover:border-blue-300 dark:hover:border-blue-600 hover:text-blue-700 dark:hover:text-blue-300 transition-all"
                      >
                        {shortcut.label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex justify-between items-center mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
              <div className="text-xs text-gray-500 dark:text-gray-400">
                {(filterAction || filterPath || filterStatusCode || filterDateFrom || filterDateTo) && (
                  <span className="flex items-center gap-1">
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    Active filters applied
                  </span>
                )}
              </div>
              <div className="flex gap-2">
                <button
                  onClick={handleClearFilters}
                  className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                >
                  Clear All
                </button>
                <button
                  onClick={handleFilter}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 transition-colors shadow-sm"
                >
                  Apply Filters
                </button>
              </div>
            </div>
          </div>

        {/* Page Header */}
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Audit Logs</h2>
          <div className="flex items-center gap-3">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Showing {logs.length} of {total} entries
            </p>
            <div className="relative">
              <button
                onClick={(e) => { e.stopPropagation(); setShowExportMenu(!showExportMenu); }}
                disabled={exporting || logs.length === 0}
                className="px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50 flex items-center gap-1"
              >
                {exporting ? '...' : 'Export'}
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              {showExportMenu && (
                <div className="absolute right-0 mt-1 w-32 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md shadow-lg z-10">
                  <button
                    onClick={() => exportLogs('csv')}
                    className="block w-full px-4 py-2 text-sm text-left text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-600"
                  >
                    CSV
                  </button>
                  <button
                    onClick={() => exportLogs('json')}
                    className="block w-full px-4 py-2 text-sm text-left text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-600"
                  >
                    JSON
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Audit Logs Table */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
          {logs.length === 0 ? (
            <div className="p-8 text-center">
              <p className="text-gray-500 dark:text-gray-400">No audit logs found.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-700">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      Time
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      User
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      Action
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      Method
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      Path
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      Target
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      Duration
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                  {logs.map((log) => (
                    <tr key={log.id} className="hover:bg-gray-50 dark:hover:bg-gray-750">
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                        {formatDate(log.created_at)}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                        {log.username || <span className="text-gray-400 italic">System</span>}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-900 dark:text-white">
                        <code className="text-xs bg-gray-100 dark:bg-gray-700 px-1.5 py-0.5 rounded">
                          {log.action}
                        </code>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className={`px-2 py-1 text-xs font-semibold rounded ${getMethodClass(log.method)}`}>
                          {log.method}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400 font-mono">
                        {log.path}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className={`px-2 py-1 text-xs font-semibold rounded ${getStatusCodeClass(log.status_code)}`}>
                          {log.status_code}
                        </span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
                        {log.target_type && (
                          <span>
                            {log.target_type}:{log.target_id}
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
                        {log.duration_ms !== null ? `${log.duration_ms}ms` : "-"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex justify-between items-center mt-6">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <span className="text-sm text-gray-600 dark:text-gray-400">
              Page {page} of {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        )}

        {/* Info Box */}
        <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md">
          <h3 className="text-sm font-medium text-blue-800 dark:text-blue-300 mb-2">About Audit Logs</h3>
          <ul className="text-sm text-blue-700 dark:text-blue-400 space-y-1 list-disc list-inside">
            <li>All API requests are automatically logged (except auth endpoints)</li>
            <li>Logs include user, action, path, status code, and duration</li>
            <li>Use filters to narrow down specific actions or time periods</li>
            <li>Failed requests are highlighted in orange/red status codes</li>
          </ul>
        </div>
      </main>
    </div>
  );
}
