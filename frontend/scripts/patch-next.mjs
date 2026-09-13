import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const targetFile = path.resolve(
  __dirname,
  "../node_modules/next/dist/client/components/app-router-instance.js"
);

if (fs.existsSync(targetFile)) {
  let content = fs.readFileSync(targetFile, "utf8");
  const targetSnippet = "action.resolve(nextState);\n    }";
  const patchedSnippet = "action.resolve(nextState);\n        setState(nextState);\n    }";

  if (content.includes("setState(nextState);")) {
    console.log("[patch-next] Already patched.");
  } else if (content.includes(targetSnippet)) {
    content = content.replace(targetSnippet, patchedSnippet);
    fs.writeFileSync(targetFile, content, "utf8");
    console.log("[patch-next] Successfully patched app-router-instance.js.");
  } else {
    console.warn("[patch-next] Target snippet not found in app-router-instance.js, skipping.");
  }
} else {
  console.log("[patch-next] next node_modules not found, skipping.");
}
