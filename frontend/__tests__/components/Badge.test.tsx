import { describe, it, expect } from "vitest";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { Badge, StatusBadge, AIBadge, ConfidenceBadge } from "@/components/ui/Badge";

/**
 * Badge 家族回归守卫。
 *
 * 重点保护「不虚构数据」硬规则：ConfidenceBadge 在 value 缺失时必须渲染
 * 降级文案，**绝不能**回退成编造的百分比。这是审计 P1-11 的直接验收点。
 */
describe("Badge Component", () => {
  it("renders severity label with severity token classes", () => {
    const html = renderToStaticMarkup(<Badge severity="critical">Critical</Badge>);
    expect(html).toContain("Critical");
    expect(html).toContain("bg-severity-critical-bg");
    expect(html).toContain("text-severity-critical-fg");
  });

  it("renders StatusBadge for a known state", () => {
    const html = renderToStaticMarkup(<StatusBadge status="resolved" label="Resolved" />);
    expect(html).toContain("Resolved");
    expect(html).toContain("bg-status-resolved-bg");
  });

  it("falls back to the unknown tone for an unrecognized status", () => {
    // @ts-expect-error 故意传入非法状态，验证不会渲染出错误语义色
    const html = renderToStaticMarkup(<StatusBadge status="not_a_state" label="?" />);
    expect(html).toContain("bg-status-unknown-bg");
  });

  it("renders AIBadge without borrowing severity colors", () => {
    const html = renderToStaticMarkup(<AIBadge state="approval" label="Requires approval" />);
    expect(html).toContain("Requires approval");
    expect(html).toContain("bg-ai-approval-bg");
  });

  describe("ConfidenceBadge", () => {
    it("renders the real percentage when a value is provided", () => {
      const html = renderToStaticMarkup(<ConfidenceBadge value={82} />);
      expect(html).toContain("82%");
    });

    it("clamps out-of-range values to 0-100", () => {
      expect(renderToStaticMarkup(<ConfidenceBadge value={140} />)).toContain("100%");
      expect(renderToStaticMarkup(<ConfidenceBadge value={-20} />)).toContain("0%");
    });

    // 硬规则：缺失置信度 → 降级文案，绝不编造数值
    it("renders the unavailable label and NO percentage when value is null/undefined", () => {
      const nullHtml = renderToStaticMarkup(
        <ConfidenceBadge value={null} unavailableLabel="Confidence unavailable" />
      );
      expect(nullHtml).toContain("Confidence unavailable");
      expect(nullHtml).not.toMatch(/\d+%/);

      const undefinedHtml = renderToStaticMarkup(<ConfidenceBadge />);
      expect(undefinedHtml).toContain("Confidence unavailable");
      expect(undefinedHtml).not.toMatch(/\d+%/);
    });

    it("treats non-finite numbers as unavailable instead of emitting NaN%", () => {
      const html = renderToStaticMarkup(<ConfidenceBadge value={NaN} />);
      expect(html).toContain("Confidence unavailable");
      expect(html).not.toContain("NaN");
      expect(html).not.toMatch(/\d+%/);
    });
  });
});
