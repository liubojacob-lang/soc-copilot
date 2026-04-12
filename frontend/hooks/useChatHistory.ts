"use client";

import { useState, useEffect, useCallback, useMemo } from "react";

const STORAGE_KEY = "ai_chat_history";
const MAX_CONVERSATIONS = 50;

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

export interface ChatConversation {
  id: string;
  title: string;
  messages: ChatMessage[];
  modelId?: string;
  modelName?: string;
  createdAt: string;
  updatedAt: string;
}

interface ChatHistoryStorage {
  conversations: ChatConversation[];
  currentConversationId: string | null;
}

export function useChatHistory() {
  const [conversations, setConversations] = useState<ChatConversation[]>([]);
  const [currentId, setCurrentId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [isLoaded, setIsLoaded] = useState(false);

  // Initialize load from localStorage
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const data: ChatHistoryStorage = JSON.parse(stored);
        setConversations(data.conversations || []);
        setCurrentId(data.currentConversationId);
      }
    } catch (e) {
      console.error("Failed to load chat history:", e);
    }
    setIsLoaded(true);
  }, []);

  // Save to localStorage
  const saveToStorage = useCallback((convs: ChatConversation[], currId: string | null) => {
    try {
      const data: ChatHistoryStorage = {
        conversations: convs,
        currentConversationId: currId,
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    } catch (e) {
      console.error("Failed to save chat history:", e);
    }
  }, []);

  // Search filter conversations
  const filteredConversations = useMemo(() => {
    if (!searchQuery.trim()) return conversations;

    const query = searchQuery.toLowerCase().trim();
    return conversations.filter((conv) => {
      // Search title
      if (conv.title.toLowerCase().includes(query)) return true;
      // Search message content
      return conv.messages.some((msg) => msg.content.toLowerCase().includes(query));
    });
  }, [conversations, searchQuery]);

  // Create new conversation
  const createNewConversation = useCallback(() => {
    const newId = `conv_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
    setCurrentId(newId);
    return newId;
  }, []);

  // Save conversation
  const saveConversation = useCallback(
    (messages: ChatMessage[], modelId?: string, modelName?: string) => {
      try {
        // Validate messages
        if (!messages || !Array.isArray(messages)) {
          console.error("saveConversation: Invalid messages array");
          return;
        }

        // Don't save if only welcome message or empty
        const userMessages = messages.filter((m) => m && m.role === "user");
        if (userMessages.length === 0) return;

        // Filter out invalid messages
        const validMessages = messages.filter((m) => m && m.role && m.content && m.timestamp);

        if (validMessages.length === 0) {
          console.error("saveConversation: No valid messages to save");
          return;
        }

        const title = generateTitle(validMessages);
        const now = new Date().toISOString();

        setConversations((prev) => {
          const existing = prev.find((c) => c.id === currentId);
          let updated: ChatConversation[];

          if (existing) {
            // Update existing conversation and move to front
            const updatedConv = {
              ...existing,
              messages: validMessages,
              title,
              modelId,
              modelName,
              updatedAt: now,
            };
            updated = [updatedConv, ...prev.filter((c) => c.id !== currentId)];
          } else {
            // Create new conversation entry
            const newConv: ChatConversation = {
              id: currentId || `conv_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`,
              title,
              messages: validMessages,
              modelId,
              modelName,
              createdAt: now,
              updatedAt: now,
            };
            // Add to front and limit max count
            updated = [newConv, ...prev].slice(0, MAX_CONVERSATIONS);
          }

          saveToStorage(updated, currentId);
          return updated;
        });
      } catch (error) {
        console.error("Error saving conversation:", error);
      }
    },
    [currentId, saveToStorage]
  );

  // Load conversation
  const loadConversation = useCallback(
    (id: string): ChatConversation | null => {
      if (!id) {
        console.error("loadConversation: Invalid conversation ID");
        return null;
      }

      const conv = conversations.find((c) => c.id === id);
      if (conv) {
        setCurrentId(id);
        saveToStorage(conversations, id);
        return conv;
      } else {
        console.error("loadConversation: Conversation not found:", id);
        return null;
      }
    },
    [conversations, saveToStorage]
  );

  // Delete conversation
  const deleteConversation = useCallback(
    (id: string) => {
      setConversations((prev) => {
        const updated = prev.filter((c) => c.id !== id);
        const newCurrentId = id === currentId ? null : currentId;
        saveToStorage(updated, newCurrentId);
        return updated;
      });
      if (id === currentId) {
        setCurrentId(null);
      }
    },
    [currentId, saveToStorage]
  );

  // Rename conversation - doesn't change position or updatedAt
  const renameConversation = useCallback(
    (id: string, newTitle: string) => {
      if (!newTitle.trim()) return;

      setConversations((prev) => {
        const updated = prev.map((c) => (c.id === id ? { ...c, title: newTitle.trim() } : c));
        saveToStorage(updated, currentId);
        return updated;
      });
    },
    [currentId, saveToStorage]
  );

  // Clear search
  const clearSearch = useCallback(() => {
    setSearchQuery("");
  }, []);

  return {
    conversations,
    filteredConversations,
    currentId,
    currentConversation: conversations.find((c) => c.id === currentId) || null,
    searchQuery,
    setSearchQuery,
    clearSearch,
    isLoaded,
    createNewConversation,
    saveConversation,
    loadConversation,
    deleteConversation,
    renameConversation,
  };
}

// Generate conversation title from first user message
function generateTitle(messages: ChatMessage[]): string {
  try {
    if (!messages || !Array.isArray(messages) || messages.length === 0) {
      return "新对话";
    }

    const firstUserMsg = messages.find((m) => m && m.role === "user");
    if (firstUserMsg && firstUserMsg.content) {
      const content = firstUserMsg.content;
      // Clean up and truncate
      const cleaned = content.replace(/\n/g, " ").trim();
      if (!cleaned) return "新对话";
      return cleaned.length > 30 ? cleaned.slice(0, 30) + "..." : cleaned;
    }
    return "新对话";
  } catch (error) {
    console.error("Error generating title:", error);
    return "新对话";
  }
}
