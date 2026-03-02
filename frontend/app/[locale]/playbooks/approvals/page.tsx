"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useTranslations, useLocale } from 'next-intl';
import Navigation from "@/components/Navigation";
import { SkeletonTable } from "@/components/common/LoadingState";
import { loadAuthState } from "@/lib/auth";
import { useKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts';
import { Search, RefreshCw, CheckCircle, XCircle, Clock, AlertCircle, ChevronLeft, ChevronRight, Play } from "lucide-react";

interface Approval {
  id: string;
  run_id: string;
  node_id: string;
  status: 'pending' | 'approved' | 'rejected' | 'expired';
  title: string;
  message: string | null;
  comments: string | null;
  requested_by: string | null;
  approved_by: string | null;
  rejected_by: string | null;
  created_at: string;
  decided_at: string | null;
  expires_at: string | null;
}

interface PaginationState {
  currentPage: number;
  pageSize: number;
  total: number;
}

export default function PlaybookApprovalsPage() {
  const router = useRouter();
  const locale = useLocale();
  const t = useTranslations('playbooks');
  const tCommon = useTranslations('common');
  
  const [mounted, setMounted] = useState(false);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  
  const [pagination, setPagination] = useState<PaginationState>({
    currentPage: 1,
    pageSize: 10,
    total: 0
  });

  const loadApprovals = async (page: number = 1) => {
    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem('access_token');
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pagination.pageSize.toString(),
      });
      if (statusFilter) {
        params.append('status', statusFilter);
      }
      
      const response = await fetch(`/api/approvals?${params.toString()}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        const data = await response.json();
        setApprovals(data.items || []);
        setPagination({
          currentPage: page,
          pageSize: pagination.pageSize,
          total: data.total || 0
        });
      } else if (response.status === 401) {
        router.push(`/${locale}/login`);
        return;
      } else {
        setError(`Failed to load approvals: ${response.statusText}`);
      }
    } catch (e) {
      console.error('Failed to load approvals:', e);
      setError((e as Error)?.message ?? "Error loading approvals");
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadApprovals(pagination.currentPage);
    setRefreshing(false);
  };

  const handlePageChange = (newPage: number) => {
    loadApprovals(newPage);
  };

  const handleApprove = async (approvalId: string) => {
    setActionLoading(approvalId);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`/api/approvals/${approvalId}/approve`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ comments: '' })
      });

      if (response.ok) {
        await loadApprovals(pagination.currentPage);
      } else {
        const data = await response.json();
        setError(data.detail || 'Failed to approve');
      }
    } catch (e) {
      setError((e as Error)?.message ?? "Error approving");
    } finally {
      setActionLoading(null);
    }
  };

  const handleReject = async (approvalId: string) => {
    setActionLoading(approvalId);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`/api/approvals/${approvalId}/reject`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ comments: '' })
      });

      if (response.ok) {
        await loadApprovals(pagination.currentPage);
      } else {
        const data = await response.json();
        setError(data.detail || 'Failed to reject');
      }
    } catch (e) {
      setError((e as Error)?.message ?? "Error rejecting");
    } finally {
      setActionLoading(null);
    }
  };

  useEffect(() => {
    setMounted(true);
    const authState = loadAuthState();
    if (!authState?.isAuthenticated) {
      router.push(`/${locale}/login`);
      return;
    }
    loadApprovals(1);
  }, [router, locale, statusFilter]);

  // Keyboard shortcuts
  useKeyboardShortcuts({
    'r': () => {
      setRefreshing(true);
      loadApprovals(pagination.currentPage).finally(() => setRefreshing(false));
    },
    '/': () => {
      document.querySelector<HTMLInputElement>('input[type="text"]')?.focus();
    },
  }, { enabled: mounted && !loading });

  if (!mounted) return null;

  const totalPages = Math.ceil(pagination.total / pagination.pageSize);

  const filteredApprovals = approvals.filter(approval => {
    if (!searchQuery) return true;
    const search = searchQuery.toLowerCase();
    return (
      approval.title.toLowerCase().includes(search) ||
      approval.run_id.toLowerCase().includes(search) ||
      (approval.message?.toLowerCase().includes(search) ?? false)
    );
  });

  const STATUS_COLORS: Record<string, string> = {
    pending: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
    approved: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    rejected: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
    expired: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-400',
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Navigation title={t('approvals.title') || 'Approvals'} subtitle={t('approvals.subtitle') || 'Manage playbook approval requests'} />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 mb-6 shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">{t('approvals.title') || 'Approval Requests'}</h2>
              <p className="text-gray-500 dark:text-gray-400 mt-1">{t('approvals.subtitle') || 'Review and manage playbook approval requests'}</p>
            </div>
          </div>

          {/* Filters */}
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder={t('approvals.searchPlaceholder') || "Search approvals..."}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <select 
              value={statusFilter} 
              onChange={(e) => setStatusFilter(e.target.value)} 
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-blue-500"
            >
              <option value="">{t('allStatuses') || 'All Statuses'}</option>
              <option value="pending">{t('statuses.pending') || 'Pending'}</option>
              <option value="approved">{t('statuses.approved') || 'Approved'}</option>
              <option value="rejected">{t('statuses.rejected') || 'Rejected'}</option>
              <option value="expired">{t('statuses.expired') || 'Expired'}</option>
            </select>
            <button 
              onClick={handleRefresh}
              disabled={refreshing}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2 transition-colors shadow-sm"
            >
              <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
              {refreshing ? tCommon('loading') : tCommon('refresh')}
            </button>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
            <span className="text-red-700 dark:text-red-300">{error}</span>
          </div>
        )}

        {/* Content */}
        {loading ? (
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4"><SkeletonTable rows={5} columns={5} /></div>
        ) : filteredApprovals.length === 0 ? (
          <div className="text-center py-16 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center">
              <CheckCircle className="w-8 h-8 text-gray-400" />
            </div>
            <p className="text-gray-500 dark:text-gray-400 text-lg mb-2">{t('approvals.noApprovals') || 'No approval requests found'}</p>
            <p className="text-gray-400 dark:text-gray-500 text-sm">{t('approvals.noApprovalsDesc') || 'Pending approvals will appear here'}</p>
          </div>
        ) : (
          <div className="bg-white dark:bg-gray-800 rounded-lg overflow-hidden shadow-sm border border-gray-200 dark:border-gray-700">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 dark:bg-gray-700 border-b border-gray-200 dark:border-gray-600">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">{t('approvals.title') || 'Title'}</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">{t('approvals.runId') || 'Run ID'}</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">{t('approvals.status') || 'Status'}</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">{t('approvals.requestedBy') || 'Requested By'}</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">{t('approvals.created') || 'Created'}</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">{t('approvals.actions') || 'Actions'}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                  {filteredApprovals.map((approval) => (
                    <tr key={approval.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                      <td className="px-6 py-4">
                        <div className="font-medium text-gray-900 dark:text-white">{approval.title}</div>
                        {approval.message && (
                          <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">{approval.message}</div>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        <a 
                          href={`/${locale}/playbooks/${approval.run_id}`}
                          className="text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 font-mono text-sm"
                        >
                          {approval.run_id.slice(0, 8)}...
                        </a>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${STATUS_COLORS[approval.status]}`}>
                          {approval.status === 'pending' && <Clock className="w-3 h-3" />}
                          {approval.status === 'approved' && <CheckCircle className="w-3 h-3" />}
                          {approval.status === 'rejected' && <XCircle className="w-3 h-3" />}
                          {approval.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-300">
                        {approval.requested_by || '-'}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-300">
                        {new Date(approval.created_at).toLocaleDateString()}
                        <div className="text-xs text-gray-400">{new Date(approval.created_at).toLocaleTimeString()}</div>
                      </td>
                      <td className="px-6 py-4 text-right">
                        {approval.status === 'pending' ? (
                          <div className="flex items-center justify-end gap-2">
                            <button 
                              className="inline-flex items-center gap-1 px-3 py-1.5 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors text-sm"
                              onClick={() => handleApprove(approval.id)}
                              disabled={actionLoading === approval.id}
                            >
                              <CheckCircle className="w-4 h-4" />
                              {t('approvals.approve') || 'Approve'}
                            </button>
                            <button 
                              className="inline-flex items-center gap-1 px-3 py-1.5 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors text-sm"
                              onClick={() => handleReject(approval.id)}
                              disabled={actionLoading === approval.id}
                            >
                              <XCircle className="w-4 h-4" />
                              {t('approvals.reject') || 'Reject'}
                            </button>
                          </div>
                        ) : (
                          <div className="text-sm text-gray-500 dark:text-gray-400">
                            {approval.approved_by && `Approved by ${approval.approved_by}`}
                            {approval.rejected_by && `Rejected by ${approval.rejected_by}`}
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              
              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 dark:border-gray-700">
                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    Showing {((pagination.currentPage - 1) * pagination.pageSize) + 1} to {Math.min(pagination.currentPage * pagination.pageSize, pagination.total)} of {pagination.total} results
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handlePageChange(pagination.currentPage - 1)}
                      disabled={pagination.currentPage === 1}
                      className="p-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </button>
                    <span className="text-sm text-gray-600 dark:text-gray-400">
                      Page {pagination.currentPage} of {totalPages}
                    </span>
                    <button
                      onClick={() => handlePageChange(pagination.currentPage + 1)}
                      disabled={pagination.currentPage === totalPages}
                      className="p-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}