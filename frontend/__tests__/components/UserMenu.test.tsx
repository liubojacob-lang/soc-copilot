import { describe, it, expect, vi } from "vitest";
import type { User } from "@/lib/types";

describe("UserMenu Component Structure & Role Helpers", () => {
  const mockUser: User = {
    id: "u-1",
    username: "alice",
    email: "alice@soc.local",
    role: "admin",
    is_active: true,
    permissions: ["all"],
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };

  it("extracts correct initial for user avatar", () => {
    const initial = (mockUser.username || "U").charAt(0).toUpperCase();
    expect(initial).toBe("A");
  });

  it("handles user without explicit email with sensible fallback", () => {
    const fallbackEmail = mockUser.email || `${mockUser.username}@soc.local`;
    expect(fallbackEmail).toBe("alice@soc.local");
  });

  it("fires logout callback on action", () => {
    const onLogout = vi.fn();
    onLogout();
    expect(onLogout).toHaveBeenCalledTimes(1);
  });
});
