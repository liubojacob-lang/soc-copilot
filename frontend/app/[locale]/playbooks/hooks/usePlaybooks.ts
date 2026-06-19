/** Custom hook for managing playbook runs and definitions */

import { useState, useCallback, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useLocale } from "next-intl";
import { api } from "@/lib/api";
import { loadAuthState, authFetch } from "@/lib/auth";
import type { QueueStats, PlaybookMetadata } from "../constants";

interface PlaybookRunResponse {
  id: string;
  playbook_name: string;
  status: string;
  mode: string;
  started_at: string;
  finished_at: string | null;
  items?: PlaybookRunResponse[];
  total?: number;
}

interface PlaybookDefinition {
  id: string;
  name: string;
  description: string | null;
  version: string;
  status: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface UsePlaybooksData {
  runs: PlaybookRunResponse[];
  playbooks: Record<string, PlaybookMetadata>;
  definitions: PlaybookDefinition[];
  queueStats: QueueStats | null;
  loading: boolean;
  error: string | null;
}

interface PaginationState {
  currentPage: number;
  pageSize: number;
  total: number;
}

export function usePlaybooks() {
  const router = useRouter();
  const locale = useLocale();

  const [data, setData] = useState<UsePlaybooksData>({
    runs: [],
    playbooks: {},
    definitions: [],
    queueStats: null,
    loading: true,
    error: null,
  });

  const [runsPagination, setRunsPagination] = useState<PaginationState>({
    currentPage: 1,
    pageSize: 20,
    total: 0,
  });

  const [definitionsPagination, setDefinitionsPagination] = useState<PaginationState>({
    currentPage: 1,
    pageSize: 10,
    total: 0,
  });

  const [filters, setFilters] = useState({ status: "", playbook: "" });

  const loadData = useCallback(
    async (page: number = 1) => {
      setData((prev) => ({ ...prev, loading: true, error: null }));
      try {
        const [runsResponse, playbooksData] = await Promise.all([
          api.listPlaybookRuns({
            status: filters.status || undefined,
            playbook_name: filters.playbook || undefined,
            page: page,
            page_size: runsPagination.pageSize,
          }),
          api.getAvailablePlaybooks(),
        ]);

        setData((prev) => ({
          ...prev,
          runs: runsResponse.items,
          playbooks: playbooksData,
          loading: false,
        }));

        setRunsPagination({
          currentPage: page,
          pageSize: runsPagination.pageSize,
          total: runsResponse.total || 0,
        });
      } catch (e: unknown) {
        setData((prev) => ({
          ...prev,
          loading: false,
          error: (e as Error)?.message ?? "Error loading data",
        }));
      }
    },
    [filters, runsPagination.pageSize]
  );

  const loadDefinitions = useCallback(
    async (page: number = 1) => {
      setData((prev) => ({ ...prev, loading: true }));
      try {
        const response = await authFetch(
          `/api/playbook-definitions?page=${page}&page_size=${definitionsPagination.pageSize}`
        );

        if (response.ok) {
          const data = await response.json();
          setData((prev) => ({
            ...prev,
            definitions: data.definitions || [],
          }));
          setDefinitionsPagination({
            currentPage: page,
            pageSize: definitionsPagination.pageSize,
            total: data.total || 0,
          });
        }
      } catch (e) {
        console.error("Failed to load definitions:", e);
      } finally {
        setData((prev) => ({ ...prev, loading: false }));
      }
    },
    [definitionsPagination.pageSize]
  );

  const loadQueueStats = useCallback(async () => {
    try {
      const { api_v74 } = await import("@/lib/api");
      const stats = await api_v74.getQueueStats();
      setData((prev) => ({ ...prev, queueStats: stats }));
    } catch (e) {
      // Silently fail for queue stats
    }
  }, []);

  // Initialize
  useEffect(() => {
    const authState = loadAuthState();
    if (!authState?.isAuthenticated) {
      router.push(`/${locale}/login`);
      return;
    }
    loadData(1);
    loadQueueStats();
    const interval = setInterval(loadQueueStats, 10000);
    return () => clearInterval(interval);
  }, [router, locale]);

  return {
    ...data,
    runsPagination,
    definitionsPagination,
    filters,
    setFilters,
    loadData,
    loadDefinitions,
  };
}
