"use client";

/**
 * AlertWebSocket Component
 * 实时告警 WebSocket 连接组件
 */

import { useEffect, useRef, useState, useCallback } from "react";
import { getAccessToken } from "@/lib/auth";

interface WebSocketMessage {
  type: "alert" | "playbook_run" | "system" | "ping" | "pong" | "error";
  data: unknown;
  timestamp: string;
  channel?: string;
}

interface AlertWebSocketProps {
  onAlert?: (alert: unknown) => void;
  onPlaybookRun?: (run: unknown) => void;
  onSystemMessage?: (message: unknown) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Error) => void;
  channels?: string[];
  enabled?: boolean;
}

export function AlertWebSocket({
  onAlert,
  onPlaybookRun,
  onSystemMessage,
  onConnect,
  onDisconnect,
  onError,
  channels = ["alerts"],
  enabled = true,
}: AlertWebSocketProps) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | undefined>(undefined);
  const [connectionStatus, setConnectionStatus] = useState<
    "disconnected" | "connecting" | "connected"
  >("disconnected");
  const [retryCount, setRetryCount] = useState(0);
  const maxRetries = 5;
  const retryDelay = Math.min(1000 * Math.pow(2, retryCount), 30000); // 指数退避

  const connect = useCallback(() => {
    if (!enabled) {
      return;
    }

    const token = getAccessToken();
    if (!token) {
      console.warn("[AlertWebSocket] No access token found");
      return;
    }

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setConnectionStatus("connecting");

    try {
      const wsBase = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";
      const wsPath = process.env.NEXT_PUBLIC_WS_ALERTS_PATH || "/ws/alerts";
      const wsUrl = `${wsBase}${wsPath}`;
      const channelParam = channels.join(",");

      // Pass token via Sec-WebSocket-Protocol to avoid URL exposure in logs/history.
      // Backend must extract token from the Sec-WebSocket-Protocol header.
      // Query parameter channels are acceptable (non-sensitive).
      const ws = new WebSocket(`${wsUrl}?channels=${channelParam}`, `access_token.${token}`);

      ws.onopen = () => {
        setConnectionStatus("connected");
        setRetryCount(0);
        onConnect?.();
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);

          switch (message.type) {
            case "alert":
              onAlert?.(message.data);
              break;
            case "playbook_run":
              onPlaybookRun?.(message.data);
              break;
            case "system":
              onSystemMessage?.(message.data);
              break;
            case "ping":
              // 自动回复 pong
              ws.send(JSON.stringify({ type: "pong", data: {} }));
              break;
            case "pong":
              // 心跳响应，无需处理
              break;
            case "error":
              console.error("[AlertWebSocket] Server error:", message.data);
              onError?.(
                new Error(
                  ((message.data as Record<string, unknown>)?.message as string) ||
                    "WebSocket error"
                )
              );
              break;
          }
        } catch (error) {
          console.error("[AlertWebSocket] Failed to parse message:", error);
        }
      };

      ws.onerror = (event) => {
        console.error("[AlertWebSocket] Error:", event);
        onError?.(new Error("WebSocket connection error"));
      };

      ws.onclose = (event) => {
        setConnectionStatus("disconnected");
        wsRef.current = null;
        onDisconnect?.();

        // 自动重连
        if (enabled && retryCount < maxRetries) {
          reconnectTimeoutRef.current = setTimeout(() => {
            setRetryCount((prev) => prev + 1);
            connect();
          }, retryDelay);
        }
      };

      wsRef.current = ws;
    } catch (error) {
      console.error("[AlertWebSocket] Failed to create WebSocket:", error);
      setConnectionStatus("disconnected");
      onError?.(error as Error);
    }
  }, [
    enabled,
    channels,
    retryCount,
    onConnect,
    onDisconnect,
    onError,
    onAlert,
    onPlaybookRun,
    onSystemMessage,
  ]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setConnectionStatus("disconnected");
  }, []);

  // 订阅频道变更
  const subscribeChannels = useCallback((newChannels: string[]) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: "subscribe",
          channels: newChannels,
        })
      );
    }
  }, []);

  // 发送消息
  const sendMessage = useCallback((message: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
      return true;
    }
    return false;
  }, []);

  useEffect(() => {
    if (enabled) {
      connect();
    } else {
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [enabled, connect, disconnect]);

  // 组件卸载时清理
  useEffect(() => {
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  // 暴露方法和状态
  useEffect(() => {
    // 将方法挂载到 window 对象上，方便外部调用
    (window as unknown as Record<string, unknown>).alertWebSocket = {
      connect,
      disconnect,
      sendMessage,
      subscribeChannels,
      getStatus: () => connectionStatus,
    };
  }, [connect, disconnect, sendMessage, subscribeChannels, connectionStatus]);

  // 这个组件不渲染任何内容
  return null;
}

// Hook: 使用 AlertWebSocket
export function useAlertWebSocket(options?: {
  onAlert?: (alert: unknown) => void;
  onPlaybookRun?: (run: unknown) => void;
  onSystemMessage?: (message: unknown) => void;
  channels?: string[];
  enabled?: boolean;
}) {
  const [connectionStatus, setConnectionStatus] = useState<
    "disconnected" | "connecting" | "connected"
  >("disconnected");
  const [latestAlert, setLatestAlert] = useState<unknown>(null);

  const handleAlert = useCallback(
    (alert: unknown) => {
      setLatestAlert(alert);
      options?.onAlert?.(alert);
    },
    [options]
  );

  const handleConnect = useCallback(() => {
    setConnectionStatus("connected");
  }, []);

  const handleDisconnect = useCallback(() => {
    setConnectionStatus("disconnected");
  }, []);

  return {
    connectionStatus,
    latestAlert,
    AlertWebSocketComponent: () => (
      <AlertWebSocket
        {...options}
        onAlert={handleAlert}
        onConnect={handleConnect}
        onDisconnect={handleDisconnect}
      />
    ),
  };
}
