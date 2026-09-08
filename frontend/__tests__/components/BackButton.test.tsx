import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { BackButton } from "@/components/common/BackButton";

const mockBack = vi.fn();
const mockPush = vi.fn();

vi.mock("@/i18n/navigation", () => ({
  useRouter: () => ({
    back: mockBack,
    push: mockPush,
  }),
}));

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => {
    const translations: Record<string, string> = {
      back: "返回",
    };
    return translations[key] || key;
  },
}));

describe("BackButton Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders with default localized '返回' label and accessible attributes", () => {
    const html = renderToStaticMarkup(<BackButton fallbackUrl="/alerts" />);
    expect(html).toContain("返回");
    expect(html).toContain('title="返回"');
    expect(html).toContain('aria-label="返回"');
    expect(html).toContain("<button");
  });

  it("renders with custom label when provided", () => {
    const html = renderToStaticMarkup(
      <BackButton fallbackUrl="/playbooks?tab=runs" label="返回列表" />
    );
    expect(html).toContain("返回列表");
    expect(html).toContain('title="返回列表"');
  });

  it("renders icon variant correctly", () => {
    const html = renderToStaticMarkup(<BackButton fallbackUrl="/alerts" variant="icon" />);
    expect(html).toContain("<button");
    expect(html).toContain('aria-label="返回"');
    expect(html).toContain("<svg");
  });

  it("renders ghost variant correctly", () => {
    const html = renderToStaticMarkup(<BackButton fallbackUrl="/alerts" variant="ghost" />);
    expect(html).toContain("返回");
    expect(html).toContain("hover:bg-surface-hover");
  });
});
