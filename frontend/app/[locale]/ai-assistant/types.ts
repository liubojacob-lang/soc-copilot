/** AI Assistant types and interfaces */

export interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
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
}

export interface QuickAction {
  icon: any;
  label: string;
  query: string;
  color: string;
}
