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
  const maxRetries = 5;

  // 频道、回调与重试计数经 ref 透传：父组件每次渲染传入的新数组/新函数
  // 不能改变 connect 的身份，否则下方 effect 会让 WebSocket 反复断开重连。
  const channelsRef = useRef(channels);
  const retryCountRef = useRef(0);
  const connectRef = useRef<() => void>(() => {});
  const callbacksRef = useRef({
    onAlert,
    onPlaybookRun,
    onSystemMessage,
    onConnect,
    onDisconnect,
    onError,
  });
  channelsRef.current = channels;
  callbacksRef.current = {
    onAlert,
    onPlaybookRun,
    onSystemMessage,
    onConnect,
    onDisconnect,
    onError,
  };

  const connect = useCallback(() => {
    if (!enabled) {
      return;
    }

    const token = getAccessToken();

    // Token is optional: with the cookie auth flow there is no JS-readable
    // token, and the backend authenticates the WS handshake via the
    // access_token cookie (sent automatically on the same-site handshake).
    if (!token && typeof document !== "undefined" && !document.cookie.includes("csrf_token")) {
      // No token AND no cookies at all — nothing to authenticate with.
      console.warn("[AlertWebSocket] No credentials available");
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
      const channelParam = channelsRef.current.join(",");

      // Pass token via Sec-WebSocket-Protocol to avoid URL exposure in logs/history.
      // Backend must extract token from the Sec-WebSocket-Protocol header.
      // Query parameter channels are acceptable (non-sensitive).
      // Cookie-authenticated sessions (no JS-readable token) omit the
      // subprotocol; the backend falls back to the access_token cookie.
      const ws = token
        ? new WebSocket(`${wsUrl}?channels=${channelParam}`, `access_token.${token}`)
        : new WebSocket(`${wsUrl}?channels=${channelParam}`);

      ws.onopen = () => {
        setConnectionStatus("connected");
        retryCountRef.current = 0;
        callbacksRef.current.onConnect?.();
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          const cb = callbacksRef.current;

          switch (message.type) {
            case "alert":
              cb.onAlert?.(message.data);
              break;
            case "playbook_run":
              cb.onPlaybookRun?.(message.data);
              break;
            case "system":
              cb.onSystemMessage?.(message.data);
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
              cb.onError?.(
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
        callbacksRef.current.onError?.(new Error("WebSocket connection error"));
      };

      ws.onclose = (event) => {
        setConnectionStatus("disconnected");
        wsRef.current = null;
        callbacksRef.current.onDisconnect?.();

        // 自动重连（指数退避）
        if (enabled && retryCountRef.current < maxRetries) {
          const retryDelay = Math.min(1000 * Math.pow(2, retryCountRef.current), 30000);
          reconnectTimeoutRef.current = setTimeout(() => {
            retryCountRef.current += 1;
            connectRef.current();
          }, retryDelay);
        }
      };

      wsRef.current = ws;
    } catch (error) {
      console.error("[AlertWebSocket] Failed to create WebSocket:", error);
      setConnectionStatus("disconnected");
      callbacksRef.current.onError?.(error as Error);
    }
  }, [enabled]);

  connectRef.current = connect;

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
