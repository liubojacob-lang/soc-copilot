/** Chat messages display component */

import { useRef, useEffect } from "react";
import { Brain, Copy, Check } from "lucide-react";
import type { Message } from "../types";

interface ChatMessagesProps {
  messages: Message[];
  streamingMessage: string;
  thinking: boolean;
  copiedIndex: number | null;
  onCopy: (text: string, index: number) => void;
  t: (key: string) => string;
}

export function ChatMessages({
  messages,
  streamingMessage,
  thinking,
  copiedIndex,
  onCopy,
  t,
}: ChatMessagesProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingMessage, thinking]);

  return (
    <div ref={messagesContainerRef} className="flex-1 overflow-y-auto p-6 space-y-4">
      {messages.map((message, index) => (
        <div
          key={index}
          className={`flex gap-3 group ${message.role === "user" ? "flex-row-reverse" : ""}`}
        >
          <div
            className={`flex-shrink-0 w-10 h-10 rounded-2xl flex items-center justify-center shadow-md ${
              message.role === "user"
                ? "bg-gradient-to-br from-blue-500 to-blue-600"
                : "bg-gradient-to-br from-purple-500 to-indigo-600"
            }`}
          >
            {message.role === "user" ? (
              <span className="text-white font-semibold text-sm">{t("userLabel")}</span>
            ) : (
              <Brain className="w-5 h-5 text-white" />
            )}
          </div>
          <div className={`flex-1 max-w-[75%] ${message.role === "user" ? "text-right" : ""}`}>
            <div
              className={`inline-block rounded-2xl px-4 py-3 shadow-sm ${
                message.role === "user"
                  ? "bg-gradient-to-r from-blue-500 to-blue-600 text-white"
                  : "bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 text-gray-900 dark:text-gray-100"
              }`}
            >
              <div className="text-sm whitespace-pre-wrap leading-relaxed">
                {message.isStreaming && index === messages.length - 1
                  ? streamingMessage
                  : message.content}
              </div>
            </div>
            <div
              className={`text-xs mt-1.5 flex items-center gap-2 ${message.role === "user" ? "justify-end" : ""}`}
            >
              <span className="text-gray-400 dark:text-gray-500">
                {message.timestamp.toLocaleTimeString()}
              </span>
              {message.content && (
                <button
                  onClick={() => onCopy(message.content, index)}
                  className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                  title={t("actions.copy")}
                >
                  {copiedIndex === index ? (
                    <Check className="w-3 h-3 text-green-500" />
                  ) : (
                    <Copy className="w-3 h-3 text-gray-400" />
                  )}
                </button>
              )}
            </div>
          </div>
        </div>
      ))}

      {thinking && (
        <div className="flex gap-3">
          <div className="flex-shrink-0 w-10 h-10 rounded-2xl bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center shadow-md">
            <Brain className="w-5 h-5 text-white" />
          </div>
          <div className="bg-white dark:bg-gray-700 rounded-2xl px-4 py-3 shadow-sm border border-gray-200 dark:border-gray-600 flex items-center gap-3">
            <div className="flex gap-1">
              <span
                className="w-2 h-2 bg-purple-500 rounded-full animate-bounce"
                style={{ animationDelay: "0ms" }}
              ></span>
              <span
                className="w-2 h-2 bg-purple-500 rounded-full animate-bounce"
                style={{ animationDelay: "150ms" }}
              ></span>
              <span
                className="w-2 h-2 bg-purple-500 rounded-full animate-bounce"
                style={{ animationDelay: "300ms" }}
              ></span>
            </div>
            <span className="text-sm text-gray-600 dark:text-gray-400">{t("thinking")}</span>
          </div>
        </div>
      )}

      <div ref={messagesEndRef} />
    </div>
  );
}
