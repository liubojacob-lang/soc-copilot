"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { loadAuthState } from "@/lib/auth";
import Navigation from "@/components/Navigation";
import { 
  Brain, 
  AlertTriangle, 
  Lightbulb, 
  FileText, 
  Send, 
  Loader2,
  Sparkles
} from "lucide-react";

interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

export default function AIAssistantPage() {
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "Hello! I'm **SOC Copilot AI** 🤖\n\nI can help you with:\n\n🔍 **Alert Analysis** - Intelligent analysis of security alerts\n💡 **Playbook Recommendations** - Suggest best response playbooks\n❓ **Natural Language Queries** - Query SOC data in plain English\n📊 **Report Generation** - Auto-generate investigation reports\n\nWhat would you like me to help you with?",
      timestamp: new Date()
    }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [aiStatus, setAiStatus] = useState<any>(null);

  useEffect(() => {
    setMounted(true);
    checkAIStatus();
  }, []);

  const checkAIStatus = async () => {
    try {
      const response = await api.get("/api/ai/status");
      setAiStatus(response.data);
    } catch (e) {
      console.error("Failed to check AI status:", e);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput("");
    
    setMessages(prev => [...prev, {
      role: "user",
      content: userMessage,
      timestamp: new Date()
    }]);

    setLoading(true);

    try {
      const queryResponse = await api.post("/api/ai/query", {
        query: userMessage
      });

      if (queryResponse.data.intent && queryResponse.data.intent !== "unknown") {
        setMessages(prev => [...prev, {
          role: "assistant",
          content: queryResponse.data.response,
          timestamp: new Date()
        }]);
      } else {
        const chatResponse = await api.post("/api/ai/chat", {
          message: userMessage,
          conversation_history: messages.slice(-5).map(m => ({
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
        content: `❌ Sorry, I encountered an error: ${error.message || "Unknown error"}`,
        timestamp: new Date()
      }]);
    } finally {
      setLoading(false);
    }
  };

  const quickActions = [
    { icon: AlertTriangle, label: "Analyze Latest Alert", query: "Analyze the most recent high severity alert" },
    { icon: Lightbulb, label: "Recommend Playbooks", query: "Recommend playbooks for current alerts" },
    { icon: FileText, label: "Generate Report", query: "Generate analysis report for recent events" },
    { icon: Brain, label: "Threat Hunting Tips", query: "Give me some threat hunting suggestions" },
  ];

  if (!mounted) return null;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Navigation title="AI Copilot" />
      
      <main className="pt-16 pb-8">
        <div className="max-w-6xl mx-auto px-4">
          {/* Header */}
          <div className="mb-6">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl">
                <Brain className="w-8 h-8 text-white" />
              </div>
              <div>
                <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                  SOC Copilot AI
                </h1>
                <p className="text-gray-600 dark:text-gray-400 flex items-center gap-2">
                  Intelligent Security Assistant
                  {aiStatus?.status === "available" ? (
                    <span className="flex items-center gap-1 text-green-600 text-sm">
                      <Sparkles className="w-4 h-4" />
                      AI Ready
                    </span>
                  ) : (
                    <span className="text-amber-600 text-sm">AI Not Configured</span>
                  )}
                </p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Chat Interface */}
            <div className="lg:col-span-2">
              <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
                {/* Messages */}
                <div className="h-[500px] overflow-y-auto p-4 space-y-4">
                  {messages.map((message, index) => (
                    <div
                      key={index}
                      className={`flex gap-3 ${message.role === "user" ? "flex-row-reverse" : ""}`}
                    >
                      <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center ${
                        message.role === "user"
                          ? "bg-blue-100 dark:bg-blue-900"
                          : "bg-gradient-to-br from-blue-500 to-purple-600"
                      }`}>
                        {message.role === "user" ? (
                          <span className="text-blue-600 dark:text-blue-400 font-semibold">You</span>
                        ) : (
                          <Brain className="w-5 h-5 text-white" />
                        )}
                      </div>
                      <div className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                        message.role === "user"
                          ? "bg-blue-600 text-white"
                          : "bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                      }`}>
                        <div className="text-sm whitespace-pre-wrap">{message.content}</div>
                        <div className={`text-xs mt-1 opacity-70`}>
                          {message.timestamp.toLocaleTimeString()}
                        </div>
                      </div>
                    </div>
                  ))}
                  
                  {loading && (
                    <div className="flex gap-3">
                      <div className="flex-shrink-0 w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                        <Brain className="w-5 h-5 text-white" />
                      </div>
                      <div className="bg-gray-100 dark:bg-gray-700 rounded-2xl px-4 py-3">
                        <Loader2 className="w-5 h-5 animate-spin text-blue-600" />
                      </div>
                    </div>
                  )}
                </div>

                {/* Input */}
                <form onSubmit={handleSubmit} className="p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      placeholder="Type your question, e.g., analyze the latest alert..."
                      className="flex-1 px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
                      disabled={loading}
                    />
                    <button
                      type="submit"
                      disabled={loading || !input.trim()}
                      className="px-6 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
                    >
                      <Send className="w-5 h-5" />
                      Send
                    </button>
                  </div>
                </form>
              </div>
            </div>

            {/* Sidebar */}
            <div className="space-y-6">
              {/* Quick Actions */}
              <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4">
                <h3 className="font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-amber-500" />
                  Quick Actions
                </h3>
                <div className="space-y-2">
                  {quickActions.map((action, index) => (
                    <button
                      key={index}
                      onClick={() => setInput(action.query)}
                      className="w-full flex items-center gap-3 p-3 text-left rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                    >
                      <action.icon className="w-5 h-5 text-gray-500" />
                      <span className="text-sm text-gray-700 dark:text-gray-300">{action.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* AI Capabilities */}
              <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4">
                <h3 className="font-semibold text-gray-900 dark:text-white mb-4">
                  AI Capabilities
                </h3>
                <div className="space-y-3">
                  <div className="flex items-center gap-3">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    <span className="text-sm text-gray-600 dark:text-gray-400">Alert Analysis</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    <span className="text-sm text-gray-600 dark:text-gray-400">Natural Language Query</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    <span className="text-sm text-gray-600 dark:text-gray-400">Playbook Recommendations</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    <span className="text-sm text-gray-600 dark:text-gray-400">Report Generation</span>
                  </div>
                </div>
              </div>

              {/* Tips */}
              <div className="bg-blue-50 dark:bg-blue-900/20 rounded-xl p-4 border border-blue-200 dark:border-blue-800">
                <h4 className="font-medium text-blue-900 dark:text-blue-100 mb-2">
                  💡 Usage Tips
                </h4>
                <ul className="text-sm text-blue-800 dark:text-blue-200 space-y-1">
                  <li>• Describe your needs in natural language</li>
                  <li>• Ask about specific alert analysis</li>
                  <li>• Request various security reports</li>
                  <li>• Get response suggestions and best practices</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
