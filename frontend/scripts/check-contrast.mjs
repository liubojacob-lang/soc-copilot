#!/usr/bin/env node
/**
 * WCAG contrast regression guard.
 *
 * WHY THIS EXISTS
 * ---------------
 * The design system keeps every readable color in CSS variables so light/dark can
 * swap wholesale. That is efficient, but it means a single hex edit in
 * `app/globals.css` can silently push a text layer below WCAG AA — and nothing in
 * the build would notice. This already happened once: dark `--color-text-tertiary`
 * shipped at 3.75:1 (needs 4.5:1) and was only caught by a hand-written audit.
 *
 * This script turns the numbers that audit produced into assertions, so the fix
 * cannot be undone by accident.
 *
 * WHAT IT CHECKS
 * --------------
 *   1. Text layers  ×  surface layers   (every real combination, AA 4.5:1)
 *   2. Badge foregrounds × own tinted backgrounds
 *      (severity / status / ai — alpha backgrounds are composited over the card)
 *   3. Dark-mode text hierarchy must have 4 DISTINCT values
 *      (primary/secondary/tertiary/muted collapsing to 3 is a real regression:
 *       it happened when tertiary and muted were both #94a3b8)
 *
 * EXEMPTIONS (documented, not silent)
 * -----------------------------------
 *   - `--color-text-disabled`: WCAG 1.4.3 exempts inactive controls. Reported for
 *     information, never fails the build.
 *   - `--color-text-inverse`: by definition used on top of accent/solid fills, not
 *     on the page surfaces. Not checked against surfaces.
 *
 * Usage:
 *   node scripts/check-contrast.mjs
 */
import { readFileSync } from "fs";
import { join } from "path";

const ROOT = join(import.meta.dirname, "..");
const CSS_FILE = join(ROOT, "app", "globals.css");

const AA_NORMAL = 4.5;
const AA_LARGE = 3.0;

// ---------------------------------------------------------------- color math

/** Parse `#rgb` / `#rrggbb` / `rgb()` / `rgba()` into {r,g,b,a}. */
function parseColor(raw) {
  const v = String(raw).trim();
  if (v.startsWith("#")) {
    let h = v.slice(1);
    if (h.length === 3)
      h = h
        .split("")
        .map((c) => c + c)
        .join("");
    if (h.length !== 6) return null;
    const n = parseInt(h, 16);
    if (Number.isNaN(n)) return null;
    return { r: (n >> 16) & 255, g: (n >> 8) & 255, b: n & 255, a: 1 };
  }
  const m = v.match(/rgba?\(([^)]+)\)/);
  if (!m) return null;
  const p = m[1]
    .split(/[,/\s]+/)
    .filter(Boolean)
    .map(parseFloat);
  if (p.length < 3 || p.some((x) => Number.isNaN(x))) return null;
  return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 };
}

/** Composite a possibly-translucent color over an opaque backdrop. */
function over(fg, bg) {
  if (fg.a >= 1) return { r: fg.r, g: fg.g, b: fg.b, a: 1 };
  return {
    r: fg.r * fg.a + bg.r * (1 - fg.a),
    g: fg.g * fg.a + bg.g * (1 - fg.a),
    b: fg.b * fg.a + bg.b * (1 - fg.a),
    a: 1,
  };
}

/** WCAG 2.1 relative luminance. */
function luminance(c) {
  const [r, g, b] = [c.r, c.g, c.b].map((v) => {
    const s = v / 255;
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** WCAG 2.1 contrast ratio, 1..21. */
function ratio(fg, bg) {
  const a = luminance(fg);
  const b = luminance(bg);
  return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
}

// ------------------------------------------------------------ css extraction

/**
 * Pull the custom properties declared in a top-level selector block.
 * Brace counting handles `@media`/nested blocks without a CSS parser dependency.
 */
function readBlock(css, selector) {
  const start = css.indexOf(selector + " {");
  if (start === -1) throw new Error(`selector \`${selector}\` not found in globals.css`);
  let depth = 0;
  let end = start;
  for (let i = css.indexOf("{", start); i < css.length; i++) {
    if (css[i] === "{") depth++;
    else if (css[i] === "}") {
      depth--;
      if (depth === 0) {
        end = i;
        break;
      }
    }
  }
  const body = css.slice(start, end);
  const vars = {};
  for (const line of body.split("\n")) {
    const m = line.match(/^\s*(--[\w-]+)\s*:\s*([^;]+);/);
    if (m) vars[m[1]] = m[2].trim();
  }
  return vars;
}

const css = readFileSync(CSS_FILE, "utf-8");
const themes = {
  light: readBlock(css, ":root"),
  dark: readBlock(css, ".dark"),
};

// ------------------------------------------------------------- check targets

const TEXT_LAYERS = [
  ["--color-text-primary", "primary"],
  ["--color-text-secondary", "secondary"],
  ["--color-text-tertiary", "tertiary"],
  ["--color-text-muted", "muted"],
  ["--color-text-link", "link"],
  ["--color-text-mono", "mono"],
];

// `--color-text-inverse` is deliberately excluded: it is used on solid accent
// fills, not on page surfaces. Checking it against card/page would be a false alarm.
const SURFACE_LAYERS = [
  ["--color-bg-page", "surface-page"],
  ["--color-bg-card", "surface-card"],
  ["--color-bg-hover", "surface-hover"],
  ["--color-bg-active", "surface-active"],
  ["--color-bg-input", "surface-input"],
];

// Badge families: each entry is `prefix` + `-fg` on `prefix` + `-bg`.
const BADGE_PREFIXES = [
  ["--sev-critical", "severity-critical"],
  ["--sev-high", "severity-high"],
  ["--sev-medium", "severity-medium"],
  ["--sev-low", "severity-low"],
  ["--sev-info", "severity-info"],
  ["--sev-neutral", "severity-neutral"],
  ["--status-active", "status-active"],
  ["--status-resolved", "status-resolved"],
  ["--status-investigating", "status-investigating"],
  ["--status-pending", "status-pending"],
  ["--status-failed", "status-failed"],
  ["--status-success", "status-success"],
  ["--status-warning", "status-warning"],
  ["--status-unknown", "status-unknown"],
  ["--status-disabled", "status-disabled"],
  ["--ai", "ai"],
  ["--ai-running", "ai-running"],
  ["--ai-completed", "ai-completed"],
  ["--ai-failed", "ai-failed"],
  ["--ai-approval", "ai-approval"],
  ["--ai-approved", "ai-approved"],
];

// Text layers that are exempt from AA under WCAG 1.4.3 (inactive controls).
// Reported as info; never fails.
const EXEMPT_TEXT = new Set(["--color-text-disabled"]);

// ------------------------------------------------------------ known backlog

/**
 * Pre-existing debt: combinations already below AA before this guard existed.
 * Failing on them would block every future commit for a reason unrelated to the
 * change under review, so they are reported loudly but do not fail the build.
 *
 * Entries are keyed by ROOT CAUSE, not by individual combination, so a new
 * violation of a different shape still fails. Each entry records WHY it is
 * tolerated and WHERE the fix is tracked. See
 * `deliverables/ui-optimization/后续路线图.md` § 五.
 */
const KNOWN_DEBT = [
  {
    id: "弱文本层级放在 hover/active 背景上",
    match: (r) =>
      (r.key.includes("on surface-hover") || r.key.includes("on surface-active")) &&
      /^(tertiary|muted|secondary|link) /.test(r.key),
    reason:
      "根因是用错了文本层级，不是 token 取值错了。深色下把 --color-bg-active 调暗到能让 muted 达标，" +
      "hover 与 active 会变得无法区分（新的可用性问题）。正确修法是改页面写法（muted → secondary/primary），" +
      "涉及 triggers / cloud-native 等页面，已登记为 B 批次必修项。",
  },
];

const rows = [];
const warnings = [];

for (const [themeName, vars] of Object.entries(themes)) {
  // ---- 1. text layers on surfaces
  for (const [fgToken, fgLabel] of TEXT_LAYERS) {
    const raw = vars[fgToken];
    if (!raw) continue;
    const fg = parseColor(raw);
    if (!fg) {
      warnings.push(`${themeName}: ${fgToken} unparseable (${raw})`);
      continue;
    }
    for (const [bgToken, bgLabel] of SURFACE_LAYERS) {
      const bg = parseColor(vars[bgToken]);
      if (!bg) continue;
      const solidFg = over(fg, bg);
      const r = ratio(solidFg, bg);
      rows.push({
        theme: themeName,
        kind: "text-on-surface",
        key: `${fgLabel} on ${bgLabel}`,
        fgToken,
        bgToken,
        ratio: r,
        min: AA_NORMAL,
        exempt: EXEMPT_TEXT.has(fgToken),
      });
    }
  }

  // ---- 2. badge foreground on its own tinted background
  const card = parseColor(vars["--color-bg-card"]);
  for (const [prefix, label] of BADGE_PREFIXES) {
    const fgRaw = vars[`${prefix}-fg`];
    const bgRaw = vars[`${prefix}-bg`];
    if (!fgRaw || !bgRaw) continue;
    const fg = parseColor(fgRaw);
    const bgTint = parseColor(bgRaw);
    if (!fg || !bgTint) {
      warnings.push(`${themeName}: ${prefix} unparseable (${fgRaw} / ${bgRaw})`);
      continue;
    }
    const bg = over(bgTint, card); // translucent tints sit on the card
    const r = ratio(over(fg, bg), bg);
    rows.push({
      theme: themeName,
      kind: "badge-fg-on-bg",
      key: `${label} fg on bg`,
      fgToken: `${prefix}-fg`,
      bgToken: `${prefix}-bg`,
      ratio: r,
      min: AA_NORMAL,
      exempt: false,
    });
  }
}

// ---- 3. dark-mode text hierarchy must stay 4 distinct values
const hierarchyFailures = [];
{
  const vars = themes.dark;
  const layers = ["primary", "secondary", "tertiary", "muted"].map((n) => [
    n,
    vars[`--color-text-${n}`],
  ]);
  const seen = new Map();
  for (const [name, val] of layers) {
    if (val === undefined) continue;
    const key = val.toLowerCase();
    if (seen.has(key)) {
      hierarchyFailures.push(
        `dark: --color-text-${name} === --color-text-${seen.get(key)} (${val}) — hierarchy collapses to 3 levels`
      );
    } else {
      seen.set(key, name);
    }
  }
}

// ------------------------------------------------------------------- report

const failures = [];
const debt = [];
for (const row of rows) {
  if (row.exempt) continue;
  if (row.ratio >= row.min) continue;
  const hit = KNOWN_DEBT.find((d) => d.match(row));
  if (hit) debt.push({ ...row, debt: hit });
  else failures.push(row);
}

// Best/worst summary per theme, useful as a quick sanity read.
const summary = Object.keys(themes).map((t) => {
  const rs = rows.filter((r) => r.theme === t && !r.exempt);
  const worst = rs.reduce((a, b) => (a.ratio <= b.ratio ? a : b));
  return `    ${t.padEnd(5)} worst: ${worst.key} @ ${worst.ratio.toFixed(2)}:1`;
});

console.log("\n[contrast] WCAG 2.1 AA regression guard\n");
console.log(`  Themes parsed            ${Object.keys(themes).length} (light / dark)`);
console.log(`  Combinations evaluated   ${rows.length}`);
console.log(`  Threshold                ${AA_NORMAL}:1 normal text · ${AA_LARGE}:1 large text`);
console.log("");
console.log("  Worst combination per theme:");
console.log(summary.join("\n"));
console.log("");

let failed = false;

if (hierarchyFailures.length > 0) {
  failed = true;
  console.error(`  ❌ Dark-mode text hierarchy collapsed (${hierarchyFailures.length}):`);
  console.error(hierarchyFailures.map((h) => `      ${h}`).join("\n"));
  console.error("");
} else {
  console.log(
    "  ✅ Dark-mode text hierarchy: 4 distinct layers (primary/secondary/tertiary/muted)\n"
  );
}

if (failures.length > 0) {
  failed = true;
  console.error(`  ❌ ${failures.length} NEW combination(s) below WCAG AA:`);
  for (const f of failures) {
    console.error(
      `      [${f.theme}] ${f.key} = ${f.ratio.toFixed(2)}:1  (needs ${f.min}:1)\n` +
        `             ${f.fgToken}  on  ${f.bgToken}`
    );
  }
  console.error("\n     Fix the token value in app/globals.css, or lower the requirement if");
  console.error("     the text is genuinely large (>= 24px, or >= 18.66px bold).\n");
} else {
  const checked = rows.filter((r) => !r.exempt);
  const passing = checked.filter((r) => r.ratio >= r.min);
  console.log(
    `  ✅ No new violations — ${passing.length}/${checked.length} combinations meet WCAG AA\n`
  );
}

if (debt.length > 0) {
  console.log(
    `  ⚠️  Pre-existing debt: ${debt.length} combination(s) below AA (does not fail the build)`
  );
  for (const id of [...new Set(debt.map((d) => d.debt.id))]) {
    const items = debt.filter((d) => d.debt.id === id);
    console.log(`\n      [${id}] × ${items.length}`);
    for (const it of items) {
      console.log(
        `        - [${it.theme}] ${it.key} = ${it.ratio.toFixed(2)}:1 (needs ${it.min}:1)`
      );
    }
    console.log(`        why tolerated: ${items[0].debt.reason}`);
  }
  console.log("");
}

if (warnings.length > 0) {
  console.log("  ⚠️  Informational:");
  console.log(warnings.map((w) => `      ${w}`).join("\n"));
  console.log("");
}

process.exit(failed ? 1 : 0);
