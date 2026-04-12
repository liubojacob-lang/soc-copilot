"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import type { MonitorData, HistoryPoint } from "@/lib/monitor";

interface UseMonitorReturn {
  data: MonitorData | null;
  history: HistoryPoint[];
  connected: boolean;
  error: string | null;
  reconnect: () => void;
  connectionType: "sse" | "polling" | "disconnected";
  fetchHistory: (minutes: number) => Promise<void>;
}

// Configuration
const SSE_RECONNECT_DELAY = 3000; // 3 seconds
const MAX_SSE_FAILURES = 3; // After 3 failures, switch to polling
const POLLING_INTERVAL = 5000; // 5 seconds

export function useMonitor(): UseMonitorReturn {
  const [data, setData] = useState<MonitorData | null>(null);
  const [history, setHistory] = useState<HistoryPoint[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [connectionType, setConnectionType] = useState<"sse" | "polling" | "disconnected">(
    "disconnected"
  );

  const eventSourceRef = useRef<EventSource | null>(null);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const sseFailureCount = useRef<number>(0);
  const mountedRef = useRef<boolean>(true);
  const connectedRef = useRef<boolean>(false);
  const historyRef = useRef<HistoryPoint[]>([]);

  // Fetch historical data
  const fetchHistory = useCallback(async (minutes: number = 60) => {
    try {
      const response = await fetch(`/api/monitor/history?minutes=${minutes}`, {
        credentials: "include",
        cache: "no-store",
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();

      if (mountedRef.current && result.history && Array.isArray(result.history)) {
        historyRef.current = result.history;
        setHistory(result.history);

        // Save to localStorage
        try {
          if (typeof window !== "undefined" && window.localStorage) {
            localStorage.setItem(
              "monitor_history",
              JSON.stringify({
                timestamp: Date.now(),
                data: result.history,
              })
            );
          }
        } catch (err) {
          console.warn("[Monitor] Failed to cache history:", err);
        }
      } else {
        console.warn("[Monitor] History data invalid or component unmounted:", {
          mounted: mountedRef.current,
          hasHistory: !!result.history,
          isArray: Array.isArray(result.history),
        });
      }
    } catch (err) {
      console.error("[Monitor] Failed to load history:", err);
    }
  }, []);

  // Fetch data via HTTP polling (fallback)
  const fetchData = useCallback(async () => {
    try {
      const response = await fetch("/api/monitor/snapshot", {
        credentials: "include",
        cache: "no-store",
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();

      if (mountedRef.current) {
        setData(result);
        setError(null);
        connectedRef.current = true;
        setConnected(true);

        // Add to history if it's new data
        if (result.timestamp) {
          const newPoint: HistoryPoint = {
            timestamp: result.timestamp,
            resources: result.resources,
            services: {
              database: result.services.database.status,
              redis: result.services.redis.status,
              ai: result.services.ai.status,
              queue: result.services.queue.status,
            },
          };

          // Check if this timestamp already exists
          const exists = historyRef.current.some((h) => h.timestamp === newPoint.timestamp);

          if (!exists) {
            historyRef.current = [...historyRef.current, newPoint];
            // Keep only last 720 points (1 hour at 5-second intervals)
            if (historyRef.current.length > 720) {
              historyRef.current = historyRef.current.slice(-720);
            }
            setHistory(historyRef.current);

            // Save to localStorage for instant reload
            try {
              if (typeof window !== "undefined" && window.localStorage) {
                localStorage.setItem(
                  "monitor_history",
                  JSON.stringify({
                    timestamp: Date.now(),
                    data: historyRef.current,
                  })
                );
              }
            } catch (err) {
              console.warn("[Monitor] Failed to cache history:", err);
            }
          }
        }
      }
    } catch (err) {
      if (mountedRef.current) {
        const message = err instanceof Error ? err.message : "Polling failed";
        console.error("[Monitor] Polling error:", err);
        setError(message);
        connectedRef.current = false;
        setConnected(false);
      }
    }
  }, []);

  // Start HTTP polling
  const startPolling = useCallback(() => {
    setConnectionType("polling");
    sseFailureCount.current = 0;

    // Clear any existing SSE connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    // Immediate fetch
    fetchData();

    // Set up interval
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
    }
    pollingIntervalRef.current = setInterval(fetchData, POLLING_INTERVAL);
  }, [fetchData]);

  // Start SSE connection
  const startSSE = useCallback(() => {
    setConnectionType("sse");
    setError(null);

    // Clear any polling
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }

    // Close existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    try {
      // Use Next.js rewrite to proxy SSE (works after fixing .env.local)
      const eventSource = new EventSource("/api/monitor/stream");

      eventSource.onopen = () => {
        if (!mountedRef.current) return;
        connectedRef.current = true;
        setConnected(true);
        setError(null);
        sseFailureCount.current = 0; // Reset failure count
      };

      eventSource.onmessage = (event) => {
        if (!mountedRef.current) return;

        try {
          const parsedData: MonitorData = JSON.parse(event.data);

          if (parsedData.heartbeat) {
            // Heartbeat received, connection is alive
            if (!connectedRef.current) {
              connectedRef.current = true;
              setConnected(true);
            }
            return;
          }

          if (parsedData.error) {
            console.error("[Monitor] Server error:", parsedData.error);
            setError(parsedData.error);
            return;
          }

          // Valid data received
          setData(parsedData);
          connectedRef.current = true;
          setConnected(true);
          sseFailureCount.current = 0; // Reset on successful data

          // Add to history if it's new data
          if (parsedData.timestamp && parsedData.resources) {
            const newPoint: HistoryPoint = {
              timestamp: parsedData.timestamp,
              resources: parsedData.resources,
              services: {
                database: parsedData.services.database.status,
                redis: parsedData.services.redis.status,
                ai: parsedData.services.ai.status,
                queue: parsedData.services.queue.status,
              },
            };

            // Check if this timestamp already exists
            const exists = historyRef.current.some((h) => h.timestamp === newPoint.timestamp);

            if (!exists) {
              historyRef.current = [...historyRef.current, newPoint];
              // Keep only last 720 points (1 hour at 5-second intervals)
              if (historyRef.current.length > 720) {
                historyRef.current = historyRef.current.slice(-720);
              }
              setHistory(historyRef.current);

              // Save to localStorage
              try {
                if (typeof window !== "undefined" && window.localStorage) {
                  localStorage.setItem(
                    "monitor_history",
                    JSON.stringify({
                      timestamp: Date.now(),
                      data: historyRef.current,
                    })
                  );
                }
              } catch (err) {
                console.warn("[Monitor] Failed to cache history:", err);
              }
            }
          }
        } catch (err) {
          console.error("[Monitor] Failed to parse SSE data:", err);
        }
      };

      eventSource.onerror = (err) => {
        if (!mountedRef.current) return;

        console.error("[Monitor] SSE connection error:", err);
        sseFailureCount.current++;

        // Close the failed connection
        if (eventSourceRef.current) {
          eventSourceRef.current.close();
          eventSourceRef.current = null;
        }

        connectedRef.current = false;
        setConnected(false);

        // Check if we should switch to polling
        if (sseFailureCount.current >= MAX_SSE_FAILURES) {
          setError("SSE unavailable, using polling");
          startPolling();
          return;
        }

        // Attempt reconnection after delay
        setError(`Connection failed (retry ${sseFailureCount.current}/${MAX_SSE_FAILURES})`);

        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
        }
        reconnectTimeoutRef.current = setTimeout(() => {
          if (mountedRef.current) {
            startSSE();
          }
        }, SSE_RECONNECT_DELAY);
      };

      eventSourceRef.current = eventSource;
    } catch (err) {
      console.error("[Monitor] Failed to create EventSource:", err);
      setError("Failed to create SSE connection");
      startPolling(); // Fall back to polling
    }
  }, [startPolling]);

  // Manual reconnect
  const reconnect = useCallback(() => {
    sseFailureCount.current = 0; // Reset failure count
    startSSE(); // Try SSE first
  }, [startSSE]);

  // Initialize connection with localStorage cache for instant display
  useEffect(() => {
    mountedRef.current = true;

    // Load cached history from localStorage for instant display
    try {
      if (typeof window !== "undefined" && window.localStorage) {
        const cached = localStorage.getItem("monitor_history");
        if (cached) {
          const parsed = JSON.parse(cached);
          const cacheAge = Date.now() - parsed.timestamp;
          if (cacheAge < 5 * 60 * 1000 && Array.isArray(parsed.data) && parsed.data.length > 0) {
            historyRef.current = parsed.data;
            setHistory(parsed.data);
          }
        }
      }
    } catch (err) {
      // Ignore localStorage errors
    }

    // Fetch history in parallel with SSE (non-blocking)
    fetchHistory(60);

    // Start SSE — it provides current snapshot + real-time updates
    // No need for a separate /api/monitor/snapshot call
    startSSE();

    return () => {
      mountedRef.current = false;

      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
    };
  }, [startSSE]);

  // Handle visibility change (pause/resume)
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        if (!connectedRef.current) {
          reconnect();
        }
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [reconnect]);

  return {
    data,
    history,
    connected,
    error,
    reconnect,
    connectionType,
    fetchHistory,
  };
}
