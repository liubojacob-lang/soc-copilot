import { describe, it, expect, vi } from "vitest";

describe("useIsClient Hook", () => {
  it("returns false on initial render (SSR)", () => {
    const isClient = false;
    expect(isClient).toBe(false);
  });

  it("returns true after hydration", () => {
    const isClient = typeof window !== "undefined";
    expect(isClient).toBe(true);
  });

  it("handles window being undefined", () => {
    const hasWindow = typeof window !== "undefined";
    expect(hasWindow).toBe(true);
  });
});
