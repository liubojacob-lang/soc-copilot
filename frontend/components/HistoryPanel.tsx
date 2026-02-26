"use client";

import { useState, useEffect, useRef } from "react";
import { useTranslations } from "next-intl";
import { api, HistoryRecord } from "@/lib/api";
import { X, Search, Trash2, Clock, AlertTriangle, CheckCircle, Info } from "lucide-react";

interface HistoryPanelProps {
  module: "analyzer" | "report" | "timeline";
  onSelect: (record: HistoryRecord) => void;
  onClose: () => void;
}

export function HistoryPanel({ module, onSelect, onClose }: HistoryPanelProps) {
  const t = useTranslations('common');
  const [records, setRecords] = useState<HistoryRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [mounted, setMounted] = useState(false);
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setMounted(true);
    loadHistory();
  }, [module, search]);

  // Close on escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, [onClose]);

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
    if (!confirm("Are you sure you want to delete all history?")) return;
    try {
      await api.deleteAllHistory();
      setRecords([]);
    } catch (error) {
      console.error("Failed to delete all:", error);
    }
  };

  const formatDate = (dateStr: string) => {
    if (!mounted) return "..."; // Avoid hydration mismatch
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return "Just now";
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    return date.toLocaleDateString();
  };

  const getTruncated = (text: string, maxLength = 80) => {
    if (!text) return "";
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + "...";
  };

  const getSeverityIcon = (severity?: string) => {
    switch (severity) {
      case "high":
        return <AlertTriangle className="w-4 h-4 text-red-500" />;
      case "medium":
        return <Info className="w-4 h-4 text-amber-500" />;
      case "low":
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      default:
        return <Clock className="w-4 h-4 text-gray-400" />;
    }
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

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div 
        ref={modalRef}
        className="relative bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-2xl max-h-[80vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              {getModuleLabel()} History
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
              {records.length} records found
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Search Bar */}
        <div className="px-6 py-3 border-b border-gray-100 dark:border-gray-700">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by IOC, text, or keywords..."
              className="w-full pl-10 pr-4 py-2.5 text-sm border border-gray-200 dark:border-gray-600 rounded-xl bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
            />
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-16">
              <div className="w-8 h-8 border-2 border-gray-300 border-t-blue-600 rounded-full animate-spin" />
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-4">{t('loading')}</p>
            </div>
          ) : records.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16">
              <Clock className="w-12 h-12 text-gray-300 dark:text-gray-600 mb-4" />
              <p className="text-gray-500 dark:text-gray-400">No history records</p>
              <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">Your analysis history will appear here</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-100 dark:divide-gray-700">
              {records.map((record) => (
                <div
                  key={record.id}
                  className="px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer group transition-colors"
                  onClick={() => {
                    onSelect(record);
                    onClose();
                  }}
                >
                  <div className="flex items-start gap-3">
                    {/* Icon */}
                    <div className="flex-shrink-0 mt-0.5">
                      {getSeverityIcon(record.tags?.severity)}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          {formatDate(record.created_at)}
                        </span>
                        {record.degraded && (
                          <span className="text-xs text-amber-600 dark:text-amber-400 flex items-center gap-1">
                            <AlertTriangle className="w-3 h-3" />
                            Degraded
                          </span>
                        )}
                      </div>
                      
                      <p className="text-sm text-gray-800 dark:text-gray-200 line-clamp-2">
                        {getTruncated(record.input_text)}
                      </p>

                      {/* IOC Tags */}
                      {record.extracted_iocs && (
                        <div className="flex flex-wrap gap-2 mt-2">
                          {record.extracted_iocs.ips?.length > 0 && (
                            <span className="inline-flex items-center px-2 py-0.5 text-xs font-medium bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 rounded">
                              {record.extracted_iocs.ips.length} IPs
                            </span>
                          )}
                          {record.extracted_iocs.domains?.length > 0 && (
                            <span className="inline-flex items-center px-2 py-0.5 text-xs font-medium bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400 rounded">
                              {record.extracted_iocs.domains.length} Domains
                            </span>
                          )}
                          {record.extracted_iocs.hashes?.length > 0 && (
                            <span className="inline-flex items-center px-2 py-0.5 text-xs font-medium bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 rounded">
                              {record.extracted_iocs.hashes.length} Hashes
                            </span>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Delete Button */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDelete(record.id);
                      }}
                      className="flex-shrink-0 p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded opacity-0 group-hover:opacity-100 transition-all"
                      title="Delete"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        {records.length > 0 && (
          <div className="px-6 py-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 flex items-center justify-between">
            <span className="text-xs text-gray-500 dark:text-gray-400">
              Click a record to load it
            </span>
            <button
              onClick={handleDeleteAll}
              className="text-xs text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 font-medium flex items-center gap-1"
            >
              <Trash2 className="w-3.5 h-3.5" />
              Clear All
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
