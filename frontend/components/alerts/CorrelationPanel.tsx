'use client';

import { useState, useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { AlertTriangle, Link2, Clock, User, Server } from 'lucide-react';

interface CorrelatedEvent {
  id: string;
  title: string;
  description: string;
  severity: string;
  attack_type: string;
  confidence_score: number;
  raw_event_count: number;
  common_entities: {
    ip_addresses: string[];
    usernames: string[];
    hostnames: string[];
  };
  first_seen: string;
  last_seen: string;
  status: string;
  assigned_to?: string;
  risk_score: number;
}

interface CorrelationPanelProps {
  alertId: string;
}

export function CorrelationPanel({ alertId }: CorrelationPanelProps) {
  const t = useTranslations('correlation');
  const [incidents, setIncidents] = useState<CorrelatedEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedIncident, setSelectedIncident] = useState<CorrelatedEvent | null>(null);

  useEffect(() => {
    fetchRelatedIncidents();
  }, [alertId]);

  const fetchRelatedIncidents = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/correlation/incidents?limit=10`);
      const data = await response.json();
      setIncidents(data);
    } catch (error) {
      console.error('Failed to fetch correlated incidents:', error);
    } finally {
      setLoading(false);
    }
  };

  const getSeverityColor = (severity: string) => {
    const colors = {
      critical: 'text-red-600 bg-red-50 border-red-200',
      high: 'text-orange-600 bg-orange-50 border-orange-200',
      medium: 'text-yellow-600 bg-yellow-50 border-yellow-200',
      low: 'text-blue-600 bg-blue-50 border-blue-200',
      info: 'text-gray-600 bg-gray-50 border-gray-200',
    };
    return colors[severity as keyof typeof colors] || colors.low;
  };

  const getStatusBadge = (status: string) => {
    const badges = {
      open: 'bg-blue-100 text-blue-700',
      investigating: 'bg-yellow-100 text-yellow-700',
      resolved: 'bg-green-100 text-green-700',
      false_positive: 'bg-gray-100 text-gray-700',
      closed: 'bg-gray-200 text-gray-800',
    };
    return badges[status as keyof typeof badges] || badges.open;
  };

  if (loading) {
    return (
      <div className="p-4 border rounded-lg bg-gray-50 animate-pulse">
        <div className="h-4 bg-gray-200 rounded w-1/3 mb-2"></div>
        <div className="h-3 bg-gray-200 rounded w-1/2"></div>
      </div>
    );
  }

  if (incidents.length === 0) {
    return (
      <div className="p-4 border rounded-lg bg-gray-50">
        <div className="flex items-center gap-2 text-gray-500">
          <Link2 className="w-4 h-4" />
          <span className="text-sm">{t('noIncidents')}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-900 flex items-center gap-2">
          <Link2 className="w-4 h-4" />
          {t('relatedIncidents')} ({incidents.length})
        </h3>
        <button
          onClick={fetchRelatedIncidents}
          className="text-xs text-blue-600 hover:text-blue-700"
        >
          Refresh
        </button>
      </div>

      {incidents.map((incident) => (
        <div
          key={incident.id}
          className={`p-3 border rounded-lg cursor-pointer transition-colors hover:bg-gray-50 ${
            selectedIncident?.id === incident.id ? 'bg-blue-50 border-blue-300' : 'bg-white'
          }`}
          onClick={() => setSelectedIncident(incident)}
        >
          {/* Header */}
          <div className="flex items-start justify-between mb-2">
            <div className="flex-1">
              <h4 className="text-sm font-medium text-gray-900">{incident.title}</h4>
              {incident.attack_type && (
                <span className="text-xs text-gray-500">{incident.attack_type}</span>
              )}
            </div>
            <div className="flex items-center gap-2">
              <span
                className={`text-xs px-2 py-1 rounded ${getSeverityColor(incident.severity)}`}
              >
                {incident.severity}
              </span>
              <span
                className={`text-xs px-2 py-1 rounded ${getStatusBadge(incident.status)}`}
              >
                {incident.status}
              </span>
            </div>
          </div>

          {/* Stats */}
          <div className="flex items-center gap-4 text-xs text-gray-600 mb-2">
            <div className="flex items-center gap-1">
              <AlertTriangle className="w-3 h-3" />
              <span>{incident.raw_event_count} events</span>
            </div>
            <div className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              <span>
                {new Date(incident.first_seen).toLocaleTimeString()} -{' '}
                {new Date(incident.last_seen).toLocaleTimeString()}
              </span>
            </div>
            <div className="flex items-center gap-1">
              <span className="font-medium">Confidence:</span>
              <span>{(incident.confidence_score * 100).toFixed(0)}%</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="font-medium">Risk:</span>
              <span>{incident.risk_score.toFixed(0)}/100</span>
            </div>
          </div>

          {/* Common Entities */}
          {(incident.common_entities.ip_addresses?.length > 0 ||
            incident.common_entities.usernames?.length > 0 ||
            incident.common_entities.hostnames?.length > 0) && (
            <div className="flex flex-wrap gap-2 text-xs">
              {incident.common_entities.ip_addresses?.length > 0 && (
                <div className="flex items-center gap-1 bg-gray-100 px-2 py-1 rounded">
                  <Server className="w-3 h-3 text-gray-500" />
                  <span className="text-gray-700">
                    {incident.common_entities.ip_addresses.slice(0, 3).join(', ')}
                    {incident.common_entities.ip_addresses.length > 3 && '...'}
                  </span>
                </div>
              )}
              {incident.common_entities.usernames?.length > 0 && (
                <div className="flex items-center gap-1 bg-gray-100 px-2 py-1 rounded">
                  <User className="w-3 h-3 text-gray-500" />
                  <span className="text-gray-700">
                    {incident.common_entities.usernames.slice(0, 2).join(', ')}
                    {incident.common_entities.usernames.length > 2 && '...'}
                  </span>
                </div>
              )}
            </div>
          )}
        </div>
      ))}

      {/* Selected Incident Detail */}
      {selectedIncident && (
        <IncidentDetailModal
          incident={selectedIncident}
          onClose={() => setSelectedIncident(null)}
          onUpdate={fetchRelatedIncidents}
        />
      )}
    </div>
  );
}

interface IncidentDetailModalProps {
  incident: CorrelatedEvent;
  onClose: () => void;
  onUpdate: () => void;
}

function IncidentDetailModal({ incident, onClose, onUpdate }: IncidentDetailModalProps) {
  const t = useTranslations('triggers');
  const [status, setStatus] = useState(incident.status);
  const [assignedTo, setAssignedTo] = useState(incident.assigned_to || '');
  const [updating, setUpdating] = useState(false);

  const handleUpdate = async () => {
    try {
      setUpdating(true);
      const params = new URLSearchParams({ status });
      if (assignedTo) params.append('assigned_to', assignedTo);

      const response = await fetch(
        `/api/correlation/incidents/${incident.id}/status?${params}`,
        { method: 'PUT' }
      );

      if (response.ok) {
        onUpdate();
        onClose();
      }
    } catch (error) {
      console.error('Failed to update incident:', error);
    } finally {
      setUpdating(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto m-4">
        {/* Header */}
        <div className="p-4 border-b flex items-center justify-between">
          <h2 className="text-lg font-semibold">Incident Details</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4">
          {/* Title & Severity */}
          <div>
            <h3 className="text-xl font-medium mb-2">{incident.title}</h3>
            <p className="text-sm text-gray-600">{incident.description}</p>
          </div>

          {/* Metadata */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="font-medium">Attack Type:</span>
              <span className="ml-2">{incident.attack_type || 'N/A'}</span>
            </div>
            <div>
              <span className="font-medium">Risk Score:</span>
              <span className="ml-2">{incident.risk_score.toFixed(0)}/100</span>
            </div>
            <div>
              <span className="font-medium">First Seen:</span>
              <span className="ml-2">{new Date(incident.first_seen).toLocaleString()}</span>
            </div>
            <div>
              <span className="font-medium">Last Seen:</span>
              <span className="ml-2">{new Date(incident.last_seen).toLocaleString()}</span>
            </div>
          </div>

          {/* Common Entities */}
          <div>
            <h4 className="font-medium text-sm mb-2">Common Entities</h4>
            <div className="space-y-2 text-sm">
              {incident.common_entities.ip_addresses?.length > 0 && (
                <div>
                  <span className="font-medium">IP Addresses:</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {incident.common_entities.ip_addresses.map((ip, i) => (
                      <span
                        key={i}
                        className="bg-gray-100 px-2 py-1 rounded text-xs"
                      >
                        {ip}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {incident.common_entities.usernames?.length > 0 && (
                <div>
                  <span className="font-medium">Usernames:</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {incident.common_entities.usernames.map((user, i) => (
                      <span
                        key={i}
                        className="bg-gray-100 px-2 py-1 rounded text-xs"
                      >
                        {user}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Actions */}
          <div className="pt-4 border-t space-y-3">
            <div>
              <label className="block text-sm font-medium mb-1">Status</label>
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value)}
                className="w-full border rounded px-3 py-2 text-sm"
              >
                <option value="open">Open</option>
                <option value="investigating">Investigating</option>
                <option value="resolved">Resolved</option>
                <option value="false_positive">False Positive</option>
                <option value="closed">Closed</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Assign To</label>
              <input
                type="text"
                value={assignedTo}
                onChange={(e) => setAssignedTo(e.target.value)}
                placeholder="Enter analyst name"
                className="w-full border rounded px-3 py-2 text-sm"
              />
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleUpdate}
                disabled={updating}
                className="flex-1 bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
              >
                {updating ? t('updatingIncident') : t('updateIncident')}
              </button>
              <button
                onClick={onClose}
                className="flex-1 border px-4 py-2 rounded hover:bg-gray-50"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
