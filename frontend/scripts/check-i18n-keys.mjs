#!/usr/bin/env node
/**
 * i18n key integrity checker — complements check-i18n-v2.ts (hardcoded-text scan).
 *
 * Checks:
 *  1. en.json ↔ zh-CN.json key parity (both directions)
 *  2. Every t("key") referenced in code resolves in BOTH catalogs
 *     (handles one file declaring the same hook variable under several namespaces)
 *  3. Per-namespace files under messages/<locale>/ stay in sync with the
 *     authoritative single-file catalog produced by sync-i18n.mjs
 *  4. Hardcoded CJK strings outside comments (English locale would show Chinese)
 *
 * Exit code 1 on parity / missing-key / drift failures; CJK findings are warnings.
 */
import { readFileSync, readdirSync, statSync } from "fs";
import { join, relative } from "path";

const ROOT = join(import.meta.dirname, "..");
const WARN_ONLY = process.argv.includes("--warn-only");

function flatten(obj, prefix = "") {
  const out = {};
  for (const [k, v] of Object.entries(obj ?? {})) {
    const key = prefix ? `${prefix}.${k}` : k;
    if (v && typeof v === "object" && !Array.isArray(v)) Object.assign(out, flatten(v, key));
    else out[key] = v;
  }
  return out;
}

const catalogs = {};
for (const locale of ["en", "zh-CN"]) {
  catalogs[locale] = flatten(JSON.parse(readFileSync(join(ROOT, "messages", `${locale}.json`), "utf8")));
}
const [enKeys, zhKeys] = [Object.keys(catalogs.en), Object.keys(catalogs["zh-CN"])];
const enSet = new Set(enKeys);
const zhSet = new Set(zhKeys);
const hasKey = (set, key) => set.has(key) || enKeys.some((k) => k.startsWith(`${key}.`)) || zhKeys.some((k) => k.startsWith(`${key}.`));

let failed = false;

// ---------- 1. parity ----------
const missingInZh = enKeys.filter((k) => !zhSet.has(k));
const missingInEn = zhKeys.filter((k) => !enSet.has(k));
if (missingInZh.length || missingInEn.length) {
  failed = true;
  console.log(`\n❌ [parity] en/zh key sets differ`);
  missingInZh.forEach((k) => console.log(`   missing in zh-CN: ${k}`));
  missingInEn.forEach((k) => console.log(`   missing in en:    ${k}`));
} else {
  console.log(`✅ [parity] en.json and zh-CN.json both have ${enKeys.length} keys`);
}

// ---------- 2. reverse key resolution ----------
function walk(dir, acc = []) {
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, e.name);
    if (e.isDirectory()) walk(p, acc);
    else if (/\.(tsx?|jsx?)$/.test(e.name) && !e.name.includes(".test.")) acc.push(p);
  }
  return acc;
}
const sourceFiles = ["app", "components", "hooks", "lib"].flatMap((d) => {
  const dir = join(ROOT, d);
  try {
    return walk(dir);
  } catch {
    return [];
  }
});

const unresolved = new Map();
let callsChecked = 0;
for (const file of sourceFiles) {
  const src = readFileSync(file, "utf8");
  // hook var -> every namespace it is declared with in this file
  const nsVars = {};
  for (const line of src.split("\n")) {
    const m = line.match(/const\s+(\w+)\s*=\s*(?:useTranslations|getTranslations)\((?:\s*["']([^"']+)["'])?\)/);
    if (m) (nsVars[m[1]] ??= new Set()).add(m[2] ?? "");
    const nsComment = line.match(/(?:\/\/|\*)\s*i18n-namespace:\s*([a-zA-Z0-9_.-]+)/);
    if (nsComment) (nsVars["t"] ??= new Set()).add(nsComment[1]);
  }
  // Sub-components in ai-assistant receive t scoped to aiAssistant
  if (file.includes("app/[locale]/ai-assistant/components") || file.includes("app/[locale]/ai-assistant/utils")) {
    (nsVars["t"] ??= new Set()).add("aiAssistant");
  }
  for (const [varName, namespaces] of Object.entries(nsVars)) {
    const re = new RegExp(`\\b${varName}\\(\\s*["']([^"']+)["']`, "g");
    let m;
    while ((m = re.exec(src))) {
      callsChecked++;
      const key = m[1];
      if (key.includes("$")) continue; // dynamic key, cannot verify statically
      const found = [...namespaces].some((ns) => {
        const full = ns === "." || ns === "" ? key : `${ns}.${key}`;
        return hasKey(enSet, full) && hasKey(zhSet, full);
      });
      if (!found) {
        const rel = relative(ROOT, file);
        if (!unresolved.has(rel)) unresolved.set(rel, new Map());
        const entry = unresolved.get(rel);
        const id = `${[...namespaces].join("|")}::${key}`;
        entry.set(id, (entry.get(id) ?? 0) + 1);
      }
    }
  }
}

const unresolvedCount = [...unresolved.values()].reduce((n, m) => n + m.size, 0);
if (unresolvedCount > 0) {
  failed = true;
  console.log(`\n❌ [keys] ${unresolvedCount} t() keys referenced in code are missing from catalogs (of ~${callsChecked} calls):`);
  for (const [file, keys] of unresolved) {
    console.log(`   ${file}`);
    for (const [id, n] of keys) {
      const [ns, key] = id.split("::");
      console.log(`      ns(${ns}) -> "${key}"${n > 1 ? ` x${n}` : ""}`);
    }
  }
} else {
  console.log(`✅ [keys] all ~${callsChecked} t() calls resolve in both catalogs`);
}

// ---------- 3. ns sub-file sync vs single catalog ----------
let drift = 0;
for (const locale of ["en", "zh-CN"]) {
  const single = catalogs[locale];
  const nsDir = join(ROOT, "messages", locale);
  const nsFlat = {};
  for (const f of readdirSync(nsDir).filter((f) => f.endsWith(".json"))) {
    Object.assign(nsFlat, flatten(JSON.parse(readFileSync(join(nsDir, f), "utf8"))));
  }
  for (const [k, v] of Object.entries(nsFlat)) {
    if (!(k in single)) {
      console.log(`⚠️  [sync] ${locale}/${k} exists in ns files but not in single catalog (sync-i18n.mjs will add it)`);
      drift++;
    } else if (JSON.stringify(single[k]) !== JSON.stringify(v)) {
      console.log(`❌ [sync] value drift at ${locale}:${k}`);
      drift++;
      failed = true;
    }
  }
}
if (drift === 0) console.log("✅ [sync] per-namespace files are in sync with single-file catalogs");

// ---------- 4. hardcoded CJK outside comments (warning) ----------
const cjkFiles = new Map();
for (const file of sourceFiles) {
  const rel = relative(ROOT, file);
  if (rel.startsWith("messages")) continue;
  const lines = readFileSync(file, "utf8").split("\n");
  lines.forEach((line, i) => {
    const trimmed = line.trim();
    if (!/[\u4e00-\u9fff]/.test(trimmed)) return;
    // skip comment-only lines and trailing comments after code
    const code = trimmed.replace(/\/\/.*$/, "").replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\*.*$/, "").replace(/\*.*$/, "");
    if (!/[\u4e00-\u9fff]/.test(code)) return;
    if (!cjkFiles.has(rel)) cjkFiles.set(rel, []);
    cjkFiles.get(rel).push(`${i + 1}: ${trimmed.slice(0, 90)}`);
  });
}
if (cjkFiles.size > 0) {
  const total = [...cjkFiles.values()].reduce((n, l) => n + l.length, 0);
  console.log(`\n⚠️  [cjk] ${total} possibly user-visible CJK lines in ${cjkFiles.size} files (review manually):`);
  for (const [file, lines] of cjkFiles) {
    console.log(`   ${file}`);
    lines.slice(0, 5).forEach((l) => console.log(`      ${l}`));
    if (lines.length > 5) console.log(`      ... +${lines.length - 5} more`);
  }
} else {
  console.log("✅ [cjk] no hardcoded CJK found in source");
}

console.log("");
if (failed && !WARN_ONLY) {
  console.log("❌ i18n key check FAILED");
  process.exit(1);
}
console.log("✅ i18n key check passed");
