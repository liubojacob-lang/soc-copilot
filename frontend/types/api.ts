/**
 * SOC Copilot - Strongly-Typed API Contract Utilities & Types
 * Automatically aligned with backend FastAPI OpenAPI specifications.
 */

import type { components, paths } from "./api.generated";

// Core Root Types
export type Schemas = components["schemas"];
export type Paths = paths;
export type Operations = paths;

// Common Entity Type Aliases
export type SecurityAlert = Schemas["SecurityAlertResponse"];
export type SecurityAlertIngest = Schemas["SecurityAlertIngest"];
export type SecurityAlertUpdate = Schemas["SecurityAlertUpdate"];

export type Case = Schemas["CaseResponse"];
export type CaseCreate = Schemas["CaseCreate"];
export type CaseUpdate = Schemas["CaseUpdate"];

export type PlaybookDefinition = Schemas["PlaybookDefinitionResponse"];
export type PlaybookDefinitionUpdate = Schemas["PlaybookDefinitionUpdate"];
export type PlaybookRun = Schemas["PlaybookRunResponse"];
export type PlaybookRunCreateRequest = Schemas["PlaybookRunCreateRequest"];

export type AuditLog = Schemas["AuditLogResponse"];
export type AIModel = Schemas["AIModelResponse"];
export type ThreatIntelItem = Schemas["ThreatIntelItem"];
export type ThreatIntelResponse = Schemas["ThreatIntelResponse"];

export type User = Schemas["UserResponse"];
export type TokenResponse = Schemas["TokenResponse"];

// Generic API response helper
export interface PaginatedResult<T> {
  items: T[];
  total: number;
  page?: number;
  page_size?: number;
  has_more?: boolean;
}
