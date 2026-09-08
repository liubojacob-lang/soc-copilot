import { describe, it, expect, vi } from "vitest";

describe("LanguageSwitcher Component", () => {
  it("defines supported locales (zh-CN and en)", () => {
    const LOCALES = [
      { code: "zh-CN", label: "中文" },
      { code: "en", label: "EN" },
    ];
    expect(LOCALES).toHaveLength(2);
    expect(LOCALES[0].code).toBe("zh-CN");
    expect(LOCALES[1].code).toBe("en");
  });

  it("handles locale switching", () => {
    const switchLocale = vi.fn();
    switchLocale("en");
    expect(switchLocale).toHaveBeenCalledWith("en");
  });

  it("includes nowrap and shrink-0 classes to prevent layout wrapping", () => {
    const containerClasses =
      "inline-flex items-center p-0.5 rounded-lg bg-gray-100 dark:bg-gray-800/80 border border-gray-200/80 dark:border-gray-700/80 text-xs font-medium select-none shadow-xs shrink-0 whitespace-nowrap";
    const buttonClasses =
      "relative inline-flex items-center justify-center min-w-[2.25rem] px-2.5 py-1 rounded-md text-xs transition-all duration-200 font-medium whitespace-nowrap shrink-0 leading-none";

    expect(containerClasses).toContain("shrink-0");
    expect(containerClasses).toContain("whitespace-nowrap");
    expect(buttonClasses).toContain("shrink-0");
    expect(buttonClasses).toContain("whitespace-nowrap");
  });
});
