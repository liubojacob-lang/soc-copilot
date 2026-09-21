#!/usr/bin/env node
/**
 * JSX 硬编码中文检查 + 棘轮
 * =============================================================================
 * 为什么需要这一道：
 * `check-i18n-keys.mjs` 只校验「键在 en / zh-CN 两侧是否对齐」。
 * 它管不了「已经接入 i18n，却把文案绕过 t() 直接写死」——那种写法键层面完全正常，
 * 静态检查看不见，只有切到 /en 才会露馅。
 *
 * 查的是 **JSX 里出现的字面中文**，三类写法都覆盖：
 *   ① 文本节点        <span>保存</span>       （含"文本单独一行"的写法）
 *   ② 属性值          <input placeholder="请输入" />、aria-label / title / alt
 *   ③ 字符串字面量    {a ? "是" : "否"}       （中文在 {} 表达式里，①②都漏）
 *
 * 刻意不查：
 *   · 注释（// * /*）——注释是给开发者看的
 *   · .ts / .json ——.ts 里没有 JSX；messages/*.json 本来就是中文文案
 *   · LanguageSwitcher.tsx —— 语言选项必须显示原生名（见 ALLOWED_FILES）
 *
 * 棘轮：存量太大时不阻断 CI，但**只许下降、不许上升**。修完一批后跑 `--update`
 * 收紧基线，此后新增任何一处都会失败。
 *
 * 用法：
 *   node scripts/check-jsx-cjk.mjs             # 检查（对比棘轮基线）
 *   node scripts/check-jsx-cjk.mjs --update    # 把当前值写为新的基线
 *   node scripts/check-jsx-cjk.mjs --list      # 列出全部命中（调试用）
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const BASELINE_FILE = path.join(ROOT, ".i18n-cjk-baseline.json");

const DIRS = ["app", "components"];
const CJK = /[\u4e00-\u9fff]/;

/** 整文件豁免：该文件里的中文全部是合理的（对象字面量，不是 JSX 文案）。 */
const ALLOWED_FILES = [
  {
    file: "components/LanguageSwitcher.tsx",
    reason: "语言选项必须显示原生名——中文用户要认得出自己的语言，本地化反而有害",
  },
];

// ① 文本节点。[^<>] 本身包含 \n，所以能覆盖"文本单独一行"的写法。
//    （早先写成 [^<>{}\n] 会把这种最常见的写法漏掉）
const TEXT_NODE = />([^<>]*[\u4e00-\u9fff][^<>]*)</g;

// ② 属性值
const ATTR_WITH_CJK =
  /\b(?:title|placeholder|aria-label|label|alt|description|content)\s*=\s*\{?\s*"([^"]*[\u4e00-\u9fff][^"]*)"/g;

// ③ 兜底：任何含 CJK 的单行字符串字面量
const STRING_LITERAL = /"([^"\n]*[\u4e00-\u9fff][^"\n]*)"/g;

function walk(dir, out = []) {
  if (!fs.existsSync(dir)) return out;
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (["node_modules", ".next", "venv", "coverage"].includes(entry.name)) continue;
      if (entry.name.startsWith(".")) continue;
      walk(full, out);
    } else if (/\.tsx$/.test(entry.name)) {
      out.push(full);
    }
  }
  return out;
}

const hits = [];

for (const dir of DIRS) {
  for (const file of walk(path.join(ROOT, dir))) {
    const rel = path.relative(ROOT, file);
    if (ALLOWED_FILES.some((a) => a.file === rel)) continue;

    const lines = fs.readFileSync(file, "utf8").split("\n");
    const seen = new Set();

    lines.forEach((raw, i) => {
      const lineNo = i + 1;
      if (/^\s*(\/\/|\*|\/\*)/.test(raw)) return; // 注释

      const add = (kind, text) => {
        const t = text.trim().slice(0, 40);
        const key = `${lineNo}|${t}`;
        if (seen.has(key)) return; // 同一行同一文案可能被多条规则命中
        seen.add(key);
        hits.push({ file: rel, line: lineNo, kind, text: t });
      };

      let m;
      TEXT_NODE.lastIndex = 0;
      while ((m = TEXT_NODE.exec(raw))) add("文本节点", m[1]);
      ATTR_WITH_CJK.lastIndex = 0;
      while ((m = ATTR_WITH_CJK.exec(raw))) add("属性", m[1]);
      STRING_LITERAL.lastIndex = 0;
      while ((m = STRING_LITERAL.exec(raw))) add("字符串", m[1]);
    });
  }
}

const listOnly = process.argv.includes("--list");
const update = process.argv.includes("--update");

/**
 * 条目键按 **(文件, 文案)**，不按行号 ——
 * 否则修掉一处后，同一个文件里其余条目的行号全变，会被误判成"新增一堆"。
 */
const entryKey = (h) => `${h.file}|${h.text}`;

function readBaseline() {
  try {
    const b = JSON.parse(fs.readFileSync(BASELINE_FILE, "utf8"));
    return { count: b.count, keys: new Set(b.entries || []) };
  } catch {
    return null;
  }
}

const show = (list) => {
  for (const h of list) {
    console.log(`     ${h.file}:${h.line}  [${h.kind}] "${h.text}"`);
  }
};

// ── --update：写基线 ──────────────────────────────────────────────────────────
if (update) {
  fs.writeFileSync(
    BASELINE_FILE,
    JSON.stringify(
      {
        count: hits.length,
        entries: [...new Set(hits.map(entryKey))].sort(),
        updatedAt: new Date().toISOString().slice(0, 10),
        note: "棘轮基线：只许下降。修完一批后重新 --update 收紧。",
      },
      null,
      2,
    ) + "\n",
  );
  console.log(`  ✅ 棘轮基线已写入：${hits.length} 处（只许下降）`);
  process.exit(0);
}

// ── --list：全量列出 ──────────────────────────────────────────────────────────
if (listOnly) {
  console.log(`  共 ${hits.length} 处：\n`);
  show(hits);
  process.exit(0);
}

const baseline = readBaseline();

// ── 无基线：按存量处理 ────────────────────────────────────────────────────────
if (baseline === null) {
  if (hits.length === 0) {
    console.log("  ✅ JSX 无硬编码中文（0 处）");
    process.exit(0);
  }
  console.log(`  ❌ JSX 硬编码中文 ${hits.length} 处（尚未建立基线）\n`);
  show(hits.slice(0, 40));
  if (hits.length > 40) console.log(`     … 另 ${hits.length - 40} 处`);
  console.log("\n  先跑 --update 记录存量，之后棘轮只许下降。");
  process.exit(1);
}

// ── 有基线：棘轮判定 ──────────────────────────────────────────────────────────
if (hits.length > baseline.count) {
  // 只报新增的 —— 否则失败时刷出几十条存量，看不出到底多了哪一处
  const added = hits.filter((h) => !baseline.keys.has(entryKey(h)));
  console.log(
    `  ❌ JSX 硬编码中文 ${hits.length} 处，超过基线 ${baseline.count} —— 新增 ${added.length} 处\n`,
  );
  show(added.length ? added : hits.slice(0, 40));
  console.log("\n  修法：文案抽到 messages/{en,zh-CN}/*.json，组件改用 t(\"key\")。");
  console.log("  确属合理的（如语言选项原生名）请加进 ALLOWED_FILES 并写明理由。");
  process.exit(1);
}

if (hits.length < baseline.count) {
  console.log(
    `  ✅ ${hits.length} 处（基线 ${baseline.count}，已下降 ${baseline.count - hits.length}）`,
  );
  console.log("     建议跑 --update 收紧基线，把成果锁住。");
  process.exit(0);
}

console.log(`  ✅ ${hits.length} 处，与基线持平`);
process.exit(0);
