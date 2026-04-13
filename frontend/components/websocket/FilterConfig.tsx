"use client";

import React, { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import { loadAuthState } from "@/lib/auth";
import { Shield, Filter, Plus, Trash2, Save, RefreshCw, CheckCircle } from "lucide-react";
import { SeverityLevel } from "@/types/wazuh";

interface FilterRule {
  id?: string;
  name: string;
  description: string;
  priority: number;
  enabled: boolean;
  minSeverity?: SeverityLevel;
  maxSeverity?: SeverityLevel;
  eventTypes?: string[];
  agentIds?: string[];
  enableAggregation: boolean;
  maxMessagesPerMinute?: number;
}

interface FilterSet {
  user_id: string;
  default_action: "allow" | "block";
  rules: FilterRule[];
}

const SEVERITY_LEVELS: SeverityLevel[] = ["critical", "high", "medium", "low", "info"];

export const FilterConfig = React.memo(function FilterConfig() {
  const t = useTranslations("websocket.filters");
  const [mounted, setMounted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const [filters, setFilters] = useState<FilterSet>({
    user_id: "",
    default_action: "allow",
    rules: [],
  });

  const [newRule, setNewRule] = useState<FilterRule>({
    name: "",
    description: "",
    priority: 0,
    enabled: true,
    enableAggregation: true,
  });

  // Fetch filters on mount
  useEffect(() => {
    const fetchFilters = async () => {
      const authState = loadAuthState();
      if (!authState?.isAuthenticated) return;

      setLoading(true);
      try {
        const response = await fetch("/api/v1/websocket/filters", {
          headers: {
            Authorization: `Bearer ${authState.tokens?.access_token}`,
          },
        });

        if (response.ok) {
          const data = await response.json();
          setFilters(data);
        }
      } catch (error) {
        console.error("Error fetching filters:", error);
        setMessage({ type: "error", text: "Failed to load filters" });
      } finally {
        setLoading(false);
      }
    };

    fetchFilters();
    setMounted(true);
  }, []);

  const handleSaveFilters = async () => {
    const authState = loadAuthState();
    if (!authState?.isAuthenticated) return;

    setSaving(true);
    setMessage(null);

    try {
      const response = await fetch("/api/v1/websocket/filters", {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${authState.tokens?.access_token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(filters),
      });

      if (response.ok) {
        setMessage({ type: "success", text: "Filters saved successfully" });
      } else {
        throw new Error("Failed to save filters");
      }
    } catch (error) {
      console.error("Error saving filters:", error);
      setMessage({ type: "error", text: "Failed to save filters" });
    } finally {
      setSaving(false);
    }
  };

  const handleClearFilters = async () => {
    const authState = loadAuthState();
    if (!authState?.isAuthenticated) return;

    setSaving(true);

    try {
      const response = await fetch("/api/v1/websocket/filters", {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${authState.tokens?.access_token}`,
        },
      });

      if (response.ok) {
        setFilters({
          user_id: filters.user_id,
          default_action: "allow",
          rules: [],
        });
        setMessage({ type: "success", text: "Filters cleared" });
      }
    } catch (error) {
      console.error("Error clearing filters:", error);
      setMessage({ type: "error", text: "Failed to clear filters" });
    } finally {
      setSaving(false);
    }
  };

  const addRule = () => {
    if (!newRule.name) {
      setMessage({ type: "error", text: "Please enter a rule name" });
      return;
    }

    setFilters({
      ...filters,
      rules: [...filters.rules, { ...newRule, id: `rule_${Date.now()}` }],
    });

    setNewRule({
      name: "",
      description: "",
      priority: 0,
      enabled: true,
      enableAggregation: true,
    });

    setMessage({ type: "success", text: "Rule added" });
  };

  const removeRule = (ruleId: string) => {
    setFilters({
      ...filters,
      rules: filters.rules.filter((r) => r.id !== ruleId),
    });
    setMessage({ type: "success", text: "Rule removed" });
  };

  const updateRule = (ruleId: string, updates: Partial<FilterRule>) => {
    setFilters({
      ...filters,
      rules: filters.rules.map((r) => (r.id === ruleId ? { ...r, ...updates } : r)),
    });
  };

  if (!mounted) return null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <Filter className="w-5 h-5" />
            Message Filters
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Control which WebSocket messages you receive
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleClearFilters}
            className="px-3 py-1.5 text-sm font-medium text-red-600 dark:text-red-400 border border-red-200 dark:border-red-800 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
          >
            <Trash2 className="w-4 h-4 inline mr-1" />
            Clear All
          </button>
          <button
            onClick={handleSaveFilters}
            disabled={saving}
            className="px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {saving ? (
              <>
                <RefreshCw className="w-4 h-4 inline mr-1 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="w-4 h-4 inline mr-1" />
                Save Filters
              </>
            )}
          </button>
        </div>
      </div>

      {/* Status Message */}
      {message && (
        <div
          className={`p-3 rounded-lg border ${
            message.type === "success"
              ? "bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800 text-green-700 dark:text-green-400"
              : "bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800 text-red-700 dark:text-red-400"
          }`}
        >
          <div className="flex items-center gap-2">
            {message.type === "success" ? (
              <CheckCircle className="w-4 h-4" />
            ) : (
              <Shield className="w-4 h-4" />
            )}
            <span className="text-sm font-medium">{message.text}</span>
          </div>
        </div>
      )}

      {/* Current Filters */}
      {filters.rules.length > 0 ? (
        <div className="space-y-4">
          {filters.rules
            .sort((a, b) => b.priority - a.priority)
            .map((rule) => (
              <div
                key={rule.id}
                className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h4 className="font-medium text-gray-900 dark:text-white">{rule.name}</h4>
                      <span
                        className={`text-xs px-2 py-0.5 rounded ${
                          rule.enabled
                            ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                            : "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-400"
                        }`}
                      >
                        {rule.enabled ? "Enabled" : "Disabled"}
                      </span>
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        Priority: {rule.priority}
                      </span>
                    </div>
                    {rule.description && (
                      <p className="text-sm text-gray-600 dark:text-gray-400">{rule.description}</p>
                    )}
                  </div>
                  <button
                    onClick={() => removeRule(rule.id!)}
                    className="p-1 text-gray-400 hover:text-red-600 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>

                {/* Rule Details */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                  {rule.minSeverity && (
                    <div>
                      <span className="text-gray-500 dark:text-gray-400">Min Severity:</span>
                      <span className="ml-2 font-medium text-gray-900 dark:text-white">
                        {rule.minSeverity.toUpperCase()}
                      </span>
                    </div>
                  )}
                  {rule.maxSeverity && (
                    <div>
                      <span className="text-gray-500 dark:text-gray-400">Max Severity:</span>
                      <span className="ml-2 font-medium text-gray-900 dark:text-white">
                        {rule.maxSeverity.toUpperCase()}
                      </span>
                    </div>
                  )}
                  {rule.eventTypes && rule.eventTypes.length > 0 && (
                    <div>
                      <span className="text-gray-500 dark:text-gray-400">Event Types:</span>
                      <div className="ml-2 flex flex-wrap gap-1">
                        {rule.eventTypes.map((et) => (
                          <span
                            key={et}
                            className="px-2 py-0.5 bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 rounded text-xs"
                          >
                            {et}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {rule.agentIds && rule.agentIds.length > 0 && (
                    <div>
                      <span className="text-gray-500 dark:text-gray-400">Agents:</span>
                      <div className="ml-2 flex flex-wrap gap-1">
                        {rule.agentIds.map((agent) => (
                          <span
                            key={agent}
                            className="px-2 py-0.5 bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400 rounded text-xs"
                          >
                            {agent}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {rule.maxMessagesPerMinute !== undefined && (
                    <div>
                      <span className="text-gray-500 dark:text-gray-400">Rate Limit:</span>
                      <span className="ml-2 font-medium text-gray-900 dark:text-white">
                        {rule.maxMessagesPerMinute} msg/min
                      </span>
                    </div>
                  )}
                </div>
              </div>
            ))}
        </div>
      ) : (
        <div className="text-center py-8 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <Filter className="w-12 h-12 text-gray-400 mx-auto mb-3" />
          <p className="text-gray-500 dark:text-gray-400">No filters configured</p>
          <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">
            Add a rule below to start filtering messages
          </p>
        </div>
      )}

      {/* Add New Rule */}
      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
        <h4 className="font-medium text-gray-900 dark:text-white mb-4">Add New Filter Rule</h4>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Rule Name
            </label>
            <input
              type="text"
              value={newRule.name}
              onChange={(e) => setNewRule({ ...newRule, name: e.target.value })}
              placeholder="e.g., High Severity Only"
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Description (Optional)
            </label>
            <input
              type="text"
              value={newRule.description}
              onChange={(e) => setNewRule({ ...newRule, description: e.target.value })}
              placeholder="Brief description of this rule"
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
          </div>

          {/* Priority */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Priority (0 = highest)
            </label>
            <input
              type="number"
              min="0"
              max="100"
              value={newRule.priority}
              onChange={(e) => setNewRule({ ...newRule, priority: parseInt(e.target.value) })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
          </div>

          {/* Min Severity */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Min Severity
            </label>
            <select
              value={newRule.minSeverity || ""}
              onChange={(e) =>
                setNewRule({ ...newRule, minSeverity: e.target.value as SeverityLevel })
              }
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            >
              <option value="">No minimum</option>
              {SEVERITY_LEVELS.map((level) => (
                <option key={level} value={level}>
                  {level.toUpperCase()}
                </option>
              ))}
            </select>
          </div>

          {/* Event Types */}
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Event Types (comma-separated)
            </label>
            <input
              type="text"
              value={newRule.eventTypes?.join(", ") || ""}
              onChange={(e) =>
                setNewRule({
                  ...newRule,
                  eventTypes: e.target.value
                    ? e.target.value.split(",").map((s) => s.trim())
                    : undefined,
                })
              }
              placeholder="malware, ssh_bruteforce, ransomware"
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
          </div>
        </div>

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="agg"
              checked={newRule.enableAggregation}
              onChange={(e) => setNewRule({ ...newRule, enableAggregation: e.target.checked })}
              className="rounded"
            />
            <label htmlFor="agg" className="text-sm text-gray-700 dark:text-gray-300">
              Enable aggregation for this rule
            </label>
          </div>
          <button
            onClick={addRule}
            disabled={!newRule.name}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            <Plus className="w-4 h-4 inline mr-1" />
            Add Rule
          </button>
        </div>
      </div>

      {/* Info Box */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
        <h4 className="text-sm font-semibold text-blue-900 dark:text-blue-100 mb-2">
          ℹ️ How Filters Work
        </h4>
        <ul className="text-sm text-blue-800 dark:text-blue-200 space-y-1">
          <li>
            • Rules are evaluated by <strong>priority</strong> (highest first)
          </li>
          <li>• First matching rule determines if message is sent</li>
          <li>
            • If no rules match, default action is{" "}
            <strong>{filters.default_action.toUpperCase()}</strong>
          </li>
          <li>
            • Messages are filtered <strong>before</strong> being sent via WebSocket
          </li>
          <li>• Filters reduce network traffic and client processing</li>
        </ul>
      </div>
    </div>
  );
});
