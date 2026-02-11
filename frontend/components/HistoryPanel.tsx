"use client";

import { useState, useEffect } from "react";
import { api, HistoryRecord } from "@/lib/api";

interface HistoryPanelProps {
  module: "analyzer" | "report" | "timeline";
  onSelect: (record: HistoryRecord) => void;
  onClose: () => void;
}

export function HistoryPanel({ module, onSelect, onClose }: HistoryPanelProps) {
  const [records, setRecords] = useState<HistoryRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    loadHistory();
  }, [module, search]);

  const loadHistory = async () => {
    setLoading(true);
    try {
      const response = await api.listHistory({
        module: module === "analyzer" ? "analyzer" : module,
        query: search || undefined,
        limit: 50,
      });
      setRecords(response.items);
    } catch (error) {
      console.error("Failed to load history:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.deleteHistory(id);
      setRecords(records.filter((r) => r.id !== id));
    } catch (error) {
      console.error("Failed to delete:", error);
    }
  };

  const handleDeleteAll = async () => {
    if (!confirm("Delete all history?")) return;
    try {
      await api.deleteAllHistory();
      setRecords([]);
    } catch (error) {
      console.error("Failed to delete all:", error);
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleString();
  };

  const getTruncated = (text: string, maxLength = 60) => {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + "...";
  };

  const getModuleLabel = () => {
    switch (module) {
      case "analyzer":
        return "Alert Analyzer";
      case "report":
        return "Report Writer";
      case "timeline":
        return "Timeline Builder";
    }
  };

  const getSeverityColor = (severity?: string) => {
    switch (severity) {
      case "high":
        return "bg-red-100 text-red-700";
      case "medium":
        return "bg-amber-100 text-amber-700";
      case "low":
        return "bg-green-100 text-green-700";
      default:
        return "bg-slate-100 text-slate-700";
    }
  };

  return (
    <div className="w-80 bg-white border-l border-slate-200 flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-slate-200">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-slate-800">{getModuleLabel()} History</h3>
          <button
            onClick={onClose}
            className="p-1 hover:bg-slate-100 rounded"
          >
            ✕
          </button>
        </div>

        {/* Search */}
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search IOCs, text..."
          className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-soc-500 focus:border-soc-500"
        />

        {/* Delete All */}
        {records.length > 0 && (
          <button
            onClick={handleDeleteAll}
            className="mt-3 text-xs text-red-600 hover:text-red-800"
          >
            Delete All
          </button>
        )}
      </div>

      {/* Records List */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="p-4 text-center text-slate-500">Loading...</div>
        ) : records.length === 0 ? (
          <div className="p-4 text-center text-slate-500">No history found</div>
        ) : (
          <div className="divide-y divide-slate-100">
            {records.map((record) => (
              <div
                key={record.id}
                className="p-3 hover:bg-slate-50 cursor-pointer group"
              >
                <div
                  className="mb-2"
                  onClick={() => onSelect(record)}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-slate-500">
                      {formatDate(record.created_at)}
                    </span>
                    {record.tags?.severity && (
                      <span className={`px-2 py-0.5 rounded text-xs ${getSeverityColor(record.tags.severity)}`}>
                        {record.tags.severity.toUpperCase()}
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-slate-700 mb-1">
                    {getTruncated(record.input_text)}
                  </p>
                  {record.degraded && (
                    <span className="text-xs text-amber-600">⚠️ Degraded mode</span>
                  )}
                  {record.extracted_iocs && (
                    <div className="flex gap-2 text-xs text-slate-500 mt-1">
                      {record.extracted_iocs.ips?.length && <span>IPs: {record.extracted_iocs.ips.length}</span>}
                      {record.extracted_iocs.domains?.length && <span>Domains: {record.extracted_iocs.domains.length}</span>}
                    </div>
                  )}
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDelete(record.id);
                  }}
                  className="text-xs text-red-500 hover:text-red-700 opacity-0 group-hover:opacity-100"
                >
                  Delete
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
