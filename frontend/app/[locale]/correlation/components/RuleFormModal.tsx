"use client";

import { useState, useEffect } from "react";
import { useTranslations, useLocale } from "next-intl";
import { X, Loader2, Sliders, Shield, Layers, AlertCircle } from "lucide-react";
import { authFetchJSON } from "@/lib/auth";
import type { CorrelationRule } from "./RuleDetailsDrawer";

interface RuleFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialData?: CorrelationRule | null;
  onSuccess: () => void;
}

export function RuleFormModal({ isOpen, onClose, initialData, onSuccess }: RuleFormModalProps) {
  const t = useTranslations("correlation");
  const locale = useLocale();
  const isZh = locale.startsWith("zh");

  const isEdit = !!initialData;

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState(50);
  const [timeWindowSeconds, setTimeWindowSeconds] = useState(300);
  const [minSimilarity, setMinSimilarity] = useState(0.7);
  const [action, setAction] = useState("aggregate");
  const [groupByField, setGroupByField] = useState("");
  const [entityTypes, setEntityTypes] = useState({
    ip_address: true,
    username: true,
    hostname: false,
    domains: false,
  });

  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (initialData) {
      setName(initialData.name || "");
      setDescription(initialData.description || "");
      setPriority(initialData.priority ?? 50);
      setTimeWindowSeconds(initialData.time_window_seconds ?? 300);
      setMinSimilarity(initialData.min_similarity ?? 0.7);
      setAction(initialData.action || "aggregate");
      setGroupByField(initialData.group_by_field || "");
      setEntityTypes({
        ip_address: initialData.entity_types?.ip_address ?? true,
        username: initialData.entity_types?.username ?? true,
        hostname: initialData.entity_types?.hostname ?? false,
        domains: initialData.entity_types?.domains ?? false,
      });
    } else {
      setName("");
      setDescription("");
      setPriority(50);
      setTimeWindowSeconds(300);
      setMinSimilarity(0.7);
      setAction("aggregate");
      setGroupByField("");
      setEntityTypes({
        ip_address: true,
        username: true,
        hostname: false,
        domains: false,
      });
    }
    setErrorMessage(null);
  }, [initialData, isOpen]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setErrorMessage(isZh ? "规则名称不能为空" : "Rule name cannot be empty");
      return;
    }

    setSubmitting(true);
    setErrorMessage(null);

    const payload = {
      name: name.trim(),
      description: description.trim() || null,
      priority: Number(priority),
      time_window_seconds: Number(timeWindowSeconds),
      min_similarity: Number(minSimilarity),
      action,
      entity_types: entityTypes,
      group_by_field: groupByField.trim() || null,
    };

    try {
      if (isEdit && initialData) {
        await authFetchJSON(`/api/correlation/rules/${initialData.id}`, {
          method: "PUT",
          body: JSON.stringify(payload),
        });
      } else {
        await authFetchJSON("/api/correlation/rules", {
          method: "POST",
          body: JSON.stringify(payload),
        });
      }

      onSuccess();
      onClose();
    } catch (err: any) {
      console.error("Failed to save rule:", err);
      setErrorMessage(
        err?.message ||
          (isEdit
            ? isZh
              ? "更新规则失败，请稍后再试"
              : "Failed to update rule"
            : isZh
              ? "创建规则失败，请检查输入"
              : "Failed to create rule")
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
      <div
        className="w-full max-w-xl bg-surface-card rounded-2xl border border-border-subtle shadow-2xl overflow-hidden flex flex-col max-h-[90vh] animate-in zoom-in-95 duration-200"
        role="dialog"
        aria-modal="true"
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-border-subtle flex items-center justify-between bg-surface-ground/50">
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-accent-500" />
            <h2 className="text-base font-bold text-text-primary">
              {isEdit ? t("editRuleTitle") : t("createRuleTitle")}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-text-muted hover:text-text-primary hover:bg-surface-hover transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 space-y-5">
          {errorMessage && (
            <div className="p-3.5 rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900/50 flex items-center gap-2.5 text-xs text-rose-700 dark:text-rose-300">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Rule Name */}
          <div>
            <label className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-1.5">
              {t("ruleName")} <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={t("ruleNamePlaceholder")}
              className="w-full px-3.5 py-2 rounded-lg border border-border-subtle bg-surface-ground text-text-primary text-sm focus:outline-none focus:border-accent-500 transition-colors"
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-1.5">
              {t("ruleDesc")}
            </label>
            <textarea
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={t("ruleDescPlaceholder")}
              className="w-full px-3.5 py-2 rounded-lg border border-border-subtle bg-surface-ground text-text-primary text-sm focus:outline-none focus:border-accent-500 transition-colors resize-none"
            />
          </div>

          {/* Priority and Time Window */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-1.5">
                {t("priority")} (1 - 100)
              </label>
              <input
                type="number"
                min={1}
                max={100}
                value={priority}
                onChange={(e) => setPriority(Math.max(1, Math.min(100, Number(e.target.value))))}
                className="w-full px-3.5 py-2 rounded-lg border border-border-subtle bg-surface-ground text-text-primary font-mono text-sm focus:outline-none focus:border-accent-500 transition-colors"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-1.5">
                {t("timeWindow")} ({isZh ? "秒" : "seconds"})
              </label>
              <select
                value={timeWindowSeconds}
                onChange={(e) => setTimeWindowSeconds(Number(e.target.value))}
                className="w-full px-3.5 py-2 rounded-lg border border-border-subtle bg-surface-ground text-text-primary text-sm focus:outline-none focus:border-accent-500 transition-colors"
              >
                <option value={60}>{isZh ? "60 秒 (1 分钟)" : "60 seconds (1 min)"}</option>
                <option value={120}>{isZh ? "120 秒 (2 分钟)" : "120 seconds (2 mins)"}</option>
                <option value={300}>{isZh ? "300 秒 (5 分钟)" : "300 seconds (5 mins)"}</option>
                <option value={600}>{isZh ? "600 秒 (10 分钟)" : "600 seconds (10 mins)"}</option>
                <option value={1800}>
                  {isZh ? "1800 秒 (30 分钟)" : "1800 seconds (30 mins)"}
                </option>
                <option value={3600}>{isZh ? "3600 秒 (1 小时)" : "3600 seconds (1 hour)"}</option>
                <option value={86400}>
                  {isZh ? "86400 秒 (24 小时)" : "86400 seconds (24 hours)"}
                </option>
              </select>
            </div>
          </div>

          {/* Min Similarity and Action */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-1.5">
                {t("minSimilarity")} ({Math.round(minSimilarity * 100)}%)
              </label>
              <input
                type="range"
                min={0.1}
                max={1.0}
                step={0.05}
                value={minSimilarity}
                onChange={(e) => setMinSimilarity(Number(e.target.value))}
                className="w-full accent-accent-600 mt-2"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-1.5">
                {t("action")}
              </label>
              <select
                value={action}
                onChange={(e) => setAction(e.target.value)}
                className="w-full px-3.5 py-2 rounded-lg border border-border-subtle bg-surface-ground text-text-primary text-sm focus:outline-none focus:border-accent-500 transition-colors"
              >
                <option value="aggregate">{t("actionAggregate")}</option>
                <option value="escalate">{t("actionEscalate")}</option>
                <option value="suppress">{t("actionSuppress")}</option>
              </select>
            </div>
          </div>

          {/* Entity Matching Types */}
          <div>
            <label className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">
              {t("entityTypes")}
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
              {[
                { key: "ip_address", label: t("ipAddress") },
                { key: "username", label: t("username") },
                { key: "hostname", label: t("hostname") },
                { key: "domains", label: t("domains") },
              ].map(({ key, label }) => {
                const isChecked = entityTypes[key as keyof typeof entityTypes];
                return (
                  <label
                    key={key}
                    className={`flex items-center gap-2 p-2.5 rounded-lg border cursor-pointer text-xs transition-colors select-none ${
                      isChecked
                        ? "bg-accent-50/60 dark:bg-accent-950/30 border-accent-300 dark:border-accent-700 text-accent-800 dark:text-accent-300 font-medium"
                        : "bg-surface-ground border-border-subtle text-text-secondary"
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={(e) =>
                        setEntityTypes((prev) => ({
                          ...prev,
                          [key]: e.target.checked,
                        }))
                      }
                      className="rounded text-accent-600 focus:ring-accent-500"
                    />
                    <span>{label}</span>
                  </label>
                );
              })}
            </div>
          </div>

          {/* Group By Field */}
          <div>
            <label className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-1.5">
              {t("groupBy")}
            </label>
            <input
              type="text"
              value={groupByField}
              onChange={(e) => setGroupByField(e.target.value)}
              placeholder={
                isZh
                  ? "如：source_ip 或 username（留空则全局多源聚合）"
                  : "e.g. source_ip or username (leave empty for global aggregation)"
              }
              className="w-full px-3.5 py-2 rounded-lg border border-border-subtle bg-surface-ground text-text-primary text-sm focus:outline-none focus:border-accent-500 transition-colors"
            />
          </div>

          {/* Footer Buttons */}
          <div className="pt-4 border-t border-border-subtle flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={submitting}
              className="px-4 py-2 text-xs font-medium rounded-lg border border-border-subtle text-text-secondary hover:bg-surface-hover transition-colors"
            >
              {t("cancel")}
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="flex items-center gap-1.5 px-4 py-2 text-xs font-medium rounded-lg bg-accent-600 text-white hover:bg-accent-700 disabled:opacity-50 transition-colors shadow-sm"
            >
              {submitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              {submitting ? (isEdit ? t("saving") : t("creating")) : t("save")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
