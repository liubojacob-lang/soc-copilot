/**
 * Frontend caching utility for API responses.
 *
 * Features:
 * - In-memory cache with TTL support
 * - Cache invalidation by key pattern
 * - Request deduplication for concurrent requests
 * - Size-based eviction
 */

export interface CacheEntry<T> {
  data: T;
  timestamp: number;
  ttl: number;
  etag?: string;
}

export interface CacheOptions {
  ttl?: number; // Time to live in milliseconds
  maxSize?: number; // Maximum number of entries
}

const DEFAULT_TTL = 5 * 60 * 1000; // 5 minutes
const DEFAULT_MAX_SIZE = 100;

class ApiCache {
  private cache = new Map<string, CacheEntry<unknown>>();
  private pendingRequests = new Map<string, Promise<unknown>>();
  private maxSize: number;

  constructor(maxSize: number = DEFAULT_MAX_SIZE) {
    this.maxSize = maxSize;
  }

  /**
   * Get cached data if valid
   */
  get<T>(key: string): T | null {
    const entry = this.cache.get(key) as CacheEntry<T> | undefined;
    if (!entry) return null;

    const now = Date.now();
    if (now - entry.timestamp > entry.ttl) {
      this.cache.delete(key);
      return null;
    }

    return entry.data;
  }

  /**
   * Set cache entry
   */
  set<T>(key: string, data: T, ttl: number = DEFAULT_TTL): void {
    // Evict oldest entries if at capacity
    if (this.cache.size >= this.maxSize) {
      const oldestKey = this.cache.keys().next().value;
      if (oldestKey) {
        this.cache.delete(oldestKey);
      }
    }

    this.cache.set(key, {
      data,
      timestamp: Date.now(),
      ttl,
    });
  }

  /**
   * Check if key exists and is valid
   */
  has(key: string): boolean {
    return this.get(key) !== null;
  }

  /**
   * Delete specific key
   */
  delete(key: string): boolean {
    return this.cache.delete(key);
  }

  /**
   * Invalidate keys matching pattern
   */
  invalidatePattern(pattern: string): number {
    let count = 0;
    const regex = new RegExp(pattern);

    for (const key of this.cache.keys()) {
      if (regex.test(key)) {
        this.cache.delete(key);
        count++;
      }
    }

    return count;
  }

  /**
   * Clear all cache
   */
  clear(): void {
    this.cache.clear();
  }

  /**
   * Get or fetch with deduplication
   * Prevents multiple identical requests from being sent simultaneously
   */
  async getOrFetch<T>(
    key: string,
    fetcher: () => Promise<T>,
    ttl: number = DEFAULT_TTL
  ): Promise<T> {
    // Check cache first
    const cached = this.get<T>(key);
    if (cached !== null) {
      return cached;
    }

    // Check for pending request
    const pending = this.pendingRequests.get(key) as Promise<T> | undefined;
    if (pending) {
      return pending;
    }

    // Start new request
    const request = fetcher()
      .then((data) => {
        this.set(key, data, ttl);
        return data;
      })
      .finally(() => {
        this.pendingRequests.delete(key);
      });

    this.pendingRequests.set(key, request);
    return request;
  }

  /**
   * Get cache statistics
   */
  getStats(): { size: number; maxSize: number; pendingRequests: number } {
    return {
      size: this.cache.size,
      maxSize: this.maxSize,
      pendingRequests: this.pendingRequests.size,
    };
  }
}

// Singleton instance
export const apiCache = new ApiCache();

// Cache key generators
export const cacheKeys = {
  playbookRuns: (params?: Record<string, string>) =>
    `playbook-runs:${JSON.stringify(params || {})}`,
  playbookRun: (id: string) => `playbook-run:${id}`,
  playbookDefinitions: (params?: Record<string, string>) =>
    `playbook-definitions:${JSON.stringify(params || {})}`,
  playbookDefinition: (id: string) => `playbook-definition:${id}`,
  threatIntel: (ioc: string, type: string) => `threat-intel:${type}:${ioc}`,
  assets: (params?: Record<string, string>) => `assets:${JSON.stringify(params || {})}`,
  aiModels: () => "ai-models",
  userSettings: () => "user-settings",
};

// Cache invalidation helpers
export const cacheInvalidators = {
  invalidatePlaybookRuns: () => apiCache.invalidatePattern("^playbook-runs:"),
  invalidatePlaybookRun: (id: string) => apiCache.delete(`playbook-run:${id}`),
  invalidatePlaybookDefinitions: () => apiCache.invalidatePattern("^playbook-definitions:"),
  invalidatePlaybookDefinition: (id: string) => apiCache.delete(`playbook-definition:${id}`),
  invalidateThreatIntel: () => apiCache.invalidatePattern("^threat-intel:"),
  invalidateAssets: () => apiCache.invalidatePattern("^assets:"),
  invalidateAll: () => apiCache.clear(),
};

export default apiCache;
