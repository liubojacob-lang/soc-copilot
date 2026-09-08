/**
 * API Module
 * Barrel re-export from lib/api/ modular structure.
 * This file exists for backward compatibility with existing imports.
 * New code should import from @/lib/api/ directly.
 */

export * from "./api/index";
export { api, api_v7, api_triggers, api_v74, api_v73, api_ai_models } from "./api/index";
