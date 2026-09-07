/** AI Assistant types and interfaces */

export interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
  routedModel?: string;
  routeReason?: string;
}

export interface AIStatus {
  status: "available" | "unavailable" | "error";
  provider?: string;
  version?: string;
  error?: string;
  features?: string[];
}

export interface AIChatResponse {
  message: string;
  response: string;
  conversation_id?: string | null;
  routed_model?: string | null;
  route_reason?: string | null;
}

export interface QuickAction {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  query: string;
  color: string;
}
