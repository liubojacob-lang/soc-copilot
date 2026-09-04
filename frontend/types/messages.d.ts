/**
 * Global translation types
 *
 * Messages catalog is sourced from messages/zh-CN.json (authoritative single-file catalog).
 * Use npm run i18n:sync to keep per-namespace files and single catalogs synchronized.
 * Use npm run i18n:test or node scripts/check-i18n-keys.mjs to verify key integrity.
 */

export type Messages = typeof import("../messages/zh-CN.json");
export type TranslationKey = keyof Messages;
