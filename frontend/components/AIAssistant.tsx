"use client";

import { useState, useRef, useEffect } from "react";
import { api } from "@/lib/api";
import { Send, Bot, User, Sparkles, AlertCircle, Loader2 } from "lucide-react";

interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

export default function AIAssistant() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "Hello! I'm SOC Copilot AI. I can help you with:\n\n• Analyzing security alerts\n• Finding playbooks\n• Answering questions about your SOC data\n• Generating reports\n
What would you like to do?",
      timestamp: new Date()
    }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput("");
    
    // Add user message
    setMessages(prev => [...prev, {
      role: "user",
      content: userMessage,
      timestamp: new Date()
    }]);

    setLoading(true);

    try {
      // First try natural language query
      const queryResponse = await api.post("/api/ai/query", {
        query: userMessage
      });

      if (queryResponse.data.intent && queryResponse.data.intent !== "unknown") {
        // Handle specific intents
        let response = queryResponse.data.response;
        
        // Add action buttons based on intent
        if (queryResponse.data.intent === "list_alerts") {
          response += "\n\n[View Alerts](/alerts)";
        } else if (queryResponse.data.intent === "list_playbooks") {
          response += "\n\n[View Playbooks](/playbooks/definitions)";
        }

        setMessages(prev => [...prev, {
          role: "assistant",
          content: response,
          timestamp: new Date()
        }]);
      } else {
        // Fall back to chat
        const chatResponse = await api.post("/api/ai/chat", {
          message: userMessage,
          conversation_history: messages.map(m => ({
            role: m.role,
            content: m.content
          }))
        });

        setMessages(prev => [...prev, {
          role: "assistant",
          content: chatResponse.data.response,
          timestamp: new Date()
        }]);
      }
    } catch (error: any) {
      setMessages(prev => [...prev, {
        role: "assistant",
        content: `I'm sorry, I encountered an error: ${error.message || "Unknown error"}`,
        timestamp: new Date()
      }]);
    } finally {
      setLoading(false);
    }
  };

  const quickActions = [
    { label: "Analyze latest alert", query: "Analyze the most recent high severity alert" },
    { label: "Show active playbooks", query: "Show me active playbook definitions" },
    { label: "Recent alerts", query: "Show me alerts from the last 24 hours" },
    { label: "Help", query: "What can you help me with?" }
  ];

  return (
    <div className="flex flex-col h-full bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-200 dark:border-gray-700">
        <div className="p-2 bg-blue-100 dark:bg-blue-900 rounded-lg">
          <Bot className="w-5 h-5 text-blue-600 dark:text-blue-400" />
        </div>
        <div>
          <h3 className="font-semibold text-gray-900 dark:text-white">SOC Copilot AI</h3>
          <p className="text-xs text-gray-500 dark:text-gray-400">Your AI security assistant</p>
        </div>
        <div className="ml-auto flex items-center gap-1">
          <Sparkles className="w-4 h-4 text-yellow-500" />
          <span className="text-xs text-gray-500 dark:text-gray-400">AI Powered</span>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="flex gap-2 px-4 py-2 border-b border-gray-200 dark:border-gray-700 overflow-x-auto">
        {quickActions.map((action, index) => (
          <button
            key={index}
            onClick={() => setInput(action.query)}
            className="px-3 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-full hover:bg-gray-200 dark:hover:bg-gray-600 whitespace-nowrap transition-colors"
          >
            {action.label}
          </button>
        ))}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex gap-3 ${message.role === "user" ? "flex-row-reverse" : ""}`}
          >
            <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
              message.role === "user"
                ? "bg-blue-100 dark:bg-blue-900"
                : "bg-purple-100 dark:bg-purple-900"
            }`}>
              {message.role === "user" ? (
                <User className="w-4 h-4 text-blue-600 dark:text-blue-400" />
              ) : (
                <Bot className="w-4 h-4 text-purple-600 dark:text-purple-400" />
              )}
            </div>
            <div className={`max-w-[80%] rounded-lg px-4 py-2 ${
              message.role === "user"
                ? "bg-blue-600 text-white"
                : "bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            }`}>
              <div className="text-sm whitespace-pre-wrap">{message.content}</div>
              <div className={`text-xs mt-1 ${
                message.role === "user" ? "text-blue-200" : "text-gray-500 dark:text-gray-400"
              }`}>
                {message.timestamp.toLocaleTimeString()}
              </div>
            </div>
          </div>
        ))}
        
        {loading && (
          <div className="flex gap-3">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-purple-100 dark:bg-purple-900 flex items-center justify-center">
              <Bot className="w-4 h-4 text-purple-600 dark:text-purple-400" />
            </div>
            <div className="bg-gray-100 dark:bg-gray-700 rounded-lg px-4 py-2">
              <Loader2 className="w-5 h-5 animate-spin text-purple-600" />
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 border-t border-gray-200 dark:border-gray-700">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask me anything about your SOC data..."
            className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
        <p className="mt-2 text-xs text-gray-500 dark:text-gray-400 text-center">
          SOC Copilot AI can make mistakes. Please verify important information.
        </p>
      </form>
    </div>
  );
}
