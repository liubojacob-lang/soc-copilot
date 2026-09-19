#!/usr/bin/env node
/**
 * Design token integrity check.
 *
 * Guards against two failure modes that already happened once in this repo:
 *
 *  1. Dead class names — code referencing `bg-surface-ground` / `text-text-muted`
 *     while `tailwind.config.ts` never defined them. Tailwind silently emits
 *     nothing, so colors just vanish with no build error. We verify every
 *     semantic-token class used in source actually exists in the generated CSS.
 *
 *  2. Token regression — semantic token adoption drifting backwards while
 *     hardcoded palette colors creep in. A ratchet baseline makes the
 *     hardcoded count only allowed to go DOWN, never up.
 *
 * Usage:
 *   node scripts/check-design-tokens.mjs            # check
 *   node scripts/check-design-tokens.mjs --update   # ratchet baseline to current
 */
import { readFileSync, writeFileSync, existsSync, readdirSync, statSync, mkdtempSync } from "fs";
import { execFileSync } from "child_process";
import { join, relative } from "path";
import { tmpdir } from "os";

const ROOT = join(import.meta.dirname, "..");
const SCAN_DIRS = ["app", "components"];
const BASELINE_FILE = join(ROOT, ".design-token-baseline.json");

const HARDCODED_COLOR =
  /(?:text|bg|border|ring|from|to|via|divide|placeholder|fill|stroke)-(?:white|black|gray|slate|zinc|neutral|red|orange|amber|yellow|green|emerald|teal|blue|indigo|purple|pink)-\d{2,3}/g;

// Semantic token families declared in tailwind.config.ts.
const SEMANTIC_TOKEN =
  /(?:text|bg|border|ring)-(?:text|surface|border|severity|status|ai)-[a-zA-Z]+(?:-[a-zA-Z]+)?/g;

function walk(dir, out = []) {
  if (!existsSync(dir)) return out;
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) walk(full, out);
    else if (/\.(tsx|ts)$/.test(full)) out.push(full);
  }
  return out;
}

const files = SCAN_DIRS.flatMap((d) => walk(join(ROOT, d)));
const hardcoded = new Map();
const semanticClasses = new Set();

for (const file of files) {
  const src = readFileSync(file, "utf-8");
  const rel = relative(ROOT, file);

  for (const m of src.matchAll(HARDCODED_COLOR)) {
    hardcoded.set(m[0], (hardcoded.get(m[0]) ?? 0) + 1);
  }
  // Only collect candidate token classes; validity is decided against real CSS.
  for (const m of src.matchAll(SEMANTIC_TOKEN)) {
    semanticClasses.add(m[0]);
  }
}

const hardcodedTotal = [...hardcoded.values()].reduce((a, b) => a + b, 0);

// ---------------------------------------------------------------- check 1
// Generate the real Tailwind output and confirm every semantic token class resolves.
function resolveTailwindBin() {
  const candidates = [
    join(ROOT, "node_modules", ".bin", "tailwindcss"),
    join(ROOT, "..", "node_modules", ".bin", "tailwindcss"),
  ];
  return candidates.find((p) => existsSync(p));
}

const tailwindBin = resolveTailwindBin();
let deadClasses = [];

if (!tailwindBin) {
  console.warn("[design-tokens] ⚠️  tailwindcss binary not found — skipping dead-class check.");
} else {
  const outCss = join(mkdtempSync(join(tmpdir(), "tw-check-")), "out.css");
  execFileSync(tailwindBin, ["-i", join(ROOT, "app", "globals.css"), "-o", outCss], {
    cwd: ROOT,
    stdio: "pipe",
  });
  const css = readFileSync(outCss, "utf-8");
  // The class may only appear behind a variant (e.g. `.hover\:border-border-strong:hover`),
  // so we look for the escaped class token anywhere in the output, with a boundary
  // check so `bg-ai-bg` doesn't satisfy `bg-ai`.
  for (const cls of semanticClasses) {
    const escaped = cls.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const present = new RegExp(escaped + "(?![\\w-])").test(css);
    if (!present) deadClasses.push(cls);
  }
  deadClasses.sort();
}

// ---------------------------------------------------------------- check 2
let baseline = null;
if (existsSync(BASELINE_FILE)) {
  baseline = JSON.parse(readFileSync(BASELINE_FILE, "utf-8"));
}

const update = process.argv.includes("--update");
if (update) {
  writeFileSync(
    BASELINE_FILE,
    JSON.stringify(
      {
        hardcodedColorCount: hardcodedTotal,
        updatedAt: new Date().toISOString().slice(0, 10),
        note: "Ratchet baseline. This number must only decrease. Run with --update only after a deliberate token migration.",
      },
      null,
      2
    ) + "\n",
    "utf-8"
  );
  console.log(`[design-tokens] ✅ baseline updated → ${hardcodedTotal}`);
  process.exit(0);
}

// ---------------------------------------------------------------- check 3
// Semantic aliasing guard.
//
// The palette is deliberately over-specified: several tokens hold the same hex on
// purpose (status-active / status-resolved / status-success are all "go green";
// sev-critical and status-failed are both "red"). Those are fine.
//
// What is NOT fine is collapsing two tokens whose *meaning* an operator must be
// able to tell apart at a glance. That already happened once: --sev-low held the
// same blue as accent / info / status-investigating / ai-running, so a "low
// severity" badge looked identical to a clickable primary button. Five distinct
// meanings shared one hue. It was fixed by moving sev-low to cyan, and this check
// exists so it cannot come back.
const CSS_FILE = join(ROOT, "app", "globals.css");
const TW_CONFIG = join(ROOT, "tailwind.config.ts");

/** Custom properties declared in a top-level selector block. */
function readTokenBlock(css, selector) {
  const start = css.indexOf(selector + " {");
  if (start === -1) return {};
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
  const vars = {};
  for (const line of css.slice(start, end).split("\n")) {
    const m = line.match(/^\s*(--[\w-]+)\s*:\s*([^;]+);/);
    if (m) vars[m[1]] = m[2].trim();
  }
  return vars;
}

const cssSrc = readFileSync(CSS_FILE, "utf-8");
const tokenThemes = {
  light: readTokenBlock(cssSrc, ":root"),
  dark: readTokenBlock(cssSrc, ".dark"),
};

// accent lives in the Tailwind palette, not in a CSS variable.
const accentBlock = readFileSync(TW_CONFIG, "utf-8").match(/accent:\s*\{([\s\S]*?)\}/);
const accent600 = accentBlock ? (accentBlock[1].match(/600:\s*"([^"]+)"/) ?? [])[1] : null;

const SEVERITY_LEVELS = ["critical", "high", "medium", "low", "info"];
const INTERACTIVE_BLUE = [
  ["--color-info", "info 语义色"],
  ["--status-investigating", "status-investigating（进行中）"],
  ["--ai-running", "ai-running（AI 运行中）"],
];

const aliasFailures = [];
const aliasNotes = [];

for (const [theme, vars] of Object.entries(tokenThemes)) {
  // Rule A — severity levels are an ORDERED scale; two levels sharing a color makes
  // the ordering unreadable.
  const seen = new Map();
  for (const lvl of SEVERITY_LEVELS) {
    const val = vars[`--sev-${lvl}`];
    if (!val) continue;
    const key = val.toLowerCase();
    if (seen.has(key)) {
      aliasFailures.push(
        `[${theme}] --sev-${lvl} === --sev-${seen.get(key)} (${val}) — 两个严重度等级同色，排序语义丢失`
      );
    } else {
      seen.set(key, lvl);
    }
  }

  // Rule B — sev-low must stay out of the interactive blue family. Blue means
  // "clickable" in this product; a severity badge must never look clickable.
  const low = vars["--sev-low"];
  if (low) {
    for (const [token, label] of INTERACTIVE_BLUE) {
      if (vars[token] && vars[token].toLowerCase() === low.toLowerCase()) {
        aliasFailures.push(
          `[${theme}] --sev-low === ${token} (${low}) — 低危徽章与「${label}」同色，无法与"可交互"区分`
        );
      }
    }
    if (accent600 && accent600.toLowerCase() === low.toLowerCase()) {
      aliasFailures.push(
        `[${theme}] --sev-low === accent-600 (${low}) — 低危徽章与主按钮/链接同色`
      );
    }
  }

  // Informational — fully redundant token pairs (same value in every slot).
  for (const [a, b, label] of [["--sev-info", "--sev-neutral", "severity: info / neutral"]]) {
    const slots = ["", "-fg", "-bg", "-border"];
    if (slots.every((s) => vars[a + s] && vars[a + s] === vars[b + s])) {
      aliasNotes.push(`[${theme}] ${label} — 4 个槽位全部同值，是冗余 token`);
    }
  }
}

// ---------------------------------------------------------------- report
const topHardcoded = [...hardcoded.entries()]
  .sort((a, b) => b[1] - a[1])
  .slice(0, 10)
  .map(([k, v]) => `      ${k} × ${v}`)
  .join("\n");

let failed = false;

console.log("\n[design-tokens] Design token integrity\n");
console.log(`  Files scanned            ${files.length}`);
console.log(`  Semantic token classes   ${semanticClasses.size}`);
console.log(`  Hardcoded color usages   ${hardcodedTotal}`);
if (baseline) console.log(`  Ratchet baseline         ${baseline.hardcodedColorCount}`);
console.log("");

if (deadClasses.length > 0) {
  failed = true;
  console.error(`  ❌ ${deadClasses.length} semantic token class(es) generate no CSS:`);
  console.error(deadClasses.map((c) => `      ${c}`).join("\n"));
  console.error("\n     Add them to tailwind.config.ts or stop using them.\n");
} else {
  console.log("  ✅ All semantic token classes resolve to real CSS\n");
}

if (aliasFailures.length > 0) {
  failed = true;
  console.error(`  ❌ ${aliasFailures.length} semantic alias collision(s):`);
  console.error(aliasFailures.map((a) => `      ${a}`).join("\n"));
  console.error(
    "\n     Two tokens with different meanings must not share a value.\n" +
      "     Pick a hue from a different family (see the sev-low comment in globals.css).\n"
  );
} else {
  console.log(
    `  ✅ Severity levels distinct (${SEVERITY_LEVELS.length}) · sev-low clear of the interactive blue family\n`
  );
}

if (aliasNotes.length > 0) {
  console.log("  ℹ️  Redundant tokens (informational):");
  console.log(aliasNotes.map((n) => `      ${n}`).join("\n"));
  console.log("");
}

if (baseline && hardcodedTotal > baseline.hardcodedColorCount) {
  failed = true;
  console.error(
    `  ❌ Hardcoded color count rose ${baseline.hardcodedColorCount} → ${hardcodedTotal}\n` +
      `     Use semantic tokens (text-text-*, bg-surface-*, border-border-*, severity-*, status-*, ai-*).\n`
  );
} else if (baseline) {
  console.log(
    `  ✅ Hardcoded colors within ratchet (${hardcodedTotal} ≤ ${baseline.hardcodedColorCount})\n`
  );
}

if (topHardcoded) {
  console.log("  Top hardcoded colors still to migrate:");
  console.log(topHardcoded + "\n");
}

process.exit(failed ? 1 : 0);
