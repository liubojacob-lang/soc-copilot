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
  config?: Record<string, unknown>;
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

export interface ActionTypeMeta {
  type: string;
  nameZh: string;
  nameEn: string;
  category: "intel" | "decision" | "action" | "data";
  categoryZh: string;
  categoryEn: string;
  descriptionZh: string;
  descriptionEn: string;
  defaultInputs: Record<string, unknown>;
}

export const ACTION_TYPE_META: Record<string, ActionTypeMeta> = {
  extract_iocs: {
    type: "extract_iocs",
    nameZh: "提取 IOC 实体",
    nameEn: "Extract IOCs",
    category: "intel",
    categoryZh: "威胁情报",
    categoryEn: "Threat Intel",
    descriptionZh: "从告警正文或日志中正则提取 IP、域名、哈希、URL 或邮箱",
    descriptionEn: "Extract IPs, domains, hashes, URLs or emails from alert body",
    defaultInputs: {
      source_field: "$.input.alert_body",
      ioc_types: ["ip", "domain", "url", "email"],
    },
  },
  ti_lookup_otx: {
    type: "ti_lookup_otx",
    nameZh: "OTX 威胁情报比对",
    nameEn: "OTX TI Lookup",
    category: "intel",
    categoryZh: "威胁情报",
    categoryEn: "Threat Intel",
    descriptionZh: "查询 AlienVault OTX 威胁情报库比对恶意置信度与脉冲历史",
    descriptionEn: "Query AlienVault OTX for malicious score and pulse history",
    defaultInputs: {
      pulse_expiration_days: 180,
      min_confidence: 75,
    },
  },
  asset_enrich: {
    type: "asset_enrich",
    nameZh: "资产信誉富化",
    nameEn: "Asset Enrichment",
    category: "intel",
    categoryZh: "威胁情报",
    categoryEn: "Threat Intel",
    descriptionZh: "关联内部资产台账、责任人、网段暴露面与已知漏洞历史",
    descriptionEn: "Enrich internal asset owner, subnet exposure and known vulnerabilities",
    defaultInputs: {
      lookup_key: "$.output.iocs[0]",
    },
  },
  decision: {
    type: "decision",
    nameZh: "条件分支决策",
    nameEn: "Decision Branch",
    category: "decision",
    categoryZh: "逻辑控制",
    categoryEn: "Control Flow",
    descriptionZh: "根据表达式对上游节点执行结果进行真假判定并分发流转",
    descriptionEn: "Evaluate condition expression to route downstream execution",
    defaultInputs: {
      expression: "$.output.ti.malicious_count >= 2",
    },
  },
  human_approval: {
    type: "human_approval",
    nameZh: "人工二次复核审批",
    nameEn: "Human Approval",
    category: "decision",
    categoryZh: "逻辑控制",
    categoryEn: "Control Flow",
    descriptionZh: "暂停执行流程并向值班安全专家发送审批挂起请求",
    descriptionEn: "Pause execution and request manual approval from security analyst",
    defaultInputs: {
      approvers: ["admin"],
      timeout_minutes: 30,
    },
  },
  sleep: {
    type: "sleep",
    nameZh: "延时等待",
    nameEn: "Delay / Sleep",
    category: "decision",
    categoryZh: "逻辑控制",
    categoryEn: "Control Flow",
    descriptionZh: "暂停流程指定秒数后继续执行下一环节",
    descriptionEn: "Pause workflow for specified duration before next step",
    defaultInputs: {
      seconds: 10,
    },
  },
  http_request: {
    type: "http_request",
    nameZh: "执行 HTTP / API 请求",
    nameEn: "HTTP / Webhook Request",
    category: "action",
    categoryZh: "响应动作",
    categoryEn: "Actions",
    descriptionZh: "向防火墙、堡垒机或微服务下发封禁、隔离等 API 操作",
    descriptionEn: "Send HTTP requests to firewall, bastion or microservices",
    defaultInputs: {
      method: "POST",
      url: "https://api.internal/v1/rules/blacklist",
      timeout: 10,
    },
  },
  slack_notify: {
    type: "slack_notify",
    nameZh: "即时协同告警通知",
    nameEn: "Alert Notification",
    category: "action",
    categoryZh: "响应动作",
    categoryEn: "Actions",
    descriptionZh: "向企业微信、飞书、Slack 或邮件网关推送协同响应消息",
    descriptionEn: "Push response notifications to Slack, Feishu, Teams or Email",
    defaultInputs: {
      webhook_url_env: "SLACK_SOC_WEBHOOK",
      message: "告警自动化已处置: {{$.output.blocked}}",
    },
  },
  generate_report: {
    type: "generate_report",
    nameZh: "处置归档报告生成",
    nameEn: "Generate Report",
    category: "action",
    categoryZh: "响应动作",
    categoryEn: "Actions",
    descriptionZh: "聚合全链路执行证据与动作记录，生成格式化结案通报",
    descriptionEn: "Aggregate incident evidence into a structured incident report",
    defaultInputs: {
      template: "standard_incident_summary",
    },
  },
  parse_json: {
    type: "parse_json",
    nameZh: "结构化数据解析",
    nameEn: "Parse JSON Data",
    category: "data",
    categoryZh: "数据处理",
    categoryEn: "Data Processing",
    descriptionZh: "提取并标准化源告警报文中的关键字段与元数据",
    descriptionEn: "Extract and normalize key fields and metadata from payload",
    defaultInputs: {
      source_field: "$.input",
    },
  },
};

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
