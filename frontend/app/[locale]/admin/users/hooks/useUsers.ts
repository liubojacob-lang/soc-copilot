/** Admin users page types and hooks */

import { useState, useCallback, useEffect } from "react";
import { useRouter } from "@/i18n/navigation";
import { loadAuthState, isAdmin, authFetchJSON, authFetch } from "@/lib/auth";

export interface User {
  id: string;
  username: string;
  email: string;
  role: "admin" | "analyst" | "auditor";
  is_active: boolean;
  created_at: string;
  last_login_at: string | null;
}

export interface PaginationInfo {
  page: number;
  limit: number;
  total: number;
  totalPages: number;
}

export function useUsers() {
  const router = useRouter();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [pagination, setPagination] = useState<PaginationInfo>({
    page: 1,
    limit: 10,
    total: 0,
    totalPages: 0,
  });
  const [filters, setFilters] = useState({
    role: "" as "" | "admin" | "analyst" | "auditor",
    status: "" as "" | "active" | "inactive",
    search: "",
  });

  const fetchUsers = useCallback(
    async (page: number = 1) => {
      setLoading(true);
      setError("");
      try {
        const skip = (page - 1) * pagination.limit;
        const params = new URLSearchParams({
          skip: skip.toString(),
          limit: pagination.limit.toString(),
        });

        if (filters.role) params.append("role", filters.role);
        if (filters.status)
          params.append("is_active", filters.status === "active" ? "true" : "false");
        if (filters.search) params.append("search", filters.search);

        const data = await authFetchJSON<{ items: User[]; total: number }>(`/api/users?${params}`);
        setUsers(data.items);
        setPagination((prev) => ({
          ...prev,
          page,
          total: data.total,
          totalPages: Math.ceil(data.total / prev.limit),
        }));
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load users");
      } finally {
        setLoading(false);
      }
    },
    [pagination.limit, filters]
  );

  const handleFilterChange = useCallback(
    (newFilters: Partial<typeof filters>) => {
      setFilters((prev) => ({ ...prev, ...newFilters }));
      fetchUsers(1); // Reset to page 1 when filters change
    },
    [fetchUsers]
  );

  const deleteUser = useCallback(async (userId: string) => {
    // 删除确认由 UI 层 ConfirmDialog 负责，此处为纯数据操作
    const response = await authFetch(`/api/users/${userId}`, {
      method: "DELETE",
    });

    if (response.ok) {
      setUsers((prev) => prev.filter((u) => u.id !== userId));
      setPagination((prev) => ({
        ...prev,
        total: prev.total - 1,
      }));
    }
  }, []);

  const updateUser = useCallback(async (userId: string, updates: Partial<User>) => {
    const response = await authFetch(`/api/users/${userId}`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(updates),
    });

    if (response.ok) {
      const updatedUser = await response.json();
      setUsers((prev) => prev.map((u) => (u.id === userId ? updatedUser : u)));
      return updatedUser;
    }
    return null;
  }, []);

  useEffect(() => {
    const authState = loadAuthState();
    if (!authState?.isAuthenticated) {
      router.push("/login");
      return;
    }
    if (!isAdmin(authState.user)) {
      router.push("/");
      return;
    }
    fetchUsers();
  }, [router]);

  return {
    users,
    loading,
    error,
    pagination,
    filters,
    fetchUsers,
    deleteUser,
    updateUser,
    handleFilterChange,
  };
}

export function generatePassword(): string {
  const length = 16;
  const charset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*";
  let password = "";
  for (let i = 0; i < length; i++) {
    password += charset.charAt(Math.floor(Math.random() * charset.length));
  }
  return password;
}
