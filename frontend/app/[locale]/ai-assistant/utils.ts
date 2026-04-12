/** Utility functions for AI Assistant */

import type { Message } from "./types";
import type { ChatMessage as HistoryChatMessage } from "@/hooks/useChatHistory";

/** Convert Message to ChatMessage for history */
export function convertToHistoryMessage(msg: Message): HistoryChatMessage {
  if (!msg || !msg.role || !msg.content || !msg.timestamp) {
    console.error("Invalid message for history conversion:", msg);
    throw new Error("Invalid message format");
  }

  return {
    role: msg.role,
    content: msg.content,
    timestamp: msg.timestamp.toISOString(),
  };
}

/** Convert ChatMessage to Message for display */
export function convertFromHistoryMessage(msg: HistoryChatMessage): Message {
  if (!msg || !msg.role || !msg.content) {
    throw new Error("Invalid message format");
  }

  // Validate role
  if (msg.role !== "user" && msg.role !== "assistant") {
    throw new Error(`Invalid role: ${msg.role}`);
  }

  // Validate and parse timestamp
  let timestamp: Date;
  try {
    timestamp = new Date(msg.timestamp);
    if (isNaN(timestamp.getTime())) {
      throw new Error("Invalid timestamp");
    }
  } catch (e) {
    console.error("Error parsing timestamp:", msg.timestamp, e);
    timestamp = new Date(); // Fallback to current time
  }

  return {
    role: msg.role,
    content: msg.content,
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
