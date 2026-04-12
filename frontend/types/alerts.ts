/**
 * Wazuh Integration Type Definitions
 */

/**
 * MITRE ATT&CK tactic information
 */
export interface MITRETactic {
  id?: string;
  tactic?: string;
  technique?: string;
  techniques?: string[];
  tactics?: string[];
}

/**
 * Severity levels for alerts
 */
export type SeverityLevel = "critical" | "high" | "medium" | "low" | "info";

/**
 * Wazuh agent information
 */
export interface WazuhAgent {
  id: string;
  name: string;
  ip?: string;
  status?: string;
  os?: {
    name?: string;
    version?: string;
  };
  version?: string;
}

/**
 * Wazuh rule information
 */
export interface WazuhRule {
  id: number;
  level: number;
  description: string;
  groups: string[];
  mitre?: {
    id?: string[];
    technique?: string[];
    tactic?: string[];
  };
}

/**
 * Wazuh alert data for streaming
 */
export interface AlertData {
  id: string;
  timestamp: string;
  source: string;
  severity: SeverityLevel;
  event_type: string;
  title: string;
  rule: WazuhRule;
  agent: WazuhAgent;
  full_log?: string;
  location?: string;
  mitre?: MITRETactic;
  iocs: string[];
  source_ip?: string;
  dest_ip?: string;
  username?: string;
  analyzed: boolean;
  correlation_id?: string;
  risk_score?: number;
  received_at: string;
  processed_at?: string;
}

/**
 * Alert aggregation data
 */
export interface AlertAggregation {
  aggregation_key: string;
  alert_count: number;
  first_seen: string;
  last_seen: string;
  severity: SeverityLevel;
  sample_alert: AlertData;
  iocs: string[];
}

/**
 * Alert stream filter
 */
export interface AlertFilter {
  min_severity?: SeverityLevel;
  agent_ids?: string[];
  event_types?: string[];
  source_ips?: string[];
  has_mitre?: boolean;
  limit?: number;
}

/**
 * Stream statistics
 */
export interface StreamStats {
  total_alerts: number;
  alerts_by_severity: Record<string, number>;
  alerts_by_event_type: Record<string, number>;
  top_agents: Array<{ name: string; count: number }>;
  top_source_ips: Array<{ ip: string; count: number }>;
  stream_start_time: string;
  last_alert_time?: string;
}

/**
 * WebSocket message format
 */
export interface WebSocketMessage {
  type: string;
  data: unknown;
  timestamp: string;
  channel?: string;
}

/**
 * Agent health status
 */
export interface AgentHealth {
  id: string;
  name: string;
  ip: string;
  status: "active" | "disconnected" | "never_connected";
  last_seen?: string;
  os?: {
    name: string;
    version: string;
  };
  version?: string;
}

/**
 * Alerts summary
 */
export interface AlertsSummary {
  total: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
}

/**
 * Stream service status
 */
export interface StreamServiceStatus {
  running: boolean;
  stats?: StreamStats;
  config?: {
    aggregation_window_seconds: number;
    max_buffer_size: number;
    max_history_size: number;
  };
}
