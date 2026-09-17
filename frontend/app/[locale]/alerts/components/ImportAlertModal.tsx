"use client";

/**
 * Import Alert Modal
 *
 * Supports:
 * - Format selection (Auto / CEF / Syslog / JSON / CSV)
 * - Text input (paste alert content)
 * - File upload (drag & drop .csv, .json, .txt, .log files)
 * - Parse preview → shows parsed alert fields in a table
 * - Confirm import → sends to API
 */

import { useState, useRef, useCallback, useEffect, type DragEvent } from "react";
import { useTranslations } from "next-intl";
import {
  Upload,
  FileText,
  X,
  RefreshCw,
  CheckCircle,
  AlertTriangle,
  Download,
  Eye,
  Trash2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/Badge";
import { useToast } from "@/components/Toast";
import {
  previewBatchImport,
  importAlertsBatch,
  type AlertBatchImportPayload,
} from "@/lib/api/security-alerts";

// ── Types ──────────────────────────────────────────────

interface ImportAlertModalProps {
  open: boolean;
  onClose: () => void;
  onImportSuccess: () => void;
}

type ImportTab = "text" | "file";

interface PreviewRecord {
  [key: string]: unknown;
}

// ── Format Options ─────────────────────────────────────

const FORMAT_OPTIONS = [
  { value: "auto", label: "Auto Detect" },
  { value: "cef", label: "CEF" },
  { value: "syslog", label: "Syslog" },
  { value: "json", label: "JSON" },
  { value: "csv", label: "CSV" },
];

// ── Severity color map for preview ─────────────────────

function severityClass(severity: string): string {
  const m: Record<string, string> = {
    critical: "text-red-700 dark:text-red-400 bg-red-50 dark:bg-red-900/20",
    high: "text-orange-700 dark:text-orange-400 bg-orange-50 dark:bg-orange-900/20",
    medium: "text-yellow-700 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-900/20",
    low: "text-green-700 dark:text-green-400 bg-green-50 dark:bg-green-900/20",
    info: "text-blue-700 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20",
  };
  return m[severity] || "text-gray-700 dark:text-gray-400";
}

// ── Component ──────────────────────────────────────────

export default function ImportAlertModal({
  open,
  onClose,
  onImportSuccess,
}: ImportAlertModalProps) {
  const t = useTranslations("alerts");
  const { showToast } = useToast();

  // State
  const [tab, setTab] = useState<ImportTab>("text");
  const [textContent, setTextContent] = useState("");
  const [format, setFormat] = useState("auto");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [previewData, setPreviewData] = useState<PreviewRecord[]>([]);
  const [formatDetected, setFormatDetected] = useState("");
  const [totalParsed, setTotalParsed] = useState(0);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── File handling ───────────────────────────────────

  const handleFileSelect = useCallback((file: File) => {
    setSelectedFile(file);
    setTab("file");
    const reader = new FileReader();
    reader.onload = (e) => {
      setTextContent((e.target?.result as string) || "");
    };
    reader.readAsText(file);
  }, []);

  const handleDrop = useCallback(
    (e: DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setIsDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFileSelect(file);
    },
    [handleFileSelect]
  );

  const handleDragOver = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  // ── Preview ──────────────────────────────────────────

  const handlePreview = useCallback(async () => {
    if (!textContent.trim()) {
      showToast("Please enter alert content", "warning");
      return;
    }

    setIsPreviewing(true);
    setPreviewData([]);
    setFormatDetected("");
    setTotalParsed(0);

    try {
      const payload: AlertBatchImportPayload = {
        content: textContent,
        format,
        preview_only: true,
      };
      const result = await previewBatchImport(payload);
      const apiData = result as unknown as {
        data?: { preview?: PreviewRecord[]; format_detected?: string; total_parsed?: number };
      } | null;
      if (apiData?.data) {
        setPreviewData(apiData.data.preview || []);
        setFormatDetected(apiData.data.format_detected || "");
        setTotalParsed(apiData.data.total_parsed || 0);
        showToast(`${apiData.data.total_parsed || 0} alert(s) parsed`, "success");
      } else {
        showToast("No alerts parsed", "warning");
      }
    } catch (err) {
      showToast(`Preview failed: ${err instanceof Error ? err.message : "Unknown error"}`, "error");
    } finally {
      setIsPreviewing(false);
    }
  }, [textContent, format, showToast]);

  // ── Import ───────────────────────────────────────────

  const handleImport = useCallback(async () => {
    if (!textContent.trim()) {
      showToast("Please enter alert content", "warning");
      return;
    }

    setIsImporting(true);
    try {
      const payload: AlertBatchImportPayload = {
        content: textContent,
        format,
        preview_only: false,
      };
      const result = await importAlertsBatch(payload);
      const apiData = result as unknown as {
        data?: {
          total_created?: number;
          total_parsed?: number;
          errors?: Array<{ row: number; error: string }>;
        };
      } | null;
      if (apiData?.data) {
        const { total_created = 0, total_parsed = 0, errors = [] } = apiData.data;
        if (errors.length > 0) {
          showToast(
            `Imported ${total_created}/${total_parsed} alerts (${errors.length} errors)`,
            "warning"
          );
        } else {
          showToast(`Successfully imported ${total_created} alert(s)`, "success");
        }
      }
      onImportSuccess();
      onClose();
    } catch (err) {
      showToast(`Import failed: ${err instanceof Error ? err.message : "Unknown error"}`, "error");
    } finally {
      setIsImporting(false);
    }
  }, [textContent, format, showToast, onImportSuccess, onClose]);

  // ── Clear ────────────────────────────────────────────

  const handleClear = useCallback(() => {
    setTextContent("");
    setSelectedFile(null);
    setPreviewData([]);
    setFormatDetected("");
    setTotalParsed(0);
    setFormat("auto");
  }, []);

  // Lock background scroll and listen for ESC key when open
  useEffect(() => {
    if (!open) return;
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.style.overflow = prevOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [open, onClose]);

  // ── Dismiss ──────────────────────────────────────────

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      {/* Modal */}
      <div
        className="relative bg-white dark:bg-gray-800 rounded-xl shadow-2xl border border-gray-200 dark:border-gray-700 max-w-2xl w-full max-h-[90vh] flex flex-col"
        onMouseDown={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
              <Upload className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Import Alerts</h2>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Paste or upload CEF, Syslog, JSON, or CSV alerts
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {/* Tab Switcher */}
          <div className="flex items-center gap-1 bg-gray-100 dark:bg-gray-900 rounded-lg p-1">
            <button
              onClick={() => setTab("text")}
              className={cn(
                "flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium rounded-md transition-colors",
                tab === "text"
                  ? "bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm"
                  : "text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
              )}
            >
              <FileText className="w-4 h-4" />
              Paste Text
            </button>
            <button
              onClick={() => setTab("file")}
              className={cn(
                "flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium rounded-md transition-colors",
                tab === "file"
                  ? "bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm"
                  : "text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
              )}
            >
              <Upload className="w-4 h-4" />
              Upload File
            </button>
          </div>

          {/* Format Selector */}
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Format:</label>
            <select
              value={format}
              onChange={(e) => setFormat(e.target.value)}
              className="px-3 py-1.5 text-sm border border-gray-200 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {FORMAT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {/* Text Area */}
          {tab === "text" && (
            <div>
              <textarea
                value={textContent}
                onChange={(e) => setTextContent(e.target.value)}
                placeholder="Paste alert content here (CEF, Syslog, JSON, or CSV)..."
                rows={8}
                className={cn(
                  "w-full px-4 py-3 text-sm border rounded-lg bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono resize-y",
                  "border-gray-200 dark:border-gray-700"
                )}
              />
              <p className="text-xs text-gray-400 mt-1">{textContent.length} characters</p>
            </div>
          )}

          {/* File Upload Area */}
          {tab === "file" && (
            <div
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              className={cn(
                "border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer",
                isDragOver
                  ? "border-blue-400 bg-blue-50 dark:bg-blue-900/20"
                  : selectedFile
                    ? "border-green-400 bg-green-50 dark:bg-green-900/20"
                    : "border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500"
              )}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv,.json,.txt,.log,.cef,.tsv"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleFileSelect(file);
                }}
                className="hidden"
              />
              {selectedFile ? (
                <div className="flex flex-col items-center gap-2">
                  <FileText className="w-10 h-10 text-green-500" />
                  <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    {selectedFile.name}
                  </p>
                  <p className="text-xs text-gray-500">
                    {(selectedFile.size / 1024).toFixed(1)} KB
                  </p>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedFile(null);
                      setTextContent("");
                    }}
                    className="text-xs text-red-500 hover:text-red-700 underline"
                  >
                    Remove
                  </button>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-2">
                  <Upload className="w-10 h-10 text-gray-400" />
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Drag & drop a file here, or click to browse
                  </p>
                  <p className="text-xs text-gray-400">Supported: .csv, .json, .txt, .log, .cef</p>
                </div>
              )}
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex items-center gap-3">
            <button
              onClick={handlePreview}
              disabled={isPreviewing || !textContent.trim()}
              className={cn(
                "flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-colors",
                "border border-gray-200 dark:border-gray-600 text-gray-700 dark:text-gray-300",
                "hover:bg-gray-50 dark:hover:bg-gray-700",
                "disabled:opacity-50 disabled:cursor-not-allowed"
              )}
            >
              <Eye className="w-4 h-4" />
              {isPreviewing ? "Parsing..." : "Preview"}
            </button>

            <button
              onClick={handleImport}
              disabled={isImporting || !textContent.trim()}
              className={cn(
                "flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-colors",
                "bg-blue-600 text-white hover:bg-blue-700",
                "disabled:opacity-50 disabled:cursor-not-allowed"
              )}
            >
              {isImporting ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Importing...
                </>
              ) : (
                <>
                  <CheckCircle className="w-4 h-4" />
                  Confirm Import
                </>
              )}
            </button>

            <button
              onClick={handleClear}
              className="flex items-center gap-1 px-3 py-2 text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
            >
              <Trash2 className="w-4 h-4" />
              Clear
            </button>
          </div>

          {/* Preview Section */}
          {(isPreviewing || previewData.length > 0) && (
            <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
              {/* Preview header */}
              <div className="flex items-center justify-between px-4 py-2 bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
                <div className="flex items-center gap-2">
                  <Eye className="w-4 h-4 text-gray-500" />
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    Preview
                  </span>
                  {formatDetected && <Badge severity="info">{formatDetected.toUpperCase()}</Badge>}
                  {totalParsed > 0 && (
                    <span className="text-xs text-gray-500">{totalParsed} alert(s) parsed</span>
                  )}
                </div>
              </div>

              {/* Loading skeleton */}
              {isPreviewing && (
                <div className="p-4 space-y-2">
                  {[1, 2, 3].map((i) => (
                    <div
                      key={i}
                      className="h-12 bg-gray-100 dark:bg-gray-700 rounded animate-pulse"
                    />
                  ))}
                </div>
              )}

              {/* Preview table */}
              {!isPreviewing && previewData.length > 0 && (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 dark:bg-gray-900">
                      <tr>
                        <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                          #
                        </th>
                        <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                          Title
                        </th>
                        <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                          Severity
                        </th>
                        <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                          Source
                        </th>
                        <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                          Event Type
                        </th>
                        <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                          Source IP
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                      {previewData.slice(0, 20).map((item, idx) => (
                        <tr
                          key={idx}
                          className="hover:bg-gray-50 dark:hover:bg-gray-750 transition-colors"
                        >
                          <td className="px-3 py-2 text-gray-400 text-xs">{idx + 1}</td>
                          <td className="px-3 py-2 max-w-[200px]">
                            <span className="text-gray-900 dark:text-white truncate block">
                              {String(item.title || "-")}
                            </span>
                          </td>
                          <td className="px-3 py-2 whitespace-nowrap">
                            <span
                              className={cn(
                                "inline-flex px-2 py-0.5 rounded text-xs font-medium",
                                severityClass(String(item.severity || "info"))
                              )}
                            >
                              {String(item.severity || "info")}
                            </span>
                          </td>
                          <td className="px-3 py-2 text-gray-600 dark:text-gray-400 text-xs">
                            {String(item.source || "-")}
                          </td>
                          <td className="px-3 py-2 text-gray-600 dark:text-gray-400 text-xs">
                            {String(item.event_type || "-")}
                          </td>
                          <td className="px-3 py-2">
                            {item.source_ip ? (
                              <code className="text-xs bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded text-gray-700 dark:text-gray-300">
                                {String(item.source_ip)}
                              </code>
                            ) : (
                              <span className="text-gray-400 text-xs">-</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {previewData.length > 20 && (
                    <div className="px-4 py-2 text-xs text-gray-400 bg-gray-50 dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700">
                      Showing 20 of {previewData.length} parsed alerts
                    </div>
                  )}
                </div>
              )}

              {/* Empty preview */}
              {!isPreviewing && previewData.length === 0 && (
                <div className="flex flex-col items-center justify-center py-8 text-center">
                  <AlertTriangle className="w-8 h-8 text-gray-300 dark:text-gray-600 mb-2" />
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    No alerts were parsed. Check the format and try again.
                  </p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <p className="text-xs text-gray-400">
            Supported formats: CEF, Syslog (RFC 3164), JSON, CSV
          </p>
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
