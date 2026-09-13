/**
 * Common types for the frontend application.
 */

/**
 * API Error structure matching backend error response.
 */
export interface ApiError {
  status: number;
  message: string;
  code: string;
  traceId?: string;
  details?: unknown;
}

/**
 * Standard API response wrapper.
 */
export interface ApiResponse<T> {
  data?: T;
  error?: string;
  message?: string;
  trace_id?: string;
}

/**
 * Paginated response.
 */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

/**
 * User information.
 */
export interface User {
  id: string;
  username: string;
  email: string;
  role: "admin" | "analyst" | "auditor";
  is_active: boolean;
  permissions: string[];
  created_at: string;
  updated_at: string;
  last_login_at?: string;
  is_totp_enabled?: boolean;
  totp_policy?: "sudo" | "login" | string;
}

/**
 * Login request.
 */
export interface LoginRequest {
  username: string;
  password: string;
}

/**
 * Login response.
 */
export interface LoginResponse {
  access_token: string;
  refresh_token?: string;
  token_type: string;
  user: User;
}

/**
 * Health check response.
 */
export interface HealthStatus {
  status: "ok" | "degraded" | "error";
  version: string;
  timestamp: string;
  uptime_seconds: number;
  components: Record<string, ComponentHealth>;
}

/**
 * Component health status.
 */
export interface ComponentHealth {
  status: "ok" | "error" | "disabled" | "degraded";
  latency_ms?: number;
  message?: string;
  details?: Record<string, unknown>;
}
