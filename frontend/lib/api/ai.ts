/**
 * AI API
 * Handles AI model management, chat, and analysis
 */

import { apiClient as client } from "./client";

interface ChatResponse {
  message: string;
  model: string;
  latency_ms: number;
}

interface AnalyzeAlertResponse {
  analysis: string;
  severity: "low" | "medium" | "high" | "critical";
  iocs: string[];
  recommendations: string[];
}

interface TimelineEvent {
  timestamp: string;
  event_type: string;
  description: string;
  source: string;
}

interface BuildTimelineResponse {
  timeline: TimelineEvent[];
  summary: string;
}

interface GenerateReportRequest {
  title: string;
  events: TimelineEvent[];
  format?: "markdown" | "html" | "pdf";
}

interface GenerateReportResponse {
  report: string;
  format: string;
  generated_at: string;
}

/**
 * List available AI models
 */
export async function listAIModels(): Promise<AIModel[]> {
  return client.get<AIModel[]>("/api/ai/models");
}

/**
 * Get AI model by ID
 */
export async function getAIModel(id: string): Promise<AIModel> {
  return client.get<AIModel>(`/api/ai/models/${id}`);
}

/**
 * Test AI model connection
 */
export async function testAIModel(id: string): Promise<TestModelResponse> {
  return client.post<TestModelResponse>("/api/ai/models/test", { model_id: id });
}

/**
 * Set default AI model
 */
export async function setDefaultAIModel(id: string): Promise<SetDefaultModelResponse> {
  return client.post<SetDefaultModelResponse>("/api/ai/models/default", { model_id: id });
}

/**
 * Send chat message
 */
export async function sendChatMessage(
  message: string,
  conversationId?: string,
  modelId?: string
): Promise<ChatResponse> {
  return client.post<ChatResponse>("/api/ai/chat", {
    message,
    conversation_id: conversationId,
    model_id: modelId,
  });
}

/**
 * Analyze security alert
 */
export async function analyzeAlert(alertData: {
  alert_id?: string;
  title: string;
  description: string;
  source: string;
  timestamp: string;
  raw_data?: Record<string, unknown>;
}): Promise<AnalyzeAlertResponse> {
  return client.post<AnalyzeAlertResponse>("/api/ai/analyze-alert", alertData, 120000);
}

/**
 * Build investigation timeline
 */
export async function buildTimeline(events: TimelineEvent[]): Promise<BuildTimelineResponse> {
  return client.post<BuildTimelineResponse>("/api/ai/build-timeline", { events }, 120000);
}

/**
 * Generate investigation report
 */
export async function generateReport(
  request: GenerateReportRequest
): Promise<GenerateReportResponse> {
  return client.post<GenerateReportResponse>("/api/ai/generate-report", request, 120000);
}

/**
 * Get AI analysis history
 */
export async function getAIHistory(params?: { limit?: number; offset?: number }): Promise<
  Array<{
    id: string;
    type: "chat" | "analyze" | "timeline" | "report";
    input: string;
    output: string;
    model: string;
    created_at: string;
  }>
> {
  return client.get("/api/ai/history", { params } as RequestInit);
}

/**
 * Clear AI chat history
 */
export async function clearAIChatHistory(conversationId: string): Promise<void> {
  return client.delete(`/api/ai/chat/history/${conversationId}`);
}

/**
 * Get AI user settings
 */
export async function getAISettings(): Promise<{
  preferred_model?: string;
  enable_streaming?: boolean;
  max_history_size?: number;
}> {
  return client.get("/api/ai/settings");
}

/**
 * Update AI user settings
 */
export async function updateAISettings(settings: {
  preferred_model?: string;
  enable_streaming?: boolean;
  max_history_size?: number;
}): Promise<void> {
  return client.put("/api/ai/settings", settings);
}

// AI Model Management (admin)
export interface AIModel {
  id: string;
  provider: string;
  display_name: string;
  description?: string;
  enabled: boolean;
  is_default: boolean;
  capabilities?: {
    chat?: boolean;
    json?: boolean;
    vision?: boolean;
    tools?: boolean;
  };
  max_tokens?: number;
  config?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface AIModelListResponse {
  models: AIModel[];
  total: number;
  default_model_id?: string;
}

export interface SetDefaultModelRequest {
  model_id: string;
}

export interface SetDefaultModelResponse {
  success: boolean;
  model_id: string;
  message: string;
}

export interface TestModelRequest {
  model_id: string;
}

export interface TestModelResponse {
  success: boolean;
  model_id: string;
  latency_ms?: number;
  provider_raw?: string;
  error_message?: string;
  response?: string;
}

export async function listAIModelsAdmin(skip = 0, limit = 100): Promise<AIModelListResponse> {
  return client.get(`/api/ai/models?skip=${skip}&limit=${limit}`);
}

export async function getDefaultModel(): Promise<AIModel> {
  return client.get("/api/ai/models/default");
}

export async function setDefaultModel(
  data: SetDefaultModelRequest
): Promise<SetDefaultModelResponse> {
  return client.post("/api/ai/models/default", data);
}

export async function testModelAdmin(data: TestModelRequest): Promise<TestModelResponse> {
  return client.post("/api/ai/models/test", data);
}

// Export AI API object
export const aiApi = {
  listModels: listAIModels,
  getModel: getAIModel,
  testModel: testAIModel,
  setDefaultModel: setDefaultAIModel,
  chat: sendChatMessage,
  analyzeAlert: analyzeAlert,
  buildTimeline: buildTimeline,
  generateReport: generateReport,
  getHistory: getAIHistory,
  clearHistory: clearAIChatHistory,
  getSettings: getAISettings,
  updateSettings: updateAISettings,
  // Admin
  listModelsAdmin: listAIModelsAdmin,
  getDefaultModel: getDefaultModel,
  setDefaultModelAdmin: setDefaultModel,
  testModelAdmin: testModelAdmin,
};
