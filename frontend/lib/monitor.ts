// Monitoring dashboard type definitions

export interface MonitorData {
  timestamp: string;
  services: ServiceHealthMap;
  resources: ResourceMetrics;
  activities: Activity[];
  metrics: RequestMetrics;
  heartbeat?: boolean;
  error?: string;
}

export interface ServiceHealthMap {
  database: ServiceStatus;
  redis: ServiceStatus;
  ai: ServiceStatus;
  queue: ServiceStatus;
}

export interface ServiceStatus {
  status: "ok" | "error" | "degraded" | "disabled" | "initializing";
  latency_ms: number | null;
  message: string;
  pending_count?: number;
}

export interface ResourceMetrics {
  cpu_percent: number;
  memory_percent: number;
  memory_used_gb: number;
  memory_total_gb: number;
  disk_percent: number;
  disk_used_gb: number;
  disk_total_gb: number;
  error?: string;
}

export interface Activity {
  type: "playbook" | "ai" | "alert" | "user";
  id: string;
  name: string;
  status: string;
  timestamp: string | null;
}

export interface RequestMetrics {
  requests_per_minute: number;
  error_rate: number;
  avg_response_time_ms: number;
}

export interface HistoryPoint {
  timestamp: string;
  resources: ResourceMetrics;
  services: Record<string, string>;
}

export interface MonitorHistory {
  hours: number;
  points: number;
  data: HistoryPoint[];
}

export type Theme = "light" | "dark" | "system";

export type Locale = "en" | "zh";
