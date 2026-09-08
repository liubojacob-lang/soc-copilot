/** Utility functions for AI Assistant */

import type { Message } from "./types";
import type { ChatMessage as HistoryChatMessage } from "@/hooks/useChatHistory";

/** Convert Message to ChatMessage for history */
/** Convert Message to ChatMessage for history */
export function convertToHistoryMessage(msg: Message): HistoryChatMessage {
  const role = msg?.role === "user" ? "user" : "assistant";
  const content = typeof msg?.content === "string" ? msg.content : "";
  let timestampStr: string;

  try {
    if (msg?.timestamp instanceof Date && !isNaN(msg.timestamp.getTime())) {
      timestampStr = msg.timestamp.toISOString();
    } else if (msg?.timestamp) {
      const parsed = new Date(msg.timestamp);
      timestampStr = !isNaN(parsed.getTime()) ? parsed.toISOString() : new Date().toISOString();
    } else {
      timestampStr = new Date().toISOString();
    }
  } catch {
    timestampStr = new Date().toISOString();
  }

  return {
    role,
    content,
    timestamp: timestampStr,
  };
}

/** Convert ChatMessage to Message for display */
export function convertFromHistoryMessage(msg: HistoryChatMessage): Message {
  const role = msg?.role === "user" ? "user" : "assistant";
  const content = typeof msg?.content === "string" ? msg.content : "";

  // Validate and parse timestamp
  let timestamp: Date;
  try {
    timestamp = msg?.timestamp ? new Date(msg.timestamp) : new Date();
    if (isNaN(timestamp.getTime())) {
      timestamp = new Date();
    }
  } catch (e) {
    console.error("Error parsing timestamp:", msg?.timestamp, e);
    timestamp = new Date(); // Fallback to current time
  }

  return {
    role,
    content,
    timestamp,
  };
}

/** Clean model name by removing provider prefixes */
export function cleanModelName(displayName: string, provider: string): string {
  const prefixes = ["智谱", "Zhipu", "GLM-", "glm-"];
  let cleaned = displayName;
  prefixes.forEach((prefix) => {
    if (cleaned.startsWith(prefix)) {
      cleaned = cleaned.slice(prefix.length);
    }
  });
  return cleaned.trim();
}

/** Get error message with fallback */
export function getErrorMessage(
  error: unknown,
  fallback: string,
  t: (key: string, params?: Record<string, string | number | Date>) => string
): string {
  if (error instanceof Error && error.message) {
    if (
      error.message.includes("image.png") &&
      error.message.includes("does not support image input")
    ) {
      return t("errors.imageNotSupported");
    }
    return error.message;
  }
  if (typeof error === "string" && error.trim()) return error;
  return fallback;
}
