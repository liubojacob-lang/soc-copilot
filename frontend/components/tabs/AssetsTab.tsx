"use client";

import { useState, useEffect } from "react";
import { useTranslations } from 'next-intl';
import {
  Search,
  Plus,
  Edit,
  Trash2,
  X,
  Server,
  User,
  Building,
} from "lucide-react";

interface Asset {
  id: string;
  hostname: string | null;
  ip: string | null;
  owner: string | null;
  business: string | null;
  criticality: "low" | "medium" | "high" | "critical";
  tags: string[];
  notes: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

const CRITICALITY_COLORS = {
  low: "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300",
  medium: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300",
  high: "bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300",
  critical: "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300",
};

export function AssetsTab() {
  const t = useTranslations('assets');
  const tCommon = useTranslations('common');
  
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  // Modal states
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [selectedAsset, setSelectedAsset] = useState<Asset | null>(null);

  // Form state
  const [formData, setFormData] = useState({
    hostname: "",
    ip: "",
    owner: "",
    business: "",
    criticality: "medium" as "low" | "medium" | "high" | "critical",
    tags: "",
    notes: "",
    is_active: true,
  });
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    loadAssets();
  }, [search]);

  const loadAssets = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem("access_token");
      const params = new URLSearchParams();
      if (search) params.append("query", search);
      params.append("limit", "50");

      const response = await fetch(`/api/assets?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) throw new Error("Failed to load assets");

      const data = await response.json();
      setAssets(data.items || []);
    } catch (err) {
      console.error("Failed to load assets:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const token = localStorage.getItem("access_token");
      const response = await fetch("/api/assets", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          ...formData,
          tags: formData.tags.split(",").map((t) => t.trim()).filter(Boolean),
        }),
      });

      if (!response.ok) throw new Error("Failed to create asset");

      setShowCreateModal(false);
      resetForm();
      loadAssets();
    } catch (err) {
      console.error("Failed to create asset:", err);
    } finally {
      setSubmitting(false);
    }
  };

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAsset) return;
    setSubmitting(true);
    try {
      const token = localStorage.getItem("access_token");
      const response = await fetch(`/api/assets/${selectedAsset.id}`, {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          ...formData,
          tags: formData.tags.split(",").map((t) => t.trim()).filter(Boolean),
        }),
      });

      if (!response.ok) throw new Error("Failed to update asset");

      setShowEditModal(false);
      resetForm();
      loadAssets();
    } catch (err) {
      console.error("Failed to update asset:", err);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to delete this asset?")) return;
    try {
      const token = localStorage.getItem("access_token");
      const response = await fetch(`/api/assets/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) throw new Error("Failed to delete asset");
      loadAssets();
    } catch (err) {
      console.error("Failed to delete asset:", err);
    }
  };

  const openEditModal = (asset: Asset) => {
    setSelectedAsset(asset);
    setFormData({
      hostname: asset.hostname || "",
      ip: asset.ip || "",
      owner: asset.owner || "",
      business: asset.business || "",
      criticality: asset.criticality,
      tags: asset.tags.join(", "),
      notes: asset.notes || "",
      is_active: asset.is_active,
    });
    setShowEditModal(true);
  };

  const resetForm = () => {
    setFormData({
      hostname: "",
      ip: "",
      owner: "",
      business: "",
      criticality: "medium",
      tags: "",
      notes: "",
      is_active: true,
    });
    setSelectedAsset(null);
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t('searchPlaceholder')}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm"
          />
        </div>
        <button
          onClick={() => {
            resetForm();
            setShowCreateModal(true);
          }}
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          <Plus className="w-4 h-4" />
          {t('create')}
        </button>
      </div>

      {/* Assets List */}
      {loading ? (
        <div className="text-center py-8">
          <div className="w-6 h-6 border-2 border-gray-300 border-t-blue-600 rounded-full animate-spin mx-auto" />
        </div>
      ) : assets.length === 0 ? (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          <Server className="w-10 h-10 mx-auto mb-2 opacity-50" />
          <p>{t('noAssets')}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {assets.map((asset) => (
            <div
              key={asset.id}
              className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3 border border-gray-200 dark:border-gray-600"
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Server className="w-4 h-4 text-gray-400" />
                  <span className="font-medium text-gray-900 dark:text-white text-sm">
                    {asset.hostname || asset.ip || t('unknown')}
                  </span>
                </div>
                <span
                  className={`px-2 py-0.5 text-xs font-medium rounded ${
                    CRITICALITY_COLORS[asset.criticality]
                  }`}
                >
                  {asset.criticality}
                </span>
              </div>

              <div className="space-y-1 text-xs text-gray-600 dark:text-gray-400">
                {asset.ip && <div>IP: {asset.ip}</div>}
                {asset.owner && (
                  <div className="flex items-center gap-1">
                    <User className="w-3 h-3" />
                    {asset.owner}
                  </div>
                )}
                {asset.business && (
                  <div className="flex items-center gap-1">
                    <Building className="w-3 h-3" />
                    {asset.business}
                  </div>
                )}
                {asset.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1">
                    {asset.tags.slice(0, 3).map((tag, i) => (
                      <span
                        key={i}
                        className="px-1.5 py-0.5 bg-gray-200 dark:bg-gray-600 rounded text-xs"
                      >
                        {tag}
                      </span>
                    ))}
                    {asset.tags.length > 3 && (
                      <span className="text-gray-400">+{asset.tags.length - 3}</span>
                    )}
                  </div>
                )}
              </div>

              <div className="flex justify-end gap-1 mt-2 pt-2 border-t border-gray-200 dark:border-gray-600">
                <button
                  onClick={() => openEditModal(asset)}
                  className="p-1 text-gray-400 hover:text-blue-600 rounded"
                >
                  <Edit className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => handleDelete(asset.id)}
                  className="p-1 text-gray-400 hover:text-red-600 rounded"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <Modal title={t('createAsset')} onClose={() => setShowCreateModal(false)}>
          <AssetForm
            formData={formData}
            setFormData={setFormData}
            onSubmit={handleCreate}
            submitting={submitting}
            submitLabel={t('create')}
            t={t}
            tCommon={tCommon}
          />
        </Modal>
      )}

      {/* Edit Modal */}
      {showEditModal && (
        <Modal title={t('editAsset')} onClose={() => setShowEditModal(false)}>
          <AssetForm
            formData={formData}
            setFormData={setFormData}
            onSubmit={handleUpdate}
            submitting={submitting}
            submitLabel={tCommon('save')}
            t={t}
            tCommon={tCommon}
          />
        </Modal>
      )}
    </div>
  );
}

// Modal Component
function Modal({ title, children, onClose }: { title: string; children: React.ReactNode; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-white dark:bg-gray-800 rounded-xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-5 py-3 border-b border-gray-200 dark:border-gray-700">
          <h3 className="font-semibold text-gray-900 dark:text-white">{title}</h3>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded">
            <X className="w-4 h-4 text-gray-400" />
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}

// Asset Form Component
function AssetForm({
  formData,
  setFormData,
  onSubmit,
  submitting,
  submitLabel,
  t,
  tCommon,
}: {
  formData: any;
  setFormData: any;
  onSubmit: (e: React.FormEvent) => void;
  submitting: boolean;
  submitLabel: string;
  t: any;
  tCommon: any;
}) {
  return (
    <form onSubmit={onSubmit} className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
            {t('hostname')}
          </label>
          <input
            type="text"
            value={formData.hostname}
            onChange={(e) => setFormData({ ...formData, hostname: e.target.value })}
            className="w-full px-2.5 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
            {t('ip')}
          </label>
          <input
            type="text"
            value={formData.ip}
            onChange={(e) => setFormData({ ...formData, ip: e.target.value })}
            className="w-full px-2.5 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
            {t('owner')}
          </label>
          <input
            type="text"
            value={formData.owner}
            onChange={(e) => setFormData({ ...formData, owner: e.target.value })}
            className="w-full px-2.5 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
            {t('business')}
          </label>
          <input
            type="text"
            value={formData.business}
            onChange={(e) => setFormData({ ...formData, business: e.target.value })}
            className="w-full px-2.5 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          />
        </div>
      </div>
      <div>
        <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
          {t('criticality')}
        </label>
        <select
          value={formData.criticality}
          onChange={(e) => setFormData({ ...formData, criticality: e.target.value })}
          className="w-full px-2.5 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
        >
          <option value="low">{t('criticalities.low')}</option>
          <option value="medium">{t('criticalities.medium')}</option>
          <option value="high">{t('criticalities.high')}</option>
          <option value="critical">{t('criticalities.critical')}</option>
        </select>
      </div>
      <div>
        <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
          {t('tags')}
        </label>
        <input
          type="text"
          value={formData.tags}
          onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
          placeholder="server, production"
          className="w-full px-2.5 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
        />
      </div>
      <div className="flex justify-end gap-2 pt-2">
        <button
          type="submit"
          disabled={submitting}
          className="px-4 py-2 text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {submitting ? tCommon('loading') : submitLabel}
        </button>
      </div>
    </form>
  );
}
