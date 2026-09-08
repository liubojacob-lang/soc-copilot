/**
 * Legacy API objects
 * Backward compatibility for older code paths that import api objects
 */

import { apiClient } from "./client";
import {
  analyzeAlert,
  buildTimeline,
  generateReport,
  generatePlaybookQueries,
  generateRemediationActions,
  getPlaybookHistory,
  getThreatIntelStats,
  healthCheck,
  lookupOTX,
  bulkLookupOTX,
} from "./alerts";
import {
  listAssets,
  getAsset,
  createAsset,
  updateAsset,
  deleteAsset,
  importAssets,
} from "./assets";
import { listHistory, getHistory, deleteHistory, deleteAllHistory } from "./history";
import {
  listPlaybookDefinitions,
  listPlaybookRuns,
  getPlaybookRun,
  createPlaybookDefinition,
  updatePlaybookDefinition,
  deletePlaybookDefinition,
  executePlaybook,
  cancelPlaybookRun,
  getRunQueueStatus,
} from "./playbooks";
import {
  listSecrets,
  getSecret,
  createSecret,
  updateSecret,
  deleteSecret,
  getKeyStatus,
  getQueueStats,
} from "./secrets";
import { listAIModelsAdmin, testModelAdmin, setDefaultModel } from "./ai";

// Legacy pages treat `api` as both an HTTP client and a namespace for domain APIs.
export const api = Object.assign(
  // Preserve the raw client methods (get/post/put/patch/delete/request)
  Object.create(apiClient),
  {
    // Assets
    listAssets,
    getAsset,
    createAsset,
    updateAsset,
    deleteAsset,
    importAssets,

    // History
    listHistory,
    getHistory,
    deleteHistory,
    deleteAllHistory,

    // Alerts / analysis
    analyzeAlert,
    buildTimeline,
    generateReport,
    generatePlaybookQueries,
    generateRemediationActions,
    getPlaybookHistory,
    getThreatIntelStats,
    healthCheck,
    lookupOTX,
    bulkLookupOTX,

    // Playbooks
    listPlaybookRuns,
    getPlaybookRun,
    createPlaybookDefinition,
    updatePlaybookDefinition,
    deletePlaybookDefinition,
    executePlaybook,
    cancelPlaybookRun,
    getRunQueueStatus,
    getAvailablePlaybooks: listPlaybookDefinitions,

    // Secrets
    listSecrets,
    getSecret,
    createSecret,
    updateSecret,
    deleteSecret,
    getKeyStatus,
    getQueueStats,
  }
);

// Legacy AI model management object
export const api_ai_models = {
  listModels: listAIModelsAdmin,
  testModel: testModelAdmin,
  setDefaultModel: setDefaultModel,
};

// Legacy queue stats object
export const api_v74 = {
  getQueueStats,
};

// Kept for backward compatibility but currently unused
export const api_v7 = apiClient;
export const api_v73 = apiClient;
export const api_triggers = apiClient;
