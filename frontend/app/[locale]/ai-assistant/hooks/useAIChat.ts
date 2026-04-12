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
  sendMessage: (message: string, conversationHistory: Message[]) => Promise<void>;
  setMessages: (messages: Message[]) => void;
  loadConversation: (
    conv: ChatConversation,
    models: Array<{ id: string; display_name: string }>
  ) => void;
  clearChat: (welcomeMessage: string) => void;
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

  const sendMessage = useCallback(
    async (userMessage: string, conversationHistory: Message[]) => {
      if (!userMessage.trim() || loading || thinking || isStreaming) {
        return;
      }

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

      try {
        const chatResponse = (await api.post("/api/ai/chat", {
          message: userMessage,
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

        typeWriterEffect(fullResponse, (text) => {
          setStreamingMessage(text);
        });

        const typingDuration = Math.max(Math.ceil(fullResponse.length / 3) * 15 + 100, 500);
        typingTimeoutRef.current = setTimeout(() => {
          clearTypingTimers();
          setStreamingMessage("");
          setIsStreaming(false);
          setMessages((prev) => {
            const newMessages = [...prev];
            const lastMessage = newMessages[newMessages.length - 1];
            if (lastMessage?.isStreaming) {
              lastMessage.content = fullResponse;
              lastMessage.isStreaming = false;
            }
            return newMessages;
          });
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
    [loading, thinking, isStreaming, selectedModelId, typeWriterEffect, clearTypingTimers]
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
    (welcomeMessage: string) => {
      clearTypingTimers();
      setMessages([
        {
          role: "assistant",
          content: welcomeMessage,
          timestamp: new Date(),
        },
      ]);
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
