import { readFileSync, writeFileSync, readdirSync, existsSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const messagesDir = join(__dirname, "..", "messages");

function deepMerge(target, source) {
  const result = { ...target };
  for (const key of Object.keys(source)) {
    const targetVal = result[key];
    const sourceVal = source[key];
    if (
      targetVal &&
      typeof targetVal === "object" &&
      !Array.isArray(targetVal) &&
      sourceVal &&
      typeof sourceVal === "object" &&
      !Array.isArray(sourceVal)
    ) {
      result[key] = deepMerge(targetVal, sourceVal);
    } else {
      result[key] = sourceVal;
    }
  }
  return result;
}

const locales = ["zh-CN", "en"];

for (const locale of locales) {
  const singleFilePath = join(messagesDir, `${locale}.json`);
  const localeSubDir = join(messagesDir, locale);

  let merged = {};
  if (existsSync(singleFilePath)) {
    try {
      merged = JSON.parse(readFileSync(singleFilePath, "utf-8"));
    } catch {
      merged = {};
    }
  }

  if (existsSync(localeSubDir)) {
    const files = readdirSync(localeSubDir).filter((f) => f.endsWith(".json"));
    for (const file of files) {
      const fullPath = join(localeSubDir, file);
      try {
        const content = JSON.parse(readFileSync(fullPath, "utf-8"));
        merged = deepMerge(merged, content);
      } catch (err) {
        console.error(`Failed to parse ${fullPath}:`, err);
      }
    }
  }

  writeFileSync(singleFilePath, JSON.stringify(merged, null, 2) + "\n", "utf-8");
  console.log(`[i18n sync] ✅ Synchronized ${locale}.json with ${Object.keys(merged).length} root namespaces.`);
}
