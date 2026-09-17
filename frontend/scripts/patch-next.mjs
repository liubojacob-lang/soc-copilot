import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

/**
 * Patches the Next.js App Router client action queue.
 *
 * Why this exists: on Next 16.2.x the router state is handed to React as a
 * promise (`useActionQueue` → `use(state)`). `handleResult` resolves that
 * promise but never mirrors the result into React state, so the first
 * client-side navigation commits and every later one is fetched, discarded and
 * never committed — the sidebar becomes unclickable. Adding the explicit
 * `setState(nextState)` makes each navigation commit.
 *
 * This script MUST run on the exact copy of `next` that the bundler resolves.
 * `next` is hoisted to the repository root by npm, so hardcoding
 * `frontend/node_modules/next` silently skipped the patch and shipped a broken
 * router. Resolution now walks Node's own algorithm first, and any failure is
 * loud (non-zero exit) instead of a warning that lets a broken build through.
 */

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);

const RELATIVE_TARGETS = [
  "dist/client/components/app-router-instance.js",
  "dist/esm/client/components/app-router-instance.js",
];

const TARGET_SNIPPET = "        action.resolve(nextState);\n    }";
const PATCHED_SNIPPET =
  "        action.resolve(nextState);\n        setState(nextState);\n    }";

function fail(message) {
  console.error(`[patch-next] ${message}`);
  process.exit(1);
}

/** Resolve the `next` package directory the bundler will actually use. */
function resolveNextDir() {
  try {
    return path.dirname(require.resolve("next/package.json"));
  } catch {
    /* fall through to the manual walk below */
  }

  // Fallback for odd install layouts: walk up from frontend/ looking for
  // node_modules/next, which covers both the local and the hoisted copy.
  let dir = path.resolve(__dirname, "..");
  for (let i = 0; i < 5; i += 1) {
    const candidate = path.join(dir, "node_modules", "next");
    if (fs.existsSync(path.join(candidate, "package.json"))) return candidate;
    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return null;
}

const nextDir = resolveNextDir();
if (!nextDir) {
  fail("could not locate the installed `next` package. Run `npm install` first.");
}

const version = (() => {
  try {
    return require(path.join(nextDir, "package.json")).version;
  } catch {
    return "unknown";
  }
})();

let patchedCount = 0;
let alreadyCount = 0;
const missing = [];

for (const relative of RELATIVE_TARGETS) {
  const targetFile = path.join(nextDir, relative);
  if (!fs.existsSync(targetFile)) {
    missing.push(relative);
    continue;
  }

  const content = fs.readFileSync(targetFile, "utf8");

  if (content.includes(PATCHED_SNIPPET)) {
    alreadyCount += 1;
    continue;
  }

  if (!content.includes(TARGET_SNIPPET)) {
    fail(
      `cannot patch ${relative}: expected snippet not found. ` +
        `Next.js ${version} changed its router internals — re-verify the navigation fix before building.`
    );
  }

  fs.writeFileSync(targetFile, content.replace(TARGET_SNIPPET, PATCHED_SNIPPET), "utf8");
  patchedCount += 1;
}

if (patchedCount === 0 && alreadyCount === 0) {
  fail(`no patchable router files found under ${nextDir} (looked for: ${RELATIVE_TARGETS.join(", ")})`);
}

console.log(
  `[patch-next] next@${version} at ${nextDir}: patched ${patchedCount}, already patched ${alreadyCount}` +
    (missing.length ? `, not present ${missing.length}` : "")
);
