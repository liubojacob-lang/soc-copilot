#!/usr/bin/env tsx

/**
 * i18n Compliance Checker v2
 * Improved version with better false positive filtering
 */

import { readFileSync, readdirSync, statSync, existsSync } from "fs";
import { join, relative } from "path";

// Configuration
const CONFIG = {
  directories: ["app", "components", "lib"],
  extensions: [".tsx", ".ts", ".jsx", ".js"],
  exclude: [
    "node_modules",
    ".next",
    "dist",
    "build",
    "messages",
    "i18n",
    "api",
    "middleware",
    ".next",
  ],

  // Patterns for hardcoded UI text (more specific but still catches real issues)
  patterns: [
    // Direct JSX content (most common real issue)
    />(Save|Cancel|Delete|Edit|Create|Update|Confirm|Submit|Search|Export|Import|Download|Upload|Loading|Error|Success|Failed)<\//g,

    // Complete UI phrases in quotes
    /["']((?:Are you sure|No data found|Please try again|View Details|Copy to clipboard))["']/g,

    // Multi-word UI labels in quotes
    /["']([A-Z][a-z]+(?:[ ][A-Z][a-z]+)+)["']/g,

    // Common form labels
    /["'](Username|Password|Email Address|Phone Number)["']/g,

    // Management pages
    /["']Secrets? Management["']/g,
    /["']User Management["']/g,
    /["']Create (?:Secret|User|Admin)["']/g,
  ],

  // Context patterns that indicate we should skip a match
  excludeContexts: [
    // Already using translations
    /\bt\(['"`][^'"`]+['"`]\)/,
    /\btCommon\(['"`][^'"`]+['"`]\)/,
    /useTranslations/,

    // Console statements
    /console\.(log|error|warn|debug|info)/,

    // Type definitions
    /interface\s+\w+/,
    /type\s+\w+\s*=/,
    /enum\s+\w+/,

    // Imports
    /import\s+.*from/,
    /require\(/,

    // Comments
    /\/\/.*$/,
    /\/\*[\s\S]*?\*\//,

    // Variable names (with common patterns)
    /\b(const|let|var)\s+\w+\s*[:=]/,

    // Function definitions
    /function\s+\w+\s*\(/,
    /\w+\s*:\s*\w+\s*=>/,

    // JSX tags (not content)
    /<[A-Z]\w+/,
    /<\/[A-Z]\w+/,

    // Object property keys (likely not UI text)
    /\w+\s*:\s*["']/,

    // Method calls
    /\.\w+\s*\(/,

    // Technical terms
    /\b(Authorization|Bearer|Content-Type|application\/json)\b/,

    // Common variable names
    /\b(data|error|result|response|request|config|options|params|state|props)\b\s*[=:]/,

    // API paths
    /\/api\//,
    /https?:\/\//,
  ],
};

interface Violation {
  file: string;
  line: number;
  column: number;
  match: string;
  context: string;
}

class I18nChecker {
  violations: Violation[] = [];
  filesScanned = 0;

  shouldExclude(filePath: string): boolean {
    return CONFIG.exclude.some((excluded) => filePath.includes(excluded));
  }

  isValidExtension(filePath: string): boolean {
    return CONFIG.extensions.some((ext) => filePath.endsWith(ext));
  }

  scanDirectory(dir: string, baseDir: string) {
    if (!existsSync(dir)) {
      console.warn(`⚠️  Directory not found: ${dir}`);
      return;
    }

    const items = readdirSync(dir);

    for (const item of items) {
      const fullPath = join(dir, item);
      const relativePath = relative(baseDir, fullPath);
      const stat = statSync(fullPath);

      if (stat.isDirectory()) {
        if (!this.shouldExclude(relativePath)) {
          this.scanDirectory(fullPath, baseDir);
        }
      } else if (stat.isFile() && this.isValidExtension(item)) {
        this.scanFile(fullPath, relativePath);
      }
    }
  }

  scanFile(filePath: string, relativePath: string) {
    try {
      const content = readFileSync(filePath, "utf-8");
      const lines = content.split("\n");
      this.filesScanned++;

      lines.forEach((line, lineIndex) => {
        const lineNumber = lineIndex + 1;
        const trimmedLine = line.trim();

        // Skip empty lines
        if (!trimmedLine) return;

        // Skip if line has exclusion context
        if (this.shouldExcludeLine(trimmedLine)) return;

        // Check each pattern
        CONFIG.patterns.forEach((pattern) => {
          // Reset regex state
          pattern.lastIndex = 0;

          const matches = trimmedLine.matchAll(pattern);
          for (const match of matches) {
            if (match.index !== undefined) {
              this.violations.push({
                file: relativePath,
                line: lineNumber,
                column: match.index + 1,
                match: match[0] || match[1] || "",
                context: trimmedLine,
              });
            }
          }
        });
      });
    } catch (error) {
      console.error(`❌ Error scanning ${relativePath}:`, error);
    }
  }

  shouldExcludeLine(line: string): boolean {
    return CONFIG.excludeContexts.some((pattern) => pattern.test(line));
  }

  printResults() {
    console.log("\n📊 Scan Results:");
    console.log(`   Files scanned: ${this.filesScanned}`);
    console.log(`   Violations found: ${this.violations.length}\n`);

    if (this.violations.length === 0) {
      console.log("✅ No hardcoded UI text found!\n");
      console.log("All files are properly internationalized. Great job! 🎉\n");
      return 0;
    }

    console.log("❌ Hardcoded UI text found:\n");

    // Group by file
    const byFile = new Map<string, Violation[]>();
    this.violations.forEach((v) => {
      if (!byFile.has(v.file)) {
        byFile.set(v.file, []);
      }
      byFile.get(v.file)!.push(v);
    });

    // Print violations
    byFile.forEach((violations, file) => {
      console.log(`📄 ${file}`);
      console.log(`   ${violations.length} violation(s):\n`);

      violations.slice(0, 10).forEach((v) => {
        console.log(`   Line ${v.line}:${v.column}`);
        console.log(`   Text: "${v.match}"`);
        console.log(
          `   Context: ${v.context.substring(0, 80)}${v.context.length > 80 ? "..." : ""}`
        );
        console.log("");
      });

      if (violations.length > 10) {
        console.log(`   ... and ${violations.length - 10} more\n`);
      }
    });

    console.log("\n💡 Suggestions:");
    console.log('   1. Replace hardcoded text with t("key")');
    console.log("   2. Add translation keys to messages/en.json and messages/zh.json");
    console.log("   3. Run npm run i18n:check again to verify fixes\n");

    return 1;
  }

  run(baseDir: string = process.cwd()): number {
    console.log("🔍 Scanning for hardcoded UI text...\n");

    CONFIG.directories.forEach((dir) => {
      const fullPath = join(baseDir, dir);
      if (existsSync(fullPath)) {
        this.scanDirectory(fullPath, baseDir);
      }
    });

    return this.printResults();
  }
}

// Run the checker
const checker = new I18nChecker();
process.exit(checker.run());
