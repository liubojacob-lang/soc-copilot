"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Modal } from "@/components/common/Modal";
import { Badge } from "@/components/ui/Badge";
import { Text, Caption } from "@/components/ui/Typography";
import { apiClient } from "@/lib/api/client";
import {
  Activity,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  RefreshCw,
  Clock,
} from "lucide-react";

export interface DiagnosticItem {
  name: string;
  status: "ok" | "warn" | "error";
  latency_ms: number | null;
  message: string;
}

export interface DiagnosticsResponse {
  timestamp: string;
  overall_status: "ok" | "warn" | "error";
  items: DiagnosticItem[];
}

interface DiagnosticsModalProps {
  open: boolean;
  onClose: () => void;
}

export function DiagnosticsModal({ open, onClose }: DiagnosticsModalProps) {
  const t = useTranslations("adminDashboard.diagnostics");
  const tCommon = useTranslations("common");
  const [data, setData] = useState<DiagnosticsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      runDiagnostics();
    }
  }, [open]);

  const runDiagnostics = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await apiClient.post<DiagnosticsResponse>("/api/v1/system/diagnostics/ping");
      setData(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run diagnostics");
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (status: "ok" | "warn" | "error") => {
    if (status === "ok") return <CheckCircle2 className="w-5 h-5 text-success-600 shrink-0" />;
    if (status === "warn") return <AlertTriangle className="w-5 h-5 text-warning-600 shrink-0" />;
    return <XCircle className="w-5 h-5 text-danger-600 shrink-0" />;
  };

  const getStatusBadge = (status: "ok" | "warn" | "error") => {
    const sev: "low" | "medium" | "critical" =
      status === "ok" ? "low" : status === "warn" ? "medium" : "critical";
    return <Badge severity={sev}>{status.toUpperCase()}</Badge>;
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-50 dark:bg-blue-900/30 rounded-lg">
            <Activity className="w-5 h-5 text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-text-primary dark:text-white">
              {t("title")}
            </h3>
            <p className="text-xs text-text-tertiary">{t("subtitle")}</p>
          </div>
        </div>
      }
      contentClassName="w-full max-w-xl"
    >
      <div className="space-y-4">
        {/* Error message */}
        {error && (
          <div className="p-3 bg-danger-50 dark:bg-danger-900/20 border border-danger-200 dark:border-danger-800/50 rounded-lg text-xs text-danger-700 dark:text-danger-300">
            {error}
          </div>
        )}

        {/* Loading Spinner */}
        {loading && (
          <div className="py-12 flex flex-col items-center justify-center gap-3">
            <RefreshCw className="w-7 h-7 animate-spin text-primary-600" />
            <Caption color="secondary">{t("running")}</Caption>
          </div>
        )}

        {/* Results */}
        {!loading && data && (
          <div className="space-y-4">
            {/* Overall Banner */}
            <div
              className={`p-4 rounded-xl border flex items-center gap-3 ${
                data.overall_status === "ok"
                  ? "bg-success-50 dark:bg-success-900/20 border-success-200 dark:border-success-800/40"
                  : data.overall_status === "warn"
                    ? "bg-warning-50 dark:bg-warning-900/20 border-warning-200 dark:border-warning-800/40"
                    : "bg-danger-50 dark:bg-danger-900/20 border-danger-200 dark:border-danger-800/40"
              }`}
            >
              {getStatusIcon(data.overall_status)}
              <div className="flex-1">
                <div className="font-semibold text-sm text-text-primary dark:text-white">
                  {data.overall_status === "ok"
                    ? t("overallHealthy")
                    : data.overall_status === "warn"
                      ? t("overallWarning")
                      : t("overallError")}
                </div>
                <div className="flex items-center gap-2 text-xs text-text-tertiary mt-0.5">
                  <Clock className="w-3 h-3" />
                  <span>{new Date(data.timestamp).toLocaleTimeString()}</span>
                </div>
              </div>
            </div>

            {/* Individual Diagnostic Items */}
            <div className="space-y-2.5">
              {data.items.map((item, idx) => (
                <div
                  key={idx}
                  className="p-3.5 bg-gray-50 dark:bg-gray-800/40 rounded-lg border border-border-default flex items-center justify-between gap-3"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    {getStatusIcon(item.status)}
                    <div className="min-w-0">
                      <div className="text-sm font-medium text-text-primary dark:text-white truncate">
                        {item.name}
                      </div>
                      <Caption color="tertiary" className="text-xs truncate block">
                        {item.message}
                      </Caption>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    {item.latency_ms !== null && (
                      <span className="font-mono text-xs text-text-secondary">
                        {item.latency_ms.toFixed(1)} ms
                      </span>
                    )}
                    {getStatusBadge(item.status)}
                  </div>
                </div>
              ))}
            </div>

            {/* Retest Button */}
            <div className="flex justify-end pt-2">
              <button
                onClick={runDiagnostics}
                className="px-3.5 py-1.5 bg-primary-600 hover:bg-primary-700 text-white rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors shadow-sm"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>{t("retest")}</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}
