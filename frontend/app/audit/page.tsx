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
  const [pageSize, setPageSize] = useState(50);
  const [total, setTotal] = useState(0);

  // Generate page numbers for smart pagination
  const getPageNumbers = (): (number | string)[] => {
    const pages: (number | string)[] = [];
    const totalPages = Math.ceil(total / pageSize);

    if (totalPages <= 7) {
      // Show all pages if 7 or fewer
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i);
      }
    } else {
      // Always show first page
      pages.push(1);

      if (page > 3) {
        pages.push("...");
      }

      // Show pages around current page
      const start = Math.max(2, page - 1);
      const end = Math.min(totalPages - 1, page + 1);

      for (let i = start; i <= end; i++) {
        pages.push(i);
      }

      if (page < totalPages - 2) {
        pages.push("...");
      }

      // Always show last page
      pages.push(totalPages);
    }

    return pages;
  };

  // Filters
  const [filterAction, setFilterAction] = useState("");
  const [filterPath, setFilterPath] = useState("");
  const [filterStatusCode, setFilterStatusCode] = useState("");
  const [filterDateFrom, setFilterDateFrom] = useState("");
  const [filterDateTo, setFilterDateTo] = useState("");
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

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
    // Initial load
    if (loading) {
      fetchAuditLogs();
      fetchStats();
    }
  }, [router]);

  // Fetch data when page, pageSize, or filters change
  useEffect(() => {
    if (!loading) {
      fetchAuditLogs();
    }
  }, [page, pageSize, filterAction, filterPath, filterStatusCode, filterDateFrom, filterDateTo]);

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
        </div>

        {/* Page Header */}
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Audit Logs</h2>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Showing {logs.length} of {total} entries
          </p>
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

        {/* Smart Pagination */}
        {total > 0 && (
          <div className="mt-6 flex flex-col sm:flex-row items-center justify-between gap-4 px-4 py-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg">
            {/* Left: Statistics */}
            <div className="text-sm text-gray-700 dark:text-gray-300">
              显示 <span className="font-semibold text-blue-600 dark:text-blue-400">{(page - 1) * pageSize + 1}</span> 到{" "}
              <span className="font-semibold text-blue-600 dark:text-blue-400">{Math.min(page * pageSize, total)}</span> 共{" "}
              <span className="font-semibold text-blue-600 dark:text-blue-400">{total}</span> 条记录
            </div>

            {/* Center: Page Numbers */}
            <div className="flex items-center gap-1">
              {/* First Page */}
              <button
                onClick={() => setPage(1)}
                disabled={page === 1}
                className="w-8 h-8 flex items-center justify-center text-sm font-medium rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                title="首页"
              >
                «
              </button>

              {/* Previous Page */}
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="w-8 h-8 flex items-center justify-center text-sm font-medium rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                title="上一页"
              >
                ‹
              </button>

              {/* Page Numbers */}
              {getPageNumbers().map((p, i) =>
                p === "..." ? (
                  <span
                    key={`ellipsis-${i}`}
                    className="w-8 h-8 flex items-center justify-center text-gray-500 dark:text-gray-400"
                  >
                    ...
                  </span>
                ) : (
                  <button
                    key={`page-${p}`}
                    onClick={() => setPage(p as number)}
                    className={`w-8 h-8 flex items-center justify-center text-sm font-medium rounded-lg transition-colors ${
                      page === p
                        ? "bg-blue-500 text-white border-blue-500 shadow-md"
                        : "border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                    }`}
                  >
                    {p}
                  </button>
                )
              )}

              {/* Next Page */}
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="w-8 h-8 flex items-center justify-center text-sm font-medium rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                title="下一页"
              >
                ›
              </button>

              {/* Last Page */}
              <button
                onClick={() => setPage(totalPages)}
                disabled={page === totalPages}
                className="w-8 h-8 flex items-center justify-center text-sm font-medium rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                title="末页"
              >
                »
              </button>
            </div>

            {/* Right: Page Size Selector */}
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600 dark:text-gray-400">每页</span>
              <select
                value={pageSize}
                onChange={(e) => {
                  setPageSize(Number(e.target.value));
                  setPage(1); // Reset to first page when changing page size
                }}
                className="text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-2 py-1.5 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="25">25</option>
                <option value="50">50</option>
                <option value="100">100</option>
                <option value="200">200</option>
              </select>
              <span className="text-sm text-gray-600 dark:text-gray-400">条</span>
            </div>
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
