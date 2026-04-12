"use client";

import { useState, useEffect } from "react";
import { api, AssetResponse, Criticality } from "@/lib/api";
import { SkeletonTable } from "@/components/common/LoadingState";
import { useTranslations } from "next-intl";

export default function AssetsPage() {
  const t = useTranslations("assets");
  const tCommon = useTranslations("common");
  const [assets, setAssets] = useState<AssetResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [criticalityFilter, setCriticalityFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [showImport, setShowImport] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [editingAsset, setEditingAsset] = useState<AssetResponse | null>(null);
  const [importJson, setImportJson] = useState("");

  const filteredAssets = assets.filter((asset) => {
    const matchesSearch =
      !search ||
      asset.hostname?.toLowerCase().includes(search.toLowerCase()) ||
      asset.ip?.toLowerCase().includes(search.toLowerCase()) ||
      asset.owner?.toLowerCase().includes(search.toLowerCase()) ||
      asset.business?.toLowerCase().includes(search.toLowerCase());
    const matchesCriticality =
      criticalityFilter === "all" || asset.criticality === criticalityFilter;
    const matchesStatus =
      statusFilter === "all" ||
      (statusFilter === "active" && asset.is_active) ||
      (statusFilter === "inactive" && !asset.is_active);
    return matchesSearch && matchesCriticality && matchesStatus;
  });

  useEffect(() => {
    loadAssets();
  }, []);

  const loadAssets = async () => {
    setLoading(true);
    try {
      const result = await api.listAssets({ query: search || undefined, limit: 100 });
      setAssets(result.items);
    } catch (error) {
      console.error("Failed to load assets:", error);
    }
    setLoading(false);
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    loadAssets();
  };

  const handleDelete = async (id: string) => {
    if (!confirm(t("deleteConfirm"))) return;
    try {
      await api.deleteAsset(id);
      loadAssets();
    } catch (error) {
      console.error("Failed to delete asset:", error);
      alert(t("deleteFailed"));
    }
  };

  const handleEdit = (asset: AssetResponse) => {
    setEditingAsset(asset);
    setShowForm(true);
  };

  const handleImport = async () => {
    try {
      const data = JSON.parse(importJson);
      const result = await api.importAssets({ assets: data });
      alert(t("importSuccess", { imported: result.imported, failed: result.failed }));
      if (result.errors.length > 0) {
        console.error("Import errors:", result.errors);
      }
      setShowImport(false);
      setImportJson("");
      loadAssets();
    } catch (error) {
      console.error("Import failed:", error);
      alert(t("importFailed"));
    }
  };

  const getCriticalityColor = (criticality: Criticality) => {
    switch (criticality) {
      case "critical":
        return "bg-red-100 text-red-800";
      case "high":
        return "bg-orange-100 text-orange-800";
      case "medium":
        return "bg-yellow-100 text-yellow-800";
      case "low":
        return "bg-green-100 text-green-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">{t("title")}</h1>
        <div className="space-x-2">
          <button
            onClick={() => setShowForm(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            + {t("addAsset")}
          </button>
          <button
            onClick={() => setShowImport(true)}
            className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
          >
            {t("importJson")}
          </button>
        </div>
      </div>

      <form onSubmit={handleSearch} className="mb-6 flex gap-2 flex-wrap">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={t("searchPlaceholder")}
          className="flex-1 min-w-[200px] px-4 py-2 border rounded"
        />
        <select
          value={criticalityFilter}
          onChange={(e) => setCriticalityFilter(e.target.value)}
          className="px-3 py-2 border rounded"
        >
          <option value="all">{t("allCriticality")}</option>
          <option value="critical">{tCommon("critical")}</option>
          <option value="high">{tCommon("high")}</option>
          <option value="medium">{tCommon("medium")}</option>
          <option value="low">{tCommon("low")}</option>
        </select>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-2 border rounded"
        >
          <option value="all">{t("allStatus")}</option>
          <option value="active">{tCommon("active")}</option>
          <option value="inactive">{tCommon("inactive")}</option>
        </select>
        <button
          type="submit"
          className="px-6 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
        >
          {tCommon("search")}
        </button>
      </form>

      {loading ? (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
          <SkeletonTable rows={8} columns={6} />
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full bg-white border">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left border">{t("hostname")}</th>
                <th className="px-4 py-2 text-left border">{t("ipAddress")}</th>
                <th className="px-4 py-2 text-left border">{t("owner")}</th>
                <th className="px-4 py-2 text-left border">{t("businessUnit")}</th>
                <th className="px-4 py-2 text-left border">{t("criticality")}</th>
                <th className="px-4 py-2 text-left border">{tCommon("actions")}</th>
              </tr>
            </thead>
            <tbody>
              {assets.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                    {t("noAssetsFound")}
                  </td>
                </tr>
              ) : (
                filteredAssets.map((asset) => (
                  <tr key={asset.id} className="hover:bg-gray-50">
                    <td className="px-4 py-2 border">{asset.hostname || "-"}</td>
                    <td className="px-4 py-2 border">{asset.ip || "-"}</td>
                    <td className="px-4 py-2 border">{asset.owner || "-"}</td>
                    <td className="px-4 py-2 border">{asset.business || "-"}</td>
                    <td className="px-4 py-2 border">
                      <span
                        className={`px-2 py-1 rounded text-xs ${getCriticalityColor(asset.criticality)}`}
                      >
                        {asset.criticality}
                      </span>
                    </td>
                    <td className="px-4 py-2 border">
                      <button
                        onClick={() => handleEdit(asset)}
                        className="text-blue-600 hover:text-blue-800 mr-2"
                      >
                        {tCommon("edit")}
                      </button>
                      <button
                        onClick={() => handleDelete(asset.id)}
                        className="text-red-600 hover:text-red-800"
                      >
                        {tCommon("delete")}
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Import Modal */}
      {showImport && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-white p-6 rounded-lg max-w-2xl w-full mx-4">
            <h2 className="text-xl font-bold mb-4">{t("importTitle")}</h2>
            <textarea
              value={importJson}
              onChange={(e) => setImportJson(e.target.value)}
              placeholder={t("importPlaceholder")}
              className="w-full h-64 px-3 py-2 border rounded font-mono text-sm"
            />
            <div className="mt-4 flex justify-end space-x-2">
              <button
                onClick={() => setShowImport(false)}
                className="px-4 py-2 border rounded hover:bg-gray-100"
              >
                {tCommon("cancel")}
              </button>
              <button
                onClick={handleImport}
                className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
              >
                {tCommon("import")}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Asset Form Modal */}
      {showForm && (
        <AssetForm
          asset={editingAsset}
          onClose={() => {
            setShowForm(false);
            setEditingAsset(null);
          }}
          onSave={() => {
            setShowForm(false);
            setEditingAsset(null);
            loadAssets();
          }}
        />
      )}
    </div>
  );
}

function AssetForm({
  asset,
  onClose,
  onSave,
}: {
  asset: AssetResponse | null;
  onClose: () => void;
  onSave: () => void;
}) {
  const t = useTranslations("assets");
  const tCommon = useTranslations("common");

  const [formData, setFormData] = useState({
    hostname: asset?.hostname || "",
    ip: asset?.ip || "",
    owner: asset?.owner || "",
    business: asset?.business || "",
    criticality: asset?.criticality || "medium",
    tags: asset?.tags?.join(", ") || "",
    notes: asset?.notes || "",
    is_active: asset?.is_active ?? true,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (asset) {
        await api.updateAsset(asset.id, {
          ...formData,
          tags: formData.tags
            .split(",")
            .map((t) => t.trim())
            .filter(Boolean),
        });
      } else {
        await api.createAsset({
          ...formData,
          tags: formData.tags
            .split(",")
            .map((t) => t.trim())
            .filter(Boolean),
        });
      }
      onSave();
    } catch (error: unknown) {
      const err = error as { status?: number; message: string };
      alert(err.message || t("saveFailed"));
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
      <div className="bg-white p-6 rounded-lg max-w-md w-full mx-4">
        <h2 className="text-xl font-bold mb-4">{asset ? t("editAsset") : t("addAssetTitle")}</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">{t("hostname")}</label>
            <input
              type="text"
              value={formData.hostname}
              onChange={(e) => setFormData({ ...formData, hostname: e.target.value })}
              className="w-full px-3 py-2 border rounded"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">{t("ipAddress")}</label>
            <input
              type="text"
              value={formData.ip}
              onChange={(e) => setFormData({ ...formData, ip: e.target.value })}
              className="w-full px-3 py-2 border rounded"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">{t("owner")}</label>
            <input
              type="text"
              value={formData.owner}
              onChange={(e) => setFormData({ ...formData, owner: e.target.value })}
              className="w-full px-3 py-2 border rounded"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">{t("businessUnit")}</label>
            <input
              type="text"
              value={formData.business}
              onChange={(e) => setFormData({ ...formData, business: e.target.value })}
              className="w-full px-3 py-2 border rounded"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">{t("criticality")}</label>
            <select
              value={formData.criticality}
              onChange={(e) =>
                setFormData({ ...formData, criticality: e.target.value as Criticality })
              }
              className="w-full px-3 py-2 border rounded"
            >
              <option value="low">{tCommon("low")}</option>
              <option value="medium">{tCommon("medium")}</option>
              <option value="high">{tCommon("high")}</option>
              <option value="critical">{tCommon("critical")}</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">{t("tags")}</label>
            <input
              type="text"
              value={formData.tags}
              onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
              className="w-full px-3 py-2 border rounded"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">{t("notes")}</label>
            <textarea
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              className="w-full px-3 py-2 border rounded"
              rows={3}
            />
          </div>
          <div className="flex items-center">
            <input
              type="checkbox"
              id="isActive"
              checked={formData.is_active}
              onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
              className="mr-2"
            />
            <label htmlFor="isActive" className="text-sm">
              {t("active")}
            </label>
          </div>
          <div className="flex justify-end space-x-2 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border rounded hover:bg-gray-100"
            >
              {tCommon("cancel")}
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              {tCommon("save")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
