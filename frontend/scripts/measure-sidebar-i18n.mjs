/**
 * 侧栏文案宽度复核工具
 *
 * 用途：确认 --sidebar-w: 216px（全语系统一）仍能容纳中英两种语言的最长导航标签。
 * 任何人新增/改动导航文案后，跑一次即可知道是否会被截断。
 *
 * 运行：node scripts/measure-sidebar-i18n.mjs
 *   --css <path>  可选，指定已编译的 Tailwind 样式表（默认自动从 dev server 拉取）
 *
 * 退出码：0 = 全部容纳；1 = 存在被截断的标签。
 *
 * 背景：侧栏宽度曾按 html[lang^="zh"] 分成 216px / 256px 两档，切换语言时
 * 整个外壳会横向位移。现在宽度与语言解耦，本脚本负责守住"两侧都不截断"。
 */
import { readFileSync, existsSync, writeFileSync, mkdtempSync } from "fs";
import { tmpdir } from "os";
import { join } from "path";
import { chromium } from "playwright";

const SIDEBAR_WIDTH = 216; // 必须与 globals.css 的 --sidebar-w 保持一致
const NAV_GROUPS = {
  groupOverview: ["home", "monitor"],
  groupOperations: ["alerts", "incidents", "correlation", "threatHunting"],
  groupIntelligence: ["threatIntel", "threatIntelDashboard", "ueba"],
  groupAutomation: ["runs", "definitions", "approvals", "triggers"],
  groupInfrastructure: ["assets", "cloudNative", "marketplace"],
  groupAI: ["aiCopilot"],
  groupReporting: ["reports", "auditLogs"],
  groupAdministration: [
    "dashboard",
    "users",
    "settings",
    "aiModels",
    "apiKeys",
    "notifications",
    "systemHealth",
    "secrets",
  ],
};

const ICON =
  '<svg class="h-4 w-4 shrink-0 text-text-tertiary" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/></svg>';

const link = (label) =>
  `<a href="#" title="${label}" class="group relative flex items-center gap-2.5 rounded-lg text-[13px] h-9 px-2.5 text-text-secondary">${ICON}<span class="sidebar-label truncate flex-1 min-w-0">${label}</span></a>`;

const group = (dict, label, items) =>
  `<div><button type="button" title="${label}" class="group/btn flex w-full items-center justify-between rounded-lg px-2.5 py-2 text-[13px] font-medium select-none text-text-secondary"><div class="flex items-center gap-2.5 min-w-0">${ICON}<span class="sidebar-group-label truncate">${label}</span></div><svg class="h-3.5 w-3.5 shrink-0 text-text-tertiary ml-2" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9l6 6 6-6"/></svg></button><div class="grid grid-rows-[1fr]"><div class="overflow-hidden space-y-0.5 pt-0.5 ml-3 pl-2 border-l border-border-subtle/80">${items
    .map((k) => link(dict[k]))
    .join("")}</div></div></div>`;

function buildPage(lang, dict, cssHref) {
  const nav = Object.entries(NAV_GROUPS)
    .map(([g, items]) => group(dict, dict[g], items))
    .join("");
  return `<!doctype html><html lang="${lang}"><head><meta charset="utf-8">${
    cssHref ? `<link rel="stylesheet" href="${cssHref}">` : ""
  }
<style>
  body { margin: 0; }
  #wrap { display: flex; min-height: 100vh; }
  main { flex: 1; }
</style></head><body><div id="wrap">
<aside class="group/sidebar fixed inset-y-0 left-0 z-30 hidden w-[var(--sidebar-w)] flex-col border-r border-border-subtle bg-surface-page lg:flex" style="height:100dvh">
  <nav aria-label="Main navigation" class="sidebar-scrollbar flex-1 overflow-y-auto overflow-x-hidden px-2 py-3 space-y-2.5">${nav}</nav>
</aside>
<main id="main-content" style="padding-left:var(--sidebar-w)">content</main>
</div></body></html>`;
}

function resolveCssHref() {
  const i = process.argv.indexOf("--css");
  if (i > -1 && process.argv[i + 1]) {
    return `file://${process.argv[i + 1]}`;
  }
  // 默认指向本地 dev server 编译产物；不存在时退化为内联最小样式（仅验文案宽度）
  return null;
}

const zh = JSON.parse(readFileSync("messages/zh-CN.json", "utf-8")).navigation;
const en = JSON.parse(readFileSync("messages/en.json", "utf-8")).navigation;
const cssHref = resolveCssHref();
if (!cssHref) {
  console.warn("[warn] 未指定 --css：使用内联最小样式，只能复核文案宽度（字体以 Inter 为准），");
  console.warn(
    "       padding-left 与真实可用宽度无法复核。要完整校验请传 --css <编译后的 layout.css>。"
  );
}

const dir = mkdtempSync(join(tmpdir(), "sidebar-measure-"));
const MINIMAL_CSS = `
  body { margin: 0; font-family: var(--font-sans, Inter, -apple-system, "Segoe UI", Roboto, sans-serif); }
  .wrap { display: flex; }
  aside { width: ${SIDEBAR_WIDTH}px; flex: 0 0 ${SIDEBAR_WIDTH}px; }
  nav { padding: 12px 8px; }
  a { display: flex; align-items: center; gap: 10px; height: 36px; padding: 0 10px; font-size: 13px; box-sizing: border-box; }
  svg { width: 16px; height: 16px; flex: 0 0 16px; }
  .sidebar-label { flex: 1 1 auto; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  button { display: flex; align-items: center; justify-content: space-between; gap: 10px; width: 100%; padding: 8px 10px; font-size: 13px; font-weight: 500; box-sizing: border-box; }
  .sidebar-group-label { white-space: nowrap; }
  .grp-inner { margin-left: 12px; padding-left: 8px; }
`;

const files = {};
for (const [tag, dict] of [
  ["en", en],
  ["zh-CN", zh],
]) {
  const p = join(dir, `${tag}.html`);
  writeFileSync(p, buildPage(tag, dict, cssHref ?? "inline.css"));
  files[tag] = p;
}
if (!cssHref) writeFileSync(join(dir, "inline.css"), MINIMAL_CSS);

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

async function probe(file) {
  await page.goto(`file://${file}`);
  await page.waitForTimeout(150);
  return page.evaluate(() => {
    const intrinsic = (el) => {
      const cs = getComputedStyle(el);
      const s = document.createElement("span");
      s.style.position = "absolute";
      s.style.visibility = "hidden";
      s.style.whiteSpace = "nowrap";
      s.style.fontFamily = cs.fontFamily;
      s.style.fontSize = cs.fontSize;
      s.style.fontWeight = cs.fontWeight;
      s.style.letterSpacing = cs.letterSpacing;
      s.textContent = el.textContent;
      document.body.appendChild(s);
      const w = +s.getBoundingClientRect().width.toFixed(1);
      s.remove();
      return w;
    };
    const rows = [...document.querySelectorAll("aside nav a")].map((a) => {
      const el = a.querySelector(".sidebar-label");
      const avail = Math.floor(a.getBoundingClientRect().right - el.getBoundingClientRect().x);
      const textW = intrinsic(el);
      return { text: el.textContent, textW, avail, fits: textW <= avail };
    });
    const groups = [...document.querySelectorAll("aside nav button")].map((b) => {
      const el = b.querySelector(".sidebar-group-label");
      const avail = Math.floor(b.getBoundingClientRect().right - el.getBoundingClientRect().x);
      const textW = intrinsic(el);
      return { text: el.textContent, textW, avail, fits: textW <= avail };
    });
    return {
      asideW: +document.querySelector("aside").getBoundingClientRect().width.toFixed(1),
      contentPadLeft: getComputedStyle(document.getElementById("main-content")).paddingLeft,
      rows,
      groups,
    };
  });
}

let failed = false;
const results = {};
for (const tag of ["en", "zh-CN"]) {
  const r = await probe(files[tag]);
  results[tag] = r;
  const all = [...r.rows, ...r.groups];
  const worst = all.reduce((a, b) => (b.textW > a.textW ? b : a));
  const overflow = all.filter((x) => !x.fits);
  if (overflow.length) failed = true;

  console.log(`\n=== ${tag} ===`);
  console.log(`侧栏宽度 ${r.asideW}px | 内容区 padding-left ${r.contentPadLeft}`);
  console.log(
    `最宽标签 "${worst.text}" ${worst.textW}px / 可用 ${worst.avail}px -> 富余 ${(worst.avail - worst.textW).toFixed(1)}px`
  );
  console.log(
    `被截断标签: ${overflow.length} 个${overflow.length ? " -> " + overflow.map((o) => o.text).join(", ") : ""}`
  );
}

const [a, b] = [results["en"], results["zh-CN"]];
const noShift = a.asideW === b.asideW && a.contentPadLeft === b.contentPadLeft;
console.log(
  `\n零位移: 侧栏 ${a.asideW} -> ${b.asideW} | padding ${a.contentPadLeft} -> ${b.contentPadLeft} ${noShift ? "✅" : "❌"}`
);
if (!noShift || failed) failed = true;
console.log(failed ? "\n❌ 复核未通过" : "\n✅ 全部标签容纳且两语系零位移");

await browser.close();
process.exit(failed ? 1 : 0);
