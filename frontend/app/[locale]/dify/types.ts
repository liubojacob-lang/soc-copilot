/** Dify integration types and interfaces */

export interface DifyWorkflow {
  id: string;
  name: string;
  description: string;
  mode: string;
  created_at: string;
  updated_at: string;
}

export interface DifyConfig {
  configured: boolean;
  connected: boolean;
  api_url: string;
  api_key?: string;
  workspace_id?: string;
}

export interface DifyConfigForm {
  difyApiUrl: string;
  difyApiKey: string;
  difyWorkspaceId: string;
}
