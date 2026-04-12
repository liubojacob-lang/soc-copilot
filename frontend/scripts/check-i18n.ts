#!/usr/bin/env tsx

/**
 * i18n Compliance Checker
 *
 * Scans frontend source files for hardcoded English text that should be internationalized.
 * Exits with code 1 if violations are found, 0 otherwise.
 *
 * Usage:
 *   npm run i18n:check
 *   tsx scripts/check-i18n.ts
 *
 * Author: Claude Code
 * Created: 2026-02-17
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
    // Skip these - they're mostly configuration or external
    "middleware",
  ],
  // Common English words/phrases that indicate hardcoded UI text
  patterns: [
    // UI Button/Action labels - must be in quotes to be UI text
    /["'](?:Save|Cancel|Delete|Edit|Create|Update|Confirm|Submit|Search|Export|Import|Download|Upload)["']/g,
    // Navigation items - in quotes
    /["'](?:Home|Dashboard|Settings|Login|Logout|Profile|Admin|Users|Help)["']/g,
    // Status messages - in quotes with context
    /["'](?:Loading|Error|Success|Failed|Warning|Info|Pending|Running)["']/g,
    // Common UI phrases - complete phrases in quotes
    /["'](?:No data found|Please try again|Are you sure|View Details|Copy to clipboard)["']/g,
    // Playbook-related terms - in quotes
    /["'](?:Playbook|Steps|Evidence|Verification|Rollback|Remediation|Impact|Severity|Summary|Entities|Recommended Actions)["']/g,
    // Alert/Security terms - in quotes
    /["'](?:Alert|Log|Analysis|Threat|Risk|Malware|Phishing|Suspicious|Incident|Correlation)["']/g,
    // Form labels - in quotes
    /["'](?:Username|Password|Email|Name|Description|Title|Content)["']/g,
    // Management pages
    /["'](?:Management|Configure|Settings|Secrets|Tokens)["']/g,
  ],
  // Patterns to exclude (false positives)
  excludePatterns: [
    // Comments
    /\/\/.*/,
    /\/\*[\s\S]*?\*\//g,
    // String literals in imports/requires
    /import.*from\s+['"][^'"]+['"]/g,
    /require\(['"][^'"]+['"]\)/g,
    // URLs
    /https?:\/\/[^\s]+/g,
    // API routes
    /\/api\/[^\s'"]+/g,
    // console.log statements
    /console\.(log|error|warn|debug)\([^)]*\)/g,

    // Type definitions and interfaces
    /:\s*['"][A-Za-z]+['"]/g,
    /interface\s+\w+\s*{[\s\S]*?}/g,
    /type\s+\w+\s*=/g,
    /enum\s+\w+\s*{[\s\S]*?}/g,

    // Function/variable declarations
    /\b(function|const|let|var)\s+\w+\s*[=:]/g,
    /\b\w+\s*:\s*\w+/g, // Type annotations

    // JSX tag names
    /<\/?\w+[\s>]/g,

    // React hooks
    /\b(use(State|Effect|Ref|Callback|Memo|Context))\(/g,

    // CSS class names
    /className=\{[^}]*\}/g,
    /className="[^"]*"/g,

    // Test data
    /expect\(.+\)\.toBe\(/g,
    /it\(['"].+['"],/g,
    /test\(['"].+['"],/g,

    // Already using t() or useTranslations
    /\bt\(['"`][^'"`]+['"`]\)/g,
    /\bt[A-Z]\w+\(['"`][^'"`]+['"`]\)/g,
    /useTranslations\([^)]*\)/g,

    // Method calls (common false positives)
    /\.\s*(toLocaleString|toFixed|toString|toLowerCase|toUpperCase|trim|substring|split|join|map|filter|reduce|find|some|every|includes|indexOf|lastIndexOf|replace|match|test|search)\s*\(/g,

    // Common technical terms that should stay in English
    /\b(Authorization|Bearer|Content-Type|application\/json)\b/g,

    // Variable names and property names (most common false positives)
    /\b(total|token|page|size|count|index|length|type|status|error|data|result|response|request|config|options|params|query|mutation|state|props|ref|key|id|name|value|label|placeholder|title|subtitle|description|message|text|content|items|list|array|object|string|number|boolean|null|undefined|true|false)\b\s*[=:]/g,

    // API field names with underscores
    /\b[a-z]+_[a-z]+(_[a-z]+)*\b/g,

    // Number and boolean literals
    /\b\d+\b/g,
    /\b(true|false|null|undefined)\b/g,

    // Empty strings or whitespace
    /['"]\s*['"]/g,
    /['"]\s*\n\s*['"]/g,

    // Object property keys (quoted)
    /['"]?\w+['"]?\s*:/g,

    // Template literals with only variables
    /`[^`]*\${[^}]*}[^`]*`/g,

    // Error class names
    /\b(new\s+)?Error\(/g,
    /throw\s+new\s+Error\(/g,

    // Async/await
    /\b(await|async|Promise)\b/g,

    // Return statements
    /\breturn\s+/g,

    // Export/import statements
    /\b(export|import|default|from)\s+/g,
  ],
};

interface Violation {
  file: string;
  line: number;
  column: number;
  pattern: string;
  match: string;
  context: string;
}

class I18nChecker {
  violations: Violation[] = [];
  filesScanned = 0;

  /**
   * Check if a directory should be excluded
   */
  shouldExclude(filePath: string): boolean {
    return CONFIG.exclude.some((excluded) => filePath.includes(excluded));
  }

  /**
   * Check if a file has valid extension
   */
  isValidExtension(filePath: string): boolean {
    return CONFIG.extensions.some((ext) => filePath.endsWith(ext));
  }

  /**
   * Scan a directory recursively
   */
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

  /**
   * Scan a single file for violations
   */
  scanFile(filePath: string, relativePath: string) {
    try {
      const content = readFileSync(filePath, "utf-8");
      const lines = content.split("\n");
      this.filesScanned++;

      lines.forEach((line, lineIndex) => {
        const lineNumber = lineIndex + 1;

        // Skip lines that are already using translations
        if (this.isLineUsingTranslations(line)) {
          return;
        }

        // Check each pattern
        CONFIG.patterns.forEach((pattern) => {
          const matches = line.matchAll(pattern);

          for (const match of matches) {
            if (this.shouldExcludeMatch(line, match)) {
              continue;
            }

            this.violations.push({
              file: relativePath,
              line: lineNumber,
              column: match.index ? match.index + 1 : 0,
              pattern: pattern.toString(),
              match: match[0],
              context: line.trim(),
            });
          }
        });
      });
    } catch (error) {
      console.error(`❌ Error scanning ${relativePath}:`, error);
    }
  }

  /**
   * Check if a line is already using translation functions
   */
  isLineUsingTranslations(line: string): boolean {
    // Lines with t('...') or t("...")
    if (/\bt\(['"`][^'"`]+['"`]\)/.test(line)) {
      return true;
    }
    // Lines with useTranslations
    if (/useTranslations/.test(line)) {
      return true;
    }
    // Lines with {t('...')} or {t("...")}
    if (/\{t\(['"`][^'"`]+['"`]\)\}/.test(line)) {
      return true;
    }
    return false;
  }

  /**
   * Check if a match should be excluded
   */
  shouldExcludeMatch(line: string, match: RegExpMatchArray): boolean {
    // Check if match is within excluded patterns
    for (const excludePattern of CONFIG.excludePatterns) {
      if (excludePattern.test(line)) {
        return true;
      }
    }

    const matchText = match[0];
    const before = line.substring(0, match.index || 0);
    const after = line.substring((match.index || 0) + matchText.length);

    // Additional heuristics to filter false positives

    // 1. Skip if it's part of a longer identifier (e.g., variable name)
    if (before.match(/\w$/) && after.match(/^\w/)) {
      return true;
    }

    // 2. Skip if it's in a string that's clearly a key or constant
    if (before.match(/['"]\s*:\s*$/) && after.match(/^\s*['"]/)) {
      return true;
    }

    // 3. Skip if it's an object property key
    if (before.match(/[{,]\s*$/) && after.match(/^\s*:/)) {
      return true;
    }

    // 4. Skip if it follows a dot (method call or property access)
    if (before.match(/\.\s*$/)) {
      return true;
    }

    // 5. Skip if it's preceded by common keywords
    if (before.match(/\b(new|typeof|instanceof|return|throw|case|in|of|delete)\s*$/)) {
      return true;
    }

    // 6. Skip variable declarations and assignments
    if (before.match(/\b(const|let|var|function)\s+\w+\s*=\s*['"]?$/) && after.match(/['"]?$/)) {
      return true;
    }

    // 7. Skip if it's a type annotation
    if (before.match(/:\s*$/) && after.match(/^\s*[,\[\]{}]/)) {
      return true;
    }

    // 8. Skip common variable names and technical terms
    const commonVariables = [
      "total",
      "count",
      "index",
      "length",
      "size",
      "page",
      "limit",
      "offset",
      "token",
      "auth",
      "user",
      "admin",
      "data",
      "result",
      "response",
      "request",
      "error",
      "status",
      "type",
      "name",
      "value",
      "key",
      "id",
      "config",
      "options",
      "params",
      "query",
      "mutation",
      "state",
      "props",
      "ref",
      "items",
      "list",
      "array",
      "object",
      "string",
      "number",
      "bool",
      "success",
      "failed",
      "pending",
      "loading",
      "running",
      "error",
      "from",
      "to",
      "at",
      "in",
      "of",
      "by",
      "with",
      "for",
      "and",
      "or",
      "step",
      "node",
      "edge",
      "graph",
      "tree",
      "list",
      "map",
      "set",
      "start",
      "end",
      "begin",
      "finish",
      "complete",
      "incomplete",
      "add",
      "remove",
      "update",
      "delete",
      "insert",
      "append",
      "prepend",
      "get",
      "set",
      "has",
      "check",
      "find",
      "search",
      "filter",
      "sort",
      "create",
      "read",
      "write",
      "update",
      "delete",
      "list",
      "true",
      "false",
      "null",
      "undefined",
      "void",
      "never",
      "unknown",
      "string",
      "number",
      "boolean",
      "object",
      "array",
      "function",
      "void",
      "any",
      "never",
      "unknown",
      "this",
      "super",
      "static",
      "public",
      "private",
      "protected",
      "async",
      "await",
      "promise",
      "resolve",
      "reject",
      "class",
      "interface",
      "type",
      "enum",
      "namespace",
      "module",
      "import",
      "export",
      "default",
      "from",
      "as",
    ];

    if (commonVariables.includes(matchText.toLowerCase())) {
      // Only exclude if it looks like a variable/property, not UI text
      if (before.match(/[\w.]\s*$/) || after.match(/^\s*[=:\[\]\),}]/)) {
        return true;
      }
    }

    // 9. Skip if it's in template literal
    if (before.includes("`") && !after.includes("`")) {
      return true;
    }

    // 10. Skip if it's a number or special value
    if (/^\d+$/.test(matchText) || /^(true|false|null|undefined)$/.test(matchText)) {
      return true;
    }

    // 11. Skip if it's an API endpoint or path
    if (before.includes("'") || before.includes('"')) {
      const quoteChar = before.endsWith("'") ? "'" : '"';
      if (
        before.endsWith(quoteChar + "/") &&
        (after.startsWith("/") || after.startsWith(quoteChar))
      ) {
        return true;
      }
    }

    // 12. Skip common technical patterns
    if (/^[a-z]+_[a-z_]+$/.test(matchText)) {
      return true; // snake_case identifiers
    }

    return false;
  }

  /**
   * Print results
   */
  printResults() {
    console.log("\n📊 Scan Results:");
    console.log(`   Files scanned: ${this.filesScanned}`);
    console.log(`   Violations found: ${this.violations.length}\n`);

    if (this.violations.length === 0) {
      console.log("✅ No hardcoded English text found!\n");
      console.log("All files are properly internationalized. Great job! 🎉\n");
      return;
    }

    console.log("❌ Hardcoded English text found:\n");

    // Group by file
    const byFile = new Map<string, Violation[]>();
    this.violations.forEach((v) => {
      if (!byFile.has(v.file)) {
        byFile.set(v.file, []);
      }
      byFile.get(v.file)!.push(v);
    });

    // Print violations grouped by file
    byFile.forEach((violations, file) => {
      console.log(`\n📄 ${file}`);
      console.log(`   ${violations.length} violation(s):\n`);

      violations.slice(0, 10).forEach((v) => {
        // Limit to 10 per file
        console.log(`   Line ${v.line}:${v.column}`);
        console.log(`   Pattern: ${v.match}`);
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
    console.log('   1. Replace hardcoded text with t("key") or useTranslations()');
    console.log("   2. Add translation keys to messages/en.json and messages/zh.json");
    console.log("   3. Run npm run i18n:check again to verify fixes\n");
  }

  /**
   * Run the checker
   */
  run(baseDir: string = process.cwd()): number {
    const frontendDir = join(baseDir);

    console.log("🔍 Scanning for hardcoded English text...\n");

    CONFIG.directories.forEach((dir) => {
      const fullPath = join(frontendDir, dir);
      if (existsSync(fullPath)) {
        this.scanDirectory(fullPath, frontendDir);
      }
    });

    this.printResults();

    // Exit code: 0 if no violations, 1 if violations found
    return this.violations.length === 0 ? 0 : 1;
  }
}

// Run the checker
const checker = new I18nChecker();
const exitCode = checker.run();
process.exit(exitCode);
