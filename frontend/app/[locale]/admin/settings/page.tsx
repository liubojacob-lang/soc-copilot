"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "@/i18n/navigation";
import { useTranslations } from "next-intl";
import { loadAuthState, authFetch } from "@/lib/auth";
import { PageHeader } from "@/components/common/PageHeader";
import { SkeletonTable } from "@/components/common/LoadingState";
import { useToast } from "@/components/Toast";
import { RotateCcw, Save, Settings2, Timer } from "lucide-react";

interface DynamicConfigItem {
  key: string;
  current_value: unknown;
  default_value: unknown;
  is_overridden: boolean;
  type: string;
  description: string;
}

interface TimeoutConfig {
  analysis_ms: number;
  default_ms: number;
  health_ms: number;
  report_ms: number;
  timeline_ms: number;
  dag_run_ms: number;
}

/** Admin system settings: API timeout reference + dynamic config overrides. */
export default function AdminSettingsPage() {
  const t = useTranslations("adminSettings");
  const tCommon = useTranslations("common");
  const router = useRouter();
  const { showToast } = useToast();

  const [authorized, setAuthorized] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<Error | null>(null);
  const [timeouts, setTimeouts] = useState<TimeoutConfig | null>(null);
  const [items, setItems] = useState<DynamicConfigItem[]>([]);
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const state = loadAuthState();
    if (!state?.isAuthenticated || state.user?.role !== "admin") {
      router.push("/");
      return;
    }
    setAuthorized(true);
  }, [router]);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const [timeoutRes, dynamicRes] = await Promise.all([
        authFetch("/api/v1/admin/settings/timeouts"),
        authFetch("/api/v1/admin/settings/dynamic"),
      ]);
      if (!timeoutRes.ok || !dynamicRes.ok) {
        throw new Error(`HTTP ${timeoutRes.status}/${dynamicRes.status}`);
      }
      setTimeouts(await timeoutRes.json());
      setItems(await dynamicRes.json());
    } catch (e) {
      setLoadError(e instanceof Error ? e : new Error(String(e)));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (authorized) load();
  }, [authorized, load]);

  const saveOverride = async (key: string, raw: string) => {
    setSaving(true);
    try {
      let value: unknown = raw;
      const item = items.find((i) => i.key === key);
      if (item?.type === "int" || item?.type === "float") {
        value = Number(raw);
        if (Number.isNaN(value)) {
          showToast(t("invalidNumber"), "error");
          return;
        }
      } else if (item?.type === "bool") {
        value = raw.trim().toLowerCase() === "true";
      }
      const response = await authFetch(`/api/v1/admin/settings/dynamic/${key}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ value }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      showToast(t("saved"), "success");
      setEditingKey(null);
      load();
    } catch (e) {
      showToast(e instanceof Error ? e.message : t("saveFailed"), "error");
    } finally {
      setSaving(false);
    }
  };

  const resetOverride = async (key: string) => {
    setSaving(true);
    try {
      const response = await authFetch(`/api/v1/admin/settings/dynamic/${key}`, {
        method: "DELETE",
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      showToast(t("resetDone"), "success");
      load();
    } catch (e) {
      showToast(e instanceof Error ? e.message : t("saveFailed"), "error");
    } finally {
      setSaving(false);
    }
  };

  if (!authorized) return null;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <PageHeader title={t("title")} subtitle={t("subtitle")} />

      <main className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {loadError && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-300 dark:border-red-800 text-red-700 dark:text-red-300 rounded-lg px-4 py-3 flex items-center justify-between">
            <span>
              {t("loadFailed")}：{loadError.message}
            </span>
            <button
              onClick={load}
              className="px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700"
            >
              {tCommon("retry")}
            </button>
          </div>
        )}

        {/* API timeouts (read-only reference) */}
        <section className="bg-white dark:bg-gray-800 shadow rounded-lg p-6 border border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <Timer className="w-5 h-5" />
            {t("timeouts")}
          </h2>
          {loading ? (
            <SkeletonTable rows={3} columns={2} />
          ) : timeouts ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
              {Object.entries(timeouts).map(([key, ms]) => (
                <div
                  key={key}
                  className="border border-gray-200 dark:border-gray-700 rounded-lg p-3"
                >
                  <p className="text-xs text-gray-500 dark:text-gray-400">{key}</p>
                  <p className="text-lg font-semibold text-gray-900 dark:text-white">{ms} ms</p>
                </div>
              ))}
            </div>
          ) : null}
        </section>

        {/* Dynamic config overrides */}
        <section className="bg-white dark:bg-gray-800 shadow rounded-lg p-6 border border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <Settings2 className="w-5 h-5" />
            {t("dynamicConfig")}
          </h2>
          {loading ? (
            <SkeletonTable rows={6} columns={4} />
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-gray-50 dark:bg-gray-900">
                  <tr>
                    <th className="px-3 py-2 text-left border-b dark:border-gray-700">
                      {t("key")}
                    </th>
                    <th className="px-3 py-2 text-left border-b dark:border-gray-700">
                      {t("currentValue")}
                    </th>
                    <th className="px-3 py-2 text-left border-b dark:border-gray-700">
                      {t("defaultValue")}
                    </th>
                    <th className="px-3 py-2 text-left border-b dark:border-gray-700">
                      {tCommon("actions")}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr key={item.key} className="border-b dark:border-gray-700 align-top">
                      <td className="px-3 py-2">
                        <p className="font-medium text-gray-900 dark:text-white">{item.key}</p>
                        {item.description && (
                          <p className="text-xs text-gray-500">{item.description}</p>
                        )}
                      </td>
                      <td className="px-3 py-2">
                        {editingKey === item.key ? (
                          <input
                            className="w-32 px-2 py-1 border rounded dark:bg-gray-900 dark:border-gray-700"
                            defaultValue={String(item.current_value)}
                            onChange={(e) => setEditValue(e.target.value)}
                            autoFocus
                          />
                        ) : (
                          <span
                            className={
                              item.is_overridden
                                ? "font-semibold text-amber-600 dark:text-amber-400"
                                : ""
                            }
                          >
                            {String(item.current_value)}
                            {item.is_overridden && (
                              <span className="ml-1 text-xs">({t("overridden")})</span>
                            )}
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2 text-gray-500">
                        {String(item.default_value ?? "—")}
                      </td>
                      <td className="px-3 py-2">
                        <div className="flex items-center gap-2">
                          {editingKey === item.key ? (
                            <button
                              onClick={() => saveOverride(item.key, editValue)}
                              disabled={saving}
                              className="px-2 py-1 bg-primary-600 text-white rounded hover:bg-primary-700 disabled:opacity-50 flex items-center gap-1"
                            >
                              <Save className="w-3.5 h-3.5" />
                              {tCommon("save")}
                            </button>
                          ) : (
                            <button
                              onClick={() => {
                                setEditingKey(item.key);
                                setEditValue(String(item.current_value));
                              }}
                              className="px-2 py-1 border rounded hover:bg-gray-50 dark:hover:bg-gray-900"
                            >
                              {t("edit")}
                            </button>
                          )}
                          {item.is_overridden && (
                            <button
                              onClick={() => resetOverride(item.key)}
                              disabled={saving}
                              className="px-2 py-1 border rounded hover:bg-gray-50 dark:hover:bg-gray-900 flex items-center gap-1 disabled:opacity-50"
                              title={t("reset")}
                            >
                              <RotateCcw className="w-3.5 h-3.5" />
                              {t("reset")}
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                  {items.length === 0 && (
                    <tr>
                      <td colSpan={4} className="px-3 py-6 text-center text-gray-500">
                        {t("noDynamic")}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
