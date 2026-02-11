"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { loadAuthState, logout } from "@/lib/auth";
import Navigation from "@/components/Navigation";
import { Check, X, RefreshCw, Clock } from "lucide-react";

export default function PlaybookApprovalsPage() {
  const router = useRouter();
  const [approvals, setApprovals] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>("pending");
  const [mounted, setMounted] = useState(false);
  const [processingId, setProcessingId] = useState<string | null>(null);

  useEffect(() => {
    setMounted(true);

    // Check authentication
    const authState = loadAuthState();
    if (!authState?.isAuthenticated) {
      router.push("/login");
      return;
    }

    loadApprovals();

    // Auto-refresh every 10 seconds for pending approvals
    const interval = setInterval(() => {
      if (filterStatus === "pending") {
        loadApprovals();
      }
    }, 10000);

    return () => clearInterval(interval);
  }, [router, filterStatus]);

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  if (!mounted) return null;

  async function loadApprovals() {
    setLoading(true);
    setError(null);
    try {
      // Note: Approvals endpoint not yet implemented in backend
      const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const token = localStorage.getItem("access_token");

      const response = await fetch(`${API_BASE}/api/playbook/approvals?status=${filterStatus}`, {
        headers: {
          "Authorization": `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        if (response.status === 404) {
          // Endpoint not yet implemented
          setApprovals([]);
          return;
        }
        throw new Error("Failed to load approvals");
      }

      const data = await response.json();
      setApprovals(data.items || []);
    } catch (e: unknown) {
      // If endpoint not implemented, show empty state with info
      setApprovals([]);
    } finally {
      setLoading(false);
    }
  }

  async function handleApprove(approvalId: string, comment: string) {
    setProcessingId(approvalId);
    try {
      const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const token = localStorage.getItem("access_token");

      await fetch(`${API_BASE}/api/playbook/approvals/${approvalId}/approve`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ comment }),
      });

      await loadApprovals();
    } catch (e: unknown) {
      setError((e as Error)?.message ?? "Failed to approve");
    } finally {
      setProcessingId(null);
    }
  }

  async function handleReject(approvalId: string, comment: string) {
    setProcessingId(approvalId);
    try {
      const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const token = localStorage.getItem("access_token");

      await fetch(`${API_BASE}/api/playbook/approvals/${approvalId}/reject`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ comment }),
      });

      await loadApprovals();
    } catch (e: unknown) {
      setError((e as Error)?.message ?? "Failed to reject");
    } finally {
      setProcessingId(null);
    }
  }

  const statusConfig = {
    pending: {
      bgColor: "bg-yellow-50 dark:bg-yellow-900/20",
      borderColor: "border-yellow-200 dark:border-yellow-800",
      textColor: "text-yellow-700 dark:text-yellow-300",
      icon: <Clock className="w-4 h-4" />,
    },
    approved: {
      bgColor: "bg-green-50 dark:bg-green-900/20",
      borderColor: "border-green-200 dark:border-green-800",
      textColor: "text-green-700 dark:text-green-300",
      icon: <Check className="w-4 h-4" />,
    },
    rejected: {
      bgColor: "bg-red-50 dark:bg-red-900/20",
      borderColor: "border-red-200 dark:border-red-800",
      textColor: "text-red-700 dark:text-red-300",
      icon: <X className="w-4 h-4" />,
    },
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Navigation title="Playbook Approvals" subtitle="Review and approve playbook execution requests" />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Filters */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 mb-6">
          <div className="flex gap-4 items-center">
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Status:</span>
            <div className="flex gap-2">
              {["pending", "approved", "rejected"].map((status) => (
                <button
                  key={status}
                  onClick={() => setFilterStatus(status)}
                  className={`px-3 py-1 rounded-lg text-sm font-medium capitalize transition-colors ${
                    filterStatus === status
                      ? "bg-blue-600 text-white"
                      : "bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600"
                  }`}
                >
                  {status}
                </button>
              ))}
            </div>
            <button
              onClick={loadApprovals}
              className="ml-auto p-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              <RefreshCw className="w-5 h-5 text-gray-600 dark:text-gray-400" />
            </button>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 px-4 py-3 rounded-lg mb-6">
            {error}
          </div>
        )}

        {/* Content */}
        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
            <p className="mt-4 text-gray-600 dark:text-gray-400">Loading approvals...</p>
          </div>
        ) : approvals.length === 0 ? (
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-12 text-center">
            <div className="w-16 h-16 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-4">
              <Check className="w-8 h-8 text-gray-400" />
            </div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
              {filterStatus === "pending" ? "No pending approvals" : `No ${filterStatus} approvals`}
            </h3>
            <p className="text-gray-600 dark:text-gray-400 mb-4">
              {filterStatus === "pending"
                ? "All caught up! No playbook executions waiting for approval."
                : `No approvals with status "${filterStatus}" found.`}
            </p>
            {filterStatus !== "pending" && (
              <button
                onClick={() => setFilterStatus("pending")}
                className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                View Pending Approvals
              </button>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            {approvals.map((approval) => {
              const config = statusConfig[approval.status as keyof typeof statusConfig] || statusConfig.pending;

              return (
                <div
                  key={approval.id}
                  className={`bg-white dark:bg-gray-800 rounded-lg border-2 p-6 ${config.borderColor}`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        {config.icon}
                        <h3 className="font-semibold text-gray-900 dark:text-white">
                          {approval.title || `Approval for ${approval.node_id}`}
                        </h3>
                        <span className={`px-2 py-1 rounded text-xs font-medium capitalize ${config.bgColor} ${config.textColor}`}>
                          {approval.status}
                        </span>
                      </div>

                      {approval.message && (
                        <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">{approval.message}</p>
                      )}

                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm text-gray-600 dark:text-gray-400 mb-4">
                        <div>
                          <span className="font-medium">Run ID:</span>
                          <button
                            onClick={() => router.push(`/playbooks/runs/${approval.run_id}`)}
                            className="ml-2 font-mono text-blue-600 dark:text-blue-400 hover:underline"
                          >
                            {approval.run_id.slice(0, 8)}...
                          </button>
                        </div>
                        <div>
                          <span className="font-medium">Node:</span>
                          <span className="ml-2 font-mono text-xs">{approval.node_id}</span>
                        </div>
                        <div>
                          <span className="font-medium">Requested by:</span>
                          <span className="ml-2">{approval.requested_by || "System"}</span>
                        </div>
                        <div>
                          <span className="font-medium">Requested:</span>
                          <span className="ml-2">{new Date(approval.created_at).toLocaleString()}</span>
                        </div>
                        {approval.expires_at && (
                          <div>
                            <span className="font-medium">Expires:</span>
                            <span className="ml-2">{new Date(approval.expires_at).toLocaleString()}</span>
                          </div>
                        )}
                      </div>

                      {approval.comments && (
                        <div className="p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Comments: </span>
                          <span className="text-sm text-gray-600 dark:text-gray-400">{approval.comments}</span>
                        </div>
                      )}

                      {approval.status !== "pending" && (
                        <div className="mt-3 p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                          <span className="text-sm text-gray-600 dark:text-gray-400">
                            {approval.status === "approved" && (
                            <>Approved by {approval.approved_by} at {new Date(approval.decided_at).toLocaleString()}</>
                            )}
                            {approval.status === "rejected" && (
                            <>Rejected by {approval.rejected_by} at {new Date(approval.decided_at).toLocaleString()}</>
                            )}
                          </span>
                        </div>
                      )}
                    </div>

                    {approval.status === "pending" && (
                      <div className="flex gap-2 ml-4">
                        <button
                          onClick={() => {
                            const comment = prompt("Enter approval comment (optional):");
                            if (comment !== null) handleApprove(approval.id, comment);
                          }}
                          disabled={processingId === approval.id}
                          className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
                        >
                          <Check className="w-4 h-4" />
                          Approve
                        </button>
                        <button
                          onClick={() => {
                            const comment = prompt("Enter rejection reason (required):");
                            if (comment) handleReject(approval.id, comment);
                          }}
                          disabled={processingId === approval.id}
                          className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50"
                        >
                          <X className="w-4 h-4" />
                          Reject
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}
