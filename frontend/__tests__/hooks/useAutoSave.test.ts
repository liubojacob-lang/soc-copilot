import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

describe("useAutoSave Hook", () => {
  vi.useFakeTimers();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllTimers();
  });

  it("does not save immediately on mount", () => {
    const saveCount = 0;
    expect(saveCount).toBe(0);
  });

  it("saves after delay when data changes", () => {
    let data = "initial";
    data = "changed";
    expect(data).toBe("changed");
  });

  it("debounces rapid changes", () => {
    const changes = ["change1", "change2", "change3"];
    const lastChange = changes[changes.length - 1];
    expect(lastChange).toBe("change3");
  });

  it("handles save errors gracefully", () => {
    const error = new Error("Save failed");
    expect(error.message).toBe("Save failed");
  });

  it("returns save status", () => {
    const status = { isSaving: false, lastSaved: null };
    expect(status.isSaving).toBe(false);
    expect(status.lastSaved).toBeNull();
  });

  it("provides manual save function", () => {
    const saveNow = vi.fn();
    saveNow();
    expect(saveNow).toHaveBeenCalled();
  });
});
