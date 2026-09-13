/**
 * API Module Index
 * Barrel re-exports for all API domains
 */

// Base client
export { ApiError, apiClient } from "./client";

// Auth utilities
export { getAccessToken, getAuthHeaders, setAccessToken, clearAccessToken } from "./auth";

// Error handling
export { handleApiError, isApiError, isApiSuccess } from "./error";
export type { ApiErrorResponse, ApiSuccessResponse, ApiResponse } from "./error";

// Domain APIs - use explicit re-exports to avoid conflicts
export {
  analyzeAlert,
  generateReport,
  buildTimeline,
  healthCheck,
  getThreatIntelStats,
  lookupOTX,
  bulkLookupOTX,
  generatePlaybookQueries,
  generateRemediationActions,
  getPlaybookHistory,
  type AlertAnalysisRequest,
  type AlertAnalysisResponse,
  type IOCsFinal,
  type IOCsLocal,
  type IOCsLLM,
  type IOCCount,
  type RecommendedAction,
  type ResponseMetadata,
  type ReportGenerationRequest,
  type ReportGenerationResponse,
  type TimelineRequest,
  type SuspiciousEvent,
  type TimelineResponse,
  type ThreatIntelItem,
  type ThreatIntelAnalysis,
  type Verdict,
  type Platform,
  type TimeRange,
  type OutputType,
  type RiskLevel,
  type ActionCategory,
  type QueryTemplate,
  type PlatformQueries,
  type GeneratePlaybookQueriesResponse,
  type RemediationStep,
  type RemediationAction,
  type GenerateRemediationActionsResponse,
  type AffectedAsset,
  type ContainmentPriority,
  type ImpactAnalysis,
} from "./alerts";

export {
  listAssets,
  getAsset,
  createAsset,
  updateAsset,
  deleteAsset,
  importAssets,
  type AssetCreate,
  type AssetUpdate,
  type AssetResponse,
  type AssetImportRequest,
  type AssetImportResponse,
  type AssetListResponse,
} from "./assets";
export type { Criticality } from "./assets";

export {
  listHistory,
  getHistory,
  deleteHistory,
  deleteAllHistory,
  type HistoryRecord,
  type HistoryListRequest,
  type HistoryListResponse,
} from "./history";

export {
  listIOCHits,
  listIOCHitsByAsset,
  listIOCHitsByHistory,
  createManualIOCHit,
  type IOCHitCreate,
  type IOCHitResponse,
  type IOCHitListResponse,
  type IOCType,
  type IOCSource,
} from "./ioc";

export {
  listTriggers,
  getTrigger,
  createWebhookTrigger,
  createCronTrigger,
  updateTrigger,
  deleteTrigger,
  regenerateWebhookSecret,
  getTriggerInvocations,
  testWebhookTrigger,
  type WebhookTriggerCreate,
  type CronTriggerCreate,
  type TriggerOut,
  type TriggerListResponse,
  type WebhookTriggerResponse,
  type CronTriggerResponse,
} from "./triggers";

export {
  listSecrets,
  getSecret,
  createSecret,
  updateSecret,
  deleteSecret,
  getKeyStatus,
  getQueueStats,
  type Secret,
  type SecretListResponse,
  type QueueStats,
} from "./secrets";

export * from "./playbooks";

export {
  listAIModels,
  getAIModel,
  testAIModel,
  setDefaultAIModel,
  sendChatMessage,
  analyzeAlert as analyzeAlertAI,
  buildTimeline as buildTimelineAI,
  generateReport as generateReportAI,
  getAIHistory,
  clearAIChatHistory,
  getAISettings,
  updateAISettings,
  listAIModelsAdmin,
  getDefaultModel,
  setDefaultModel,
  testModelAdmin,
  aiApi,
  type AIModel,
  type AIModelListResponse,
  type SetDefaultModelRequest,
  type SetDefaultModelResponse,
  type TestModelRequest,
  type TestModelResponse,
} from "./ai";

// Threat Intelligence (v1, typed)
export {
  lookupIoc,
  batchIocQuery,
  getTICacheStats,
  detectIocType,
  type TIIOCType,
  type TIVerdict,
  type ThreatIntelLookupResponse,
  type IOCBatchRequestItem,
  type IOCBatchResultItem,
  type IOCBatchResponse,
} from "./threat-intel";

// Legacy API objects (backward compatibility)
export { api, api_v7, api_triggers, api_v74, api_v73, api_ai_models } from "./legacy";

// Security Alerts (v1)
export {
  listSecurityAlerts,
  getSecurityAlert,
  updateSecurityAlert,
  deleteSecurityAlert,
  getAlertStats,
  getAlertLifecycle,
  addAlertNote,
  type AlertSeverity,
  type AlertStatus,
  type SecurityAlertItem,
  type AlertNoteItem,
  type TimelineEvent,
  type SecurityAlertListResponse,
  type SecurityAlertUpdatePayload,
  type SecurityAlertStats,
  type AlertListFilters,
} from "./security-alerts";

// Cases (v1)
export {
  listCases,
  getCase,
  createCase,
  updateCase,
  deleteCase,
  transitionCaseStatus,
  getCaseAlerts,
  linkAlertToCase,
  unlinkAlertFromCase,
  getCaseComments,
  addCaseComment,
  getCaseTimeline,
  mapCaseSeverity,
  CASE_STATUS_OPTIONS,
  CASE_SEVERITY_OPTIONS,
  STATUS_TRANSITIONS,
  type CaseSeverity,
  type CaseStatus,
  type SecurityCase,
  type CaseListResponse,
  type CaseFilters,
  type CaseCreatePayload,
  type CaseUpdatePayload,
  type CaseStatusTransition,
  type CaseComment,
  type CaseCommentCreate,
  type CaseAlert,
  type CaseTimelineEvent,
} from "./cases";

// Dashboard
export {
  getDashboardStats,
  toAlertTrendPoints,
  toSeverityBuckets,
  toAssetRiskItems,
  type DashboardStats,
  type SeverityDistribution,
  type StatusDistribution,
  type TrendPoint,
  type TrendPointBySeverity,
  type TopSource,
  type TopRiskyAsset,
  type AlertTrendPoint,
  type SeverityBucket,
  type AssetRiskItem,
} from "./dashboard";
