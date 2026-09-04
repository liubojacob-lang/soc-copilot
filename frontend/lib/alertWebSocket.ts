/**
 * Wazuh Real-time Alert Stream WebSocket Client
 *
 * Handles WebSocket connection for real-time Wazuh alerts with:
 * - Auto-reconnection with exponential backoff
 * - Message filtering and routing
 * - Connection health monitoring
 * - Subscription management
 */

import { WebSocketMessage, AlertData, StreamStats, AlertFilter } from "@/types/wazuh";

export type WazuhMessageHandler = (data: AlertData) => void;
export type ConnectionChangeHandler = (connected: boolean) => void;
export type ErrorHandler = (error: Error) => void;

export interface WazuhWebSocketConfig {
  url?: string;
  token?: string;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  heartbeatInterval?: number;
  enableAggregation?: boolean;
  filters?: AlertFilter;
}

export interface WazuhWebSocketState {
  connected: boolean;
  connecting: boolean;
  reconnectAttempts: number;
  isManualClose: boolean;
  lastMessageTime?: Date;
  lastError?: Error;
}

const DEFAULT_CONFIG: Required<Omit<WazuhWebSocketConfig, "token" | "filters">> = {
  url: "",
  reconnectInterval: 3000,
  maxReconnectAttempts: 10,
  heartbeatInterval: 30000,
  enableAggregation: true,
};

// Internal config type that allows optional token and filters
type InternalConfig = Required<Omit<WazuhWebSocketConfig, "token" | "filters">> & {
  token?: string;
  filters?: AlertFilter;
};

/**
 * Wazuh WebSocket Client for Real-time Alert Streaming
 */
export class WazuhWebSocketClient {
  private ws: WebSocket | null = null;
  private config: InternalConfig;
  private state: WazuhWebSocketState;
  private handlers: Map<string, Set<WazuhMessageHandler>>;
  private connectionHandlers: Set<ConnectionChangeHandler>;
  private errorHandlers: Set<ErrorHandler>;
  private heartbeatTimer: NodeJS.Timeout | null = null;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private messageQueue: WebSocketMessage[] = [];
  private isManualClose = false;

  constructor(config: WazuhWebSocketConfig = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
    this.state = {
      connected: false,
      connecting: false,
      reconnectAttempts: 0,
      isManualClose: false,
    };
    this.handlers = new Map();
    this.connectionHandlers = new Set();
    this.errorHandlers = new Set();

    // Set default URL if not provided
    if (!this.config.url) {
      // Use NEXT_PUBLIC_WS_URL if available, otherwise derive from API_URL
      const wsUrl = process.env.NEXT_PUBLIC_WS_URL;
      const wsPath = process.env.NEXT_PUBLIC_WS_ALERTS_PATH || "/ws/alerts";
      if (wsUrl) {
        this.config.url = wsUrl.includes("/ws/") ? wsUrl : `${wsUrl.replace(/\/$/, "")}${wsPath}`;
      } else if (typeof window !== "undefined") {
        // Browser: derive same-origin WebSocket URL from current location.
        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        this.config.url = `${protocol}//${window.location.host}${wsPath}`;
      } else {
        // Server-side fallback (SSR): use internal API URL.
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const wsProtocolUrl = apiUrl.replace("http://", "ws://").replace("https://", "wss://");
        this.config.url = `${wsProtocolUrl.replace(/\/$/, "")}${wsPath}`;
      }
    }
  }

  /**
   * Connect to WebSocket server
   *
   * Auth: token (if available) is passed via the Sec-WebSocket-Protocol
   * header, never via the URL (query params leak into logs/history).
   * Without a token the cookie-authenticated session is used — the browser
   * attaches same-site cookies to the handshake and the backend falls back
   * to the access_token cookie.
   */
  connect(token?: string): void {
    if (this.state.connecting || this.state.connected) {
      return;
    }

    if (token) {
      this.config.token = token;
    }

    this.state.connecting = true;
    this.isManualClose = false;

    try {
      const wsUrl = new URL(this.config.url);
      wsUrl.searchParams.set("channels", "wazuh");

      this.ws = this.config.token
        ? new WebSocket(wsUrl.toString(), `access_token.${this.config.token}`)
        : new WebSocket(wsUrl.toString());

      this.ws.onopen = this.handleOpen.bind(this);
      this.ws.onmessage = this.handleMessage.bind(this);
      this.ws.onerror = this.handleError.bind(this);
      this.ws.onclose = this.handleClose.bind(this);
    } catch (error) {
      this.state.connecting = false;
      this.notifyError(error as Error);
      this.scheduleReconnect();
    }
  }

  /**
   * Disconnect from WebSocket server
   */
  disconnect(): void {
    this.isManualClose = true;
    this.stopHeartbeat();
    this.clearReconnectTimer();

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    this.state.connected = false;
    this.state.connecting = false;
    this.notifyConnectionChange(false);
  }

  /**
   * Subscribe to alert messages
   */
  onAlert(handler: WazuhMessageHandler): () => void {
    if (!this.handlers.has("alert")) {
      this.handlers.set("alert", new Set());
    }
    this.handlers.get("alert")!.add(handler);

    // Return unsubscribe function
    return () => {
      this.handlers.get("alert")?.delete(handler);
    };
  }

  /**
   * Subscribe to aggregated alert messages
   */
  onAggregatedAlert(handler: WazuhMessageHandler): () => void {
    if (!this.handlers.has("aggregated_alert")) {
      this.handlers.set("aggregated_alert", new Set());
    }
    this.handlers.get("aggregated_alert")!.add(handler);

    return () => {
      this.handlers.get("aggregated_alert")?.delete(handler);
    };
  }

  /**
   * Subscribe to system messages
   */
  onSystemMessage(handler: WazuhMessageHandler): () => void {
    if (!this.handlers.has("system")) {
      this.handlers.set("system", new Set());
    }
    this.handlers.get("system")!.add(handler);

    return () => {
      this.handlers.get("system")?.delete(handler);
    };
  }

  /**
   * Subscribe to connection state changes
   */
  onConnectionChange(handler: ConnectionChangeHandler): () => void {
    this.connectionHandlers.add(handler);
    handler(this.state.connected);

    return () => {
      this.connectionHandlers.delete(handler);
    };
  }

  /**
   * Subscribe to errors
   */
  onError(handler: ErrorHandler): () => void {
    this.errorHandlers.add(handler);

    return () => {
      this.errorHandlers.delete(handler);
    };
  }

  /**
   * Update subscription filters
   */
  updateFilters(filters: Partial<AlertFilter>): void {
    this.config.filters = { ...this.config.filters, ...filters };

    if (this.state.connected && this.ws) {
      this.send({
        type: "subscribe",
        data: { filters: this.config.filters },
        timestamp: new Date().toISOString(),
      });
    }
  }

  /**
   * Get current connection state
   */
  getState(): Readonly<WazuhWebSocketState> {
    return { ...this.state, isManualClose: this.isManualClose };
  }

  /**
   * Send a message through WebSocket
   */
  private send(message: WebSocketMessage): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      // Queue message for when connection is established
      this.messageQueue.push(message);
    }
  }

  /**
   * Handle WebSocket open event
   */
  private handleOpen(): void {
    this.state.connected = true;
    this.state.connecting = false;
    this.state.reconnectAttempts = 0;
    this.state.lastError = undefined;

    this.notifyConnectionChange(true);

    // Send queued messages
    while (this.messageQueue.length > 0) {
      const message = this.messageQueue.shift();
      if (message) {
        this.send(message);
      }
    }

    // Apply initial filters
    if (this.config.filters) {
      this.send({
        type: "subscribe",
        data: { filters: this.config.filters },
        timestamp: new Date().toISOString(),
      });
    }

    // Start heartbeat
    this.startHeartbeat();
  }

  /**
   * Handle WebSocket message event
   */
  private handleMessage(event: MessageEvent): void {
    try {
      const message: WebSocketMessage = JSON.parse(event.data);
      this.state.lastMessageTime = new Date();

      // Handle ping/pong
      if (message.type === "ping") {
        this.send({
          type: "pong",
          data: { timestamp: new Date().toISOString() },
          timestamp: new Date().toISOString(),
        });
        return;
      }

      if (message.type === "pong") {
        return; // Ignore pong responses
      }

      // Route message to appropriate handlers
      const handlers = this.handlers.get(message.type);
      if (handlers) {
        handlers.forEach((handler) => {
          try {
            handler(message.data as AlertData);
          } catch (error) {
            console.error("[WazuhWebSocket] Handler error:", error);
          }
        });
      }

      // Also route to wildcard 'alert' handlers for aggregated_alert
      if (message.type === "aggregated_alert") {
        const alertHandlers = this.handlers.get("alert");
        if (alertHandlers) {
          alertHandlers.forEach((handler) => {
            try {
              handler(message.data as AlertData);
            } catch (error) {
              console.error("[WazuhWebSocket] Handler error:", error);
            }
          });
        }
      }
    } catch (error) {
      console.error("[WazuhWebSocket] Message parse error:", error);
    }
  }

  /**
   * Handle WebSocket error event
   */
  private handleError(event: Event): void {
    const error = new Error("WebSocket error occurred");
    this.state.lastError = error;
    this.notifyError(error);
  }

  /**
   * Handle WebSocket close event
   */
  private handleClose(event: CloseEvent): void {
    this.state.connected = false;
    this.state.connecting = false;
    this.ws = null;

    this.stopHeartbeat();
    this.notifyConnectionChange(false);

    if (!this.isManualClose) {
      this.scheduleReconnect();
    }
  }

  /**
   * Schedule reconnection attempt
   */
  private scheduleReconnect(): void {
    if (this.isManualClose) {
      return;
    }

    if (this.state.reconnectAttempts >= this.config.maxReconnectAttempts) {
      const error = new Error("Max reconnection attempts reached");
      this.notifyError(error);
      return;
    }

    // Exponential backoff
    const delay = this.config.reconnectInterval * Math.pow(2, this.state.reconnectAttempts);

    this.reconnectTimer = setTimeout(() => {
      this.state.reconnectAttempts++;
      this.connect();
    }, delay);
  }

  /**
   * Clear reconnection timer
   */
  private clearReconnectTimer(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  /**
   * Start heartbeat timer
   */
  private startHeartbeat(): void {
    this.stopHeartbeat();

    this.heartbeatTimer = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.send({
          type: "ping",
          data: {},
          timestamp: new Date().toISOString(),
        });
      }
    }, this.config.heartbeatInterval);
  }

  /**
   * Stop heartbeat timer
   */
  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  /**
   * Notify connection state change
   */
  private notifyConnectionChange(connected: boolean): void {
    this.connectionHandlers.forEach((handler) => {
      try {
        handler(connected);
      } catch (error) {
        console.error("[WazuhWebSocket] Connection handler error:", error);
      }
    });
  }

  /**
   * Notify error
   */
  private notifyError(error: Error): void {
    this.errorHandlers.forEach((handler) => {
      try {
        handler(error);
      } catch (err) {
        console.error("[WazuhWebSocket] Error handler error:", err);
      }
    });
  }
}

/**
 * Create a singleton Wazuh WebSocket client instance
 */
let wazuhWsClient: WazuhWebSocketClient | null = null;

export function getWazuhWebSocketClient(config?: WazuhWebSocketConfig): WazuhWebSocketClient {
  if (!wazuhWsClient) {
    wazuhWsClient = new WazuhWebSocketClient(config);
  } else if (config) {
    // Update config if provided
    Object.assign(wazuhWsClient["config"], config);
  }
  return wazuhWsClient;
}

export function resetWazuhWebSocketClient(): void {
  if (wazuhWsClient) {
    wazuhWsClient.disconnect();
    wazuhWsClient = null;
  }
}
