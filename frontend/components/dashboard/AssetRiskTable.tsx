"use client";

/**
 * AssetRiskTable - DataTable showing top N risky assets
 */

import { useMemo } from "react";
import { ShieldAlert, Server } from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/Badge";
import { DataTable, type ColumnDef } from "@/components/ui/DataTable";
import type { AssetRiskItem } from "@/lib/api/dashboard";

interface AssetRiskTableProps {
  data: AssetRiskItem[];
  isLoading?: boolean;
  className?: string;
  title?: string;
}

function getRiskBadge(score: number): {
  severity: "critical" | "high" | "medium" | "low" | "info";
  label: string;
} {
  if (score >= 80) return { severity: "critical", label: "Critical" };
  if (score >= 60) return { severity: "high", label: "High" };
  if (score >= 40) return { severity: "medium", label: "Medium" };
  if (score >= 20) return { severity: "low", label: "Low" };
  return { severity: "info", label: "Info" };
}

export function AssetRiskTable({
  data,
  isLoading = false,
  className,
  title = "Asset Risk Top 10",
}: AssetRiskTableProps) {
  const columns = useMemo<ColumnDef<AssetRiskItem>[]>(
    () => [
      {
        key: "asset_name",
        header: "Asset Name",
        width: "2fr",
        cell: (row) => (
          <div className="flex items-center gap-2">
            <Server className="w-4 h-4 text-gray-400 shrink-0" />
            <div className="min-w-0">
              <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                {row.asset_name}
              </p>
              <p className="text-xs text-text-tertiary">{row.asset_type}</p>
            </div>
          </div>
        ),
      },
      {
        key: "risk_score",
        header: "Risk Score",
        width: "110px",
        align: "center",
        cell: (row) => {
          const { severity, label } = getRiskBadge(row.risk_score);
          return (
            <div className="flex items-center gap-2 justify-center">
              <div
                className={cn("h-2 w-16 rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden")}
              >
                <div
                  className={cn(
                    "h-full rounded-full transition-all duration-500",
                    row.risk_score >= 80
                      ? "bg-red-500"
                      : row.risk_score >= 60
                        ? "bg-orange-500"
                        : row.risk_score >= 40
                          ? "bg-amber-500"
                          : row.risk_score >= 20
                            ? "bg-blue-500"
                            : "bg-gray-400"
                  )}
                  style={{ width: `${Math.min(row.risk_score, 100)}%` }}
                />
              </div>
              <span className="text-sm font-semibold text-gray-900 dark:text-white w-8 text-right">
                {row.risk_score}
              </span>
            </div>
          );
        },
      },
      {
        key: "ip_address",
        header: "IP",
        width: "130px",
        cell: (row) => (
          <span className="text-sm font-mono text-gray-600 dark:text-gray-400">
            {row.ip_address || "—"}
          </span>
        ),
      },
      {
        key: "alert_count",
        header: "Alerts",
        width: "90px",
        align: "center",
        cell: (row) => {
          const critical = row.critical_count || 0;
          const high = row.high_count || 0;
          return (
            <div className="flex items-center gap-1 justify-center">
              <span className="text-sm font-semibold text-gray-900 dark:text-white">
                {row.alert_count}
              </span>
              {(critical > 0 || high > 0) && (
                <span className="flex items-center gap-0.5 ml-1">
                  {critical > 0 && (
                    // 原为 bg-red-100 + text-red-600（3.95:1）。改用 severity 语义槽位：
                    // critical-fg on critical-bg = 5.91:1，且明暗两套值由 token 自带。
                    <span className="text-[10px] px-1 rounded bg-severity-critical-bg text-severity-critical-fg font-semibold">
                      {critical}C
                    </span>
                  )}
                  {high > 0 && (
                    <span className="text-[10px] px-1 rounded bg-severity-high-bg text-severity-high-fg font-semibold">
                      {high}H
                    </span>
                  )}
                </span>
              )}
            </div>
          );
        },
      },
    ],
    []
  );

  if (isLoading) {
    return (
      <div
        className={cn(
          "bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5",
          className
        )}
      >
        <div className="animate-pulse">
          <div className="h-5 bg-gray-200 dark:bg-gray-700 rounded w-40 mb-4" />
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-10 bg-gray-100 dark:bg-gray-700 rounded" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden",
        className
      )}
    >
      <div className="px-5 pt-5 pb-0">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-amber-500" />
          {title}
        </h3>
      </div>
      <DataTable
        data={data}
        columns={columns}
        emptyState={{
          icon: <Server className="w-8 h-8" />,
          title: "No assets",
          description: "No asset risk data available.",
        }}
        showPagination={false}
      />
    </div>
  );
}
