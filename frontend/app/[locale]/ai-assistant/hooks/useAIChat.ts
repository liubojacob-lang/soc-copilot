/** Custom hook for AI chat functionality */

import { useState, useCallback, useRef, useEffect } from "react";
import { api } from "@/lib/api";
import { convertToHistoryMessage, convertFromHistoryMessage } from "../utils";
import type { Message, AIChatResponse } from "../types";
import type { ChatConversation } from "@/hooks/useChatHistory";

interface UseAIChatOptions {
  selectedModelId?: string;
  onConversationSave?: (messages: any[], modelId?: string, modelName?: string) => void;
}

interface UseAIChatResult {
  messages: Message[];
  loading: boolean;
  thinking: boolean;
  isStreaming: boolean;
  streamingMessage: string;
  sendMessage: (
    message: string,
    conversationHistory: Message[],
    /** 可选业务上下文（如当前调查的告警）。仅拼进发给模型的 payload，不进入聊天记录展示。 */
    context?: string
  ) => Promise<void>;
  setMessages: (messages: Message[]) => void;
  loadConversation: (
    conv: ChatConversation,
    models: Array<{ id: string; display_name: string }>
  ) => void;
  clearChat: (welcomeMessage?: string) => void;
}

export function useAIChat({
  selectedModelId,
  onConversationSave,
}: UseAIChatOptions): UseAIChatResult {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [thinking, setThinking] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingMessage, setStreamingMessage] = useState("");

  const typingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const typingTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearTypingTimers = useCallback(() => {
    if (typingIntervalRef.current) {
      clearInterval(typingIntervalRef.current);
      typingIntervalRef.current = null;
    }
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
      typingTimeoutRef.current = null;
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      clearTypingTimers();
    };
  }, [clearTypingTimers]);

  const typeWriterEffect = useCallback(
    (text: string, callback: (text: string) => void) => {
      clearTypingTimers();
      let index = 0;
      const chunkSize = 3;

      typingIntervalRef.current = setInterval(() => {
        index = Math.min(index + chunkSize, text.length);
        callback(text.slice(0, index));
        if (index >= text.length && typingIntervalRef.current) {
          clearInterval(typingIntervalRef.current);
          typingIntervalRef.current = null;
        }
      }, 15);
    },
    [clearTypingTimers]
  );

  /** Try the SSE streaming endpoint; returns null when streaming is not
   * available (caller falls back to the one-shot request). */
  const streamChat = useCallback(
    async (
      userMessage: string,
      history: Array<{ role: string; content: string }>,
      onDelta: (delta: string) => void
    ): Promise<{ routedModel?: string; routeReason?: string } | null> => {
      const { ensureCSRFToken, addCSRFToken } = await import("@/lib/csrf");
      await ensureCSRFToken();
      const options = addCSRFToken({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include" as const,
        body: JSON.stringify({
          message: userMessage,
          ...(selectedModelId ? { model_id: selectedModelId } : {}),
          conversation_history: history,
        }),
      });

      const response = await fetch("/api/ai/chat/stream", options);
      const contentType = response.headers.get("content-type") || "";
      if (!response.ok || !contentType.includes("text/event-stream")) {
        return null;
      }

      let routedModel: string | undefined;
      let routeReason: string | undefined;

      const reader = response.body?.getReader();
      if (!reader) return null;
      const decoder = new TextDecoder();
      let buffer = "";

      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const frames = buffer.split("\n\n");
        buffer = frames.pop() || "";
        for (const frame of frames) {
          const line = frame.trim();
          if (!line.startsWith("data:")) continue;
          try {
            const event = JSON.parse(line.slice(5).trim());
            if (event.meta?.routed_model) {
              routedModel = event.meta.routed_model;
              routeReason = event.meta.route_reason;
            }
            if (typeof event.delta === "string" && event.delta.length > 0) {
              onDelta(event.delta);
            }
            if (event.done) {
              return { routedModel, routeReason };
            }
          } catch {
            // malformed frame — skip
          }
        }
      }
      return { routedModel, routeReason };
    },
    [selectedModelId]
  );

  const sendMessage = useCallback(
    async (userMessage: string, conversationHistory: Message[], context?: string) => {
      if (!userMessage.trim() || loading || thinking || isStreaming) {
        return;
      }

      // 上下文只进模型 payload：聊天记录保持用户原文，界面不出现机器前缀
      const payloadMessage = context ? `${context}\n\n${userMessage}` : userMessage;

      const userEntry: Message = {
        role: "user",
        content: userMessage,
        timestamp: new Date(),
      };

      const history = [...conversationHistory, userEntry].slice(-10).map((m) => ({
        role: m.role,
        content: m.content,
      }));

      clearTypingTimers();
      setStreamingMessage("");
      setLoading(true);
      setThinking(true);
      setIsStreaming(false);
      setMessages((prev) => [...prev, userEntry]);

      const finishStreamingMessage = (
        fullText: string,
        routedModel?: string,
        routeReason?: string
      ) => {
        setStreamingMessage("");
        setIsStreaming(false);
        setMessages((prev) => {
          const newMessages = [...prev];
          const lastMessage = newMessages[newMessages.length - 1];
          if (lastMessage?.isStreaming) {
            lastMessage.content = fullText;
            lastMessage.isStreaming = false;
            if (routedModel) lastMessage.routedModel = routedModel;
            if (routeReason) lastMessage.routeReason = routeReason;
          }
          return newMessages;
        });
      };

      try {
        // Preferred path: real SSE streaming from the provider
        try {
          setThinking(false);
          setIsStreaming(true);
          setMessages((prev) => [
            ...prev,
            {
              role: "assistant",
              content: "",
              timestamp: new Date(),
              isStreaming: true,
            },
          ]);

          let streamed = "";
          const meta = await streamChat(payloadMessage, history, (delta) => {
            streamed += delta;
            setStreamingMessage(streamed);
          });

          if (streamed.length > 0 || meta) {
            finishStreamingMessage(
              streamed || "No response from AI service",
              meta?.routedModel,
              meta?.routeReason
            );
            return;
          }
          // No stream frames — remove placeholder and fall through to one-shot
          setMessages((prev) => prev.filter((m) => !m.isStreaming));
        } catch (streamError) {
          console.warn("[AI Assistant] Streaming unavailable, falling back:", streamError);
          setMessages((prev) => prev.filter((m) => !m.isStreaming));
        }

        // Fallback: one-shot request + typewriter effect
        setThinking(true);
        const chatResponse = (await api.post("/api/ai/chat", {
          message: payloadMessage,
          ...(selectedModelId ? { model_id: selectedModelId } : {}),
          conversation_history: history,
        })) as unknown as AIChatResponse;

        const fullResponse =
          typeof chatResponse?.response === "string" ? chatResponse.response.trim() : "";

        if (!fullResponse) {
          setMessages((prev) => [
            ...prev,
            {
              role: "assistant",
              content: "No response from AI service",
              timestamp: new Date(),
            },
          ]);
          return;
        }

        const routedModel = chatResponse?.routed_model ?? undefined;
        const routeReason = chatResponse?.route_reason ?? undefined;

        setThinking(false);
        setIsStreaming(true);
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: "",
            timestamp: new Date(),
            isStreaming: true,
            routedModel,
            routeReason,
          },
        ]);

        typeWriterEffect(fullResponse, (text) => {
          setStreamingMessage(text);
        });

        const typingDuration = Math.max(Math.ceil(fullResponse.length / 3) * 15 + 100, 500);
        typingTimeoutRef.current = setTimeout(() => {
          clearTypingTimers();
          finishStreamingMessage(fullResponse, routedModel, routeReason);
        }, typingDuration);
      } catch (error) {
        console.error("[AI Assistant] Chat request error:", error);
        clearTypingTimers();
        setStreamingMessage("");
        setIsStreaming(false);
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: "Service unavailable. Please try again.",
            timestamp: new Date(),
          },
        ]);
      } finally {
        setLoading(false);
        setThinking(false);
      }
    },
    [
      loading,
      thinking,
      isStreaming,
      selectedModelId,
      streamChat,
      typeWriterEffect,
      clearTypingTimers,
    ]
  );

  const loadConversation = useCallback(
    (conv: ChatConversation, models: Array<{ id: string; display_name: string }>) => {
      if (!conv || !conv.messages || !Array.isArray(conv.messages)) {
        console.error("Invalid conversation data:", conv);
        return;
      }

      const loadedMessages = conv.messages
        .filter((msg) => msg && msg.role && msg.content)
        .map(convertFromHistoryMessage) as Message[];

      if (loadedMessages.length === 0) {
        console.warn("No valid messages found in conversation:", conv.id);
        return;
      }

      setMessages(loadedMessages);

      // Restore model selection if available
      if (conv.modelId) {
        const model = models.find((m) => m.id === conv.modelId);
        if (model && onConversationSave) {
          onConversationSave(loadedMessages, model.id, model.display_name);
        }
      }

      // Clear any streaming state
      clearTypingTimers();
      setIsStreaming(false);
      setStreamingMessage("");
      setThinking(false);
      setLoading(false);
    },
    [clearTypingTimers, onConversationSave]
  );

  const clearChat = useCallback(
    (welcomeMessage?: string) => {
      clearTypingTimers();
      if (welcomeMessage) {
        setMessages([
          {
            role: "assistant",
            content: welcomeMessage,
            timestamp: new Date(),
          },
        ]);
      } else {
        setMessages([]);
      }
      setIsStreaming(false);
      setStreamingMessage("");
      setThinking(false);
      setLoading(false);
    },
    [clearTypingTimers]
  );

  return {
    messages,
    loading,
    thinking,
    isStreaming,
    streamingMessage,
    sendMessage,
    setMessages,
    loadConversation,
    clearChat,
  };
}
