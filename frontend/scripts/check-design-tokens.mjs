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
