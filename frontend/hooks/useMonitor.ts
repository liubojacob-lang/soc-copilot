'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import type { MonitorData, HistoryPoint } from '@/lib/monitor';

interface UseMonitorReturn {
  data: MonitorData | null;
  history: HistoryPoint[];
  connected: boolean;
  error: string | null;
  reconnect: () => void;
  connectionType: 'sse' | 'polling' | 'disconnected';
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
  const [connectionType, setConnectionType] = useState<'sse' | 'polling' | 'disconnected'>('disconnected');

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
      console.log(`[Monitor] Fetching history for last ${minutes} minutes...`);
      const response = await fetch(`/api/monitor/history?minutes=${minutes}`, {
        credentials: 'include',
        cache: 'no-store',
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      console.log('[Monitor] History API response:', {
        pointsCount: result.history?.length,
        metadata: result.metadata,
        firstPoint: result.history?.[0],
        lastPoint: result.history?.[result.history?.length - 1],
      });

      if (mountedRef.current && result.history && Array.isArray(result.history)) {
        historyRef.current = result.history;
        setHistory(result.history);

        // Save to localStorage
        try {
          if (typeof window !== 'undefined' && window.localStorage) {
            localStorage.setItem('monitor_history', JSON.stringify({
              timestamp: Date.now(),
              data: result.history,
            }));
          }
        } catch (err) {
          console.warn('[Monitor] Failed to cache history:', err);
        }

        console.log(`[Monitor] ✓ History loaded and set: ${result.history.length} points`);
      } else {
        console.warn('[Monitor] History data invalid or component unmounted:', {
          mounted: mountedRef.current,
          hasHistory: !!result.history,
          isArray: Array.isArray(result.history),
        });
      }
    } catch (err) {
      console.error('[Monitor] Failed to load history:', err);
    }
  }, []);

  // Fetch data via HTTP polling (fallback)
  const fetchData = useCallback(async () => {
    try {
      const response = await fetch('/api/monitor/snapshot', {
        credentials: 'include',
        cache: 'no-store',
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
            }
          };
          
          // Check if this timestamp already exists
          const exists = historyRef.current.some(
            h => h.timestamp === newPoint.timestamp
          );
          
          if (!exists) {
            historyRef.current = [...historyRef.current, newPoint];
            // Keep only last 720 points (1 hour at 5-second intervals)
            if (historyRef.current.length > 720) {
              historyRef.current = historyRef.current.slice(-720);
            }
            setHistory(historyRef.current);

            // Save to localStorage for instant reload
            try {
              if (typeof window !== 'undefined' && window.localStorage) {
                localStorage.setItem('monitor_history', JSON.stringify({
                  timestamp: Date.now(),
                  data: historyRef.current,
                }));
              }
            } catch (err) {
              console.warn('[Monitor] Failed to cache history:', err);
            }
          }
        }
        
        console.log('[Monitor] Polling: Data received');
      }
    } catch (err) {
      if (mountedRef.current) {
        const message = err instanceof Error ? err.message : 'Polling failed';
        console.error('[Monitor] Polling error:', err);
        setError(message);
        connectedRef.current = false;
        setConnected(false);
      }
    }
  }, []);

  // Start HTTP polling
  const startPolling = useCallback(() => {
    console.log('[Monitor] Switching to HTTP polling mode');
    setConnectionType('polling');
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
    console.log('[Monitor] Attempting SSE connection');
    setConnectionType('sse');
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
      const eventSource = new EventSource('/api/monitor/stream');

      eventSource.onopen = () => {
        if (!mountedRef.current) return;
        console.log('[Monitor] ✓ SSE connection established');
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
            console.error('[Monitor] Server error:', parsedData.error);
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
              }
            };
            
            // Check if this timestamp already exists
            const exists = historyRef.current.some(
              h => h.timestamp === newPoint.timestamp
            );
            
            if (!exists) {
              historyRef.current = [...historyRef.current, newPoint];
              // Keep only last 720 points (1 hour at 5-second intervals)
              if (historyRef.current.length > 720) {
                historyRef.current = historyRef.current.slice(-720);
              }
              setHistory(historyRef.current);

              // Save to localStorage
              try {
                if (typeof window !== 'undefined' && window.localStorage) {
                  localStorage.setItem('monitor_history', JSON.stringify({
                    timestamp: Date.now(),
                    data: historyRef.current,
                  }));
                }
              } catch (err) {
                console.warn('[Monitor] Failed to cache history:', err);
              }
            }
          }
        } catch (err) {
          console.error('[Monitor] Failed to parse SSE data:', err);
        }
      };

      eventSource.onerror = (err) => {
        if (!mountedRef.current) return;

        console.error('[Monitor] SSE connection error:', err);
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
          console.log(`[Monitor] SSE failed ${sseFailureCount.current} times, switching to polling`);
          setError('SSE unavailable, using polling');
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
            console.log('[Monitor] Reconnecting SSE...');
            startSSE();
          }
        }, SSE_RECONNECT_DELAY);
      };

      eventSourceRef.current = eventSource;
    } catch (err) {
      console.error('[Monitor] Failed to create EventSource:', err);
      setError('Failed to create SSE connection');
      startPolling(); // Fall back to polling
    }
  }, [startPolling]);

  // Manual reconnect
  const reconnect = useCallback(() => {
    console.log('[Monitor] Manual reconnect requested');
    sseFailureCount.current = 0; // Reset failure count
    startSSE(); // Try SSE first
  }, [startSSE]);

  // Initialize connection with immediate snapshot for faster initial load
  useEffect(() => {
    mountedRef.current = true;

    // 🔥 Speed optimization: Load history from localStorage first (instant)
    // IMPORTANT: Only access localStorage on client-side to avoid hydration errors
    const loadCachedHistory = () => {
      try {
        if (typeof window === 'undefined' || !window.localStorage) {
          return false;
        }
        const cached = localStorage.getItem('monitor_history');
        if (cached) {
          const parsed = JSON.parse(cached);
          // Only use cache if it's recent (last 5 minutes)
          const cacheAge = Date.now() - parsed.timestamp;
          if (cacheAge < 5 * 60 * 1000 && Array.isArray(parsed.data) && parsed.data.length > 0) {
            console.log('[Monitor] ✅ Using cached history:', parsed.data.length, 'points');
            historyRef.current = parsed.data;
            setHistory(parsed.data);
            return true;
          }
        }
      } catch (err) {
        console.warn('[Monitor] Failed to load cached history:', err);
      }
      return false;
    };

    // 🔥 Speed optimization: Fetch initial data immediately via snapshot
    // This shows data quickly while SSE is connecting
    const loadInitialData = async () => {
      const startTime = Date.now();

      try {
        // Try to load from cache first for instant display
        const hasCached = loadCachedHistory();

        // Then fetch fresh history from server
        console.log('[Monitor] 📊 Loading history data...');
        await fetchHistory(60); // Load last 60 minutes of history

        // Then load current snapshot
        console.log('[Monitor] ⚡ Loading initial data...');
        const response = await fetch('/api/monitor/snapshot', {
          credentials: 'include',
          cache: 'no-store',
        });

        if (response.ok) {
          const result = await response.json();
          if (mountedRef.current) {
            setData(result);
            setError(null);
            connectedRef.current = true;
            setConnected(true);
            
            // Add current data to history if not already present
            if (result.timestamp && result.resources) {
              const newPoint: HistoryPoint = {
                timestamp: result.timestamp,
                resources: result.resources,
                services: {
                  database: result.services.database.status,
                  redis: result.services.redis.status,
                  ai: result.services.ai.status,
                  queue: result.services.queue.status,
                }
              };
              
              const exists = historyRef.current.some(
                h => h.timestamp === newPoint.timestamp
              );
              
              if (!exists) {
                historyRef.current = [...historyRef.current, newPoint];
                setHistory(historyRef.current);
              }
            }
            
            console.log('[Monitor] ✅ Initial data loaded in', Date.now() - startTime, 'ms');
          }
        }
      } catch (err) {
        console.error('[Monitor] Initial data load failed:', err);
      }
    };

    // Load initial data immediately
    loadInitialData();

    // Then start SSE for real-time updates
    startSSE();

    return () => {
      mountedRef.current = false;

      // Clean up all connections
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
      if (document.visibilityState === 'visible') {
        console.log('[Monitor] Page visible, resuming connection');
        if (!connectedRef.current) {
          reconnect();
        }
      } else {
        console.log('[Monitor] Page hidden, connection continues');
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [reconnect]);

  return {
    data,
    history,
    connected,
    error,
    reconnect,
    connectionType,
    fetchHistory
  };
}
