import { useMemo } from "react";
import { loadAuthState, type User } from "@/lib/auth";

export function usePermission(permission: string) {
  return useMemo(() => {
    if (typeof window === "undefined") return false;
    const auth = loadAuthState();
    const user: User | null = auth?.user ?? null;
    if (!user) return false;
    if (user.role === "admin") return true;
    const permissions = user.permissions ?? [];
    return permissions.includes(permission);
  }, [permission]);
}
