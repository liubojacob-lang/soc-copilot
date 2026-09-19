"use client";

import { useState, useEffect, useRef } from "react";
import { useTranslations, useLocale, useFormatter } from "next-intl";
import {
  X,
  Shield,
  Clock,
  Sliders,
  CheckCircle,
  XCircle,
  Lock,
  Edit2,
  Trash2,
  Loader2,
  Copy,
  Check,
  Activity,
  Layers,
  Sparkles,
} from "lucide-react";
import { getLocalizedRule } from "@/lib/correlationRulesI18n";
import { useFocusTrap } from "@/hooks/useFocusTrap";

export interface CorrelationRule {
  id: string;
  name: string;
  description: string | null;
  enabled: boolean;
  is_builtin?: boolean;
  priority: number;
  time_window_seconds: number;
  min_similarity: number;
  entity_types?: Record<string, boolean>;
  conditions?: Record<string, any>;
  action?: string;
  action_params?: Record<string, any>;
  group_by_field?: string | null;
  total_correlations: number;
  last_triggered?: string | null;
  created_at: string;
}

interface RuleDetailsDrawerProps {
  rule: CorrelationRule | null;
  isOpen: boolean;
  onClose: () => void;
  onToggle: (ruleId: string) => Promise<void>;
  isToggling: boolean;
  onEdit?: (rule: CorrelationRule) => void;
  onDelete?: (ruleId: string) => Promise<void>;
  isDeleting?: boolean;
}

export function RuleDetailsDrawer({
  rule,
  isOpen,
  onClose,
  onToggle,
  isToggling,
  onEdit,
  onDelete,
  isDeleting = false,
}: RuleDetailsDrawerProps) {
  const t = useTranslations("correlation");
  const locale = useLocale();
  const format = useFormatter();
  const [copiedId, setCopiedId] = useState(false);

  // Lock background scroll when drawer is open
  useEffect(() => {
    if (!isOpen) return;
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prevOverflow;
    };
  }, [isOpen]);

  // Escape-to-close + focus trap, aligned with the shared Modal component
  const drawerRef = useRef<HTMLDivElement>(null);
  useFocusTrap(isOpen && !!rule, onClose, drawerRef);

  if (!isOpen || !rule) return null;

  const { displayName, displayDescription, displayCategory } = getLocalizedRule(rule, locale);
  const isBuiltin = rule.is_builtin ?? !rule.id.includes("custom");

  const handleCopyId = () => {
    navigator.clipboard.writeText(rule.id);
    setCopiedId(true);
    setTimeout(() => setCopiedId(false), 2000);
  };

  const formatWindow = (seconds: number) => {
    if (seconds < 60) return `${seconds}s`;
    const mins = Math.floor(seconds / 60);
    const rem = seconds % 60;
    if (rem === 0) return `${seconds}s (${mins}m)`;
    return `${seconds}s (${mins}m ${rem}s)`;
  };

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end bg-black/40 backdrop-blur-sm animate-in fade-in duration-200"
      onMouseDown={(e) => {
        // 仅点击遮罩本身(非内容)时关闭
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={drawerRef}
        className="w-full max-w-xl bg-surface-card border-l border-border-subtle shadow-2xl h-full flex flex-col overflow-hidden animate-in slide-in-from-right duration-250"
        role="dialog"
        aria-modal="true"
        tabIndex={-1}
        // 阻止 mousedown 冒泡到遮罩(避免误关闭)
        onMouseDown={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 py-5 border-b border-border-subtle flex items-start justify-between gap-4 bg-surface-ground/50">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap mb-2">
              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300 border border-blue-200/60 dark:border-blue-800/40">
                {displayCategory}
              </span>
              {isBuiltin ? (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-purple-50 text-purple-700 dark:bg-purple-950/40 dark:text-purple-300 border border-purple-200/60 dark:border-purple-800/40">
                  <Lock className="w-3 h-3" />
                  {t("builtinRule")}
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300 border border-amber-200/60 dark:border-amber-800/40">
                  <Sparkles className="w-3 h-3" />
                  {t("customRule")}
                </span>
              )}
              {rule.enabled ? (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                  <CheckCircle className="w-3 h-3" />
                  {t("enabled")}
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-surface-hover text-text-muted border border-border-subtle">
                  <XCircle className="w-3 h-3" />
                  {t("disabled")}
                </span>
              )}
            </div>

            <h2 className="text-lg font-bold text-text-primary tracking-tight line-clamp-2">
              {displayName}
            </h2>
            {rule.name !== displayName && (
              <p className="text-xs font-mono text-text-muted mt-1 break-all">{rule.name}</p>
            )}
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-text-muted hover:text-text-primary hover:bg-surface-hover transition-colors"
            title={locale.startsWith("zh") ? "关闭" : "Close"}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Rule Notice */}
          {isBuiltin ? (
            <div className="p-3.5 rounded-lg bg-blue-50/70 dark:bg-blue-950/30 border border-blue-200/70 dark:border-blue-800/50 flex gap-3 text-xs text-blue-900 dark:text-blue-200">
              <Lock className="w-4 h-4 shrink-0 text-blue-600 dark:text-blue-400 mt-0.5" />
              <p className="leading-relaxed">{t("builtinRuleNotice")}</p>
            </div>
          ) : null}

          {/* Description */}
          <div>
            <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">
              {t("ruleDesc")}
            </h3>
            <p className="text-sm text-text-primary bg-surface-ground p-3.5 rounded-lg border border-border-subtle leading-relaxed">
              {displayDescription || rule.description || "—"}
            </p>
          </div>

          {/* Core Match Parameters */}
          <div>
            <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-3 flex items-center gap-2">
              <Sliders className="w-4 h-4 text-accent-500" />
              {t("coreParams")}
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 bg-surface-ground rounded-lg border border-border-subtle">
                <span className="text-xs text-text-secondary block mb-1">{t("priority")}</span>
                <span className="text-base font-bold text-text-primary font-mono">
                  {rule.priority} <span className="text-xs font-normal text-text-muted">/ 100</span>
                </span>
              </div>
              <div className="p-3 bg-surface-ground rounded-lg border border-border-subtle">
                <span className="text-xs text-text-secondary block mb-1">{t("timeWindow")}</span>
                <span className="text-base font-bold text-text-primary font-mono">
                  {formatWindow(rule.time_window_seconds)}
                </span>
              </div>
              <div className="p-3 bg-surface-ground rounded-lg border border-border-subtle">
                <span className="text-xs text-text-secondary block mb-1">{t("minSimilarity")}</span>
                <span className="text-base font-bold text-text-primary font-mono">
                  {(rule.min_similarity * 100).toFixed(0)}%
                </span>
              </div>
              <div className="p-3 bg-surface-ground rounded-lg border border-border-subtle">
                <span className="text-xs text-text-secondary block mb-1">{t("action")}</span>
                <span className="text-sm font-semibold text-text-primary capitalize">
                  {rule.action === "escalate"
                    ? t("actionEscalate")
                    : rule.action === "suppress"
                      ? t("actionSuppress")
                      : t("actionAggregate")}
                </span>
              </div>
            </div>
          </div>

          {/* Entity Matching Types */}
          <div>
            <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2 flex items-center gap-2">
              <Layers className="w-4 h-4 text-accent-500" />
              {t("entityTypes")}
            </h3>
            <div className="grid grid-cols-2 gap-2">
              {[
                { key: "ip_address", label: t("ipAddress") },
                { key: "username", label: t("username") },
                { key: "hostname", label: t("hostname") },
                { key: "domains", label: t("domains") },
              ].map(({ key, label }) => {
                const isMatched = rule.entity_types?.[key] ?? false;
                return (
                  <div
                    key={key}
                    className={`px-3 py-2 rounded-lg border text-xs flex items-center justify-between ${
                      isMatched
                        ? "bg-emerald-50/50 border-emerald-200 dark:bg-emerald-950/20 dark:border-emerald-800 text-text-primary"
                        : "bg-surface-ground border-border-subtle text-text-muted opacity-60"
                    }`}
                  >
                    <span>{label}</span>
                    {isMatched ? (
                      <span className="font-semibold text-emerald-600 dark:text-emerald-400">
                        {locale.startsWith("zh") ? "✓ 匹配" : "✓ Match"}
                      </span>
                    ) : (
                      <span>—</span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Grouping & Advanced Details */}
          {rule.group_by_field && (
            <div>
              <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">
                {t("groupBy")}
              </h3>
              <div className="p-3 bg-surface-ground rounded-lg border border-border-subtle font-mono text-xs text-text-primary">
                {rule.group_by_field}
              </div>
            </div>
          )}

          {/* Runtime & Metrics */}
          <div>
            <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-3 flex items-center gap-2">
              <Activity className="w-4 h-4 text-accent-500" />
              {t("runtimeMetrics")}
            </h3>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between py-2 border-b border-border-subtle">
                <span className="text-text-secondary">{t("correlations")}</span>
                <span className="font-mono font-semibold text-text-primary">
                  {rule.total_correlations} {locale.startsWith("zh") ? "次" : "times"}
                </span>
              </div>
              <div className="flex justify-between py-2 border-b border-border-subtle">
                <span className="text-text-secondary">{t("created")}</span>
                <span className="text-text-primary">
                  {rule.created_at
                    ? format.dateTime(new Date(rule.created_at), {
                        dateStyle: "medium",
                        timeStyle: "short",
                      })
                    : "—"}
                </span>
              </div>
              <div className="flex justify-between items-center py-2">
                <span className="text-text-secondary">
                  {locale.startsWith("zh") ? "规则 ID" : "Rule ID"}
                </span>
                <div className="flex items-center gap-1.5 font-mono text-[11px] text-text-muted">
                  <span className="max-w-[200px] truncate">{rule.id}</span>
                  <button
                    onClick={handleCopyId}
                    className="p-1 hover:text-text-primary rounded hover:bg-surface-hover"
                    title={locale.startsWith("zh") ? "复制 ID" : "Copy ID"}
                  >
                    {copiedId ? (
                      <Check className="w-3.5 h-3.5 text-emerald-500" />
                    ) : (
                      <Copy className="w-3.5 h-3.5" />
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="p-4 border-t border-border-subtle bg-surface-ground flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            {!isBuiltin && onEdit && (
              <button
                onClick={() => onEdit(rule)}
                className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg border border-border-subtle text-text-primary hover:bg-surface-hover transition-colors"
              >
                <Edit2 className="w-3.5 h-3.5" />
                {t("edit")}
              </button>
            )}
            {!isBuiltin && onDelete && (
              <button
                disabled={isDeleting}
                onClick={() => onDelete(rule.id)}
                className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg border border-rose-200 dark:border-rose-900/50 text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/40 disabled:opacity-50 transition-colors"
              >
                {isDeleting ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Trash2 className="w-3.5 h-3.5" />
                )}
                {t("delete")}
              </button>
            )}
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 text-xs font-medium rounded-lg border border-border-subtle text-text-secondary hover:bg-surface-hover transition-colors"
            >
              {t("cancel")}
            </button>
            <button
              type="button"
              disabled={isToggling}
              onClick={() => onToggle(rule.id)}
              className={`flex items-center gap-1.5 px-4 py-2 text-xs font-medium rounded-lg transition-colors disabled:opacity-50 text-white shadow-sm ${
                rule.enabled
                  ? "bg-rose-600 hover:bg-rose-700"
                  : "bg-emerald-600 hover:bg-emerald-700"
              }`}
            >
              {isToggling && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              {rule.enabled ? t("disable") : t("enable")}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
