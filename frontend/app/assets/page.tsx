"use client";

import { useState, useEffect } from "react";
import { api, AssetResponse, Criticality } from "@/lib/api";

export default function AssetsPage() {
  const [assets, setAssets] = useState<AssetResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [showImport, setShowImport] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [editingAsset, setEditingAsset] = useState<AssetResponse | null>(null);
  const [importJson, setImportJson] = useState("");

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
    if (!confirm("Are you sure you want to delete this asset?")) return;
    try {
      await api.deleteAsset(id);
      loadAssets();
    } catch (error) {
      console.error("Failed to delete asset:", error);
      alert("Failed to delete asset");
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
      alert(`Imported: ${result.imported}, Failed: ${result.failed}`);
      if (result.errors.length > 0) {
        console.error("Import errors:", result.errors);
      }
      setShowImport(false);
      setImportJson("");
      loadAssets();
    } catch (error) {
      console.error("Import failed:", error);
      alert("Invalid JSON or import failed");
    }
  };

  const getCriticalityColor = (criticality: Criticality) => {
    switch (criticality) {
      case "critical": return "bg-red-100 text-red-800";
      case "high": return "bg-orange-100 text-orange-800";
      case "medium": return "bg-yellow-100 text-yellow-800";
      case "low": return "bg-green-100 text-green-800";
      default: return "bg-gray-100 text-gray-800";
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Assets Management</h1>
        <div className="space-x-2">
          <button
            onClick={() => setShowForm(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            + Add Asset
          </button>
          <button
            onClick={() => setShowImport(true)}
            className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
          >
            Import JSON
          </button>
        </div>
      </div>

      <form onSubmit={handleSearch} className="mb-6 flex gap-2">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by hostname, IP, owner, business..."
          className="flex-1 px-4 py-2 border rounded"
        />
        <button
          type="submit"
          className="px-6 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
        >
          Search
        </button>
      </form>

      {loading ? (
        <div className="text-center py-8">Loading...</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full bg-white border">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left border">Hostname</th>
                <th className="px-4 py-2 text-left border">IP</th>
                <th className="px-4 py-2 text-left border">Owner</th>
                <th className="px-4 py-2 text-left border">Business</th>
                <th className="px-4 py-2 text-left border">Criticality</th>
                <th className="px-4 py-2 text-left border">Actions</th>
              </tr>
            </thead>
            <tbody>
              {assets.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                    No assets found
                  </td>
                </tr>
              ) : (
                assets.map((asset) => (
                  <tr key={asset.id} className="hover:bg-gray-50">
                    <td className="px-4 py-2 border">{asset.hostname || "-"}</td>
                    <td className="px-4 py-2 border">{asset.ip || "-"}</td>
                    <td className="px-4 py-2 border">{asset.owner || "-"}</td>
                    <td className="px-4 py-2 border">{asset.business || "-"}</td>
                    <td className="px-4 py-2 border">
                      <span className={`px-2 py-1 rounded text-xs ${getCriticalityColor(asset.criticality)}`}>
                        {asset.criticality}
                      </span>
                    </td>
                    <td className="px-4 py-2 border">
                      <button
                        onClick={() => handleEdit(asset)}
                        className="text-blue-600 hover:text-blue-800 mr-2"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDelete(asset.id)}
                        className="text-red-600 hover:text-red-800"
                      >
                        Delete
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
            <h2 className="text-xl font-bold mb-4">Import Assets (JSON)</h2>
            <textarea
              value={importJson}
              onChange={(e) => setImportJson(e.target.value)}
              placeholder='[{"hostname": "web-prod-01", "ip": "10.0.1.10", "criticality": "high"}]'
              className="w-full h-64 px-3 py-2 border rounded font-mono text-sm"
            />
            <div className="mt-4 flex justify-end space-x-2">
              <button
                onClick={() => setShowImport(false)}
                className="px-4 py-2 border rounded hover:bg-gray-100"
              >
                Cancel
              </button>
              <button
                onClick={handleImport}
                className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
              >
                Import
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
          tags: formData.tags.split(",").map(t => t.trim()).filter(Boolean),
        });
      } else {
        await api.createAsset({
          ...formData,
          tags: formData.tags.split(",").map(t => t.trim()).filter(Boolean),
        });
      }
      onSave();
    } catch (error: unknown) {
      const err = error as { status?: number; message: string };
      alert(err.message || "Failed to save asset");
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
      <div className="bg-white p-6 rounded-lg max-w-md w-full mx-4">
        <h2 className="text-xl font-bold mb-4">
          {asset ? "Edit Asset" : "Add Asset"}
        </h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Hostname</label>
            <input
              type="text"
              value={formData.hostname}
              onChange={(e) => setFormData({ ...formData, hostname: e.target.value })}
              className="w-full px-3 py-2 border rounded"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">IP Address</label>
            <input
              type="text"
              value={formData.ip}
              onChange={(e) => setFormData({ ...formData, ip: e.target.value })}
              className="w-full px-3 py-2 border rounded"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Owner</label>
            <input
              type="text"
              value={formData.owner}
              onChange={(e) => setFormData({ ...formData, owner: e.target.value })}
              className="w-full px-3 py-2 border rounded"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Business Unit</label>
            <input
              type="text"
              value={formData.business}
              onChange={(e) => setFormData({ ...formData, business: e.target.value })}
              className="w-full px-3 py-2 border rounded"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Criticality</label>
            <select
              value={formData.criticality}
              onChange={(e) => setFormData({ ...formData, criticality: e.target.value as Criticality })}
              className="w-full px-3 py-2 border rounded"
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Tags (comma-separated)</label>
            <input
              type="text"
              value={formData.tags}
              onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
              className="w-full px-3 py-2 border rounded"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Notes</label>
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
            <label htmlFor="isActive" className="text-sm">Active</label>
          </div>
          <div className="flex justify-end space-x-2 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border rounded hover:bg-gray-100"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Save
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
