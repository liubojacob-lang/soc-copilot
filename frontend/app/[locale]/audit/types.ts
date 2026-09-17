/** Audit log types and interfaces */

export interface AuditLog {
  id: string;
  user_id: string | null;
  username: string | null;
  action: string;
  method: string;
  path: string;
  status_code: number;
  target_type: string | null;
  target_id: string | null;
  ip_address: string | null;
  duration_ms: number | null;
  created_at: string;
}

export interface AuditLogStats {
  total_requests: number;
  last_24h_requests: number;
  failed_requests: number;
}

export interface AuditFilters {
  action: string;
  path: string;
  statusCode: string;
  dateFrom: string;
  dateTo: string;
}

export interface QuickFilter {
  name: string;
  icon: string;
  filter: {
    filterAction: string;
    filterPath: string;
    filterStatusCode: string;
  };
  description: string;
}

export interface FilterOption {
  value: string;
  label: string;
}
