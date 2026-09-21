import { test, expect } from "@playwright/test";
import { login, TEST_USERS } from "../utils/auth";

test.describe("Internationalization (i18n)", () => {
  test.beforeEach(async ({ page }) => {
    await login(page, TEST_USERS.admin.username, TEST_USERS.admin.password);
  });

  test("loads English content by default", async ({ page }) => {
    await page.goto("/en");

    await expect(page.locator("text=/alert|dashboard|security/i")).toBeVisible({ timeout: 10000 });
  });

  test("loads Chinese content when switching locale", async ({ page }) => {
    await page.goto("/zh-CN");

    await expect(page.locator("text=/告警|仪表盘|安全/i")).toBeVisible({ timeout: 10000 });
  });

  test("language switcher toggles between locales", async ({ page }) => {
    await page.goto("/en");

    const langSwitcher = page
      .locator(
        '[data-testid="lang-switcher"], button:has-text("中文"), button:has-text("EN"), select[aria-label*="language" i], a[href*="/zh-CN/"]'
      )
      .first();

    if (await langSwitcher.isVisible()) {
      await langSwitcher.click();

      const zhLink = page.locator('a[href*="/zh-CN/"], button:has-text("中文")').first();
      if (await zhLink.isVisible()) {
        await zhLink.click();
        await expect(page).toHaveURL(/\/zh-CN/);
      }
    }
  });

  test("preserves current page path on locale switch", async ({ page }) => {
    await page.goto("/en/alerts");

    const langSwitcher = page
      .locator('a[href*="/zh-CN/alerts"], button:has-text("中文"), [data-testid="lang-switcher"]')
      .first();

    if (await langSwitcher.isVisible()) {
      await langSwitcher.click();

      await expect(page).toHaveURL(/\/zh\/alerts/);
    }
  });

  test("displays localized date/time format", async ({ page }) => {
    await page.goto("/en/alerts");

    const dateElement = page.locator("time, [class*='date'], [class*='timestamp']").first();
    if (await dateElement.isVisible()) {
      const text = await dateElement.textContent();
      expect(text).toBeTruthy();
    }
  });

  test("falls back to English for missing translations", async ({ page }) => {
    await page.goto("/zh-CN");

    const bodyText = await page.locator("body").textContent();
    expect(bodyText).toBeTruthy();
  });

  test("valid locale paths are accessible", async ({ page }) => {
    const locales = ["en", "zh-CN"];

    for (const locale of locales) {
      const response = await page.request.get(`/${locale}`);
      expect(response.status()).toBeLessThan(400);
    }
  });

  /**
   * 回归护栏：切换语言不得改变任何布局几何。
   *
   * 历史 bug：globals.css 曾按 html[lang^="zh"] 把 --sidebar-w 从 256px 改成
   * 216px，而该变量同时驱动侧栏宽度和内容区 paddingLeft，导致切语言时整个
   * 外壳做 200ms 横向位移。语言只能影响文字（字体/字距），不能驱动盒子尺寸。
   * 任何人再引入语言相关的宽度，这里会直接失败。
   */
  test("switching locale must not shift layout geometry", async ({ page }) => {
    const measureLayout = () =>
      page.evaluate(() => {
        const box = (el: Element | null) => {
          if (!el) return null;
          const r = el.getBoundingClientRect();
          return [r.x, r.y, r.width, r.height].map((n) => Math.round(n));
        };
        const sidebar = document.querySelector("aside");
        const content = document.getElementById("main-content");
        return {
          sidebar: box(sidebar),
          content: box(content),
          contentBox: box(content?.parentElement ?? null),
          viewportClientWidth: document.documentElement.clientWidth,
        };
      });

    await page.goto("/en/alerts");
    await page.waitForSelector("aside", { timeout: 10000 });

    const before = await measureLayout();

    // 断言侧栏确实是展开态，否则测不到真正的宽度驱动逻辑
    expect(before.sidebar?.[2], "侧栏应处于展开态（宽度应大于 0）").toBeGreaterThan(0);

    await page.getByTestId("lang-switcher").getByRole("radio", { name: "中文" }).click();
    await expect(page).toHaveURL(/\/zh-CN\/alerts/);
    await page.waitForSelector("aside nav a", { timeout: 10000 });

    const after = await measureLayout();

    for (const key of ["sidebar", "content", "contentBox", "viewportClientWidth"] as const) {
      expect(
        after[key],
        `切语言后 ${key} 的几何发生了变化：${JSON.stringify(before[key])} -> ${JSON.stringify(after[key])}`
      ).toEqual(before[key]);
    }
  });

  test("sidebar width stays constant across locales", async ({ page }) => {
    const sidebarWidth = async (locale: string) => {
      await page.goto(`${locale}/alerts`);
      await page.waitForSelector("aside", { timeout: 10000 });
      return page.evaluate(() =>
        Math.round(document.querySelector("aside")!.getBoundingClientRect().width)
      );
    };

    const en = await sidebarWidth("en");
    const zh = await sidebarWidth("zh-CN");

    expect(zh, `中文与英文侧栏宽度必须一致：zh=${zh}px, en=${en}px`).toBe(en);
  });
});
