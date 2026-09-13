import { describe, it, expect, beforeEach } from "vitest";
import { useThemeStore } from "@/stores/themeStore";

describe("Theme Management & ThemeStore", () => {
  beforeEach(() => {
    useThemeStore.setState({ theme: "system" });
  });

  it("supports 'light', 'dark', and 'system' themes", () => {
    const validThemes = ["light", "dark", "system"] as const;
    expect(validThemes).toHaveLength(3);

    useThemeStore.getState().setTheme("dark");
    expect(useThemeStore.getState().theme).toBe("dark");

    useThemeStore.getState().setTheme("light");
    expect(useThemeStore.getState().theme).toBe("light");

    useThemeStore.getState().setTheme("system");
    expect(useThemeStore.getState().theme).toBe("system");
  });

  it("cycles correctly across light -> dark -> system -> light with toggleTheme()", () => {
    useThemeStore.getState().setTheme("light");
    useThemeStore.getState().toggleTheme();
    expect(useThemeStore.getState().theme).toBe("dark");

    useThemeStore.getState().toggleTheme();
    expect(useThemeStore.getState().theme).toBe("system");

    useThemeStore.getState().toggleTheme();
    expect(useThemeStore.getState().theme).toBe("light");
  });

  it("correctly resolves theme when set to light or dark", () => {
    useThemeStore.getState().setTheme("light");
    expect(useThemeStore.getState().getResolvedTheme()).toBe("light");

    useThemeStore.getState().setTheme("dark");
    expect(useThemeStore.getState().getResolvedTheme()).toBe("dark");
  });

  it("resolves system theme based on fallback or environment", () => {
    useThemeStore.getState().setTheme("system");
    const resolved = useThemeStore.getState().getResolvedTheme();
    expect(["light", "dark"]).toContain(resolved);
  });
});
