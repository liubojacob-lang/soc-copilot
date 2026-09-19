/** Chat messages display component with Markdown and Code block highlighting */

"use client";

import React, { useRef, useEffect, useState } from "react";
import { useFormatter } from "next-intl";
import { Brain, Copy, Check, Sparkles, Terminal, ChevronDown } from "lucide-react";
import ReactMarkdown from "react-markdown";
import type { Message } from "../types";

interface ChatMessagesProps {
  messages: Message[];
  streamingMessage: string;
  thinking: boolean;
  copiedIndex: number | null;
  onCopy: (text: string, index: number) => void;
  t: (key: string) => string;
}

/** Code block component with Mac header and Copy button */
function CodeBlock({ children, className }: { children?: React.ReactNode; className?: string }) {
  const [copied, setCopied] = useState(false);
  const match = /language-(\w+)/.exec(className || "");
  const lang = match ? match[1] : "text";
  const codeString = String(children).replace(/\n$/, "");

  const handleCopyCode = () => {
    navigator.clipboard.writeText(codeString);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="my-3 rounded-xl overflow-hidden border border-gray-700/80 bg-[#1e1e24] shadow-md">
      <div className="flex items-center justify-between px-3.5 py-1.5 bg-[#141418] border-b border-gray-800 text-xs">
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500/80 inline-block"></span>
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500/80 inline-block"></span>
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/80 inline-block"></span>
          </div>
          <span className="font-mono text-[11px] text-text-tertiary uppercase tracking-wider ml-1.5">
            {lang}
          </span>
        </div>
        <button
          type="button"
          onClick={handleCopyCode}
          className="flex items-center gap-1 text-[11px] text-text-tertiary hover:text-white px-2 py-0.5 rounded hover:bg-gray-800 transition-colors"
          title="复制代码"
        >
          {copied ? (
            <>
              <Check className="w-3 h-3 text-emerald-400" />
              <span className="text-emerald-400">已复制</span>
            </>
          ) : (
            <>
              <Copy className="w-3 h-3" />
              <span>复制</span>
            </>
          )}
        </button>
      </div>
      <pre className="p-3.5 overflow-x-auto text-[12px] font-mono text-gray-200 leading-relaxed">
        <code>{children}</code>
      </pre>
    </div>
  );
}

/** Parses raw model output into thinking content and final response */
function parseThinkingContent(rawText: string): { thinking: string | null; content: string } {
  if (!rawText) return { thinking: null, content: "" };

  // Case 1: <think> ... </think>
  const thinkTagRegex = /<think>([\s\S]*?)<\/think>/i;
  const thinkMatch = rawText.match(thinkTagRegex);
  if (thinkMatch) {
    const thinking = thinkMatch[1].trim();
    const content = rawText.replace(thinkTagRegex, "").trim();
    return { thinking, content };
  }

  // Case 2: "Here's a thinking process:\n\n"
  const thinkProcessPrefix = "Here's a thinking process:";
  if (rawText.startsWith(thinkProcessPrefix)) {
    const afterPrefix = rawText.slice(thinkProcessPrefix.length);
    // Usually ends when actual response starts or has numbered reasoning
    const parts = afterPrefix.split(/\n\n(?=[#*-]|\d+\.\s+\*\*|[A-Z\u4e00-\u9fa5]{2,})/);
    if (parts.length > 1) {
      const thinking = parts.slice(0, -1).join("\n\n").trim();
      const content = parts[parts.length - 1].trim();
      return { thinking, content };
    }
  }

  return { thinking: null, content: rawText };
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
  const format = useFormatter();

  useEffect(() => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
    }
  }, [messages, streamingMessage, thinking]);

  return (
    <div
      ref={messagesContainerRef}
      className="flex-1 min-h-0 overflow-y-auto px-4 sm:px-6 py-6 space-y-6 max-w-4xl mx-auto w-full"
    >
      {messages.map((message, index) => {
        const isUser = message.role === "user";
        const rawContent =
          message.isStreaming && index === messages.length - 1 ? streamingMessage : message.content;

        const { thinking: thinkingBlock, content: mainContent } = isUser
          ? { thinking: null, content: rawContent }
          : parseThinkingContent(rawContent);

        return (
          <div
            key={index}
            className={`flex gap-3.5 group animate-fadeIn ${
              isUser ? "flex-row-reverse" : "flex-row"
            }`}
          >
            {/* Avatar */}
            <div
              className={`flex-shrink-0 w-8 h-8 sm:w-9 sm:h-9 rounded-xl flex items-center justify-center shadow-sm ${
                isUser
                  ? "bg-gradient-to-tr from-blue-600 to-indigo-600 text-white"
                  : "bg-gradient-to-tr from-purple-600 to-indigo-600 text-white ring-2 ring-purple-500/10"
              }`}
            >
              {isUser ? (
                <span className="font-semibold text-xs">{t("userLabel")}</span>
              ) : (
                <Brain className="w-4 h-4 text-white" />
              )}
            </div>

            {/* Bubble Container */}
            <div
              className={`flex-1 max-w-[85%] sm:max-w-[80%] ${isUser ? "text-right" : "text-left"}`}
            >
              <div
                className={`inline-block rounded-2xl px-4 py-3 shadow-sm ${
                  isUser
                    ? "bg-gradient-to-r from-accent-600 to-indigo-600 text-white text-sm leading-relaxed text-left"
                    : "bg-surface-card border border-border-subtle text-text-primary w-full"
                }`}
              >
                {isUser ? (
                  <div className="whitespace-pre-wrap">{rawContent}</div>
                ) : (
                  <div>
                    {/* Collapsible Thinking Process */}
                    {thinkingBlock && (
                      <details className="mb-3 group rounded-xl border border-ai/20 bg-ai/5 overflow-hidden text-xs">
                        <summary className="px-3 py-2 cursor-pointer font-medium text-ai-fg flex items-center justify-between hover:bg-ai/10 select-none transition-colors">
                          <span className="flex items-center gap-1.5">
                            <Sparkles className="w-3.5 h-3.5 text-ai-fg" />
                            <span>思考推演过程</span>
                          </span>
                          <span className="text-[10px] text-ai-fg/70 group-open:rotate-180 transition-transform">
                            ▼
                          </span>
                        </summary>
                        <div className="p-3 border-t border-ai/15 text-text-secondary whitespace-pre-wrap leading-relaxed font-mono text-[11px] max-h-56 overflow-y-auto bg-surface-ground/40">
                          {thinkingBlock}
                        </div>
                      </details>
                    )}

                    {/* Markdown Body */}
                    <div className="text-sm prose prose-sm dark:prose-invert max-w-none break-words leading-relaxed text-text-primary">
                      <ReactMarkdown
                        components={{
                          // react-markdown v9+ removed the `inline` prop; block code arrives as <pre><code>
                          pre({ children }: any) {
                            const codeEl = Array.isArray(children) ? children[0] : children;
                            return (
                              <CodeBlock className={codeEl?.props?.className}>
                                {codeEl?.props?.children}
                              </CodeBlock>
                            );
                          },
                          code({ className, children, ...props }: any) {
                            return (
                              <code
                                className={`px-1.5 py-0.5 rounded bg-surface-hover border border-border-subtle text-ai-fg font-mono text-xs ${className ?? ""}`}
                                {...props}
                              >
                                {children}
                              </code>
                            );
                          },
                          p({ children }) {
                            return <p className="mb-2.5 last:mb-0 leading-relaxed">{children}</p>;
                          },
                          h1({ children }) {
                            return (
                              <h1 className="text-base font-bold my-3 text-text-primary border-b border-border-subtle pb-1">
                                {children}
                              </h1>
                            );
                          },
                          h2({ children }) {
                            return (
                              <h2 className="text-sm font-bold my-2.5 text-text-primary">
                                {children}
                              </h2>
                            );
                          },
                          h3({ children }) {
                            return (
                              <h3 className="text-xs font-bold my-2 text-text-secondary uppercase tracking-wide">
                                {children}
                              </h3>
                            );
                          },
                          ul({ children }) {
                            return <ul className="list-disc pl-5 my-2 space-y-1">{children}</ul>;
                          },
                          ol({ children }) {
                            return <ol className="list-decimal pl-5 my-2 space-y-1">{children}</ol>;
                          },
                          li({ children }) {
                            return <li className="my-0.5 leading-relaxed">{children}</li>;
                          },
                          blockquote({ children }) {
                            return (
                              <blockquote className="border-l-4 border-ai pl-3 my-2 text-text-secondary italic bg-ai/5 py-1 rounded-r">
                                {children}
                              </blockquote>
                            );
                          },
                        }}
                      >
                        {mainContent || (message.isStreaming ? "..." : "")}
                      </ReactMarkdown>
                    </div>
                  </div>
                )}
              </div>

              {/* Message Footer Info */}
              <div
                className={`text-[11px] mt-1.5 flex items-center gap-2 ${
                  isUser ? "justify-end text-text-muted" : "justify-start text-text-muted"
                }`}
              >
                <span>{format.dateTime(message.timestamp, { timeStyle: "medium" })}</span>

                {/* Auto-routed Model Chip */}
                {!isUser && message.routedModel && (
                  <span
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-ai/10 text-ai-fg border border-ai/20"
                    title={message.routeReason || undefined}
                  >
                    <span>⚡ 智能路由: {message.routedModel.split("/").pop()}</span>
                  </span>
                )}

                {/* Copy Message Button */}
                {rawContent && (
                  <button
                    onClick={() => onCopy(rawContent, index)}
                    className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-surface-hover rounded text-text-muted hover:text-text-primary"
                    title={t("actions.copy")}
                  >
                    {copiedIndex === index ? (
                      <Check className="w-3 h-3 text-emerald-500" />
                    ) : (
                      <Copy className="w-3 h-3" />
                    )}
                  </button>
                )}
              </div>
            </div>
          </div>
        );
      })}

      {/* Thinking / Streaming Indicator */}
      {thinking && (
        <div className="flex gap-3.5 animate-fadeIn">
          <div className="flex-shrink-0 w-8 h-8 sm:w-9 sm:h-9 rounded-xl bg-gradient-to-tr from-accent-600 to-indigo-600 flex items-center justify-center shadow-sm">
            <Brain className="w-4 h-4 text-white animate-pulse" />
          </div>
          <div className="bg-surface-card rounded-2xl px-4 py-3 shadow-sm border border-border-subtle flex items-center gap-2.5">
            <div className="flex gap-1">
              <span
                className="w-2 h-2 bg-ai rounded-full animate-bounce"
                style={{ animationDelay: "0ms" }}
              />
              <span
                className="w-2 h-2 bg-ai rounded-full animate-bounce"
                style={{ animationDelay: "150ms" }}
              />
              <span
                className="w-2 h-2 bg-ai rounded-full animate-bounce"
                style={{ animationDelay: "300ms" }}
              />
            </div>
            <span className="text-xs text-text-muted font-medium">正在研判与逻辑推演中...</span>
          </div>
        </div>
      )}

      <div ref={messagesEndRef} />
    </div>
  );
}
