/**
 * i18n Test Script
 * 检查翻译文件的完整性
 */

import * as en from "../messages/en.json";
import * as zh from "../messages/zh.json";

// 检查两个文件的键是否一致
function checkKeys(obj1: any, obj2: any, path = ""): string[] {
  const errors: string[] = [];
  const keys1 = Object.keys(obj1);
  const keys2 = Object.keys(obj2);

  // 检查en中有但zh中没有的键
  for (const key of keys1) {
    const currentPath = path ? `${path}.${key}` : key;
    if (!(key in obj2)) {
      errors.push(`Missing in zh: ${currentPath}`);
    } else if (typeof obj1[key] === "object" && obj1[key] !== null) {
      errors.push(...checkKeys(obj1[key], obj2[key], currentPath));
    }
  }

  // 检查zh中有但en中没有的键
  for (const key of keys2) {
    const currentPath = path ? `${path}.${key}` : key;
    if (!(key in obj1)) {
      errors.push(`Missing in en: ${currentPath}`);
    }
  }

  return errors;
}

// 检查英文残留（zh.json中的英文值）
function checkEnglishResiduals(obj: any, path = ""): string[] {
  const errors: string[] = [];

  for (const key of Object.keys(obj)) {
    const currentPath = path ? `${path}.${key}` : key;
    const value = obj[key];

    if (typeof value === "string") {
      // 检查是否包含明显的英文单词（长度>3且全是英文）
      const englishWords = value.match(/[a-zA-Z]{4,}/g);
      if (englishWords && englishWords.length > 0) {
        // 排除一些常见的保留词
        const reservedWords = [
          "API",
          "URL",
          "ID",
          "JSON",
          "CSV",
          "PDF",
          "HTML",
          "SQL",
          "IP",
          "SSL",
          "TLS",
          "SSH",
          "HTTP",
          "HTTPS",
        ];
        const nonReserved = englishWords.filter((w) => !reservedWords.includes(w.toUpperCase()));
        if (nonReserved.length > 0) {
          errors.push(`English residual at ${currentPath}: "${value}"`);
        }
      }
    } else if (typeof value === "object" && value !== null) {
      errors.push(...checkEnglishResiduals(value, currentPath));
    }
  }

  return errors;
}

console.log("🔍 Testing i18n files...\n");

// 检查键一致性
const keyErrors = checkKeys(en, zh);
if (keyErrors.length > 0) {
  console.log("❌ Key mismatches found:");
  keyErrors.forEach((e) => console.log(`  - ${e}`));
} else {
  console.log("✅ All keys match between en.json and zh.json");
}

console.log("\n");

// 检查英文残留
const residualErrors = checkEnglishResiduals(zh);
if (residualErrors.length > 0) {
  console.log("⚠️  English residuals found in zh.json:");
  residualErrors.slice(0, 20).forEach((e) => console.log(`  - ${e}`));
  if (residualErrors.length > 20) {
    console.log(`  ... and ${residualErrors.length - 20} more`);
  }
} else {
  console.log("✅ No English residuals found in zh.json");
}

console.log("\n📊 Summary:");
console.log(`   Key errors: ${keyErrors.length}`);
console.log(`   English residuals: ${residualErrors.length}`);
