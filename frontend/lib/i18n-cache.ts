"use client";

const CACHE_PREFIX = "i18n:";
// v2: invalidate entries stored under the pre-rename "zh" locale key.
const CACHE_VERSION = "v2";
const MAX_AGE = 7 * 24 * 60 * 60 * 1000; // 7 days

interface CacheEntry {
  data: any;
  timestamp: number;
  version: string;
}

interface I18nCacheStats {
  hits: number;
  misses: number;
  preloads: number;
}

class I18nCacheManager {
  private memoryCache: Map<string, CacheEntry> = new Map();
  private loadingPromises: Map<string, Promise<any>> = new Map();
  private stats: I18nCacheStats = { hits: 0, misses: 0, preloads: 0 };

  async getTranslations(locale: string, namespace?: string): Promise<any> {
    const cacheKey = this.getCacheKey(locale, namespace);

    const memoryCached = this.memoryCache.get(cacheKey);
    if (memoryCached && this.isValid(memoryCached)) {
      this.stats.hits++;
      return memoryCached.data;
    }

    const storageCached = this.getFromStorage(cacheKey);
    if (storageCached && this.isValid(storageCached)) {
      this.memoryCache.set(cacheKey, storageCached);
      this.stats.hits++;
      return storageCached.data;
    }

    if (this.loadingPromises.has(cacheKey)) {
      return this.loadingPromises.get(cacheKey);
    }

    this.stats.misses++;
    const loadPromise = this.loadFromNetwork(locale, namespace);
    this.loadingPromises.set(cacheKey, loadPromise);

    try {
      const data = await loadPromise;
      this.setCache(cacheKey, data);
      return data;
    } finally {
      this.loadingPromises.delete(cacheKey);
    }
  }

  async preloadLocale(locale: string, namespaces?: string[]): Promise<void> {
    if (typeof window === "undefined") return;

    const tasks: Promise<void>[] = [];

    if (namespaces && namespaces.length > 0) {
      for (const ns of namespaces) {
        const cacheKey = this.getCacheKey(locale, ns);
        if (!this.memoryCache.has(cacheKey)) {
          tasks.push(
            this.getTranslations(locale, ns).then(() => {
              this.stats.preloads++;
            })
          );
        }
      }
    } else {
      const cacheKey = this.getCacheKey(locale);
      if (!this.memoryCache.has(cacheKey)) {
        tasks.push(
          this.getTranslations(locale).then(() => {
            this.stats.preloads++;
          })
        );
      }
    }

    if (tasks.length > 0 && "requestIdleCallback" in window) {
      (window as any).requestIdleCallback(() => Promise.all(tasks));
    } else if (tasks.length > 0) {
      setTimeout(() => Promise.all(tasks), 100);
    }
  }

  async switchLocale(locale: string, namespace?: string): Promise<any> {
    const cacheKey = this.getCacheKey(locale, namespace);
    const cached = this.memoryCache.get(cacheKey);

    if (cached) {
      return cached.data;
    }

    return this.getTranslations(locale, namespace);
  }

  invalidate(locale: string, namespace?: string): void {
    const cacheKey = this.getCacheKey(locale, namespace);
    this.memoryCache.delete(cacheKey);

    try {
      localStorage.removeItem(cacheKey);
    } catch {}
  }

  clearAll(): void {
    this.memoryCache.clear();
    this.stats = { hits: 0, misses: 0, preloads: 0 };

    try {
      const keysToRemove: string[] = [];
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && key.startsWith(CACHE_PREFIX)) {
          keysToRemove.push(key);
        }
      }
      keysToRemove.forEach((key) => localStorage.removeItem(key));
    } catch {}
  }

  getStats(): I18nCacheStats & { memorySize: number } {
    return {
      ...this.stats,
      memorySize: this.memoryCache.size,
    };
  }

  has(locale: string, namespace?: string): boolean {
    const cacheKey = this.getCacheKey(locale, namespace);
    return this.memoryCache.has(cacheKey);
  }

  private getCacheKey(locale: string, namespace?: string): string {
    return namespace ? `${CACHE_PREFIX}${locale}:${namespace}` : `${CACHE_PREFIX}${locale}`;
  }

  private isValid(entry: CacheEntry): boolean {
    if (entry.version !== CACHE_VERSION) {
      return false;
    }
    return Date.now() - entry.timestamp < MAX_AGE;
  }

  private getFromStorage(key: string): CacheEntry | null {
    try {
      const stored = localStorage.getItem(key);
      if (stored) {
        const parsed: CacheEntry = JSON.parse(stored);
        if (this.isValid(parsed)) {
          return parsed;
        }
        localStorage.removeItem(key);
      }
    } catch {}

    return null;
  }

  private setCache(key: string, data: any): void {
    const entry: CacheEntry = {
      data,
      timestamp: Date.now(),
      version: CACHE_VERSION,
    };

    this.memoryCache.set(key, entry);

    try {
      localStorage.setItem(key, JSON.stringify(entry));
    } catch {}
  }

  private async loadFromNetwork(locale: string, namespace?: string): Promise<any> {
    try {
      if (namespace) {
        const module = await import(`../messages/${locale}/${namespace}.json`);
        return module.default;
      }
      const module = await import(`../messages/${locale}.json`);
      return module.default;
    } catch {
      const module = await import(`../messages/${locale}.json`);
      return module.default;
    }
  }
}

export const i18nCache = new I18nCacheManager();

export type { I18nCacheStats };
