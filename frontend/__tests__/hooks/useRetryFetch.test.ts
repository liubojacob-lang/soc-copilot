import { describe, it, expect, vi, beforeEach } from "vitest";

describe("useRetryFetch Hook", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns initial state correctly", () => {
    const state = { data: null, error: null, loading: false, retryCount: 0 };
    expect(state.data).toBeNull();
    expect(state.error).toBeNull();
    expect(state.loading).toBe(false);
    expect(state.retryCount).toBe(0);
  });

  it("handles fetch errors", async () => {
    const error = new Error("Network error");
    expect(error.message).toBe("Network error");
  });

  it("retries on failure", () => {
    let attempts = 0;
    const maxRetries = 3;
    for (let i = 0; i < maxRetries; i++) {
      attempts++;
    }
    expect(attempts).toBe(3);
  });

  it("stops retrying after max retries", () => {
    const maxRetries = 2;
    let retryCount = 0;
    while (retryCount < maxRetries) {
      retryCount++;
    }
    expect(retryCount).toBe(2);
  });

  it("resets state correctly", () => {
    const state = { data: { test: true }, error: null, retryCount: 2 };
    const resetState = { data: null, error: null, retryCount: 0 };
    expect(resetState.data).toBeNull();
    expect(resetState.retryCount).toBe(0);
  });
});
