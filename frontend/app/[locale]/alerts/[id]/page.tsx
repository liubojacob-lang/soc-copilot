'use client';

/**
 * Alert Details Page
 * 告警详情页面
 */

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useLocale } from 'next-intl';
import { ArrowLeft, RefreshCw, AlertTriangle } from 'lucide-react';
import { loadAuthState, authFetchJSON } from '@/lib/auth';
import { useToast } from '@/components/Toast';

// Components
import { AlertStatusBadge, SeverityBadge } from '@/components/AlertStatusBadge';
import { ThreatIntelCard } from '@/components/alerts/ThreatIntelCard';
import { MITREMapping } from '@/components/alerts/MITREMapping';
import { CorrelatedAlerts, SimpleCorrelationList } from '@/components/alerts/CorrelatedAlerts';
import { AlertActions } from '@/components/alerts/AlertActions';
import { TimelineView, RecentTimeline } from '@/components/alerts/TimelineView';
import { AlertNotes } from '@/components/alerts/AlertNotes';
import { useAlertWebSocket } from '@/components/AlertWebSocket';

interface AlertDetails {
  id: string;
  title: string;
  description?: string;
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  status: 'new' | 'investigating' | 'resolved' | 'false_positive' | 'escalated';
  source: string;
  event_type: string;
  timestamp: string;
  threat_score?: number;
  assigned_to?: string;
  assigned_at?: string;
  resolved_at?: string;
  resolved_by?: string;
  resolution_note?: string;
  source_ip?: string;
  destination_ip?: string;
  agent_name?: string;
  rule_id?: string;
  rule_mitre?: string[];
  full_log?: string;
  raw_data?: any;
  // Enrichment data
  enriched_at?: string;
  iocs?: Array<{
    type: string;
    value: string;
    reputation: string;
    confidence: number;
  }>;
  mitre_tactics?: Array<{
    tactic: string;
    techniques: string[];
  }>;
  // Lifecycle data
  timeline?: Array<{
    id: string;
    timestamp: string;
    event_type: string;
    description: string;
    user?: string;
  }>;
  notes?: Array<{
    id: string;
    user_id: string;
    username: string;
    content: string;
    created_at: string;
  }>;
  // Correlated alerts
  correlated_alerts?: any[];
}

interface SecurityAlertListResponse {
  total: number;
  alerts: any[];
  page: number;
  page_size: number;
}

interface CorrelationGroupData {
  id: string;
  name: string;
  description: string;
  correlation_type: 'temporal' | 'attack_chain' | 'threat_intel' | 'asset_based';
  confidence: number;
  alerts: Array<{
    id: string;
    title: string;
    description?: string;
    severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
    status: 'new' | 'investigating' | 'resolved' | 'false_positive';
    source: string;
    timestamp: string;
    event_type: string;
  }>;
  created_at: string;
  common_indicators: Array<{
    type: 'ip' | 'domain' | 'hash' | 'agent' | 'user';
    value: string;
    count: number;
  }>;
  mitre_tactics?: string[];
}

function normalizeStatus(status?: string): AlertDetails["status"] {
  if (!status) return "new";
  if (status === "open") return "new";
  if (status === "closed") return "resolved";
  if (status === "investigating") return "investigating";
  if (status === "resolved") return "resolved";
  if (status === "false_positive") return "false_positive";
  if (status === "escalated") return "escalated";
  return "new";
}

function normalizeCorrelationStatus(status?: string): 'new' | 'investigating' | 'resolved' | 'false_positive' {
  const normalized = normalizeStatus(status);
  if (normalized === 'escalated') return 'investigating';
  return normalized;
}

export default function AlertDetailsPage() {
  const locale = useLocale();
  const params = useParams();
  const router = useRouter();
  const { showToast } = useToast();
  const alertId = params.id as string;

  const [alert, setAlert] = useState<AlertDetails | null>(null);
  const [correlationGroups, setCorrelationGroups] = useState<CorrelationGroupData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'timeline' | 'notes' | 'correlations'>('overview');

  // 获取告警详情
  const fetchCorrelatedAlerts = async (currentAlert: AlertDetails) => {
    const queries: Array<{ key: string; url: string; type: CorrelationGroupData['correlation_type']; indicator?: { type: 'ip' | 'agent'; value: string } }> = [];
    if (currentAlert.source) {
      queries.push({
        key: `source:${currentAlert.source}`,
        url: `/api/v1/security-alerts/?source=${encodeURIComponent(currentAlert.source)}&page=1&page_size=20`,
        type: 'attack_chain',
      });
    }
    if (currentAlert.source_ip) {
      queries.push({
        key: `ip:${currentAlert.source_ip}`,
        url: `/api/v1/security-alerts/?source_ip=${encodeURIComponent(currentAlert.source_ip)}&page=1&page_size=20`,
        type: 'threat_intel',
        indicator: { type: 'ip', value: currentAlert.source_ip },
      });
    }
    if (currentAlert.agent_name) {
      queries.push({
        key: `agent:${currentAlert.agent_name}`,
        url: `/api/v1/security-alerts/?agent_name=${encodeURIComponent(currentAlert.agent_name)}&page=1&page_size=20`,
        type: 'asset_based',
        indicator: { type: 'agent', value: currentAlert.agent_name },
      });
    }

    if (queries.length === 0) {
      setCorrelationGroups([]);
      return;
    }

    const responses = await Promise.all(
      queries.map(async (q) => {
        try {
          const data = await authFetchJSON<SecurityAlertListResponse>(q.url);
          return { query: q, alerts: data.alerts || [] };
        } catch {
          return { query: q, alerts: [] };
        }
      })
    );

    const groups: CorrelationGroupData[] = responses
      .map(({ query, alerts }) => {
        const related = alerts
          .filter((a) => String(a.id) !== String(currentAlert.id))
          .map((a) => ({
            id: String(a.id),
            title: String(a.title || `Alert #${a.id}`),
            description: a.description ? String(a.description) : undefined,
            severity: (String(a.severity || 'info').toLowerCase() as CorrelationGroupData['alerts'][number]['severity']),
            status: normalizeCorrelationStatus(a.status),
            source: String(a.source || 'unknown'),
            timestamp: String(a.event_timestamp || a.created_at || new Date().toISOString()),
            event_type: String(a.event_type || 'unknown'),
          }));

        if (related.length === 0) return null;
        const uniqueRelated = Array.from(new Map(related.map((a) => [a.id, a])).values());

        return {
          id: query.key,
          name: query.type === 'attack_chain' ? 'Same Source Correlation' : query.type === 'threat_intel' ? 'Same Source IP Correlation' : 'Same Agent Correlation',
          description: `Found ${uniqueRelated.length} related alerts by ${query.key}`,
          correlation_type: query.type,
          confidence: Math.min(95, 50 + uniqueRelated.length * 8),
          alerts: uniqueRelated,
          created_at: new Date().toISOString(),
          common_indicators: query.indicator
            ? [{ type: query.indicator.type, value: query.indicator.value, count: uniqueRelated.length + 1 }]
            : [],
        } as CorrelationGroupData;
      })
      .filter(Boolean) as CorrelationGroupData[];

    setCorrelationGroups(groups);
  };

  const fetchAlertDetails = async () => {
    try {
      setLoading(true);
      setError(null);
      const [alertData, lifecycleData] = await Promise.all([
        authFetchJSON<any>(`/api/v1/security-alerts/${alertId}`),
        authFetchJSON<any>(`/api/v1/alerts/${alertId}/lifecycle`).catch(() => null),
      ]);

      const normalized: AlertDetails = {
        id: String(alertData.id),
        title: alertData.title || `Alert #${alertData.id}`,
        description: alertData.description,
        severity: alertData.severity || 'info',
        status: normalizeStatus(lifecycleData?.status || alertData.status),
        source: alertData.source || 'unknown',
        event_type: alertData.event_type || 'unknown',
        timestamp: alertData.event_timestamp || alertData.created_at,
        source_ip: alertData.source_ip,
        destination_ip: alertData.destination_ip,
        agent_name: alertData.agent_name,
        rule_id: alertData.rule_id,
        rule_mitre: alertData.rule_mitre ? String(alertData.rule_mitre).split(',') : [],
        full_log: alertData.full_log,
        assigned_to: lifecycleData?.assigned_to?.username || alertData.assigned_to,
        notes: lifecycleData?.notes || [],
        timeline: lifecycleData?.timeline || [],
        correlated_alerts: [],
      };

      setAlert(normalized);
      await fetchCorrelatedAlerts(normalized);
    } catch (err: any) {
      setError(err.message || 'Failed to load alert');
    } finally {
      setLoading(false);
    }
  };

  // 刷新威胁情报
  const refreshThreatIntel = async () => {
    try {
      const token = localStorage.getItem("access_token");
      const response = await fetch(`/api/v1/alert-enrichment/process/${alertId}`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      });
      if (!response.ok) throw new Error('Failed to refresh');

      await fetchAlertDetails();
      showToast('Threat intelligence refreshed', 'success');
    } catch (error) {
      console.error('Failed to refresh threat intel:', error);
      showToast('Failed to refresh threat intelligence', 'error');
    }
  };

  // 处理告警操作
  const handleAction = async (action: string, data?: any) => {
    try {
      let endpoint = '';
      let body: any = {};
      let method: 'POST' | 'PATCH' = 'POST';

      switch (action) {
        case 'resolve':
        case 'false_positive':
          endpoint = `/api/v1/alerts/${alertId}/resolve`;
          body = data;
          break;
        case 'assign':
          endpoint = `/api/v1/alerts/${alertId}/assign`;
          body = data;
          break;
        case 'escalate':
          endpoint = `/api/v1/alerts/${alertId}/escalate`;
          body = data;
          break;
        case 'reopen':
          endpoint = `/api/v1/alerts/${alertId}/status?status=new`;
          method = 'PATCH';
          break;
        default:
          return;
      }

      const token = localStorage.getItem("access_token");
      const response = await fetch(endpoint, {
        method,
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: method === 'POST' ? JSON.stringify(body) : undefined,
      });

      if (!response.ok) throw new Error('Action failed');

      await fetchAlertDetails();
      showToast(`Action "${action}" completed`, 'success');
    } catch (error) {
      console.error('Action failed:', error);
      showToast(`Action "${action}" failed`, 'error');
      throw error;
    }
  };

  // 添加备注
  const handleAddNote = async (content: string) => {
    const token = localStorage.getItem("access_token");
    const response = await fetch(`/api/v1/alerts/${alertId}/notes`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ content }),
    });

    if (!response.ok) throw new Error('Failed to add note');
    await fetchAlertDetails();
    showToast('Note added', 'success');
  };

  const { AlertWebSocketComponent } = useAlertWebSocket({
    enabled: !!alert,
    channels: ['alerts'],
    onAlert: (incoming) => {
      if (!alert || String(incoming?.id) !== String(alert.id)) return;
      setAlert((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          status: normalizeStatus(incoming?.status || prev.status),
          severity: (incoming?.severity || prev.severity),
          title: incoming?.title || prev.title,
          description: incoming?.description ?? prev.description,
          timestamp: incoming?.event_timestamp || incoming?.created_at || prev.timestamp,
          source_ip: incoming?.source_ip ?? prev.source_ip,
          destination_ip: incoming?.destination_ip ?? prev.destination_ip,
          agent_name: incoming?.agent_name ?? prev.agent_name,
        };
      });
      showToast('Alert updated in real time', 'info');
    },
  });

  // 初始加载
  useEffect(() => {
    const authState = loadAuthState();
    if (!authState?.isAuthenticated) {
      router.push(`/${locale}/login`);
      return;
    }
    if (alertId) {
      fetchAlertDetails();
    }
  }, [alertId, router, locale]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error || !alert) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <div className="max-w-7xl mx-auto px-4 py-8">
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-8 text-center">
            <AlertTriangle className="w-16 h-16 text-red-500 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-red-900 dark:text-red-300 mb-2">
              {error || 'Alert not found'}
            </h2>
            <button
              onClick={() => router.back()}
              className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
            >
              Go Back
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <AlertWebSocketComponent />

      {/* Header */}
      <div className="bg-white dark:bg-gray-800 shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center gap-4">
            <button
              onClick={() => router.back()}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
            >
              <ArrowLeft className="w-5 h-5 text-gray-600 dark:text-gray-400" />
            </button>

            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <SeverityBadge severity={alert.severity} />
                <AlertStatusBadge status={alert.status} />
              </div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                {alert.title}
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                {alert.source} • {alert.event_type} • {new Date(alert.timestamp).toLocaleString()}
              </p>
            </div>

            <button
              onClick={fetchAlertDetails}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
              title="Refresh"
            >
              <RefreshCw className="w-5 h-5 text-gray-600 dark:text-gray-400" />
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Column (2/3) */}
          <div className="lg:col-span-2 space-y-6">
            {/* Tabs */}
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
              <div className="flex border-b border-gray-200 dark:border-gray-700">
                {[
                  { key: 'overview', label: 'Overview' },
                  { key: 'timeline', label: 'Timeline' },
                  { key: 'notes', label: 'Notes' },
                  { key: 'correlations', label: 'Correlations' },
                ].map((tab) => (
                  <button
                    key={tab.key}
                    onClick={() => setActiveTab(tab.key as any)}
                    className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                      activeTab === tab.key
                        ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                        : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              <div className="p-6">
                {activeTab === 'overview' && (
                  <div className="space-y-6">
                    {/* Description */}
                    {alert.description && (
                      <div>
                        <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">
                          Description
                        </h3>
                        <p className="text-gray-700 dark:text-gray-300">{alert.description}</p>
                      </div>
                    )}

                    {/* Technical Details */}
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-gray-500 dark:text-gray-400">Source IP:</span>
                        <span className="ml-2 font-mono text-gray-900 dark:text-white">
                          {alert.source_ip || 'N/A'}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-500 dark:text-gray-400">Destination IP:</span>
                        <span className="ml-2 font-mono text-gray-900 dark:text-white">
                          {alert.destination_ip || 'N/A'}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-500 dark:text-gray-400">Agent:</span>
                        <span className="ml-2 text-gray-900 dark:text-white">
                          {alert.agent_name || 'N/A'}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-500 dark:text-gray-400">Rule ID:</span>
                        <span className="ml-2 font-mono text-gray-900 dark:text-white">
                          {alert.rule_id || 'N/A'}
                        </span>
                      </div>
                    </div>

                    {/* Full Log */}
                    {alert.full_log && (
                      <div>
                        <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">
                          Full Log
                        </h3>
                        <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto text-xs">
                          {alert.full_log}
                        </pre>
                      </div>
                    )}
                  </div>
                )}

                {activeTab === 'timeline' && (
                  <TimelineView events={(alert.timeline || []) as any} />
                )}

                {activeTab === 'notes' && (
                  <AlertNotes
                    notes={alert.notes || []}
                    onAdd={handleAddNote}
                  />
                )}

                {activeTab === 'correlations' && (
                  <CorrelatedAlerts
                    groups={correlationGroups}
                    onAlertClick={(id) => router.push(`/${locale}/alerts/${id}`)}
                  />
                )}
              </div>
            </div>
          </div>

          {/* Sidebar Column (1/3) */}
          <div className="space-y-6">
            {/* Response Actions */}
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
              <AlertActions
                alertId={alert.id}
                currentStatus={alert.status}
                onAction={handleAction}
              />
            </div>

            {/* Threat Intelligence */}
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
              <ThreatIntelCard
                data={{
                  iocs: alert.iocs || [],
                  mitre_tactics: alert.mitre_tactics || [],
                  threat_score: alert.threat_score || 0,
                  enrichment_status: alert.enriched_at ? 'enriched' : 'pending',
                  enriched_at: alert.enriched_at,
                }}
                onRefresh={refreshThreatIntel}
              />
            </div>

            {/* MITRE ATT&CK */}
            {alert.mitre_tactics && alert.mitre_tactics.length > 0 && (
              <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
                <MITREMapping tactics={alert.mitre_tactics || []} />
              </div>
            )}

            {/* Quick Timeline */}
            {alert.timeline && alert.timeline.length > 0 && (
              <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
                <RecentTimeline events={alert.timeline} limit={5} />
              </div>
            )}

            {/* Related Alerts */}
            {correlationGroups.length > 0 && (
              <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
                <SimpleCorrelationList
                  groups={correlationGroups}
                  onAlertClick={(id) => router.push(`/${locale}/alerts/${id}`)}
                />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
