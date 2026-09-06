/** Playbooks page types and constants */

export interface PlaybookRun {
  id: string;
  playbook_name: string;
  status: string;
  mode: string;
  started_at: string;
  finished_at: string | null;
}

export interface PlaybookMetadata {
  name: string;
  description: string;
  version: string;
  estimated_duration_seconds: number;
  steps: Record<string, unknown>[];
}

export interface QueueStats {
  running: number;
  queued: number;
  max_concurrent: number;
}

export const STATUS_COLORS: Record<string, string> = {
  pending: "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300",
  running: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300",
  success: "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300",
  failed: "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300",
  partial: "bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300",
  skipped: "bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400",
  queued: "bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300",
};

export const MODE_COLORS: Record<string, string> = {
  dry_run: "bg-purple-50 text-purple-700 dark:bg-purple-900/50 dark:text-purple-300",
  apply: "bg-red-50 text-red-700 dark:bg-red-900/50 dark:text-red-300",
};

// ── DAG definition types & helpers (shared by create / detail / edit pages) ──

export interface DagNodeDef {
  id: string;
  type: string;
  step_id: string;
  name: string;
  position_x?: number;
  position_y?: number;
  action?: string;
  inputs?: Record<string, unknown>;
}

export interface DagEdgeDef {
  source: string;
  target: string;
  condition?: string;
}

export interface DagDefinition {
  nodes: DagNodeDef[];
  edges: DagEdgeDef[];
}

export const VALID_NODE_TYPES = new Set([
  "ti_lookup_otx",
  "extract_iocs",
  "parse_json",
  "decision",
  "sleep",
  "http_request",
  "asset_enrich",
  "risk_score",
  "action_plan",
  "timeline_build",
  "slack_notify",
  "normalize",
  "generate_report",
  "human_approval",
]);

export const TYPE_ALIASES: Record<string, string> = {
  alert_ingest: "parse_json",
  parse: "parse_json",
  enrich_ti: "ti_lookup_otx",
  ti_lookup: "ti_lookup_otx",
  iocs: "extract_iocs",
  ioc_extract: "extract_iocs",
  notify: "slack_notify",
  email: "slack_notify",
  webhook: "http_request",
  api: "http_request",
  report: "generate_report",
  approval: "human_approval",
  risk: "risk_score",
  timeline: "timeline_build",
  enrich: "asset_enrich",
  condition: "decision",
};

export function normalizeNodeType(raw?: string): string {
  if (!raw) return "parse_json";
  const trimmed = raw.trim().toLowerCase();
  if (VALID_NODE_TYPES.has(trimmed)) return trimmed;
  if (TYPE_ALIASES[trimmed]) return TYPE_ALIASES[trimmed];
  return "parse_json";
}

/**
 * Parse and sanitize a DAG JSON document ({ nodes: [], edges: [] }).
 * Throws Error with a user-facing message when the document is invalid.
 */
export function parseDagDefinition(text: string): DagDefinition {
  const parsed = JSON.parse(text) as Record<string, unknown>;
  if (!Array.isArray(parsed.nodes) || !Array.isArray(parsed.edges)) {
    throw new Error("JSON 必须包含 'nodes' 数组与 'edges' 数组");
  }
  return {
    nodes: (parsed.nodes as Record<string, unknown>[]).map((n, idx) => ({
      id: typeof n.id === "string" ? n.id : `node-${idx + 1}`,
      type: normalizeNodeType((n.type || n.action || n.step_id) as string),
      step_id: typeof n.step_id === "string" ? n.step_id : (n.id as string) || `step_${idx + 1}`,
      name: typeof n.name === "string" ? n.name : (n.id as string) || `节点 ${idx + 1}`,
      position_x: typeof n.position_x === "number" ? n.position_x : 60 + idx * 260,
      position_y: typeof n.position_y === "number" ? n.position_y : 160,
      action: typeof n.action === "string" ? n.action : undefined,
      inputs: (n.inputs as Record<string, unknown>) || {},
    })),
    edges: (parsed.edges as DagEdgeDef[]).filter(
      (e) => e && typeof e.source === "string" && typeof e.target === "string"
    ),
  };
}
